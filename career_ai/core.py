import hashlib
import json
import re
from collections import Counter

ALIASES = {
    "python": ["python"], "sql": ["sql"], "databricks": ["databricks"],
    "pyspark": ["pyspark"], "delta lake": ["delta lake"],
    "mlflow": ["mlflow"], "rag": ["rag", "retrieval augmented generation"],
    "langgraph": ["langgraph"], "aws": ["aws", "amazon web services"],
    "fastapi": ["fastapi"], "docker": ["docker"],
    "machine learning": ["machine learning", "aprendizaje automático"],
    "llm": ["llm", "llms", "large language models"],
    "spark": ["spark", "apache spark"], "airflow": ["airflow", "apache airflow"],
    "dbt": ["dbt"], "kafka": ["kafka", "apache kafka"],
    "azure": ["azure", "microsoft azure"],
    "gcp": ["gcp", "google cloud", "google cloud platform"],
    "snowflake": ["snowflake"], "postgresql": ["postgresql", "postgres"],
    "git": ["git"], "terraform": ["terraform"],
    "kubernetes": ["kubernetes", "k8s"], "etl": ["etl", "elt"],
    "power bi": ["power bi", "powerbi"], "pandas": ["pandas"],
}
TAXONOMY_VERSION = hashlib.sha256(json.dumps(ALIASES, sort_keys=True).encode()).hexdigest()[:12]

def skills(text):
    return sorted(key for key, aliases in ALIASES.items() if any(
        re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text.casefold())
        for alias in aliases))

def normalize(row):
    if not isinstance(row, dict):
        raise ValueError("Job must be an object")
    clean = {}
    for key in ("title", "company", "description"):
        value = row.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Missing or invalid {key}")
        clean[key] = " ".join(value.split())
    clean["source_url"] = row.get("source_url", "")
    identity = "\0".join(clean[k].casefold() for k in ("company", "title", "description"))
    clean["job_id"] = hashlib.sha256(identity.encode()).hexdigest()
    clean["skills"] = skills(clean["description"])
    return clean

def match(job, profile):
    known = set(skills(" ".join(profile)))
    required = set(job["skills"])
    return {"matched_skills": sorted(required & known),
            "missing_skills": sorted(required - known),
            "skill_coverage": round(len(required & known) / len(required), 4) if required else None,
            "method": "keyword_mentions_v1"}

def pipeline(rows):
    unique, rejected = {}, []
    for index, row in enumerate(rows):
        try:
            job = normalize(row)
            unique[job["job_id"]] = job
        except ValueError as exc:
            rejected.append({"row_index": index, "reason": str(exc)})
    counts = Counter(skill for job in unique.values() for skill in job["skills"])
    return {"schema_version": "1.0", "extractor_version": "keyword_mentions_v1",
            "taxonomy_version": TAXONOMY_VERSION,
            "jobs": list(unique.values()), "skill_demand": dict(sorted(counts.items())),
            "quality": {"input_rows": len(rows), "accepted_unique": len(unique),
                        "rejected_rows": len(rejected),
                        "duplicates": len(rows)-len(rejected)-len(unique)},
            "rejected": rejected}
