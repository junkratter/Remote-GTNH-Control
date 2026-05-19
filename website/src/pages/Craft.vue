<template>
    <div class="page craft-page">
        <header class="craft-page__header glass-card">
            <div class="craft-page__titles">
                <h2>{{ t('craft.title') }}</h2>
                <p class="craft-page__subtitle">{{ t('craft.subtitle') }}</p>
            </div>
            <div class="craft-page__hdr-actions">
                <el-button :loading="loading.health" @click="loadHealth">{{ t('craft.health_btn') }}</el-button>
                <el-button :icon="Refresh" @click="refreshStock">{{ t('craft.stock_refresh') }}</el-button>
            </div>
        </header>

        <div class="craft-nei glass-card">
            <aside class="craft-nei__panel craft-nei__items">
                <el-input v-model="query.q" clearable :placeholder="t('craft.search_ph')" @keyup.enter="runSearch" />
                <div class="craft-nei__grid">
                    <button
                        v-for="it in items"
                        :key="it.id"
                        type="button"
                        class="craft-nei__slot"
                        :class="{ 'craft-nei__slot--sel': picked?.id === it.id }"
                        @click="pickItem(it)"
                    >
                        <img v-if="iconUrl(it)" :src="iconUrl(it)" alt="" class="craft-nei__ico" />
                        <span v-else class="craft-nei__ico-ph">?</span>
                    </button>
                </div>
                <div class="craft-nei__pager">
                    <el-button text :disabled="offset <= 0" @click="pagePrev">{{ t('craft.prev') }}</el-button>
                    <span>{{ offset + 1 }}–{{ offset + items.length }}</span>
                    <el-button text :disabled="items.length < limit" @click="pageNext">{{ t('craft.next') }}</el-button>
                </div>
            </aside>

            <main class="craft-nei__viewport">
                <div class="craft-nei__crumbs">
                    <el-tag
                        v-for="(c, i) in crumbs"
                        :key="i"
                        class="craft-nei__crumb"
                        effect="plain"
                        @click="crumbJump(i)"
                    >
                        {{ c.label }}
                    </el-tag>
                </div>

                <div class="craft-nei__modes">
                    <el-radio-group v-model="recipeMode" size="small">
                        <el-radio-button label="recipes">{{ t('craft.mode_recipes') }}</el-radio-button>
                        <el-radio-button label="uses">{{ t('craft.mode_uses') }}</el-radio-button>
                    </el-radio-group>
                    <div v-if="recipeList.length" class="craft-nei__recipe-nav">
                        <el-button text :disabled="recipeIdx <= 0" @click="recipeIdx -= 1">{{ t('craft.prev') }}</el-button>
                        <span>{{ recipeIdx + 1 }} / {{ recipeList.length }}</span>
                        <el-button text :disabled="recipeIdx >= recipeList.length - 1" @click="recipeIdx += 1">{{ t('craft.next') }}</el-button>
                    </div>
                </div>

                <WikiRecipeCraftingPanel
                    v-if="activeRecipe"
                    :recipe="activeRecipe"
                    :stock-qty-by-key="stockQtyByKey"
                    @select-item="onIngredientPick"
                />
                <el-empty v-else :description="t('craft.pick_item')" />

                <section class="craft-nei__plan glass-card craft-nei__plan--panel">
                    <h3>{{ t('craft.plan_panel') }}</h3>
                    <el-form label-position="top" :model="planForm" class="craft-nei__plan-form">
                        <el-form-item :label="t('craft.amount')">
                            <el-input-number v-model="planForm.amount" :min="1" />
                        </el-form-item>
                        <el-form-item :label="t('craft.client')">
                            <el-input v-model="planForm.client_id" clearable />
                        </el-form-item>
                        <el-form-item :label="t('craft.ae_stock_client')">
                            <el-input v-model="planForm.ae_stock_client_id" clearable />
                        </el-form-item>
                        <div class="craft-nei__plan-actions">
                            <el-button type="primary" :loading="loading.plan" :disabled="!goalAliasId" @click="submitPlan">
                                {{ t('craft.build_plan') }}
                            </el-button>
                            <el-button :disabled="!rootJobId" @click="refreshPlan">{{ t('craft.refresh_plan') }}</el-button>
                            <el-button :disabled="!rootJobId" @click="startPlan">{{ t('craft.start_plan') }}</el-button>
                        </div>
                    </el-form>
                    <pre v-if="planTreeText" class="craft-nei__plan-json">{{ planTreeText }}</pre>
                </section>
            </main>
        </div>
    </div>
</template>

