<template>
    <div class="page">
        <header class="page__header">
            <h2>{{ t('quests.title') }}</h2>
            <el-button :icon="Refresh" :loading="loading" @click="load">{{ t('quests.refresh') }}</el-button>
        </header>

        <div class="page-quests__toolbar glass-card">
            <el-radio-group v-model="viewMode" size="small" :disabled="searchMode">
                <el-radio-button label="board">{{ t('quests.view_board') }}</el-radio-button>
                <el-radio-button label="tree">{{ t('quests.view_tree') }}</el-radio-button>
            </el-radio-group>
            <el-select
                v-if="viewMode === 'board' && !searchMode"
                v-model="selectedLineRootId"
                filterable
                class="page-quests__line-select"
                :placeholder="t('quests.select_line')"
            >
                <el-option
                    v-for="line in questLines"
                    :key="line.id"
                    :label="lineLabel(line)"
                    :value="line.id"
                />
            </el-select>
            <el-input
                v-model="searchQuery"
                :placeholder="t('quests.search_ph')"
                clearable
                class="page-quests__search-input"
                @keyup.enter="runSearch"
            />
            <el-button type="primary" :loading="searchLoading" :disabled="searchQuery.trim().length < 2" @click="runSearch">
                {{ t('quests.search_btn') }}
            </el-button>
            <el-button v-if="searchMode" text type="primary" @click="clearSearch">{{ t('quests.back_tree') }}</el-button>
        </div>

        <el-skeleton v-if="loading && !quests.length && !searchMode" animated :rows="6" class="glass-card" />
        <el-empty v-else-if="!quests.length && !searchMode" :description="t('quests.empty')" />
        <QuestBoard
            v-else-if="!searchMode && viewMode === 'board' && selectedLineRootId"
            :line-root-id="selectedLineRootId"
            class="glass-card page-quests__board-wrap"
            @select="openQuest"
        />
        <div v-else-if="!searchMode && viewMode === 'tree'" v-loading="loading" class="glass-card">
            <el-tree
                :data="treeData"
                :props="{ label: 'label', children: 'children' }"
                class="page-quests__tree"
                default-expand-all
                node-key="id"
                @node-click="onTreeClick"
            />
        </div>
        <div v-else v-loading="searchLoading" class="glass-card page-quests__results">
            <el-empty v-if="!searchResults.length" :description="t('quests.empty')" />
            <el-table
                v-else
                :data="searchResults"
                stripe
                max-height="480"
                highlight-current-row
                @row-click="onSearchRowClick"
            >
                <el-table-column prop="id" label="ID" width="72" />
                <el-table-column prop="name" :label="t('wiki.col.name')" min-width="200" show-overflow-tooltip />
                <el-table-column prop="quest_line" :label="t('quests.col_line')" width="100" />
            </el-table>
        </div>

        <QuestDetailDialog v-model:visible="detailOpen" :quest-id="selectedQuestId" />
    </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { Refresh } from '@element-plus/icons-vue';
import api from '@/api';
import QuestDetailDialog from '@/components/QuestDetailDialog.vue';
import QuestBoard from '@/components/QuestBoard.vue';
import { ensureBqRuLoaded, bqLineName } from '@/utils/bqLocale';

const { t, locale } = useI18n();
const quests = ref([]);
const questLines = ref([]);
const loading = ref(false);
const searchQuery = ref('');
const searchResults = ref([]);
const searchLoading = ref(false);
const searchMode = ref(false);
const viewMode = ref('board');
const selectedLineRootId = ref(null);
const detailOpen = ref(false);
const selectedQuestId = ref(null);

const treeData = computed(() => {
    const byParent = new Map();
    for (const q of quests.value) {
        const label = q.id < 0 && q.bq_id
            ? bqLineName(q.bq_id, q.name, locale.value)
            : q.name;
        const arr = byParent.get(q.parent_id) || [];
        arr.push({ ...q, label, children: [] });
        byParent.set(q.parent_id, arr);
    }
    function attach(parentId) {
        const children = byParent.get(parentId) || [];
        for (const child of children) child.children = attach(child.id);
        return children;
    }
    return attach(null);
});

function lineLabel(line) {
    return bqLineName(line.bq_id, line.name, locale.value);
}

function openQuest(id) {
    if (id == null || id <= 0) return;
    selectedQuestId.value = id;
    detailOpen.value = true;
}

function onTreeClick(data) {
    openQuest(data.id);
}

function onSearchRowClick(row) {
    openQuest(row.id);
}

async function loadLines() {
    try {
        const { data } = await api.GET('/api/quests/lines', {});
        if (data?.code === 200 && Array.isArray(data.data)) {
            questLines.value = data.data;
            if (!selectedLineRootId.value && questLines.value.length) {
                const tierLv = questLines.value.find((l) =>
                    /tier\s*1\s*-\s*lv/i.test(l.name || ''),
                );
                selectedLineRootId.value = (tierLv || questLines.value[0]).id;
            }
        }
    } catch {
        questLines.value = [];
    }
}

async function load() {
    loading.value = true;
    try {
        if (locale.value === 'ru') await ensureBqRuLoaded();
        const { data } = await api.GET('/api/quests/tree', {});
        if (data?.code === 200 && Array.isArray(data.data)) {
            quests.value = data.data;
        } else {
            quests.value = [];
        }
        await loadLines();
    } catch {
        quests.value = [];
    } finally {
        loading.value = false;
    }
}

async function runSearch() {
    const q = searchQuery.value.trim();
    if (q.length < 2) return;
    searchLoading.value = true;
    searchMode.value = true;
    try {
        const { data } = await api.GET('/api/quests/search', { params: { query: { q, limit: 80 } } });
        if (data?.code === 200 && Array.isArray(data.data)) {
            searchResults.value = data.data;
        } else {
            searchResults.value = [];
        }
    } catch {
        searchResults.value = [];
    } finally {
        searchLoading.value = false;
    }
}

function clearSearch() {
    searchMode.value = false;
    searchResults.value = [];
}

onMounted(load);
watch(locale, async (loc) => {
    if (loc === 'ru') await ensureBqRuLoaded();
});
</script>

<style scoped>
.page-quests__toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
    padding: 12px 14px;
    margin-bottom: 10px;
}
.page-quests__line-select {
    min-width: 220px;
    max-width: 360px;
}
.page-quests__search-input {
    max-width: 320px;
    flex: 1 1 200px;
}
.page-quests__tree {
    background: transparent !important;
}
.page-quests__tree :deep(.el-tree-node__content) {
    cursor: pointer;
}
.page-quests__tree :deep(.el-tree-node__content):hover {
    background: var(--glass-bg-weak);
}
.page-quests__results {
    padding: 8px 0;
}
.page-quests__board-wrap {
    padding: 0 !important;
    overflow: hidden;
}
</style>
