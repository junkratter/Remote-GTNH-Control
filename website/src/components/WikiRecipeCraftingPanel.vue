<template>
    <div v-if="recipe" class="mc-recipe">
        <div class="mc-recipe__machine glass-card">
            <span class="mc-recipe__machine-label">{{ t('wiki.recipe.machine') }}</span>
            <strong class="mc-recipe__machine-name">{{ displayType }}</strong>
            <span v-if="recipe.duration" class="mc-recipe__meta">{{ t('wiki.recipe.ticks', { n: recipe.duration }) }}</span>
            <span v-if="recipe.eu_per_tick" class="mc-recipe__meta">{{ t('wiki.recipe.eu', { n: recipe.eu_per_tick }) }}</span>
        </div>
        <div class="mc-recipe__flow">
            <div class="mc-recipe__io">
                <div class="mc-recipe__io-label">{{ t('wiki.recipe.inputs') }}</div>
                <div v-if="inputCells.length" class="mc-recipe__grid" :style="inputGridStyle">
                    <el-tooltip
                        v-for="(cell, idx) in inputCells"
                        :key="'in-' + idx"
                        :content="cell?.title || ''"
                        :disabled="!cell?.title"
                        placement="top"
                        :show-after="200"
                    >
                        <div :class="mcSlotDynClass(cell)" @click="onSlotClick(cell)">
                            <template v-if="cell">
                                <img
                                    v-if="cell.kind === 'item' && cell.image"
                                    :src="cell.image"
                                    class="mc-slot__img"
                                    alt=""
                                />
                                <div v-else-if="cell.kind === 'fluid'" class="mc-slot__fluid">{{ cell.label }}</div>
                                <span v-if="cell.amount > 1" class="mc-slot__amt">{{ cell.amount }}</span>
                            </template>
                        </div>
                    </el-tooltip>
                </div>
                <p v-else class="mc-recipe__empty">{{ t('wiki.detail.empty') }}</p>
            </div>
            <div class="mc-recipe__arrow" aria-hidden="true">➜</div>
            <div class="mc-recipe__io">
                <div class="mc-recipe__io-label">{{ t('wiki.recipe.outputs') }}</div>
                <div v-if="outputCells.length" class="mc-recipe__grid" :style="outputGridStyle">
                    <el-tooltip
                        v-for="(cell, idx) in outputCells"
                        :key="'out-' + idx"
                        :content="cell?.title || ''"
                        :disabled="!cell?.title"
                        placement="top"
                        :show-after="200"
                    >
                        <div :class="mcSlotDynClass(cell)" @click="onSlotClick(cell)">
                            <template v-if="cell">
                                <img
                                    v-if="cell.kind === 'item' && cell.image"
                                    :src="cell.image"
                                    class="mc-slot__img"
                                    alt=""
                                />
                                <div v-else-if="cell.kind === 'fluid'" class="mc-slot__fluid">{{ cell.label }}</div>
                                <span v-if="cell.amount > 1" class="mc-slot__amt">{{ cell.amount }}</span>
                                <span
                                    v-if="cell.chance != null && cell.chance < 100"
                                    class="mc-slot__chance"
                                >{{ cell.chance }}%</span>
                            </template>
                        </div>
                    </el-tooltip>
                </div>
                <p v-else class="mc-recipe__empty">{{ t('wiki.detail.empty') }}</p>
            </div>
        </div>
    </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { nesqlApi } from '@/api';
import itemUtil from '@/utils/items';

const { t } = useI18n();

const props = defineProps({
    recipe: { type: Object, required: true },
    /** Keys ``"${item_id}_${damage}"`` → AE-backed quantity for craft overlays */
    stockQtyByKey: { type: Object, default: () => ({}) },
});

const emit = defineEmits(['select-item']);

function stockBorderClass(cell) {
    if (!cell?.item_id || !props.stockQtyByKey || !Object.keys(props.stockQtyByKey).length) {
        return '';
    }
    const key = `${cell.item_id}_${cell.damage ?? 0}`;
    const need = cell.amount ?? 1;
    const have = Number(props.stockQtyByKey[key] ?? 0);
    if (have >= need) return 'mc-slot--in-stock';
    return 'mc-slot--missing';
}

