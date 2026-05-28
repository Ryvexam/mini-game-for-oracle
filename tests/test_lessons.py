from __future__ import annotations

from backend.db.oracle_object_repository import SQL_CHALLENGE


def test_sql_challenge_contains_real_oracle_object_code() -> None:
    assert "CREATE TYPE resource_node_t AS OBJECT" in SQL_CHALLENGE.sql_code
    assert "MEMBER FUNCTION harvest_amount RETURN NUMBER" in SQL_CHALLENGE.sql_code
    assert SQL_CHALLENGE.choices[1] == "MEMBER FUNCTION harvest_amount RETURN NUMBER"
