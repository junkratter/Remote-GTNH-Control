<template>
    <div v-loading="loading" class="quest-board">
        <header class="quest-board__header">
            <h3 class="quest-board__title">{{ lineTitle }}</h3>
            <span v-if="completion" class="quest-board__progress">
                {{ t('quests.board.completion', { done: completion.done, total: completion.total }) }}
            </span>
        </header>
        <div
            ref="viewportEl"
            class="quest-board__viewport"
            @wheel.prevent="onWheel"
            @mousedown="onPanStart"
        >
            <div class="quest-board__canvas" :style="canvasStyle">
                <svg class="quest-board__edges" :width="canvasW" :height="canvasH">
                    <line
                        v-for="(e, i) in edgeSegments"
                        :key="i"
                        :x1="e.x1"
                        :y1="e.y1"
                        :x2="e.x2"
                        :y2="e.y2"
                    />
                </svg>
                <button
                    v-for="node in nodes"
                    :key="node.id"
                    type="button"
                    class="quest-board__node"
                    :style="nodeStyle(node)"
                    :title="node.name"
                    @click="$emit('select', node.id)"
                >
                    <img
                        v-if="node.icon"
                        :src="node.icon"
                        class="quest-board__icon"
                        alt=""
                    />
                    <span v-else class="quest-board__fallback" :title="node.name">?</span>
                </button>
            </div>
        </div>
        <p v-if="!loading && !nodes.length" class="quest-board__hint">{{ t('quests.board.empty_line') }}</p>
        <p v-else-if="layoutMode === 'auto'" class="quest-board__hint quest-board__hint--sub">
            {{ t('quests.board.auto_layout') }}
        </p>
    </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import api, { nesqlApi } from '@/api';
import itemUtil from '@/utils/items';
import {
    ensureBqRuLoaded,
    bqLineName,
    bqQuestName,
} from '@/utils/bqLocale';
import { layoutQuestNodes } from '@/utils/questLayout';

const props = defineProps({
    lineRootId: { type: Number, required: true },
});
defineEmits(['select']);

const { t, locale } = useI18n();
const loading = ref(false);
const board = ref(null);
const scale = ref(1);
const panX = ref(0);
const panY = ref(0);
const viewportEl = ref(null);
let panning = false;
let panStart = { x: 0, y: 0, px: 0, py: 0 };

const completion = computed(() => board.value?.completion);
const lineTitle = computed(() => {
    const line = board.value?.line;
    if (!line) return '';
    return bqLineName(line.bq_id, line.name, locale.value);
});

const iconUrls = ref({});
const layoutMode = ref('auto');

const nodes = computed(() => {
    const raw = board.value?.quests || [];
    const edges = board.value?.edges || [];
    const laid = layoutQuestNodes(raw, edges);
    return laid.map((q) => {
        const name = bqQuestName(q.bq_id, q.name, locale.value);
        return { ...q, name, icon: iconUrls.value[q.id] || null };
    });
});

async function waitForItems(timeoutMs = 20000) {
    return new Promise((resolve) => {
        if (itemUtil.items) {
            resolve(true);
            return;
        }
        const start = Date.now();
        const tick = () => {
            if (itemUtil.items) {
                resolve(true);
                return;
            }
            if (Date.now() - start > timeoutMs) {
                resolve(false);
                return;
            }
            requestAnimationFrame(tick);
        };
        itemUtil.loadItems();
        tick();
    });
}

async function loadIcons(quests) {
    await waitForItems();
    const next = { ...iconUrls.value };
    const batch = 40;
    for (let i = 0; i < quests.length; i += batch) {
        const slice = quests.slice(i, i + batch);
        await Promise.all(
            slice.map(async (q) => {
                if (!q.icon_item_id) return;
                try {
                    const resp = await nesqlApi.item(q.icon_item_id);
                    const r = itemUtil.fromNesqlItem(resp.data);
                    if (r?.image) next[q.id] = r.image;
                } catch {
                    /* ignore */
                }
            }),
        );
    }
    iconUrls.value = next;
}

const nodeById = computed(() => {
    const m = new Map();
    for (const n of nodes.value) m.set(n.id, n);
    return m;
});

const canvasW = computed(() => {
    let max = 800;
    for (const n of nodes.value) {
        max = Math.max(max, (n.pos_x || 0) + (n.size_x || 24) + 80);
    }
    return max;
});

const canvasH = computed(() => {
    let max = 600;
    for (const n of nodes.value) {
        max = Math.max(max, (n.pos_y || 0) + (n.size_y || 24) + 80);
    }
    return max;
});

const canvasStyle = computed(() => ({
    width: `${canvasW.value}px`,
    height: `${canvasH.value}px`,
    transform: `translate(${panX.value}px, ${panY.value}px) scale(${scale.value})`,
    transformOrigin: '0 0',
}));

function nodeCenter(n) {
    const w = n.size_x || 24;
    const h = n.size_y || 24;
    return { x: (n.pos_x || 0) + w / 2, y: (n.pos_y || 0) + h / 2 };
}