function mcSlotDynClass(cell) {
    const xs = ['mc-slot'];
    if (cell?.item_id) xs.push('mc-slot--clickable');
    const sb = stockBorderClass(cell);
    if (sb) xs.push(sb);
    return xs.join(' ');
}

const itemCache = ref(new Map());
const inputCells = ref([]);
const outputCells = ref([]);

const displayType = computed(
    () => props.recipe.recipe_type_label || props.recipe.recipe_type || '—',
);

const isCraftingGrid = computed(() => {
    const label = (props.recipe.recipe_type_label || '').toLowerCase();
    const rt = (props.recipe.recipe_type || '').toLowerCase();
    return (
        label.includes('shaped')
        || label.includes('shapeless')
        || label.includes('crafting')
        || rt.includes('minecraft')
    );
});

const inputGridStyle = computed(() => {
    if (isCraftingGrid.value) {
        return { gridTemplateColumns: 'repeat(3, var(--mc-slot))' };
    }
    const n = inputCells.value.length;
    const cols = Math.min(6, Math.max(1, Math.ceil(Math.sqrt(n))));
    return { gridTemplateColumns: `repeat(${cols}, var(--mc-slot))` };
});

const outputGridStyle = computed(() => {
    const n = outputCells.value.length;
    const cols = Math.min(6, Math.max(1, Math.ceil(Math.sqrt(n)) || 1));
    return { gridTemplateColumns: `repeat(${cols}, var(--mc-slot))` };
});

function sortSlots(slots) {
    return [...(slots || [])].sort((a, b) => (a.slot ?? 0) - (b.slot ?? 0));
}

function dedupeSlots(slots) {
    const bySlot = new Map();
    for (const s of sortSlots(slots)) {
        if (!s || (!s.item_id && !s.fluid_id)) continue;
        const key = s.slot ?? 0;
        const prev = bySlot.get(key);
        if (!prev) {
            bySlot.set(key, { ...s });
            continue;
        }
        if (s.item_id === prev.item_id && s.fluid_id === prev.fluid_id) {
            prev.amount = (prev.amount ?? 1) + (s.amount ?? 1);
        }
    }
    return [...bySlot.values()].sort((a, b) => (a.slot ?? 0) - (b.slot ?? 0));
}

function buildInputCells(slots) {
    const unique = dedupeSlots(slots);
    if (!unique.length) return [];

    if (isCraftingGrid.value) {
        const bySlot = new Map();
        for (const s of unique) {
            const slot = Math.min(8, Math.max(0, s.slot ?? 0));
            if (!bySlot.has(slot)) bySlot.set(slot, s);
        }
        const grid = [];
        for (let i = 0; i < 9; i += 1) {
            grid.push(bySlot.get(i) || null);
        }
        return grid;
    }
    return unique;
}

function buildOutputCells(slots) {
    return dedupeSlots(slots);
}

