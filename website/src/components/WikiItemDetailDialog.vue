<template>
    <el-dialog
        v-model="visible"
        :title="headerTitle"
        width="min(720px, 94vw)"
        class="wiki-item-dialog"
        destroy-on-close
        @closed="onClosed"
    >
        <div v-loading="loading" class="wiki-item-dialog__body">
            <template v-if="item">
                <div class="wiki-item-dialog__hero">
                    <div class="mc-slot wiki-item-dialog__icon-slot">
                        <img v-if="resolved?.image" :src="resolved.image" class="mc-slot__img" alt="" />
                    </div>
                    <div>
                        <h3 class="wiki-item-dialog__name">{{ displayName }}</h3>
                        <p v-if="resolved?.subtitle" class="wiki-item-dialog__registry">
                            {{ resolved.subtitle }}
                        </p>
                    </div>
                </div>

                <p><b>ID:</b> {{ item.id }}</p>
                <p><b>{{ t('wiki.col.internal') }}:</b> {{ item.unlocal_name }}</p>
                <p><b>{{ t('wiki.col.mod') }}:</b> {{ item.mod_id }}</p>
                <p><b>{{ t('wiki.col.damage') }}:</b> {{ item.damage }}</p>
                <p v-if="item.nbt_hash"><b>NBT:</b> <code>{{ item.nbt_hash }}</code></p>

                <el-divider>{{ t('wiki.detail.oredict') }}</el-divider>
                <el-tag v-for="o in item.oredict || []" :key="o" style="margin: 0 4px 4px 0;">
                    {{ o }}
                </el-tag>
                <p v-if="!(item.oredict && item.oredict.length)" class="wiki-item-dialog__hint">
                    {{ t('wiki.detail.empty') }}
                </p>

                <el-divider>{{ t('wiki.detail.aspects') }}</el-divider>
                <el-tag
                    v-for="a in item.aspects || []"
                    :key="a.aspect_name"
                    type="info"
                    style="margin: 0 4px 4px 0;"
                >
                    {{ a.aspect_name }} × {{ a.amount }}
                </el-tag>
                <p v-if="!(item.aspects && item.aspects.length)" class="wiki-item-dialog__hint">
                    {{ t('wiki.detail.empty') }}
                </p>

                <el-divider>{{ t('wiki.detail.recipes_out') }}</el-divider>
                <p class="wiki-item-dialog__hint">{{ t('wiki.detail.recipe_click') }}</p>
                <el-table
                    v-if="outRecipes.length"
                    :data="outRecipes"
                    size="small"
                    highlight-current-row
                    @row-click="onOutRecipeClick"
                >
                    <el-table-column prop="id" label="ID" width="80" />
                    <el-table-column :label="t('wiki.detail.recipe_type')" min-width="200">
                        <template #default="{ row }">
                            {{ row.recipe_type_label || row.recipe_type }}
                        </template>
                    </el-table-column>
                    <el-table-column prop="duration" :label="t('wiki.detail.duration')" width="100" />
                    <el-table-column prop="eu_per_tick" label="EU/t" width="100" />
                </el-table>
                <p v-else class="wiki-item-dialog__hint">{{ t('wiki.detail.empty') }}</p>

                <WikiRecipeCraftingPanel
                    v-if="recipeDetail"
                    :recipe="recipeDetail"
                    @select-item="openNestedItem"
                />
            </template>
        </div>
    </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { nesqlApi } from '@/api';
import itemUtil from '@/utils/items';
import WikiRecipeCraftingPanel from '@/components/WikiRecipeCraftingPanel.vue';

const { t } = useI18n();

const props = defineProps({
    itemId: { type: Number, default: null },
});
const visible = defineModel('visible', { type: Boolean, default: false });

const loading = ref(false);
const item = ref(null);
const resolved = ref(null);
const outRecipes = ref([]);
const recipeDetail = ref(null);

const displayName = computed(() => resolved.value?.title || item.value?.localized_name || '');

const headerTitle = computed(() => displayName.value || t('wiki.detail.title'));

async function loadItem(id) {
    loading.value = true;
    item.value = null;
    resolved.value = null;
    outRecipes.value = [];
    recipeDetail.value = null;
    try {
        if (!itemUtil.items) itemUtil.loadItems();
        await waitForItems();
        const resp = await nesqlApi.item(id);
        item.value = resp.data;
        resolved.value = itemUtil.fromNesqlItem(resp.data);
        const recipes = await nesqlApi.recipes({ output_item_id: id, limit: 20 });
        outRecipes.value = recipes.data?.recipes || [];
    } catch {
        item.value = null;
    } finally {
        loading.value = false;
    }
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

async function onOutRecipeClick(row) {
    if (!row?.id) return;
    try {
        const resp = await nesqlApi.recipe(row.id);
        recipeDetail.value = resp.data;
    } catch {
        recipeDetail.value = null;
    }
}

function openNestedItem(itemId) {
    if (itemId == null || itemId <= 0) return;
    loadItem(itemId);
}

function onClosed() {
    item.value = null;
    resolved.value = null;
    outRecipes.value = [];
    recipeDetail.value = null;
}

watch(
    () => [visible.value, props.itemId],
    ([open, id]) => {
        if (open && id != null && id > 0) loadItem(id);
    },
);
</script>

<style scoped>
.wiki-item-dialog__body p {
    margin: 4px 0;
    word-break: break-word;
}
.wiki-item-dialog__hint {
    color: var(--el-text-color-secondary);
    font-style: italic;
    font-size: 13px;
}
.wiki-item-dialog__hero {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 12px;
}
.wiki-item-dialog__icon-slot {
    --mc-slot: 52px;
    width: var(--mc-slot);
    height: var(--mc-slot);
    flex-shrink: 0;
}
.wiki-item-dialog__name {
    margin: 0 0 4px;
    font-size: 1.15rem;
}
.wiki-item-dialog__registry {
    margin: 0;
    font-size: 12px;
    color: var(--el-text-color-secondary);
    font-family: var(--el-font-family-monospace);
}
</style>
