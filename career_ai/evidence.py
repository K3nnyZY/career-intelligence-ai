"""Deterministic extraction. Offsets always refer to the supplied, unmodified text."""
import re

from career_ai.core import ALIASES, TAXONOMY_VERSION

EXTRACTOR_VERSION = "evidence_rules_v1"
MAX_TEXT = 100_000
PATTERNS = {
    skill: re.compile(r"(?<!\w)(?:" + "|".join(
        re.escape(alias) for alias in sorted(aliases, key=len, reverse=True)
    ) + r")(?!\w)", re.IGNORECASE)
    for skill, aliases in ALIASES.items()
}
REQUIRED = re.compile(r"\b(?:required|requirements|must|mandatory|essential|requisitos|obligatori[oa]s?|indispensable|imprescindible|se requiere|necesario)\b", re.I)
DESIRABLE = re.compile(r"\b(?:preferred|desirable|nice[- ]to[- ]have|bonus|optional|plus|deseables?|deseable|valoramos|valorable|opcional)\b", re.I)
NEG_PREFIX = re.compile(r"\b(?:no\s+(?:se\s+)?(?:requiere|requerimos|necesita|necesitamos|tengo|tiene|poseo)|sin\s+(?:experiencia|conocimientos?)\s+(?:en|de)|(?:do\s+not|don't|does\s+not)\s+(?:require|have)|without\s+(?:experience\s+(?:in|with)|knowledge\s+of))\b", re.I)
NEG_SUFFIX = re.compile(r"^\s*(?:(?:is|are)\s+)?(?:not\s+(?:required|needed)|no\s+(?:es\s+)?(?:necesari[oa]|obligatori[oa]|requerid[oa]))\b", re.I)
ACTION = re.compile(r"\b(?:desarroll[eé]|implement[eé]|constru[ií]|diseñ[eé]|migr[eé]|optimic[eé]|automatic[eé]|lider[eé]|built|developed|implemented|designed|migrated|optimized|automated|led)\b", re.I)
HEADINGS = r"(?:required(?: skills| qualifications)?|requirements|mandatory|essential|requisitos(?: obligatorios)?|obligatorios|preferred(?: skills| qualifications)?|desirable|nice[- ]to[- ]have|bonus|optional|deseables|deseable|valoramos|opcional)"