<script setup>
import { Refresh } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import WikiRecipeCraftingPanel from '@/components/WikiRecipeCraftingPanel.vue';
import { craftApi, nesqlApi } from '@/api';
import Setting from '@/utils/setting';
import itemUtil from '@/utils/items';
import { openEventsStream } from '@/utils/events';

const { t } = useI18n();

const query = reactive({ q: '' });
const limit = 48;
const offset = ref(0);
const items = ref([]);
const loading = reactive({ items: false, plan: false, health: false });

const picked = ref(null);
const recipeMode = ref('recipes');
const recipeList = ref([]);
const recipeIdx = ref(0);
const crumbs = ref([]);

const planForm = reactive({ amount: 1, client_id: '', ae_stock_client_id: '' });
const goalAliasId = ref(null);
const rootJobId = ref(null);
const planTreeText = ref('');
const stockQtyByKey = ref({});

let sse = null;

const activeRecipe = computed(() => recipeList.value[recipeIdx.value] || null);

function apiBaseForEvents() {
    return Setting.get('backendUrl') || import.meta.env.VITE_API_BASE || '';
}

function iconUrl(it) {
    try {
        const def = itemUtil.fromNesqlItem(it);
        return def?.image || '';
    } catch {
        return '';
    }
}

async function runSearch() {
    loading.items = true;
    try {
        await itemUtil.loadItems();
        const r = await nesqlApi.items({ q: query.q || undefined, limit, offset: offset.value });
        items.value = r.data?.items || r.data || [];
    } catch (e) {
        ElMessage.error(String(e));
    } finally {
        loading.items = false;
    }
}

function pagePrev() {
    offset.value = Math.max(0, offset.value - limit);
    runSearch();
}

function pageNext() {
    offset.value += limit;
    runSearch();
}

async function pickItem(it) {
    picked.value = it;
    crumbs.value = [{ label: it.localized_name || it.unlocal_name || `#${it.id}`, item_id: it.id, damage: it.damage ?? 0 }];
    recipeIdx.value = 0;
    await loadRecipesForPick();
    await resolveGoalAlias(it.id, it.damage ?? 0);
}

async function loadRecipesForPick() {
    if (!picked.value) return;
    const id = picked.value.id;
    const params =
        recipeMode.value === 'uses'
            ? { input_item_id: id, limit: 80, offset: 0 }
            : { output_item_id: id, limit: 80, offset: 0 };
    try {
        const r = await nesqlApi.recipes(params);
        recipeList.value = r.data?.recipes || r.data || [];
        recipeIdx.value = 0;
    } catch (e) {
        ElMessage.error(String(e));
        recipeList.value = [];
    }
}

async function resolveGoalAlias(nesqlItemId, damage) {
    try {
        const r = await craftApi.resolveAlias(nesqlItemId, damage);
        goalAliasId.value = r.data?.alias_id ?? null;
    } catch {
        goalAliasId.value = null;
    }
}

async function onIngredientPick(itemId) {
    const damage = 0;
    try {
        const body = await nesqlApi.item(itemId);
        const it = body.data;
        crumbs.value.push({
            label: it.localized_name || it.unlocal_name || `#${itemId}`,
            item_id: itemId,
            damage: it.damage ?? 0,
        });
        picked.value = it;
        recipeMode.value = 'recipes';
        await loadRecipesForPick();
        await resolveGoalAlias(itemId, it.damage ?? 0);
    } catch (e) {
        ElMessage.error(String(e));
    }
}

async function crumbJump(idx) {
    crumbs.value = crumbs.value.slice(0, idx + 1);
    const c = crumbs.value[idx];
    if (!c) return;
    try {
        const body = await nesqlApi.item(c.item_id);
        picked.value = body.data;
        recipeIdx.value = 0;
        await loadRecipesForPick();
        await resolveGoalAlias(c.item_id, c.damage ?? body.data?.damage ?? 0);
    } catch (e) {
        ElMessage.error(String(e));
    }
}

watch(recipeMode, () => {
    loadRecipesForPick();
});

async function refreshStock() {
    if (!planForm.client_id?.trim() || !goalAliasId.value || !picked.value) {
        ElMessage.info(t('craft.stock_need'));
        return;
    }
    try {
        const r = await craftApi.stock(planForm.client_id.trim(), String(goalAliasId.value));
        const q = r.data?.quantities || {};
        const gid = goalAliasId.value;
        const amt = Number(q[gid] ?? q[String(gid)] ?? 0);
        const key = `${picked.value.id}_${picked.value.damage ?? 0}`;
        stockQtyByKey.value = { [key]: amt };
        ElMessage.success(t('common.success'));
    } catch (e) {
        ElMessage.error(String(e));
    }
}

