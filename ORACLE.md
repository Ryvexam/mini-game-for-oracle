
# Oracle Objet — notes de présentation

Tout l'état du jeu vit dans Oracle (objet-relationnel). **Pas d'ORM**, SQL/PL/SQL brut via
`python-oracledb`, bind variables partout. Schéma : `backend/db/schema.sql`.

## Schéma UML (types objet)

```
                    ┌─────────────────────────────┐
                    │ entity_t          «NOT FINAL»│
                    ├─────────────────────────────┤
                    │ id, display_name, x, y       │
                    ├─────────────────────────────┤
                    │ + move_to(x, y)              │
                    └─────────────┬───────────────┘
                       UNDER      │      UNDER
                ┌──────────────────┴──────────────────┐
                ▲ (héritage)                           ▲
   ┌────────────────────────────┐        ┌────────────────────────┐
   │ player_t                   │        │ npc_t                  │
   ├────────────────────────────┤        ├────────────────────────┤
   │ skin_id, wood, stone, ore  │        │ role, quest_marker     │
   ├────────────────────────────┤        └────────────────────────┘
   │ + move_to(x,y) «OVERRIDING»│
   │ + gain_resource(kind, amt) │
   └────────────────────────────┘

   ┌────────────────────────────┐   ┌────────────────────────────┐
   │ resource_node_t            │   │ chest_t                    │
   ├────────────────────────────┤   ├────────────────────────────┤
   │ id, kind, x, y, amount     │   │ id, owner, x, y, wood,     │
   ├────────────────────────────┤   │ stone, ore                 │
   │ + harvest_amount() NUMBER  │   ├────────────────────────────┤
   └────────────────────────────┘   │ + store(kind, qty)         │
                                     │ + total() NUMBER           │
   ┌────────────────────────────┐   └────────────────────────────┘
   │ action_result_t «retour»   │
   ├────────────────────────────┤
   │ ok, message, resource_kind,│
   │ amount                     │
   └────────────────────────────┘

Tables d'objets (OF type_t) :
  game_players        OF player_t          game_chests          OF chest_t
  game_npcs           OF npc_t             game_resource_nodes  OF resource_node_t

Package PL/SQL : game_actions_pkg
  create_or_get_player() → player_t        harvest_resource()      → action_result_t
  move_player()          → player_t        answer_sql_challenge()  → action_result_t
  deposit_resources()    → action_result_t
  (lit l'objet via VALUE() + FOR UPDATE, appelle ses méthodes, réécrit la ligne)
```

### Schéma relationnel (tables + clés étrangères)

```
                          ┌────────────────────┐
                          │ game_world_meta     │   (1 ligne : seed du monde)
                          │ id PK, seed         │   isolée, pas de FK
                          └────────────────────┘

                          ┌────────────────────┐
                          │ game_players  (PK id)│ ◄──── pivot central
                          │ display_name, x, y,  │
                          │ skin_id, wood, stone,│
                          │ ore                  │
                          └─────────┬───────────┘
        owner_fk  ┌─────────────────┼──────────────────┬───────────────────┐
                  │ 0..1            │ 0..1             │ 0..*              │ 0..1
        ┌─────────▼────────┐ ┌──────▼──────────┐ ┌─────▼──────────┐ ┌──────▼────────────┐
        │ game_chests      │ │ game_player_    │ │ game_sql_      │ │ game_player_stats │
        │ id PK, owner FK, │ │ quests          │ │ answers        │ │ pseudo PK/FK,     │
        │ x, y, wood,      │ │ pseudo PK/FK,   │ │ pseudo PK/FK,  │ │ wood/stone/ore_   │
        │ stone, ore       │ │ quest_id,       │ │ challenge_id PK│ │ gathered,         │
        └──────────────────┘ │ step_index,     │ │ is_correct,    │ │ harvest_actions,  │
                             │ step_progress,  │ │ answered_at    │ │ distance_moved,   │
                             │ updated_at      │ └────────┬───────┘ │ sql_attempts/     │
                             └─────────────────┘          │         │ correct, joined/  │
                                                           │         │ updated_at        │
                          ┌────────────────────┐           │         └───────────────────┘
                          │ game_sql_challenges │ ──────────┘ challenge_id
                          │ id PK, prompt,      │   (1..* réponses par défi)
                          │ sql_code, choice_1..│
                          │ 3, correct_index    │
                          └────────────────────┘

  game_npcs / game_resource_nodes : tables d'objets sans FK (peuplées par génération
  procédurale). game_leaderboard : vue sur game_player_stats avec RANK() (pas une table).
```

