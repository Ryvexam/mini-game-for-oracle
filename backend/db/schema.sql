SET DEFINE OFF

BEGIN
  EXECUTE IMMEDIATE 'DROP VIEW game_leaderboard';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP TABLE game_player_stats PURGE';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP TABLE game_sql_challenges PURGE';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP TABLE game_sql_answers PURGE';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP TABLE game_player_quests PURGE';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP TABLE game_resource_nodes PURGE';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP TABLE game_chests PURGE';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP TABLE game_npcs PURGE';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP TABLE game_players PURGE';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP TABLE game_world_meta PURGE';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP TYPE action_result_t FORCE';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP TYPE player_t FORCE';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP TYPE resource_node_t FORCE';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP TYPE chest_t FORCE';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP TYPE npc_t FORCE';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

BEGIN
  EXECUTE IMMEDIATE 'DROP TYPE entity_t FORCE';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

CREATE OR REPLACE TYPE entity_t AS OBJECT (
  id VARCHAR2(80),
  display_name VARCHAR2(80),
  x NUMBER,
  y NUMBER,
  MEMBER PROCEDURE move_to(new_x NUMBER, new_y NUMBER)
) NOT FINAL;
/

CREATE OR REPLACE TYPE BODY entity_t AS
  MEMBER PROCEDURE move_to(new_x NUMBER, new_y NUMBER) IS
  BEGIN
    x := new_x;
    y := new_y;
  END;
END;
/

CREATE OR REPLACE TYPE player_t UNDER entity_t (
  skin_id VARCHAR2(40),
  wood NUMBER,
  stone NUMBER,
  ore NUMBER,
  OVERRIDING MEMBER PROCEDURE move_to(new_x NUMBER, new_y NUMBER),
  MEMBER PROCEDURE gain_resource(resource_kind VARCHAR2, amount NUMBER)
);
/

CREATE OR REPLACE TYPE BODY player_t AS
  OVERRIDING MEMBER PROCEDURE move_to(new_x NUMBER, new_y NUMBER) IS
  BEGIN
    x := new_x;
    y := new_y;
  END;

  MEMBER PROCEDURE gain_resource(resource_kind VARCHAR2, amount NUMBER) IS
  BEGIN
    IF resource_kind = 'wood' THEN
      wood := wood + amount;
    ELSIF resource_kind = 'stone' THEN
      stone := stone + amount;
    ELSIF resource_kind = 'ore' THEN
      ore := ore + amount;
    END IF;
  END;
END;
/

CREATE OR REPLACE TYPE npc_t UNDER entity_t (
  role VARCHAR2(40),
  quest_marker VARCHAR2(2)
);
/

CREATE OR REPLACE TYPE resource_node_t AS OBJECT (
  id VARCHAR2(80),
  kind VARCHAR2(20),
  x NUMBER,
  y NUMBER,
  amount NUMBER,
  MEMBER FUNCTION harvest_amount RETURN NUMBER
);
/

CREATE OR REPLACE TYPE BODY resource_node_t AS
  MEMBER FUNCTION harvest_amount RETURN NUMBER IS
  BEGIN
    IF amount <= 0 THEN
      RETURN 0;
    END IF;
    RETURN LEAST(1, amount);
  END;
END;
/

CREATE OR REPLACE TYPE action_result_t AS OBJECT (
  ok NUMBER,
  message VARCHAR2(240),
  resource_kind VARCHAR2(20),
  amount NUMBER
);
/

CREATE OR REPLACE TYPE chest_t AS OBJECT (
  id VARCHAR2(80),
  owner VARCHAR2(24),
  x NUMBER,
  y NUMBER,
  wood NUMBER,
  stone NUMBER,
  ore NUMBER,
  MEMBER PROCEDURE store(resource_kind VARCHAR2, qty NUMBER),
  MEMBER FUNCTION total RETURN NUMBER
);
/

CREATE OR REPLACE TYPE BODY chest_t AS
  MEMBER PROCEDURE store(resource_kind VARCHAR2, qty NUMBER) IS
  BEGIN
    IF resource_kind = 'wood' THEN
      wood := wood + qty;
    ELSIF resource_kind = 'stone' THEN
      stone := stone + qty;
    ELSIF resource_kind = 'ore' THEN
      ore := ore + qty;
    END IF;
  END;

  MEMBER FUNCTION total RETURN NUMBER IS
  BEGIN
    RETURN NVL(wood, 0) + NVL(stone, 0) + NVL(ore, 0);
  END;