async function loadHealth() {
    loading.health = true;
    try {
        const r = await craftApi.health();
        ElMessage.success(JSON.stringify(r.data));
    } catch (e) {
        ElMessage.error(String(e));
    } finally {
        loading.health = false;
    }
}

async function submitPlan() {
    if (!goalAliasId.value) return;
    loading.plan = true;
    try {
        const r = await craftApi.createPlan({
            goal_alias_id: goalAliasId.value,
            amount: planForm.amount,
            client_id: planForm.client_id || null,
            ae_stock_client_id: planForm.ae_stock_client_id || null,
        });
        rootJobId.value = r.data?.root_job_id ?? null;
        await refreshPlan();
        ElMessage.success(t('common.success'));
    } catch (e) {
        ElMessage.error(String(e));
    } finally {
        loading.plan = false;
    }
}

async function refreshPlan() {
    if (!rootJobId.value) return;
    try {
        const r = await craftApi.getPlan(rootJobId.value);
        planTreeText.value = JSON.stringify(r.data, null, 2);
    } catch (e) {
        ElMessage.error(String(e));
    }
}

async function startPlan() {
    if (!rootJobId.value) return;
    try {
        await craftApi.start(rootJobId.value, { client_id: planForm.client_id || null });
        ElMessage.success(t('common.success'));
        await refreshPlan();
    } catch (e) {
        ElMessage.error(String(e));
    }
}

function onSse(ev) {
    let outer;
    try {
        outer = JSON.parse(ev.data);
    } catch {
        return;
    }
    if (outer.topic !== 'craft') return;
    const p = outer.payload || {};
    if (p.root_job_id === rootJobId.value || p.root_id === rootJobId.value) refreshPlan();
}

function syncSse() {
    if (sse) sse.close();
    const token = Setting.get('token');
    if (!token) return;
    sse = openEventsStream(apiBaseForEvents(), token, onSse, { topics: ['craft'] });
}

watch(rootJobId, () => syncSse());

onMounted(() => {
    itemUtil.loadItems().catch(() => {});
    runSearch();
    syncSse();
});

onUnmounted(() => {
    if (sse) sse.close();
});
</script>

<style scoped>
.craft-page__header {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 12px;
    padding: 14px 16px;
    margin-bottom: 14px;
}
.craft-page__titles h2 {
    margin: 0;
    font-size: 20px;
}
.craft-page__subtitle {
    margin: 4px 0 0;
    font-size: 13px;
    color: var(--el-text-color-secondary);
}
.craft-page__hdr-actions {
    display: flex;
    gap: 8px;
    align-items: center;
}
.craft-nei {
    display: grid;
    grid-template-columns: minmax(200px, 260px) 1fr;
    gap: 12px;
    padding: 12px;
}
@media (max-width: 900px) {
    .craft-nei {
        grid-template-columns: 1fr;
    }
}
.craft-nei__panel {
    padding: 10px;
}
.craft-nei__grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(44px, 1fr));
    gap: 6px;
    margin-top: 10px;
    max-height: min(52vh, 520px);
    overflow: auto;
}
.craft-nei__slot {
    width: 44px;
    height: 44px;
    border: 2px solid #2e1e0ecc;
    background: linear-gradient(145deg, #c6c6c6 0%, #8a8a8a 55%, #6e6e6e 100%);
    padding: 0;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
}
.craft-nei__slot--sel {
    outline: 2px solid #409eff;
}
.craft-nei__ico {
    width: 36px;
    height: 36px;
    image-rendering: pixelated;
    object-fit: contain;
}
.craft-nei__ico-ph {
    font-size: 12px;
    opacity: 0.8;
}
.craft-nei__pager {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 10px;
    font-size: 12px;
}
.craft-nei__viewport {
    min-width: 0;
}
.craft-nei__crumbs {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 10px;
}
.craft-nei__crumb {
    cursor: pointer;
}
.craft-nei__modes {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 10px;
    align-items: center;
}
.craft-nei__recipe-nav {
    display: flex;
    gap: 8px;
    align-items: center;
    font-size: 13px;
}
.craft-nei__plan {
    margin-top: 14px;
    padding: 12px;
}
.craft-nei__plan-form {
    max-width: 420px;
}
.craft-nei__plan-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}
.craft-nei__plan-json {
    margin-top: 12px;
    max-height: 220px;
    overflow: auto;
    font-size: 11px;
    background: var(--el-fill-color-dark);
    padding: 8px;
    border-radius: 6px;
}
</style>
