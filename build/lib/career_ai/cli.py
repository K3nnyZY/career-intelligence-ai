import argparse
import json
from pathlib import Path
from career_ai.core import pipeline, match

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/sample_jobs.json")
    parser.add_argument("--profile", default="data/sample_profile.json")
    parser.add_argument("--output", default="out/analysis.json")
    args = parser.parse_args()
    result = pipeline(json.loads(Path(args.input).read_text()))
    profile = json.loads(Path(args.profile).read_text())["skills"]
    for job in result["jobs"]:
        job["match"] = match(job, profile)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result["quality"]))

if __name__ == "__main__":
    main()
