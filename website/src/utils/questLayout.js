/** Quest board layout: BQ canvas coords or auto graph / grid fallback. */

const GAP_X = 88;
const GAP_Y = 72;
const PAD = 48;

/**
 * @param {Array<{id:number,pos_x?:number|null,pos_y?:number|null,size_x?:number,size_y?:number}>} quests
 * @param {Array<{from:number,to:number}>} edges
 * @returns {typeof quests}
 */
export function layoutQuestNodes(quests, edges = []) {
    if (!quests.length) return [];

    const withPos = quests.filter((q) => q.pos_x != null && q.pos_y != null);
    if (withPos.length === quests.length) {
        return quests.map((q) => ({
            ...q,
            size_x: q.size_x || 24,
            size_y: q.size_y || 24,
        }));
    }

    if (!edges.length) {
        return layoutGrid(quests);
    }

    return layoutLayered(quests, edges);
}

function layoutGrid(quests) {
    const cols = Math.max(1, Math.ceil(Math.sqrt(quests.length)));
    return quests.map((q, i) => ({
        ...q,
        pos_x: PAD + (i % cols) * GAP_X,
        pos_y: PAD + Math.floor(i / cols) * GAP_Y,
        size_x: q.size_x || 24,
        size_y: q.size_y || 24,
    }));
}

function layoutLayered(quests, edges) {
    const byId = new Map(quests.map((q) => [q.id, { ...q, size_x: q.size_x || 24, size_y: q.size_y || 24 }]));
    const inDeg = new Map();
    for (const q of quests) inDeg.set(q.id, 0);
    for (const e of edges) {
        if (!byId.has(e.from) || !byId.has(e.to)) continue;
        inDeg.set(e.to, (inDeg.get(e.to) || 0) + 1);
    }

    const layers = [];
    const visited = new Set();
    let frontier = quests.filter((q) => (inDeg.get(q.id) || 0) === 0).map((q) => q.id);

    while (frontier.length) {
        layers.push([...frontier]);
        const next = [];
        for (const id of frontier) {
            visited.add(id);
            for (const e of edges) {
                if (e.from !== id || !byId.has(e.to)) continue;
                inDeg.set(e.to, inDeg.get(e.to) - 1);
                if (inDeg.get(e.to) === 0 && !visited.has(e.to)) next.push(e.to);
            }
        }
        frontier = [...new Set(next)];
    }

    for (const q of quests) {
        if (!visited.has(q.id)) {
            if (!layers.length) layers.push([]);
            layers[layers.length - 1].push(q.id);
        }
    }

    layers.forEach((ids, col) => {
        const colH = ids.length * GAP_Y;
        ids.forEach((id, row) => {
            const node = byId.get(id);
            if (!node) return;
            node.pos_x = PAD + col * GAP_X;
            node.pos_y = PAD + row * GAP_Y - colH / 2 + GAP_Y / 2;
        });
    });

    return Array.from(byId.values());
}
