import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BADCASES_PATH = ROOT / "docs" / "badcases.json"


def test_badcases_have_query_and_expected_answer():
    data = json.loads(BADCASES_PATH.read_text(encoding="utf-8"))
    badcases = data["badcases"]

    assert badcases
    seen_ids = set()
    for case in badcases:
        assert case["id"].startswith("BC-")
        assert case["id"] not in seen_ids
        seen_ids.add(case["id"])
        assert case["query"].strip()
        assert case["expected_answer"].strip()
        assert case["actual_answer"].strip()
        assert case["status"] in {"open", "fixed", "wont_fix"}
