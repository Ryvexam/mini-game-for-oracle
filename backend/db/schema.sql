SET DEFINE OFF

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

CREATE TABLE game_player_quests (
  pseudo VARCHAR2(24 CHAR) PRIMARY KEY,
  quest_id VARCHAR2(80) NOT NULL,
  step_index NUMBER DEFAULT 0 NOT NULL,
  updated_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
  CONSTRAINT game_player_quests_player_fk FOREIGN KEY (pseudo) REFERENCES game_players(id)
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

    UPDATE game_player_quests
    SET step_index = CASE
      WHEN quest_id = 'oracle-village-initiation' AND step_index = 1 THEN 2
      ELSE step_index
    END,
    updated_at = SYSTIMESTAMP
    WHERE pseudo = p_pseudo;

    RETURN action_result_t(1, 'Ressource récoltée.', v_resource, v_amount);
  END;

  FUNCTION answer_sql_challenge(
    p_pseudo VARCHAR2,
    p_challenge_id VARCHAR2,
    p_answer_index NUMBER
  ) RETURN action_result_t IS
    v_correct NUMBER;
  BEGIN
    v_correct := CASE
      WHEN p_challenge_id = 'object-type-method' AND p_answer_index = 1 THEN 1
      ELSE 0
    END;

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
      UPDATE game_player_quests
      SET step_index = 3,
          updated_at = SYSTIMESTAMP
      WHERE pseudo = p_pseudo
        AND quest_id = 'oracle-village-initiation';
      RETURN action_result_t(1, 'Bonne réponse SQL. Quête terminée.', NULL, 0);
    END IF;

    RETURN action_result_t(0, 'Mauvaise réponse SQL. Relis le code.', NULL, 0);
  END;
END game_actions_pkg;
/
