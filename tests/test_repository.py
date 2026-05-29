from __future__ import annotations

from backend.db.oracle_object_repository import (
    generate_tiles,
    generated_resources,
    split_oracle_script,
    validate_identifier,
    validate_pseudo,
)


def test_split_oracle_script_handles_slash_blocks() -> None:
    script = """
SET DEFINE OFF
CREATE TYPE demo_t AS OBJECT (name VARCHAR2(10));
/
BEGIN
  NULL;
END;
/
"""
    statements = split_oracle_script(script)
    assert len(statements) == 2
    assert statements[0].startswith("CREATE TYPE demo_t")
    assert statements[1].startswith("BEGIN")
    assert statements[1].endswith("END;")


def test_split_oracle_script_keeps_update_set_inside_blocks() -> None:
    script = """
SET DEFINE OFF
BEGIN
  UPDATE game_players
  SET x = 10,
      y = 20
  WHERE id = 'test';
END;
/
"""
    statements = split_oracle_script(script)
    assert "SET x = 10" in statements[0]


def test_validate_identifier_rejects_sql_like_input() -> None:
    try:
        validate_identifier("object-type'; drop table x; --")
    except ValueError:
        return
    raise AssertionError("identifier should have been rejected")


def test_validate_pseudo_rejects_sql_like_input() -> None:
    try:
        validate_pseudo("max'; drop table game_players; --")
    except ValueError:
        return
    raise AssertionError("pseudo should have been rejected")


def test_validate_pseudo_accepts_french_letters() -> None:
    validate_pseudo("Renée-42")


def test_chunk_generation_is_deterministic() -> None:
    assert generate_tiles(2, -3) == generate_tiles(2, -3)
    assert len(generate_tiles(0, 0)) == 8


def test_chunk_generation_contains_coherent_features() -> None:
    joined = "".join(
        "".join(generate_tiles(chunk_x, chunk_y))
        for chunk_y in range(-4, 5)
        for chunk_x in range(-4, 5)
    )
    assert "w" in joined
    assert "v" in joined
    assert "d" in joined


def test_rivers_are_not_too_wide() -> None:
    for chunk_x in range(-2, 3):
        for chunk_y in range(-2, 3):
            for row in generate_tiles(chunk_x, chunk_y):
                assert "www" not in row


def test_generated_resources_include_forest_clusters() -> None:
    resources = [
        resource
        for chunk_y in range(-4, 5)
        for chunk_x in range(-4, 5)
        for resource in generated_resources(chunk_x, chunk_y)
    ]
    tree_count = sum(1 for resource in resources if resource.kind == "tree")
    assert tree_count >= 20
