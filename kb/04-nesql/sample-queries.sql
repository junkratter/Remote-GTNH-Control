-- Примеры запросов после импорта NESQL в SQLite.
-- Использовать в API /api/nesql/* и для отладки.

-- 1. Поиск предмета по локализованному имени.
SELECT id, unlocal_name, localized_name, mod_id, damage
FROM nesql_items
WHERE localized_name LIKE '%Iron Ingot%'
ORDER BY mod_id, unlocal_name
LIMIT 50;

-- 2. Все рецепты, где Iron Ingot — output.
SELECT r.id, r.recipe_type, r.duration, r.eu_per_tick
FROM nesql_recipes r,
     json_each(r.outputs_json) o
WHERE o.value->>'item_id' = (
    SELECT id FROM nesql_items WHERE unlocal_name = 'item.ingotIron' LIMIT 1
)
LIMIT 100;

-- 3. Что входит в рецепт по ID.
SELECT i.localized_name, ri.amount
FROM nesql_recipes r,
     json_each(r.inputs_json) inp
JOIN nesql_items i ON i.id = (inp.value->>'item_id')
WHERE r.id = 42;

-- 4. Ore dictionary: «что считается ingotIron».
SELECT od.name, i.unlocal_name, i.mod_id
FROM nesql_oredict od
JOIN nesql_oredict_items odi ON odi.ore_id = od.id
JOIN nesql_items i ON i.id = odi.item_id
WHERE od.name = 'ingotIron';

-- 5. Дерево квестов.
WITH RECURSIVE qtree(id, name, parent_id, depth) AS (
    SELECT id, name, parent_id, 0 FROM nesql_quests WHERE parent_id IS NULL
    UNION ALL
    SELECT q.id, q.name, q.parent_id, qt.depth + 1
    FROM nesql_quests q JOIN qtree qt ON q.parent_id = qt.id
)
SELECT printf('%*s%s', depth * 2, '', name) AS tree
FROM qtree ORDER BY id;

-- 6. Top-аспекты у предметов с Metallum.
SELECT i.localized_name, ia.amount
FROM nesql_item_aspects ia
JOIN nesql_items i ON i.id = ia.item_id
WHERE ia.aspect_name = 'Metallum'
ORDER BY ia.amount DESC
LIMIT 20;
