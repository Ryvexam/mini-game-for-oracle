from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "backend" / "db" / "schema.sql").read_text(encoding="utf-8")
SEED = (ROOT / "backend" / "db" / "seed.sql").read_text(encoding="utf-8")


def test_schema_contains_game_oracle_object_features() -> None:
    required = [
        "CREATE OR REPLACE TYPE entity_t AS OBJECT",
        "CREATE OR REPLACE TYPE player_t UNDER entity_t",
        "OVERRIDING MEMBER PROCEDURE move_to",
        "MEMBER PROCEDURE gain_resource",
        "CREATE OR REPLACE TYPE resource_node_t AS OBJECT",
        "MEMBER FUNCTION harvest_amount RETURN NUMBER",
        "CREATE TABLE game_players OF player_t",
        "CREATE TABLE game_resource_nodes OF resource_node_t",
        "CREATE OR REPLACE PACKAGE game_actions_pkg",
    ]
    for snippet in required:
        assert snippet in SCHEMA


def test_schema_defines_stats_triggers_and_view() -> None:
    required = [
        "CREATE TABLE game_player_stats",
        "CREATE OR REPLACE TRIGGER trg_player_stats_create",
        "CREATE OR REPLACE TRIGGER trg_player_stats_resources",
        "CREATE OR REPLACE TRIGGER trg_player_stats_distance",
        "CREATE OR REPLACE TRIGGER trg_player_stats_sql",
        "CREATE OR REPLACE VIEW game_leaderboard",
        "AFTER UPDATE OF wood, stone, ore ON game_players",
    ]
    for snippet in required:
        assert snippet in SCHEMA


def test_seed_contains_spawn_game_entities() -> None:
    assert "npc_t('sage-oracle'" in SEED
    assert "resource_node_t('spawn-rock-1'" in SEED
    assert "resource_node_t('spawn-tree-1'" in SEED


def test_no_credentials_in_sql() -> None:
    forbidden = ["MonPassword", "CoursObjet", "ORACLE_PASSWORD", "localhost:1521"]
    for value in forbidden:
        assert value not in SCHEMA
        assert value not in SEED
