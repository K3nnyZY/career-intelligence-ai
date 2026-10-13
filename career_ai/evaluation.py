"""Offline labeled-corpus evaluation. Reports contain IDs and labels, never CV text."""
import argparse
import hashlib
import json
import math
import time
from pathlib import Path

from career_ai.documents import DocumentError, extract_document
from career_ai.evidence import EXTRACTOR_VERSION, TAXONOMY_VERSION, compare, extract_profile, mentions


def percentile(values, fraction):
    if not values:
        return None
    values = sorted(values)
    return round(values[max(0, math.ceil(len(values) * fraction) - 1)], 3)


def metrics(tp, fp, fn):
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    return {"true_positives": tp, "false_positives": fp, "false_negatives": fn,
            "precision": precision, "recall": recall, "f1": f1}


def validate_dataset(dataset):
    if not isinstance(dataset, dict) or dataset.get("schema_version") != "1.0":
        raise ValueError("Dataset: schema_version debe ser 1.0.")
    if not isinstance(dataset.get("dataset_id"), str) or not dataset["dataset_id"].strip():
        raise ValueError("Dataset: falta dataset_id.")
    cases = dataset.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Dataset: cases debe ser una lista no vacía.")
    ids = set()
    for case in cases:
        if not isinstance(case, dict) or case.get("kind") not in {"cv", "vacancy"}:
            raise ValueError("Dataset: kind debe ser cv o vacancy.")
        identity = case.get("case_id")
        if not isinstance(identity, str) or not identity or identity in ids:
            raise ValueError("Dataset: case_id vacío o duplicado.")
        ids.add(identity)
        if ("text" in case) == ("file" in case):
            raise ValueError("Dataset: cada caso necesita text o file, exclusivamente.")
        for field in ("text", "file"):
            if field in case and not isinstance(case[field], str):
                raise ValueError("Dataset: text/file deben ser cadenas.")
        expected = case.get("expected_skills")
        if not isinstance(expected, list) or not all(isinstance(item, str) and item.strip() for item in expected) or len(set(expected)) != len(expected):
            raise ValueError("Dataset: expected_skills debe contener etiquetas únicas no vacías.")
        source = case.get("source", {})
        if not isinstance(source, dict) or source.get("type") not in {"synthetic", "real"}:
            raise ValueError("Dataset: falta source.type (synthetic o real).")
        if source["type"] == "real" and (source.get("permission") != "authorized" or not source.get("reference") or not source.get("captured_at")):
            raise ValueError("Dataset: un caso real requiere procedencia, fecha y permiso autorizado.")
        labels = case.get("expected_requirements")
        if labels is not None and (case["kind"] != "vacancy" or not isinstance(labels, dict) or
                                   set(labels) != set(expected) or any(label not in {"required", "desirable", "unspecified"} for label in labels.values())):
            raise ValueError("Dataset: expected_requirements debe etiquetar todas las habilidades de una vacante.")
    comparisons = dataset.get("comparisons", [])
    if not isinstance(comparisons, list):
        raise ValueError("Dataset: comparisons debe ser una lista.")
    kinds = {case["case_id"]: case["kind"] for case in cases}
    gold_skills = {case["case_id"]: set(case["expected_skills"]) for case in cases}
    for comparison in comparisons:
        if not isinstance(comparison, dict) or kinds.get(comparison.get("cv_id")) != "cv" or kinds.get(comparison.get("vacancy_id")) != "vacancy":
            raise ValueError("Dataset: comparación con referencias inválidas.")
        identity = comparison.get("comparison_id")
        if not isinstance(identity, str) or not identity or identity in ids:
            raise ValueError("Dataset: comparison_id vacío o duplicado.")
        ids.add(identity)
        for key in ("expected_matched", "expected_missing"):
            values = comparison.get(key)
            if not isinstance(values, list) or not all(isinstance(value, str) and value.strip() for value in values) or len(set(values)) != len(values):
                raise ValueError("Dataset: comparación sin etiquetas esperadas válidas.")
        if set(comparison["expected_matched"]) & set(comparison["expected_missing"]):
            raise ValueError("Dataset: etiquetas de comparación contradictorias.")
        if set(comparison["expected_matched"]) | set(comparison["expected_missing"]) != gold_skills[comparison["vacancy_id"]]:
            raise ValueError("Dataset: cada comparación debe cubrir todas las habilidades etiquetadas de su vacante.")


