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

        replay = case.get("replay")
        if replay:
            assert replay["cid"] > 0
            assert replay["message_id"] > 0
            assert replay.get("assistant_message_id", 1) > 0

            history_limit = replay.get("history_limit")
            assert history_limit is None or history_limit > 0

            endpoint = replay.get("endpoint")
            if endpoint:
                assert endpoint.startswith(("GET ", "POST "))
