<template>
    <div class="page">
        <header class="page__header">
            <h2>{{ t('wiki.title') }}</h2>
            <el-tag v-if="meta && !meta.available" type="warning" effect="plain" round>
                {{ t('wiki.meta.unavailable') }}
            </el-tag>
            <el-tag v-else-if="meta" type="success" effect="plain" round>
                {{ t('wiki.meta.imported', { count: itemsCount, size: formatBytes(meta.size_bytes) }) }}
            </el-tag>
        </header>

        <el-form :inline="true" class="page__filters">
            <el-form-item>
                <el-input
                    v-model="query"
                    :placeholder="t('wiki.search_placeholder')"
                    :prefix-icon="Search"
                    clearable
                    @input="onInput"
                    class="page-wiki__input"
                />
            </el-form-item>
            <el-form-item>
                <el-select
                    v-model="modId"
                    :placeholder="t('wiki.filter.mod_all')"
                    clearable
                    filterable
                    class="page-wiki__select"
                    @change="reload(0)"
                >
                    <el-option
                        v-for="mod in mods"
                        :key="mod.mod_id"
                        :label="`${mod.mod_id} (${mod.items_count})`"
                        :value="mod.mod_id"
                    />
                </el-select>
            </el-form-item>
        </el-form>

        <el-table
            v-loading="loading"
            :data="displayResults"
            stripe
            highlight-current-row
            class="page-wiki__table"
            @row-click="onRowClick"
        >
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column :label="t('wiki.col.name')" min-width="240">
                <template #default="{ row }">
                    {{ row.display_name }}
                </template>
            </el-table-column>
            <el-table-column prop="unlocal_name" :label="t('wiki.col.internal')" min-width="240" show-overflow-tooltip />
            <el-table-column prop="mod_id" :label="t('wiki.col.mod')" min-width="120" />
            <el-table-column prop="damage" :label="t('wiki.col.damage')" width="100" />
            <el-table-column prop="stack_size" :label="t('wiki.col.stack')" width="100" />
        </el-table>

        <el-pagination
            v-if="total > pageSize"
            :total="total"
            :page-size="pageSize"
            :current-page="page"
            background
            :layout="paginationLayout"
            class="page-wiki__pagination"
            @current-change="onPageChange"
        />

        <WikiItemDetailDialog v-model:visible="detailOpen" :item-id="selectedItemId" />
    </div>
</template>

<script setup>
import { computed, inject, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import { Search } from '@element-plus/icons-vue';
import { nesqlApi } from '@/api';
import itemUtil from '@/utils/items';
import WikiItemDetailDialog from '@/components/WikiItemDetailDialog.vue';

const { t } = useI18n();
const isMobile = inject('isMobile');
const paginationLayout = computed(() => (isMobile.value
    ? 'prev, pager, next'
    : 'prev, pager, next, total'));

const meta = ref(null);
const mods = ref([]);
const query = ref('');
const modId = ref(null);

const results = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = 50;
const loading = ref(false);

const selectedItemId = ref(null);
const detailOpen = ref(false);

const itemsCount = computed(() => {
    if (!meta.value || !meta.value.modules) return 0;
    const row = meta.value.modules.find((m) => m.module === 'items');
    return row ? row.row_count : 0;
});

const displayResults = computed(() =>
    results.value.map((row) => ({
        ...row,
        display_name: itemUtil.items
            ? itemUtil.nesqlDisplayName(row)
            : (row.localized_name || row.unlocal_name),
    })),
);

let debounce = null;

onMounted(async () => {
    itemUtil.loadItems();
    try {
        const m = await nesqlApi.meta();
        meta.value = m.data;
        if (m.data?.available) {
            const ms = await nesqlApi.mods();
            mods.value = ms.data || [];
            reload(0);
        }
    } catch (err) {
        ElMessage.error(String(err));
    }
});

function onInput() {
    if (debounce) clearTimeout(debounce);
    debounce = setTimeout(() => reload(0), 250);
}

function onPageChange(p) {
    reload((p - 1) * pageSize);
}

async function reload(offset) {
    if (!meta.value?.available) return;
    loading.value = true;
    try {
        const params = { limit: pageSize, offset };
        if (query.value) params.q = query.value;
        if (modId.value) params.mod_id = modId.value;
        const resp = await nesqlApi.items(params);
        results.value = resp.data?.items || [];
        total.value = resp.data?.total || 0;
        page.value = Math.floor(offset / pageSize) + 1;
    } catch (err) {
        ElMessage.error(String(err));
    } finally {
        loading.value = false;
    }
}

function onRowClick(row) {
    selectedItemId.value = row.id;
    detailOpen.value = true;
}

function formatBytes(bytes) {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    let v = bytes;
    while (v > 1024 && i < units.length - 1) {
        v /= 1024;
        i += 1;
    }
    return `${v.toFixed(1)} ${units[i]}`;
}
</script>

<style scoped>
.page-wiki__input { width: clamp(200px, 36vw, 360px); }
.page-wiki__select { width: clamp(160px, 26vw, 240px); }
.page-wiki__table { width: 100%; }
.page-wiki__pagination {
    display: flex;
    justify-content: flex-end;
    flex-wrap: wrap;
    gap: 8px;
}

@media (max-width: 640px) {
    .page-wiki__input,
    .page-wiki__select {
        width: 100% !important;
    }
}
</style>