END;
/

CREATE TABLE game_world_meta (
  id NUMBER PRIMARY KEY,
  seed NUMBER NOT NULL
);
/

INSERT INTO game_world_meta (id, seed) VALUES (1, 73244475);
/

CREATE TABLE game_players OF player_t (
  CONSTRAINT game_players_pk PRIMARY KEY (id)
);
/

CREATE TABLE game_npcs OF npc_t (
  CONSTRAINT game_npcs_pk PRIMARY KEY (id)
);
/

CREATE TABLE game_resource_nodes OF resource_node_t (
  CONSTRAINT game_resource_nodes_pk PRIMARY KEY (id)
);
/

CREATE TABLE game_chests OF chest_t (
  CONSTRAINT game_chests_pk PRIMARY KEY (id),
  CONSTRAINT game_chests_owner_fk FOREIGN KEY (owner) REFERENCES game_players(id)
);
/

CREATE TABLE game_player_quests (
  pseudo VARCHAR2(24 CHAR) PRIMARY KEY,
  quest_id VARCHAR2(80) NOT NULL,
  step_index NUMBER DEFAULT 0 NOT NULL,
  step_progress NUMBER DEFAULT 0 NOT NULL,
  updated_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
  CONSTRAINT game_player_quests_player_fk FOREIGN KEY (pseudo) REFERENCES game_players(id)
);
/

CREATE TABLE game_sql_challenges (
  id VARCHAR2(80) PRIMARY KEY,
  prompt VARCHAR2(400) NOT NULL,
  sql_code VARCHAR2(1000) NOT NULL,
  choice_1 VARCHAR2(200) NOT NULL,
  choice_2 VARCHAR2(200) NOT NULL,
  choice_3 VARCHAR2(200) NOT NULL,
  correct_index NUMBER NOT NULL
);
/

CREATE TABLE game_sql_answers (
  pseudo VARCHAR2(24 CHAR) NOT NULL,
  challenge_id VARCHAR2(80) NOT NULL,
  is_correct NUMBER(1) DEFAULT 0 NOT NULL,
  answered_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
  CONSTRAINT game_sql_answers_pk PRIMARY KEY (pseudo, challenge_id),
  CONSTRAINT game_sql_answers_player_fk FOREIGN KEY (pseudo) REFERENCES game_players(id)
);
/

CREATE TABLE game_player_stats (
  pseudo VARCHAR2(24 CHAR) PRIMARY KEY,
  wood_gathered NUMBER DEFAULT 0 NOT NULL,
  stone_gathered NUMBER DEFAULT 0 NOT NULL,
  ore_gathered NUMBER DEFAULT 0 NOT NULL,
  harvest_actions NUMBER DEFAULT 0 NOT NULL,
  distance_moved NUMBER DEFAULT 0 NOT NULL,
  sql_attempts NUMBER DEFAULT 0 NOT NULL,
  sql_correct NUMBER DEFAULT 0 NOT NULL,
  joined_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
  updated_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
  CONSTRAINT game_player_stats_player_fk FOREIGN KEY (pseudo) REFERENCES game_players(id)
);
/

-- Create a stats row whenever a new player object is inserted.
CREATE OR REPLACE TRIGGER trg_player_stats_create
AFTER INSERT ON game_players
FOR EACH ROW
BEGIN
  INSERT INTO game_player_stats (pseudo) VALUES (:NEW.id);
END;
/

-- Accumulate gathered resources and harvest count from inventory growth.
CREATE OR REPLACE TRIGGER trg_player_stats_resources
AFTER UPDATE OF wood, stone, ore ON game_players
FOR EACH ROW
DECLARE
  v_wood NUMBER := GREATEST(NVL(:NEW.wood, 0) - NVL(:OLD.wood, 0), 0);
  v_stone NUMBER := GREATEST(NVL(:NEW.stone, 0) - NVL(:OLD.stone, 0), 0);
  v_ore NUMBER := GREATEST(NVL(:NEW.ore, 0) - NVL(:OLD.ore, 0), 0);
BEGIN
  IF v_wood + v_stone + v_ore > 0 THEN
    UPDATE game_player_stats
    SET wood_gathered = wood_gathered + v_wood,
        stone_gathered = stone_gathered + v_stone,
        ore_gathered = ore_gathered + v_ore,
        harvest_actions = harvest_actions + 1,
        updated_at = SYSTIMESTAMP
    WHERE pseudo = :NEW.id;
  END IF;
