SET DEFINE OFF

INSERT INTO game_npcs VALUES (
  npc_t('sage-oracle', 'Sage Oracle', 300, 280, 'oracle_sage', '!')
);
/

INSERT INTO game_npcs VALUES (
  npc_t('mineur-luma', 'Luma la mineuse', 1740, 360, 'miner', '!')
);
/

INSERT INTO game_npcs VALUES (
  npc_t('marchand-moki', 'Moki le marchand', 360, 1740, 'merchant', NULL)
);
/

INSERT INTO game_resource_nodes VALUES (
  resource_node_t('spawn-rock-1', 'rock', 450, 365, 12)
);
/

INSERT INTO game_resource_nodes VALUES (
  resource_node_t('spawn-ore-1', 'ore', 585, 420, 8)
);
/

INSERT INTO game_resource_nodes VALUES (
  resource_node_t('spawn-tree-1', 'tree', 210, 420, 10)
);
/

INSERT INTO game_chests VALUES (
  chest_t('village-chest', NULL, 330, 360, 0, 0, 0)
);
/

INSERT INTO game_chests VALUES (
  chest_t('moki-chest', NULL, 460, 1800, 0, 0, 0)
);
/

INSERT INTO game_sql_challenges VALUES (
  'obj-method',
  'Dans ce type Oracle, quelle ligne declare une methode membre ?',
  'CREATE TYPE resource_node_t AS OBJECT (' || CHR(10) ||
  '  id VARCHAR2(80),' || CHR(10) ||
  '  kind VARCHAR2(20),' || CHR(10) ||
  '  MEMBER FUNCTION harvest_amount RETURN NUMBER' || CHR(10) ||
  ') NOT FINAL;',
  'kind VARCHAR2(20)',
  'MEMBER FUNCTION harvest_amount RETURN NUMBER',
  'NOT FINAL',
  1
);
/

INSERT INTO game_sql_challenges VALUES (
  'obj-inherit',
  'Quelle clause fait que player_t herite de entity_t ?',
  'CREATE TYPE player_t UNDER entity_t (' || CHR(10) ||
  '  wood NUMBER,' || CHR(10) ||
  '  OVERRIDING MEMBER FUNCTION describe RETURN VARCHAR2' || CHR(10) ||
  ');',
  'UNDER entity_t',
  'OVERRIDING MEMBER FUNCTION',
  'wood NUMBER',
  0
);
/

INSERT INTO game_sql_challenges VALUES (
  'obj-table',
  'Quelle syntaxe cree une table d''objets Oracle ?',
  'CREATE TABLE game_players OF player_t (' || CHR(10) ||
  '  CONSTRAINT game_players_pk PRIMARY KEY (id)' || CHR(10) ||
  ');',
  'CREATE TABLE game_players (id VARCHAR2)',
  'CREATE TABLE game_players OF player_t',
  'CREATE OBJECT game_players',
  1
);
/

INSERT INTO game_sql_challenges VALUES (
  'obj-body',
  'Ou est implemente le code des methodes d''un type objet ?',
  'CREATE OR REPLACE TYPE BODY chest_t AS' || CHR(10) ||
  '  MEMBER PROCEDURE store(resource_kind VARCHAR2, qty NUMBER) IS' || CHR(10) ||
  '  BEGIN' || CHR(10) ||
  '    wood := wood + qty;' || CHR(10) ||
  '  END;' || CHR(10) ||
  'END;',
  'Dans le TYPE BODY',
  'Dans la table OF chest_t',
  'Dans un trigger',
  0
);
/

INSERT INTO game_sql_challenges VALUES (
  'obj-ref',
  'Quelle fonction renvoie l''instance objet complete d''une ligne ?',
  'SELECT VALUE(p) INTO v_player' || CHR(10) ||
  'FROM game_players p' || CHR(10) ||
  'WHERE p.id = :pseudo;',
  'REF(p)',
  'VALUE(p)',
  'DEREF(p)',
  1
);
/

INSERT INTO game_sql_challenges VALUES (
  'obj-constructor',
  'Quelle methode construit une instance personnalisee d''un type objet ?',
  'CREATE TYPE chest_t AS OBJECT (' || CHR(10) ||
  '  id VARCHAR2(80),' || CHR(10) ||
  '  CONSTRUCTOR FUNCTION chest_t(p_id VARCHAR2) RETURN SELF AS RESULT' || CHR(10) ||
  ');',
  'CONSTRUCTOR FUNCTION',
  'MEMBER PROCEDURE init',
  'STATIC build',
  0
);
/

INSERT INTO game_sql_challenges VALUES (
  'obj-map',
  'Quelle methode permet a Oracle de trier des objets ?',
  'CREATE TYPE resource_node_t AS OBJECT (' || CHR(10) ||
  '  amount NUMBER,' || CHR(10) ||
  '  MAP MEMBER FUNCTION sort_key RETURN NUMBER' || CHR(10) ||
  ');',
  'MAP MEMBER FUNCTION',
  'SORT FUNCTION',
  'COMPARE MEMBER',
  0
);
/

INSERT INTO game_sql_challenges VALUES (
  'obj-deref',
  'Quelle fonction suit une REF pour obtenir l''objet pointe ?',
  'SELECT DEREF(c.owner_ref) INTO v_owner' || CHR(10) ||
  'FROM game_chests c' || CHR(10) ||
  'WHERE c.id = :chest_id;',
  'DEREF(ref)',
  'VALUE(ref)',
  'REF(obj)',
  0
);
/

INSERT INTO game_sql_challenges VALUES (
  'obj-coll',
  'Comment declarer une collection de ces objets en Oracle ?',
  'CREATE TYPE resource_list_t AS' || CHR(10) ||
  '  TABLE OF resource_node_t;',
  'TABLE OF resource_node_t',
  'ARRAY resource_node_t',
  'LIST OF resource_node_t',
  0
);
/

INSERT INTO game_sql_challenges VALUES (
  'obj-static',
  'Quelle methode s''appelle sans instance de l''objet ?',
  'CREATE TYPE player_t AS OBJECT (' || CHR(10) ||
  '  wood NUMBER,' || CHR(10) ||
  '  STATIC FUNCTION spawn RETURN player_t' || CHR(10) ||
  ');',
  'STATIC FUNCTION',
  'MEMBER FUNCTION',
  'MAP MEMBER',
  0
);
/

COMMIT;
/