## 1. Héritage de types objet

```sql
CREATE TYPE entity_t AS OBJECT (x NUMBER, y NUMBER,
  MEMBER PROCEDURE move_to(...)) NOT FINAL;

CREATE TYPE player_t UNDER entity_t (        -- héritage
  wood NUMBER, stone NUMBER, ore NUMBER,
  OVERRIDING MEMBER PROCEDURE move_to(...));  -- polymorphisme

CREATE TYPE npc_t UNDER entity_t (role VARCHAR2(20), ...);
```

- **Héritage** : `player_t` et `npc_t` `UNDER entity_t`.
- **Polymorphisme** : `player_t` redéfinit `move_to` (`OVERRIDING`).
- **Encapsulation** : la logique est dans le `TYPE BODY` (ex. `chest_t.store`,
  `resource_node_t.harvest_amount`).

Autres types : `chest_t`, `resource_node_t`, `action_result_t` (structure de retour).

## 2. Tables d'objets (`OF type_t`)

```sql
CREATE TABLE game_players OF player_t (...);
CREATE TABLE game_npcs    OF npc_t (...);
```

Lecture/écriture de l'instance objet complète avec `VALUE()` + appel de méthode :

```sql
SELECT VALUE(p) INTO v_player FROM game_players p WHERE p.id = :pseudo FOR UPDATE;
v_player.move_to(:x, :y);                    -- méthode objet
UPDATE game_players p SET x = v_player.x, y = v_player.y WHERE p.id = :pseudo;
```

### Extraits de méthodes (`TYPE BODY`)