END;
/

-- Track total distance walked from position updates.
CREATE OR REPLACE TRIGGER trg_player_stats_distance
AFTER UPDATE OF x, y ON game_players
FOR EACH ROW
DECLARE
  v_step NUMBER := SQRT(POWER(NVL(:NEW.x, 0) - NVL(:OLD.x, 0), 2)
                      + POWER(NVL(:NEW.y, 0) - NVL(:OLD.y, 0), 2));
BEGIN
  IF v_step > 0 THEN
    UPDATE game_player_stats
    SET distance_moved = distance_moved + v_step,
        updated_at = SYSTIMESTAMP
    WHERE pseudo = :NEW.id;
  END IF;
END;
/

-- Count SQL challenge attempts and correct answers.
CREATE OR REPLACE TRIGGER trg_player_stats_sql
AFTER INSERT OR UPDATE ON game_sql_answers
FOR EACH ROW
BEGIN
  UPDATE game_player_stats
  SET sql_attempts = sql_attempts + 1,
      sql_correct = sql_correct + NVL(:NEW.is_correct, 0),
      updated_at = SYSTIMESTAMP
  WHERE pseudo = :NEW.pseudo;
END;
/

CREATE OR REPLACE VIEW game_leaderboard AS
SELECT s.pseudo,
       s.wood_gathered,
       s.stone_gathered,
       s.ore_gathered,
       s.harvest_actions,
       s.distance_moved,
       s.sql_attempts,
       s.sql_correct,
       (s.wood_gathered + s.stone_gathered + s.ore_gathered) AS total_gathered,
       RANK() OVER (
         ORDER BY (s.wood_gathered + s.stone_gathered + s.ore_gathered) DESC
       ) AS rank_position
FROM game_player_stats s;
/

CREATE OR REPLACE PACKAGE game_actions_pkg AS
  FUNCTION create_or_get_player(
    p_pseudo VARCHAR2,
    p_skin_id VARCHAR2
  ) RETURN player_t;

  FUNCTION move_player(
    p_pseudo VARCHAR2,
    p_x NUMBER,
    p_y NUMBER
  ) RETURN player_t;

  FUNCTION harvest_resource(
    p_pseudo VARCHAR2,
    p_target_id VARCHAR2
  ) RETURN action_result_t;

  FUNCTION answer_sql_challenge(
    p_pseudo VARCHAR2,
    p_challenge_id VARCHAR2,
    p_answer_index NUMBER
  ) RETURN action_result_t;

  FUNCTION deposit_resources(
    p_pseudo VARCHAR2,
    p_chest_id VARCHAR2
  ) RETURN action_result_t;
END game_actions_pkg;
/

