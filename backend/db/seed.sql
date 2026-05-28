SET DEFINE OFF

INSERT INTO game_npcs VALUES (
  npc_t('sage-oracle', 'Sage Oracle', 300, 280, 'oracle_sage', '!')
);
/

INSERT INTO game_npcs VALUES (
  npc_t('mineur-luma', 'Luma la mineuse', 390, 318, 'miner', '!')
);
/

INSERT INTO game_npcs VALUES (
  npc_t('marchand-moki', 'Moki le marchand', 512, 286, 'merchant', NULL)
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

COMMIT;
/