Procédure membre (encapsulation de l'inventaire) :

```sql
MEMBER PROCEDURE gain_resource(resource_kind VARCHAR2, amount NUMBER) IS
BEGIN
  IF resource_kind = 'wood' THEN     wood  := wood  + amount;
  ELSIF resource_kind = 'stone' THEN stone := stone + amount;
  ELSIF resource_kind = 'ore' THEN   ore   := ore   + amount;
  END IF;
END;
```

Fonction membre (retourne une valeur calculée) :

```sql
MEMBER FUNCTION harvest_amount RETURN NUMBER IS
BEGIN
  IF amount <= 0 THEN RETURN 0; END IF;
  RETURN LEAST(1, amount);
END;
```

## 3. Logique métier = package PL/SQL

`game_actions_pkg` : `create_or_get_player`, `move_player`, `harvest_resource`,
`answer_sql_challenge`, `deposit_resources`. Retourne des `action_result_t`. Seule porte
d'écriture, verrous `FOR UPDATE` centralisés.

Fonction du package qui lit l'objet, appelle sa méthode, réécrit la ligne :

```sql
FUNCTION move_player(p_pseudo VARCHAR2, p_x NUMBER, p_y NUMBER) RETURN player_t IS
  v_player player_t;
BEGIN
  SELECT VALUE(p) INTO v_player FROM game_players p
  WHERE p.id = p_pseudo FOR UPDATE;   -- verrou ligne

  v_player.move_to(p_x, p_y);          -- méthode objet (polymorphe)

  UPDATE game_players p SET x = v_player.x, y = v_player.y
  WHERE p.id = p_pseudo;
  RETURN v_player;
END;
```

Création idempotente avec gestion d'exception :

```sql
FUNCTION create_or_get_player(p_pseudo VARCHAR2, p_skin_id VARCHAR2) RETURN player_t IS
  v_player player_t;
BEGIN
  SELECT VALUE(p) INTO v_player FROM game_players p WHERE p.id = p_pseudo;
  RETURN v_player;
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    v_player := player_t(p_pseudo, p_pseudo, 240, 300, NVL(p_skin_id,'player'), 0, 0, 0);
    INSERT INTO game_players VALUES (v_player);   -- insertion d'un objet
    RETURN v_player;
END;
```

## 4. Triggers (stats automatiques)

Les stats ne sont **pas** calculées en Python — triggers sur `game_players` :
`AFTER INSERT` (crée la ligne), `AFTER UPDATE OF wood/stone/ore` (cumule le butin),
`AFTER UPDATE OF x/y` (distance), + compteurs SQL.

## 5. Vue + analytique (classement)

```sql
RANK() OVER (ORDER BY wood_gathered + stone_gathered + ore_gathered DESC) AS rank_position
```

## 6. Inventaire du code PL/SQL

### Méthodes objet (`TYPE BODY`)

| Type | Méthode | Genre | Rôle |
|---|---|---|---|
| `entity_t` | `move_to(new_x, new_y)` | MEMBER PROCEDURE | Affecte `x`, `y` |
| `player_t` | `move_to(new_x, new_y)` | OVERRIDING MEMBER PROCEDURE | Redéfinition (polymorphisme) |
| `player_t` | `gain_resource(kind, amount)` | MEMBER PROCEDURE | Incrémente wood/stone/ore |
| `resource_node_t` | `harvest_amount()` | MEMBER FUNCTION → NUMBER | Qté récoltable (`LEAST(1, amount)`) |
| `chest_t` | `store(kind, qty)` | MEMBER PROCEDURE | Ajoute au coffre |
| `chest_t` | `total()` | MEMBER FUNCTION → NUMBER | Somme du contenu |

### Fonctions du package `game_actions_pkg`

| Fonction | Retour | Rôle |
|---|---|---|
| `create_or_get_player(pseudo, skin_id)` | `player_t` | Idempotent : lit ou insère (gère `NO_DATA_FOUND`) |
| `move_player(pseudo, x, y)` | `player_t` | `VALUE() FOR UPDATE` → `move_to` → `UPDATE` |
| `harvest_resource(pseudo, target_id)` | `action_result_t` | Verrouille joueur + nœud, transfère la ressource |
| `answer_sql_challenge(pseudo, challenge_id, answer_index)` | `action_result_t` | Vérifie la réponse, MERGE dans `game_sql_answers` |
| `deposit_resources(pseudo, chest_id)` | `action_result_t` | Vide l'inventaire dans le coffre |

### Triggers (stats automatiques, jamais en Python)

| Trigger | Événement | Effet |
|---|---|---|
| `trg_player_stats_create` | `AFTER INSERT ON game_players` | Crée la ligne `game_player_stats` |
| `trg_player_stats_resources` | `AFTER UPDATE OF wood, stone, ore` | Cumule le butin + `harvest_actions` |
| `trg_player_stats_distance` | `AFTER UPDATE OF x, y` | Ajoute `SQRT(Δx²+Δy²)` à `distance_moved` |
| `trg_player_stats_sql` | `AFTER INSERT OR UPDATE ON game_sql_answers` | Compte `sql_attempts` / `sql_correct` |

### Vue

| Vue | Détail |
|---|---|
| `game_leaderboard` | `RANK() OVER (ORDER BY total_gathered DESC)` sur `game_player_stats` |

Exemple de corps de trigger (distance, calcul SQL pur) :

```sql
CREATE OR REPLACE TRIGGER trg_player_stats_distance
AFTER UPDATE OF x, y ON game_players FOR EACH ROW
DECLARE
  v_step NUMBER := SQRT(POWER(:NEW.x - :OLD.x, 2) + POWER(:NEW.y - :OLD.y, 2));
BEGIN
  IF v_step > 0 THEN
    UPDATE game_player_stats SET distance_moved = distance_moved + v_step
    WHERE pseudo = :NEW.id;
  END IF;
END;
```

## En résumé

| Concept Oracle Objet | Où |
|---|---|
| Héritage / `UNDER` | `player_t`, `npc_t` |
| Polymorphisme / `OVERRIDING` | `player_t.move_to` |
| Encapsulation / `TYPE BODY` | `chest_t.store`, `resource_node_t.harvest_amount` |
| Object tables / `OF type_t` | `game_players`, `game_npcs`, `game_chests`, `game_resource_nodes` |
| `VALUE()` + méthodes | lecture/écriture joueur |
| PL/SQL package | `game_actions_pkg` |
| Triggers | stats joueur |
| Vue + `RANK()` | `game_leaderboard` |

Python = orchestration seule (binds, génération du monde, API/WebSocket). Aucune règle de jeu hors d'Oracle.