CREATE OR REPLACE PACKAGE BODY game_actions_pkg AS
  FUNCTION create_or_get_player(
    p_pseudo VARCHAR2,
    p_skin_id VARCHAR2
  ) RETURN player_t IS
    v_player player_t;
  BEGIN
    BEGIN
      SELECT VALUE(p) INTO v_player
      FROM game_players p
      WHERE p.id = p_pseudo;
      RETURN v_player;
    EXCEPTION
      WHEN NO_DATA_FOUND THEN
        v_player := player_t(
          p_pseudo,
          p_pseudo,
          240,
          300,
          NVL(p_skin_id, 'player'),
          0,
          0,
          0
        );
        INSERT INTO game_players VALUES (v_player);
        INSERT INTO game_player_quests (pseudo, quest_id, step_index)
        VALUES (p_pseudo, 'oracle-village-initiation', 0);
        RETURN v_player;
    END;
  END;

  FUNCTION move_player(
    p_pseudo VARCHAR2,
    p_x NUMBER,
    p_y NUMBER
  ) RETURN player_t IS
    v_player player_t;
  BEGIN
    SELECT VALUE(p) INTO v_player
    FROM game_players p
    WHERE p.id = p_pseudo
    FOR UPDATE;

    v_player.move_to(p_x, p_y);

    UPDATE game_players p
    SET x = v_player.x,
        y = v_player.y
    WHERE p.id = p_pseudo;

    RETURN v_player;
  END;

  FUNCTION harvest_resource(
    p_pseudo VARCHAR2,
    p_target_id VARCHAR2
  ) RETURN action_result_t IS
    v_player player_t;
    v_node resource_node_t;
    v_amount NUMBER;
    v_resource VARCHAR2(20);
  BEGIN
    SELECT VALUE(p) INTO v_player
    FROM game_players p
    WHERE p.id = p_pseudo
    FOR UPDATE;

    SELECT VALUE(r) INTO v_node
    FROM game_resource_nodes r
    WHERE r.id = p_target_id
    FOR UPDATE;

    v_amount := v_node.harvest_amount();
    IF v_amount <= 0 THEN
      RETURN action_result_t(0, 'Cette ressource est épuisée.', v_node.kind, 0);
    END IF;

    v_node.amount := v_node.amount - v_amount;
    v_resource := CASE v_node.kind
      WHEN 'tree' THEN 'wood'
      WHEN 'rock' THEN 'stone'
      ELSE 'ore'
    END;
    v_player.gain_resource(v_resource, v_amount);

    UPDATE game_players p
    SET wood = v_player.wood,
        stone = v_player.stone,
        ore = v_player.ore
    WHERE p.id = p_pseudo;

    UPDATE game_resource_nodes r
    SET amount = v_node.amount
    WHERE r.id = p_target_id;

    RETURN action_result_t(1, 'Ressource récoltée.', v_resource, v_amount);
  END;

  FUNCTION answer_sql_challenge(
    p_pseudo VARCHAR2,
    p_challenge_id VARCHAR2,
    p_answer_index NUMBER
  ) RETURN action_result_t IS
    v_correct NUMBER := 0;
    v_expected NUMBER;
  BEGIN
    BEGIN
      SELECT correct_index INTO v_expected
      FROM game_sql_challenges
      WHERE id = p_challenge_id;
    EXCEPTION
      WHEN NO_DATA_FOUND THEN
        RETURN action_result_t(0, 'Défi SQL inconnu.', NULL, 0);
    END;

    IF p_answer_index = v_expected THEN
      v_correct := 1;
    END IF;

    UPDATE game_sql_answers
    SET is_correct = v_correct,
        answered_at = SYSTIMESTAMP
    WHERE pseudo = p_pseudo
      AND challenge_id = p_challenge_id;

    IF SQL%ROWCOUNT = 0 THEN
      INSERT INTO game_sql_answers (pseudo, challenge_id, is_correct)
      VALUES (p_pseudo, p_challenge_id, v_correct);
    END IF;

    IF v_correct = 1 THEN
      RETURN action_result_t(1, 'Bonne réponse SQL.', NULL, 0);
    END IF;

    RETURN action_result_t(0, 'Mauvaise réponse SQL. Relis le code.', NULL, 0);
  END;

  FUNCTION deposit_resources(
    p_pseudo VARCHAR2,
    p_chest_id VARCHAR2
  ) RETURN action_result_t IS
    v_player player_t;
    v_chest chest_t;
    v_total NUMBER;
  BEGIN
    SELECT VALUE(p) INTO v_player
    FROM game_players p
    WHERE p.id = p_pseudo
    FOR UPDATE;

    BEGIN
      SELECT VALUE(c) INTO v_chest
      FROM game_chests c
      WHERE c.id = p_chest_id
      FOR UPDATE;
    EXCEPTION
      WHEN NO_DATA_FOUND THEN
        RETURN action_result_t(0, 'Coffre introuvable.', NULL, 0);
    END;

    v_total := NVL(v_player.wood, 0) + NVL(v_player.stone, 0) + NVL(v_player.ore, 0);
    IF v_total <= 0 THEN
      RETURN action_result_t(0, 'Rien à déposer.', NULL, 0);
    END IF;

    v_chest.store('wood', NVL(v_player.wood, 0));
    v_chest.store('stone', NVL(v_player.stone, 0));
    v_chest.store('ore', NVL(v_player.ore, 0));

    UPDATE game_chests c
    SET wood = v_chest.wood,
        stone = v_chest.stone,
        ore = v_chest.ore
    WHERE c.id = p_chest_id;

    v_player.wood := 0;
    v_player.stone := 0;
    v_player.ore := 0;

    UPDATE game_players p
    SET wood = 0,
        stone = 0,
        ore = 0
    WHERE p.id = p_pseudo;

    RETURN action_result_t(1, 'Objets déposés dans le coffre.', NULL, v_total);
  END;
END game_actions_pkg;
/
