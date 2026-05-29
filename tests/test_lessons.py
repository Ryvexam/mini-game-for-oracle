from __future__ import annotations

from backend.db.oracle_object_repository import QUEST_CATALOG, QUEST_INDEX


def test_quest_catalog_is_a_consistent_chain() -> None:
    assert len(QUEST_CATALOG) >= 5
    ids = [quest["id"] for quest in QUEST_CATALOG]
    assert len(ids) == len(set(ids))
    assert QUEST_INDEX[QUEST_CATALOG[0]["id"]] == 0


def test_sql_steps_reference_challenge_ids() -> None:
    for quest in QUEST_CATALOG:
        for step in quest["steps"]:
            if step["kind"] == "sql":
                assert step.get("challenge_id"), f"missing challenge_id in {quest['id']}"