def evaluate(dataset, base_dir):
    validate_dataset(dataset)
    results, latencies, texts = [], [], {}
    totals = {"cv": [0, 0, 0], "vacancy": [0, 0, 0]}
    requirement_correct = requirement_total = 0
    errors = 0
    for case in dataset["cases"]:
        start = time.perf_counter()
        row = {"case_id": case["case_id"], "kind": case["kind"]}
        try:
            if "file" in case:
                path = (base_dir / case["file"]).resolve()
                # Keep documents within the private dataset directory; no arbitrary file reads.
                if not path.is_relative_to(base_dir.resolve()):
                    raise ValueError("unsafe_path")
                with path.open("rb") as handle:
                    from career_ai.documents import MAX_FILE_BYTES
                    content = handle.read(MAX_FILE_BYTES + 1)
                text = extract_document(content, path.suffix.lower().lstrip("."))["text"]
            else:
                text = case["text"]
            if case["kind"] == "cv":
                predicted = set(extract_profile(text)["skills"])
                labels = {}
            else:
                evidence = [item for item in mentions(text, vacancy=True) if item["requirement"] != "excluded"]
                predicted = {item["skill"] for item in evidence}
                rank = {"unspecified": 0, "desirable": 1, "required": 2}
                labels = {skill: max((item["requirement"] for item in evidence if item["skill"] == skill), key=rank.get) for skill in predicted}
            texts[case["case_id"]] = text
            gold = set(case["expected_skills"])
            tp, fp, fn = len(predicted & gold), len(predicted - gold), len(gold - predicted)
            for index, value in enumerate((tp, fp, fn)):
                totals[case["kind"]][index] += value
            row.update(metrics(tp, fp, fn), omitted=sorted(gold - predicted), incorrect=sorted(predicted - gold))
            expected_labels = case.get("expected_requirements", {})
            requirement_total += len(expected_labels)
            requirement_correct += sum(labels.get(skill) == label for skill, label in expected_labels.items())
            row["requirement_errors"] = [{"skill": skill, "expected": label, "predicted": labels.get(skill)}
                                         for skill, label in expected_labels.items() if labels.get(skill) != label]
        except (DocumentError, OSError, ValueError) as exc:
            errors += 1
            row["error"] = exc.code if isinstance(exc, DocumentError) else "read_or_contract_error"
            # Failed files still contribute omissions, so recall cannot improve by skipping them.
            totals[case["kind"]][2] += len(case["expected_skills"])
            requirement_total += len(case.get("expected_requirements", {}))
        elapsed = (time.perf_counter() - start) * 1000
        latencies.append(elapsed)
        row["latency_ms"] = round(elapsed, 3)
        results.append(row)
    comparison_results, matching_totals = [], [0, 0, 0]
    exact = matching_errors = 0
    matching_latencies = []
    for case in dataset.get("comparisons", []):
        started = time.perf_counter()
        row = {"comparison_id": case["comparison_id"]}
        try:
            result = compare(texts[case["cv_id"]], texts[case["vacancy_id"]])
            matched = {item["skill"] for item in result["skills"] if item["status"] == "matched"}
            missing = {item["skill"] for item in result["skills"] if item["status"] == "missing_evidence"}
            gold = set(case["expected_matched"])
            for index, value in enumerate((len(matched & gold), len(matched - gold), len(gold - matched))):
                matching_totals[index] += value
            passed = matched == gold and missing == set(case["expected_missing"])
            exact += passed
            row.update(exact_match=passed, false_matches=sorted(matched - gold), missed_matches=sorted(gold - matched),
                       missing_label_errors=sorted(missing ^ set(case["expected_missing"])))
        except (KeyError, ValueError):
            row["error"] = "unavailable_or_invalid_text"
            matching_errors += 1
            matching_totals[2] += len(case["expected_matched"])
        elapsed = (time.perf_counter() - started) * 1000
        row["latency_ms"] = round(elapsed, 3)
        matching_latencies.append(elapsed)
        comparison_results.append(row)
    tp, fp, fn = (sum(values[index] for values in totals.values()) for index in range(3))
    return {"report_version": "1.0", "dataset_id": dataset["dataset_id"],
            "dataset_sha256": hashlib.sha256(json.dumps(dataset, sort_keys=True).encode()).hexdigest(),
            "extractor_version": EXTRACTOR_VERSION, "taxonomy_version": TAXONOMY_VERSION,
            "source_counts": {kind: sum(case["source"]["type"] == kind for case in dataset["cases"]) for kind in ("real", "synthetic")},
            "extraction": {**metrics(tp, fp, fn), "by_kind": {kind: metrics(*values) for kind, values in totals.items()},
                           "case_count": len(results), "error_count": errors,
                           "latency_ms": {"p50": percentile(latencies, .5), "p95": percentile(latencies, .95)},
                           "requirement_accuracy": requirement_correct / requirement_total if requirement_total else None,
                           "requirement_labels": requirement_total},
            "matching": {**metrics(*matching_totals), "comparison_count": len(comparison_results),
                         "exact_match_rate": exact / len(comparison_results) if comparison_results else None,
                         "error_count": matching_errors,
                         "latency_ms": {"p50": percentile(matching_latencies, .5), "p95": percentile(matching_latencies, .95)}},
            "cases": results, "comparisons": comparison_results}