const edgeSegments = computed(() => {
    const edges = board.value?.edges || [];
    const out = [];
    for (const e of edges) {
        const a = nodeById.value.get(e.from);
        const b = nodeById.value.get(e.to);
        if (!a || !b) continue;
        const ca = nodeCenter(a);
        const cb = nodeCenter(b);
        out.push({ x1: ca.x, y1: ca.y, x2: cb.x, y2: cb.y });
    }
    return out;
});

function nodeStyle(node) {
    const w = node.size_x || 24;
    const h = node.size_y || 24;
    return {
        left: `${node.pos_x}px`,
        top: `${node.pos_y}px`,
        width: `${w}px`,
        height: `${h}px`,
    };
}

function onWheel(ev) {
    const delta = ev.deltaY > 0 ? -0.08 : 0.08;
    scale.value = Math.min(2.5, Math.max(0.35, scale.value + delta));
}

function onPanStart(ev) {
    if (ev.button !== 0) return;
    panning = true;
    panStart = { x: ev.clientX, y: ev.clientY, px: panX.value, py: panY.value };
    window.addEventListener('mousemove', onPanMove);
    window.addEventListener('mouseup', onPanEnd);
}

function onPanMove(ev) {
    if (!panning) return;
    panX.value = panStart.px + (ev.clientX - panStart.x);
    panY.value = panStart.py + (ev.clientY - panStart.y);
}

function onPanEnd() {
    panning = false;
    window.removeEventListener('mousemove', onPanMove);
    window.removeEventListener('mouseup', onPanEnd);
}

async function load() {
    if (!props.lineRootId) return;
    loading.value = true;
    try {
        if (locale.value === 'ru') await ensureBqRuLoaded();
        const { data } = await api.GET('/api/quests/board', {
            params: { query: { line_root_id: props.lineRootId } },
        });
        if (data?.code === 200) {
            board.value = data.data;
            layoutMode.value = data.data?.layout || 'auto';
            iconUrls.value = {};
            if (data.data?.quests?.length) await loadIcons(data.data.quests);
        } else board.value = null;
        panX.value = 24;
        panY.value = 24;
        scale.value = 1;
    } catch {
        board.value = null;
    } finally {
        loading.value = false;
    }
}

onMounted(load);
watch(() => props.lineRootId, load);
watch(locale, () => {
    if (locale.value === 'ru') ensureBqRuLoaded();
});
</script>

<style scoped>
.quest-board {
    display: flex;
    flex-direction: column;
    min-height: 420px;
}
.quest-board__header {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    justify-content: center;
    gap: 12px;
    padding: 8px 12px 4px;
}
.quest-board__title {
    margin: 0;
    font-size: 1.15rem;
    font-weight: 700;
    color: #3d2914;
    text-shadow: 0 1px 0 rgba(255, 255, 255, 0.35);
}
.quest-board__progress {
    font-size: 0.9rem;
    color: #5c4228;
}
.quest-board__viewport {
    flex: 1;
    overflow: hidden;
    cursor: grab;
    border-radius: 8px;
    margin: 0 8px 8px;
    min-height: 360px;
    background:
        radial-gradient(ellipse at 30% 20%, rgba(255, 248, 220, 0.9), transparent 55%),
        linear-gradient(165deg, #e8d4a8 0%, #d4bc88 35%, #c9b078 70%, #e0cfa0 100%);
    box-shadow: inset 0 0 40px rgba(80, 50, 20, 0.12);
}
.quest-board__viewport:active {
    cursor: grabbing;
}
.quest-board__canvas {
    position: relative;
    margin: 16px;
}
.quest-board__edges {
    position: absolute;
    left: 0;
    top: 0;
    pointer-events: none;
}
.quest-board__edges line {
    stroke: #3dff3d;
    stroke-width: 4;
    stroke-linecap: round;
    filter: drop-shadow(0 0 2px rgba(0, 200, 0, 0.6));
}
.quest-board__node {
    position: absolute;
    padding: 2px;
    border: 2px solid #8b4513;
    border-radius: 2px;
    background: linear-gradient(180deg, #f5e6c8 0%, #dcc9a0 100%);
    box-shadow: 1px 2px 4px rgba(0, 0, 0, 0.25);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
}
.quest-board__node:hover {
    border-color: #2e8b2e;
    z-index: 2;
}
.quest-board__icon {
    width: 100%;
    height: 100%;
    object-fit: contain;
    image-rendering: pixelated;
}
.quest-board__hint {
    text-align: center;
    color: #5c4228;
    font-size: 13px;
    margin: 0 0 12px;
}
.quest-board__hint--sub {
    font-size: 11px;
    opacity: 0.85;
    margin-top: -6px;
}
.quest-board__fallback {
    font-size: 18px;
    font-weight: 700;
    color: #5c4228;
    opacity: 0.65;
}
</style>
