<template>
    <el-dialog
        v-model="visible"
        :title="displayName || t('quests.detail_title')"
        width="min(560px, 92vw)"
        class="quest-detail-dialog"
        destroy-on-close
        @closed="onClosed"
    >
        <div v-loading="loading" class="quest-book">
            <template v-if="quest">
                <h3 class="quest-book__title">{{ displayName }}</h3>
                <div
                    v-if="descriptionHtml"
                    class="quest-book__desc"
                    v-html="descriptionHtml"
                />
                <section v-if="tasks.length" class="quest-book__section">
                    <h4>{{ t('quests.tasks') }}</h4>
                    <div v-for="(task, ti) in tasks" :key="ti" class="quest-book__task">
                        <p class="quest-book__task-name">
                            {{ task.name || task.type }}
                            <span v-if="task.number_required > 0" class="quest-book__req">
                                × {{ task.number_required }}
                            </span>
                        </p>
                        <div v-if="task.items?.length" class="quest-book__items">
                            <div
                                v-for="(it, ii) in task.items"
                                :key="ii"
                                class="mc-slot quest-book__slot"
                                :title="it.title"
                            >
                                <img v-if="it.image" :src="it.image" class="mc-slot__img" alt="" />
                                <span v-if="it.amount > 1" class="mc-slot__amt">{{ it.amount }}</span>
                            </div>
                        </div>
                    </div>
                </section>
                <section v-if="rewards.length" class="quest-book__section">
                    <h4>{{ t('quests.rewards') }}</h4>
                    <div v-for="(rew, ri) in rewards" :key="ri" class="quest-book__task">
                        <p class="quest-book__task-name">
                            {{ rew.name || rew.type }}
                            <span v-if="rew.xp">+{{ rew.xp }} XP</span>
                        </p>
                        <div v-if="rew.items?.length" class="quest-book__items">
                            <div
                                v-for="(it, ii) in rew.items"
                                :key="ii"
                                class="mc-slot quest-book__slot"
                                :title="it.title"
                            >
                                <img v-if="it.image" :src="it.image" class="mc-slot__img" alt="" />
                                <span v-if="it.amount > 1" class="mc-slot__amt">{{ it.amount }}</span>
                            </div>
                        </div>
                    </div>
                </section>
            </template>
        </div>
    </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { nesqlApi } from '@/api';
import itemUtil from '@/utils/items';
import { mcFormatToHtml } from '@/utils/mcFormat';
import { ensureBqRuLoaded, bqQuestDesc, bqQuestName } from '@/utils/bqLocale';

const { t, locale } = useI18n();

const props = defineProps({
    questId: { type: Number, default: null },
});
const visible = defineModel('visible', { type: Boolean, default: false });

const loading = ref(false);
const quest = ref(null);
const itemCache = ref(new Map());

const displayName = computed(() => {
    const q = quest.value;
    if (!q) return '';
    return bqQuestName(q.bq_id, q.name, locale.value);
});

const descriptionHtml = computed(() => {
    const q = quest.value;
    if (!q) return '';
    const text = bqQuestDesc(q.bq_id, q.description, locale.value);
    return mcFormatToHtml(text);
});

const tasks = computed(() => enrichEntries(quest.value?.tasks || []));
const rewards = computed(() => enrichEntries(quest.value?.rewards || []));

function enrichEntries(entries) {
    return entries.map((e) => ({
        ...e,
        items: (e.items || []).map((row) => resolveItemRow(row)).filter(Boolean),
    }));
}

function resolveItemRow(row) {
    const cached = itemCache.value.get(row.item_id);
    if (!cached) {
        return {
            amount: row.amount ?? 1,
            image: itemUtil.staticAsset('img/default.png'),
            title: `#${row.item_id}`,
        };
    }
    const r = itemUtil.fromNesqlItem(cached);
    return {
        amount: row.amount ?? 1,
        image: r?.image || itemUtil.staticAsset('img/default.png'),
        title: r?.title || cached.localized_name,
    };
}

async function loadQuest(id) {
    loading.value = true;
    quest.value = null;
    itemCache.value = new Map();
    try {
        if (locale.value === 'ru') await ensureBqRuLoaded();
        if (!itemUtil.items) itemUtil.loadItems();
        const body = await nesqlApi.quest(id);
        const q = body.data;
        quest.value = {
            ...q,
            tasks: q.tasks || [],
            rewards: q.rewards || [],
        };
        const ids = new Set();
        for (const list of [quest.value.tasks, quest.value.rewards]) {
            for (const entry of list) {
                for (const it of entry.items || []) {
                    if (it.item_id) ids.add(it.item_id);
                }
            }
        }
        await Promise.all(
            [...ids].map(async (itemId) => {
                try {
                    const resp = await nesqlApi.item(itemId);
                    itemCache.value.set(itemId, resp.data);
                } catch {
                    itemCache.value.set(itemId, null);
                }
            }),
        );
        quest.value = { ...quest.value };
    } catch {
        quest.value = null;
    } finally {
        loading.value = false;
    }
}

function onClosed() {
    quest.value = null;
}

watch(
    () => [visible.value, props.questId],
    ([open, id]) => {
        if (open && id != null && id > 0) loadQuest(id);
    },
);
</script>

<style scoped>
.quest-book {
    min-height: 120px;
    padding: 4px 2px;
    background: linear-gradient(180deg, #2a2218 0%, #1a1510 100%);
    border: 3px solid #4a3c28;
    border-radius: 4px;
    color: #e8dcc8;
}
.quest-book__title {
    margin: 0 0 10px;
    font-size: 18px;
    color: #ffdd55;
    text-shadow: 1px 1px 0 #3a2a10;
}
.quest-book__desc {
    font-size: 14px;
    line-height: 1.45;
    margin-bottom: 14px;
    white-space: pre-wrap;
}
.quest-book__section h4 {
    margin: 0 0 8px;
    font-size: 13px;
    color: #c9a86c;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.quest-book__task {
    margin-bottom: 12px;
}
.quest-book__task-name {
    margin: 0 0 6px;
    font-size: 13px;
}
.quest-book__req {
    color: #aaa;
    font-size: 12px;
}
.quest-book__items {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
}
.quest-book__slot {
    width: 40px;
    height: 40px;
}
.mc-slot {
    box-sizing: border-box;
    border: 2px solid #2e1e0ecc;
    background: linear-gradient(145deg, #c6c6c6 0%, #8a8a8a 40%, #6e6e6e 100%);
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
}
.mc-slot__img {
    width: 32px;
    height: 32px;
    image-rendering: pixelated;
    object-fit: contain;
}
.mc-slot__amt {
    position: absolute;
    right: 2px;
    bottom: 1px;
    font-size: 10px;
    font-weight: 700;
    color: #fff;
    text-shadow: 0 0 3px #000;
}
</style>