def main():
    parser = argparse.ArgumentParser(description="Evalúa extracción y matching contra etiquetas manuales.")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path, default=Path("out/evaluation-report.json"))
    parser.add_argument("--require-real", action="store_true", help="Exige casos reales autorizados: >=20 vacantes y >=3 CV.")
    parser.add_argument("--min-precision", type=float, default=0)
    parser.add_argument("--min-recall", type=float, default=0)
    parser.add_argument("--min-match-exact", type=float, default=0)
    parser.add_argument("--min-requirement-accuracy", type=float, default=0)
    parser.add_argument("--max-errors", type=int, default=0)
    args = parser.parse_args()
    if any(not 0 <= value <= 1 for value in (args.min_precision, args.min_recall, args.min_match_exact, args.min_requirement_accuracy)) or args.max_errors < 0:
        parser.error("Umbrales fuera de rango.")
    try:
        dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
        validate_dataset(dataset)
        if args.require_real:
            real = [case for case in dataset["cases"] if case["source"]["type"] == "real"]
            if len(real) != len(dataset["cases"]) or sum(case["kind"] == "vacancy" for case in real) < 20 or sum(case["kind"] == "cv" for case in real) < 3 or len(dataset.get("comparisons", [])) < 20:
                parser.error("La validación real requiere >=20 vacantes, >=3 CV y >=20 comparaciones reales autorizadas, sin muestras sintéticas.")
        report = evaluate(dataset, args.dataset.parent)
    except (OSError, json.JSONDecodeError, ValueError):
        parser.error("No se pudo leer el dataset o su contrato es inválido. Consulta docs/evaluation.md.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Reports are private too; no raw text or document paths are written.
    with args.output.open("w", encoding="utf-8") as handle:
        args.output.chmod(0o600)
        json.dump(report, handle, indent=2, ensure_ascii=False)
    summary = report["extraction"]
    print(json.dumps({"extraction": summary, "matching": report["matching"]}, ensure_ascii=False))
    if (summary["error_count"] + report["matching"]["error_count"] > args.max_errors or
        (summary["precision"] is None and args.min_precision > 0) or
        (summary["recall"] is None and args.min_recall > 0) or
        (summary["precision"] or 0) < args.min_precision or
        (summary["recall"] or 0) < args.min_recall or
        (report["matching"]["exact_match_rate"] or 0) < args.min_match_exact or
        (summary["requirement_accuracy"] or 0) < args.min_requirement_accuracy):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
