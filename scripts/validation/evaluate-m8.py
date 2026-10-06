"""Evaluate an access-controlled expert record without echoing identities or transcripts."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services/api/src"))

from socrat.tutor.evaluation import TutorEvaluation, evaluate  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("record", type=Path)
args = parser.parse_args()
try:
    if args.record.stat().st_size > 5_000_000:
        raise ValueError("oversized record")
    report = evaluate(TutorEvaluation.model_validate_json(args.record.read_text(encoding="utf-8")))
except (ValueError, OSError):
    print("Invalid private evaluation record; inspect locally. No record contents were emitted.")
    raise SystemExit(2) from None
print(json.dumps(report, indent=2))
raise SystemExit(0 if report["recorded_evidence_ready"] else 1)