function waitForItems(timeoutMs = 15000) {
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

function mapSlot(s, isOutput) {
    if (!s) return null;
    if (s.fluid_id) {
        return {
            kind: 'fluid',
            label: `${t('wiki.recipe.fluid')} #${s.fluid_id}`,
            amount: s.amount ?? 1,
            chance: isOutput ? (s.chance != null ? s.chance : 100) : null,
        };
    }
    if (!s.item_id) return null;
    const it = itemCache.value.get(s.item_id);
    if (!it) {
        return {
            kind: 'item',
            item_id: s.item_id,
            damage: s.damage ?? it?.damage ?? 0,
            image: itemUtil.staticAsset('img/default.png'),
            title: `#${s.item_id}`,
            amount: s.amount ?? 1,
            chance: isOutput ? (s.chance != null ? s.chance : 100) : null,
        };
    }
    const resolved = itemUtil.fromNesqlItem(it);
    return {
        kind: 'item',
        item_id: s.item_id,
        damage: s.damage ?? it?.damage ?? 0,
        image: resolved?.image || itemUtil.staticAsset('img/default.png'),
        title: resolved?.title || it.localized_name || it.unlocal_name,
        amount: s.amount ?? 1,
        chance: isOutput ? (s.chance != null ? s.chance : 100) : null,
    };
}

function onSlotClick(cell) {
    if (cell?.item_id) emit('select-item', cell.item_id);
}

async function hydrate() {
    const r = props.recipe;
    const rawIn = buildInputCells(r.inputs || []);
    const rawOut = buildOutputCells(r.outputs || []);

    await waitForItems();

    const ids = new Set();
    for (const s of [...rawIn, ...rawOut]) {
        if (s?.item_id) ids.add(s.item_id);
    }
    for (const id of ids) {
        if (!itemCache.value.has(id)) {
            try {
                const body = await nesqlApi.item(id);
                itemCache.value.set(id, body.data);
            } catch {
                itemCache.value.set(id, null);
            }
        }
    }

    inputCells.value = rawIn.map((s) => mapSlot(s, false));
    outputCells.value = rawOut.map((s) => mapSlot(s, true));
}

watch(
    () => props.stockQtyByKey,
    () => {
        hydrate();
    },
    { deep: true },
);

watch(
    () => props.recipe,
    () => {
        itemCache.value = new Map();
        hydrate();
    },
    { immediate: true, deep: true },
);
</script>

<style scoped>
.mc-recipe {
    margin-top: 12px;
}
.mc-recipe__machine {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 8px 14px;
    padding: 10px 12px;
    margin-bottom: 12px;
}
.mc-recipe__machine-label {
    color: var(--el-text-color-secondary);
    font-size: 13px;
}
.mc-recipe__machine-name {
    font-size: 15px;
}
.mc-recipe__meta {
    font-size: 12px;
    color: var(--el-text-color-secondary);
}
.mc-recipe__flow {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px 18px;
}
.mc-recipe__io-label {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-bottom: 6px;
}
.mc-recipe__grid {
    --mc-slot: 44px;
    display: grid;
    gap: 4px;
}
.mc-recipe__arrow {
    font-size: 22px;
    color: var(--el-text-color-secondary);
    padding: 0 4px;
}
.mc-recipe__empty {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    font-style: italic;
}
.mc-slot {
    width: var(--mc-slot);
    height: var(--mc-slot);
    box-sizing: border-box;
    border: 2px solid #2e1e0ecc;
    border-bottom-color: #1a120899;
    border-right-color: #1a120899;
    background: linear-gradient(145deg, #c6c6c6 0%, #8a8a8a 40%, #6e6e6e 100%);
    box-shadow: inset 1px 1px 0 #ffffff55;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
}
.mc-slot--clickable {
    cursor: pointer;
}
.mc-slot--clickable:hover {
    border-color: #4a8fd4;
    box-shadow: inset 1px 1px 0 #ffffff88, 0 0 6px rgba(74, 143, 212, 0.45);
}
.mc-slot--in-stock {
    outline: 2px solid rgba(46, 160, 67, 0.85);
    outline-offset: -1px;
}
.mc-slot--missing {
    outline: 2px solid rgba(200, 60, 60, 0.75);
    outline-offset: -1px;
}
.mc-slot__img {
    width: 36px;
    height: 36px;
    image-rendering: pixelated;
    object-fit: contain;
}
.mc-slot__fluid {
    font-size: 10px;
    text-align: center;
    padding: 2px;
    color: #1a5080;
    font-weight: 600;
    line-height: 1.15;
    word-break: break-word;
}
.mc-slot__amt {
    position: absolute;
    right: 2px;
    bottom: 1px;
    font-size: 11px;
    font-weight: 700;
    color: #fff;
    text-shadow: 0 0 3px #000;
}
.mc-slot__chance {
    position: absolute;
    left: 2px;
    top: 1px;
    font-size: 10px;
    font-weight: 600;
    color: #ffd54f;
    text-shadow: 0 0 2px #000;
}
</style>