def validate_text(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("El texto no puede estar vacío.")
    if len(text) > MAX_TEXT:
        raise ValueError(f"El texto supera {MAX_TEXT} caracteres.")


def segments(text):
    # Keep punctuation and newline boundaries without rewriting evidence.
    pattern = r"[^\n;.!?]+(?:[;.!?]|$)"
    for line in re.finditer(r"[^\n]+", text):
        for part in re.finditer(pattern, line.group()):
            # A contrast starts a new clause: 'No Python, pero SQL obligatorio'.
            start = line.start() + part.start()
            end = line.start() + part.end()
            cursor = start
            for contrast in re.finditer(r"\b(?:but|pero|sin embargo|although)\b", text[start:end], re.I):
                stop = start + contrast.start()
                if text[cursor:stop].strip():
                    yield cursor, stop
                cursor = start + contrast.end()
            if text[cursor:end].strip():
                yield cursor, end


def mentions(text, *, vacancy=False):
    validate_text(text)
    found = []
    section = "unspecified"
    for start, end in segments(text):
        quote = text[start:end]
        matches = sorted(
            [(m.start(), m.end(), skill) for skill, pattern in PATTERNS.items()
             for m in pattern.finditer(quote)], key=lambda x: (x[0], x[2])
        )
        required, desirable = bool(REQUIRED.search(quote)), bool(DESIRABLE.search(quote))
        local = "required" if required and not desirable else "desirable" if desirable and not required else None
        # Only a short, standalone heading sets the subsequent section.
        if local and (re.fullmatch(r"\s*[-*•]?\s*" + HEADINGS + r"\s*:?\s*", quote, re.I) or
                      re.match(r"\s*[-*•]?\s*" + HEADINGS + r"\s*:", quote, re.I)):
            section = local
        elif not matches and re.fullmatch(r"\s*(?:responsibilities|responsabilidades|benefits|beneficios|about us|sobre nosotros|funciones)\s*:?\s*", quote, re.I):
            section = "unspecified"
        for pos, stop, skill in matches:
            if len(found) >= 1000:
                raise ValueError("Hay demasiadas menciones de habilidades; reduce el texto a los fragmentos relevantes.")
            # Suffix negation must immediately follow this alias, never another skill.
            negated = bool(NEG_PREFIX.search(quote[:pos]) or NEG_SUFFIX.search(quote[stop:]))
            requirement = (local or section) if vacancy else "mentioned"
            if required and desirable:
                requirement = "unspecified" if vacancy else "mentioned"
            quote_begin, quote_finish = max(0, pos - 200), min(len(quote), stop + 200)
            found.append({
                "skill": skill, "matched_text": quote[pos:stop],
                "start": start + pos, "end": start + stop,
                "quote": quote[quote_begin:quote_finish],
                "quote_start": start + quote_begin, "quote_end": start + quote_finish,
                "requirement": "excluded" if negated else requirement,
            })
    return found


def extract_profile(text):
    evidence = mentions(text)
    active = [item for item in evidence if item["requirement"] != "excluded"]
    signals = []
    for start, end in segments(text):
        quote = text[start:end]
        if ACTION.search(quote):
            signals.append({"quote": quote, "start": start, "end": end,
                            "skills": sorted({item["skill"] for item in active
                                              if start <= item["start"] < end})})
    return {"text": text, "skills": sorted({item["skill"] for item in active}),
            "evidence": evidence, "experience_signals": signals,
            "extractor_version": EXTRACTOR_VERSION, "taxonomy_version": TAXONOMY_VERSION,
            "warnings": ["Revisa el texto, las habilidades y los fragmentos de experiencia. La extracción usa un diccionario; no verifica años, dominio ni seniority."]}


def compare(cv_text, vacancy_text, selected_skills=None):
    profile = extract_profile(cv_text)
    job_evidence = mentions(vacancy_text, vacancy=True)
    known = set(profile["skills"] if selected_skills is None else selected_skills)
    if not known <= set(profile["skills"]):
        raise ValueError("Las habilidades seleccionadas deben aparecer en el texto revisado del CV.")
    active = [item for item in job_evidence if item["requirement"] != "excluded"]
    rows = []
    for skill in sorted({item["skill"] for item in active}):
        evidence = [item for item in active if item["skill"] == skill]
        labels = {item["requirement"] for item in evidence}
        label = "required" if "required" in labels else "desirable" if "desirable" in labels else "unspecified"
        rows.append({"skill": skill, "requirement": label,
                     "status": "matched" if skill in known else "missing_evidence",
                     "vacancy_evidence": evidence,
                     "cv_evidence": [item for item in profile["evidence"]
                                     if item["skill"] == skill and skill in known
                                     and item["requirement"] != "excluded"]})
    groups = {}
    for label in ("required", "desirable", "unspecified"):
        items = [row for row in rows if row["requirement"] == label]
        matched = [row["skill"] for row in items if row["status"] == "matched"]
        groups[label] = {"matched": matched,
                         "missing_evidence": [row["skill"] for row in items if row["status"] != "matched"],
                         "coverage": round(len(matched) / len(items), 4) if items else None}
    matched = {row["skill"] for row in rows if row["status"] == "matched"}
    highlights = [dict(signal, relevant_skills=sorted(set(signal["skills"]) & matched))
                  for signal in profile["experience_signals"] if set(signal["skills"]) & matched]
    warnings = ["Cobertura de habilidades reconocidas; no es probabilidad de contratación.",
                "Sin evidencia significa que no se encontró una mención seleccionada en el CV revisado; no implica que carezcas de esa habilidad.",
                "Los requisitos se clasifican con reglas en español e inglés. Contextos ambiguos, alternativas y negaciones complejas necesitan revisión humana."]
    if not rows:
        warnings.append("No se reconocieron habilidades en la vacante; no hay cobertura calculable.")
    return {"schema_version": "1.0", "extractor_version": EXTRACTOR_VERSION,
            "taxonomy_version": TAXONOMY_VERSION, "evidence_source": "reviewed_cv_text",
            "groups": groups, "skills": rows, "highlights": highlights,
            "excluded_mentions": [item for item in job_evidence if item["requirement"] == "excluded"],
            "warnings": warnings}
