<template>
    <div class="page">
        <header class="page__header">
            <h2>{{ t('autocraft.title') }}</h2>
            <el-button :icon="Refresh" @click="loadAll">{{ t('common.refresh') }}</el-button>
        </header>

        <el-tabs v-model="tab" class="page-autocraft__tabs">
            <!-- Patterns -->
            <el-tab-pane name="patterns" :label="t('autocraft.patterns.title')">
                <div class="page__filters">
                    <el-button
                        type="primary"
                        :icon="Plus"
                        @click="openPatternDialog()"
                    >
                        {{ t('autocraft.patterns.add') }}
                    </el-button>
                </div>

                <el-empty
                    v-if="!loading.patterns && patterns.length === 0"
                    :description="t('autocraft.patterns.empty')"
                />

                <el-table
                    v-else
                    :data="patterns"
                    v-loading="loading.patterns"
                    stripe
                    class="page-autocraft__table"
                >
                    <el-table-column prop="id" :label="t('autocraft.patterns.col_id')" width="70" />
                    <el-table-column
                        prop="label"
                        :label="t('autocraft.patterns.col_label')"
                        min-width="160"
                        show-overflow-tooltip
                    />
                    <el-table-column
                        prop="interface_address"
                        :label="t('autocraft.patterns.col_iface')"
                        min-width="220"
                        show-overflow-tooltip
                    />
                    <el-table-column prop="slot" :label="t('autocraft.patterns.col_slot')" width="80" />
                    <el-table-column prop="kind" :label="t('autocraft.patterns.col_kind')" width="120" />
                    <el-table-column :label="t('common.actions')" min-width="220">
                        <template #default="{ row }">
                            <el-button size="small" @click.stop="openPatternDialog(row)">
                                {{ t('common.edit') }}
                            </el-button>
                            <el-button size="small" type="primary" @click.stop="programPattern(row)">
                                {{ t('autocraft.patterns.program') }}
                            </el-button>
                            <el-button size="small" type="danger" @click.stop="removePattern(row)">
                                {{ t('common.delete') }}
                            </el-button>
                        </template>
                    </el-table-column>
                </el-table>
            </el-tab-pane>

            <!-- Queue -->
            <el-tab-pane name="queue" :label="t('autocraft.requests.title')">
                <div class="page__filters">
                    <el-button type="primary" :icon="Plus" @click="openCraftDialog">
                        {{ t('autocraft.requests.request_item') }}
                    </el-button>
                    <el-button :icon="Cpu" @click="openCpuDialog">
                        {{ t('autocraft.cpus.scan') }}
                    </el-button>
                </div>

                <el-empty
                    v-if="!loading.requests && requests.length === 0"
                    :description="t('autocraft.requests.empty')"
                />

                <el-table
                    v-else
                    :data="requests"
                    v-loading="loading.requests"
                    stripe
                    class="page-autocraft__table"
                >
                    <el-table-column prop="id" :label="t('autocraft.requests.col_id')" width="70" />
                    <el-table-column
                        prop="client_id"
                        :label="t('autocraft.requests.col_client')"
                        min-width="120"
                        show-overflow-tooltip
                    />
                    <el-table-column prop="item_name" :label="t('autocraft.requests.col_item')" min-width="220" show-overflow-tooltip />
                    <el-table-column prop="amount" :label="t('autocraft.requests.col_amount')" width="100" />
                    <el-table-column prop="cpu_name" :label="t('autocraft.requests.col_cpu')" min-width="120" />
                    <el-table-column :label="t('autocraft.requests.col_state')" width="130">
                        <template #default="{ row }">
                            <el-tag :type="stateColor(row.state)" round>{{ requestStateLabel(row.state) }}</el-tag>
                        </template>
                    </el-table-column>
                    <el-table-column :label="t('common.actions')" width="120">
                        <template #default="{ row }">
                            <el-button
                                v-if="row.cpu_name"
                                size="small"
                                type="warning"
                                @click="cancelRequest(row)"
                            >
                                {{ t('common.cancel') }}
                            </el-button>
                        </template>
                    </el-table-column>
                </el-table>
            </el-tab-pane>

            <!-- Plan (server-side ME planner) -->
            <el-tab-pane name="plan" :label="t('autocraft.plan.title')">
                <p class="page-autocraft__wiki-hint">{{ t('autocraft.plan.hint') }}</p>
                <div class="page-autocraft__row">
                    <el-form label-position="top" :model="craftPlan.form" class="page-autocraft__col">
                        <el-form-item :label="t('autocraft.plan.goal_alias')">
                            <el-input-number v-model="craftPlan.form.goal_alias_id" :min="1" />
                        </el-form-item>
                        <el-form-item :label="t('autocraft.plan.amount')">
                            <el-input-number v-model="craftPlan.form.amount" :min="1" />
                        </el-form-item>
                        <el-form-item :label="t('autocraft.plan.client')">
                            <el-input v-model="craftPlan.form.client_id" clearable />
                        </el-form-item>
                    </el-form>
                </div>
                <div class="page-autocraft__wiki-toolbar">
                    <el-button type="primary" :loading="craftPlan.loading" @click="submitCraftPlan">
                        {{ t('autocraft.plan.build') }}
                    </el-button>
                    <el-button :disabled="!craftPlan.root_job_id" @click="refreshCraftTree">
                        {{ t('autocraft.plan.refresh_tree') }}
                    </el-button>
                </div>
                <div v-if="craftPlan.treeText" class="page-autocraft__tree-wrap">
                    <div class="page-autocraft__tree-label">{{ t('autocraft.plan.tree') }}</div>
                    <pre class="page-autocraft__tree">{{ craftPlan.treeText }}</pre>
                </div>
                <el-empty v-else :description="t('autocraft.plan.empty')" />
            </el-tab-pane>
        </el-tabs>

        <!-- Pattern editor -->
        <el-dialog
            v-model="patternDialog.visible"
            :title="patternDialog.editing ? t('autocraft.patterns.edit') : t('autocraft.patterns.add')"
            :width="dialogWidth"
            destroy-on-close
        >
            <el-form label-position="top" :model="patternDialog.form">
                <el-form-item :label="t('autocraft.patterns.field.label')">
                    <el-input v-model="patternDialog.form.label" />
                </el-form-item>
                <el-form-item :label="t('autocraft.patterns.field.iface')">
                    <el-input v-model="patternDialog.form.interface_address" />
                </el-form-item>
                <div class="page-autocraft__row">
                    <el-form-item :label="t('autocraft.patterns.field.slot')" class="page-autocraft__col">
                        <el-input-number v-model="patternDialog.form.slot" :min="1" :max="36" />
                    </el-form-item>
                    <el-form-item :label="t('autocraft.patterns.field.kind')" class="page-autocraft__col">
                        <el-select v-model="patternDialog.form.kind">
                            <el-option :label="t('autocraft.patterns.kind_processing')" value="processing" />
                            <el-option :label="t('autocraft.patterns.kind_crafting')" value="crafting" />
                        </el-select>
                    </el-form-item>
                </div>
                <el-form-item :label="t('autocraft.patterns.field.inputs')">
                    <ItemList v-model="patternDialog.form.inputs" />
                </el-form-item>
                <el-form-item :label="t('autocraft.patterns.field.outputs')">
                    <ItemList v-model="patternDialog.form.outputs" />
                </el-form-item>
            </el-form>
            <template #footer>
                <el-button type="default" @click="openWikiFromPattern">{{ t('autocraft.wiki.fill_from') }}</el-button>
                <el-button @click="patternDialog.visible = false">{{ t('common.cancel') }}</el-button>
                <el-button type="primary" @click="savePattern">{{ t('common.save') }}</el-button>
            </template>
        </el-dialog>

        <!-- NESQL recipe picker (pattern inputs/outputs) -->
        <el-dialog
            v-model="wikiDialog.visible"
            :title="t('autocraft.wiki.dialog_title')"
            :width="dialogWidth"
            destroy-on-close
            @closed="resetWikiDialog"
        >
            <el-alert :title="t('autocraft.wiki.hint')" type="info" show-icon class="page-autocraft__wiki-hint" />
            <div v-if="wikiDialog.mode === 'items'" class="page-autocraft__wiki-search">
                <el-input
                    v-model="wikiDialog.query"
                    :placeholder="t('autocraft.wiki.search_ph')"
                    clearable
                    @keyup.enter="searchWikiItems"
                />
                <el-button type="primary" :loading="wikiDialog.loading" @click="searchWikiItems">
                    {{ t('autocraft.wiki.search_btn') }}
                </el-button>
            </div>
            <el-empty v-if="wikiDialog.mode === 'items' && !wikiDialog.loading && wikiDialog.items.length === 0" :description="t('autocraft.wiki.no_items')" />
            <el-table
                v-if="wikiDialog.mode === 'items' && wikiDialog.items.length"
                :data="wikiDialog.items"
                max-height="360"
                class="page-autocraft__table"
                @row-click="wikiPickItem"
            >
                <el-table-column prop="localized_name" :label="t('autocraft.requests.col_item')" min-width="200" />
                <el-table-column prop="unlocal_name" min-width="220" show-overflow-tooltip />
            </el-table>

            <div v-if="wikiDialog.mode === 'recipes'" class="page-autocraft__wiki-toolbar">
                <el-button text type="primary" @click="wikiBackToItems">{{ t('autocraft.wiki.back') }}</el-button>
                <span class="page-autocraft__wiki-for">{{ t('autocraft.wiki.recipes_for') }}: {{ wikiDialog.pickedLabel }}</span>
            </div>
            <el-empty
                v-if="wikiDialog.mode === 'recipes' && !wikiDialog.loading && wikiDialog.recipes.length === 0"
                :description="t('autocraft.wiki.no_recipes')"
            />
            <el-table
                v-if="wikiDialog.mode === 'recipes' && wikiDialog.recipes.length"
                :data="wikiDialog.recipes"
                max-height="360"
                class="page-autocraft__table"
            >
                <el-table-column min-width="280">
                    <template #default="{ row }">
                        {{
                            t('autocraft.wiki.recipe_line', {
                                type: row.recipe_type || '—',
                                eu: row.eu_per_tick ?? '—',
                                ticks: row.duration ?? '—',
                            })
                        }}
                    </template>
                </el-table-column>
                <el-table-column width="120" align="right">
                    <template #default="{ row }">
                        <el-button size="small" type="primary" @click="applyWikiRecipe(row)">
                            {{ t('autocraft.wiki.apply') }}
                        </el-button>
                    </template>
                </el-table-column>
            </el-table>
            <template #footer>
                <el-button @click="wikiDialog.visible = false">{{ t('common.cancel') }}</el-button>
            </template>
        </el-dialog>

        <!-- Craft request -->
        <el-dialog
            v-model="craftDialog.visible"
            :title="t('autocraft.requests.request_item')"
            :width="dialogWidth"
        >
            <el-form label-position="top" :model="craftDialog.form">
                <el-form-item :label="t('autocraft.requests.field.client')">
                    <el-input v-model="craftDialog.form.client_id" />
                </el-form-item>
                <el-form-item :label="t('autocraft.requests.field.item')">
                    <el-input v-model="craftDialog.form.item_name" />
                </el-form-item>
                <div class="page-autocraft__row">
                    <el-form-item :label="t('autocraft.requests.field.damage')" class="page-autocraft__col">
                        <el-input-number v-model="craftDialog.form.item_damage" :min="0" />
                    </el-form-item>
                    <el-form-item :label="t('autocraft.requests.field.amount')" class="page-autocraft__col">
                        <el-input-number v-model="craftDialog.form.amount" :min="1" />
                    </el-form-item>
                </div>
                <el-form-item :label="t('autocraft.requests.field.cpu')">
                    <el-input v-model="craftDialog.form.cpu_name" />
                </el-form-item>
            </el-form>
            <template #footer>
                <el-button @click="craftDialog.visible = false">{{ t('common.cancel') }}</el-button>
                <el-button type="primary" @click="submitCraft">{{ t('autocraft.requests.submit') }}</el-button>
            </template>
        </el-dialog>

        <!-- CPU scan -->
        <el-dialog
            v-model="cpuDialog.visible"
            :title="t('autocraft.cpus.scan')"
            :width="dialogWidth"
        >
            <el-form label-position="top" :model="cpuDialog.form">
                <el-form-item :label="t('autocraft.requests.field.client')">
                    <el-input v-model="cpuDialog.form.client_id" />
                </el-form-item>
                <el-form-item>
                    <el-checkbox v-model="cpuDialog.form.detail">
                        {{ t('autocraft.cpus.detail') }}
                    </el-checkbox>
                </el-form-item>
            </el-form>
            <template #footer>
                <el-button @click="cpuDialog.visible = false">{{ t('common.cancel') }}</el-button>
                <el-button type="primary" @click="submitCpuScan">{{ t('common.confirm') }}</el-button>
            </template>
        </el-dialog>
    </div>
</template>

<script setup>
import { computed, inject, onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Refresh, Plus, Cpu } from '@element-plus/icons-vue';
import { autocraftApi, craftApi, nesqlApi } from '@/api';
import itemUtil from '@/utils/items';
import Setting from '@/utils/setting';
import { openEventsStream } from '@/utils/events';

import ItemList from '@/components/ItemList.vue';

const { t } = useI18n();
const isMobile = inject('isMobile');

const tab = ref('patterns');
const patterns = ref([]);
const requests = ref([]);
const loading = reactive({ patterns: false, requests: false });

/** Suppress repeated “awaiting choice” dialogs until the tree is clean or a new plan is built. */
const awaitingChoiceAlertShown = ref(false);

const dialogWidth = computed(() => (isMobile.value ? '92%' : '520px'));

const patternDialog = reactive({
    visible: false,
    editing: null,
    form: emptyPattern(),
});

const craftDialog = reactive({
    visible: false,
    form: emptyCraft(),
});

const cpuDialog = reactive({
    visible: false,
    form: { client_id: '', detail: true },
});

const wikiDialog = reactive({
    visible: false,
    mode: 'items',
    query: '',
    loading: false,
    items: [],
    recipes: [],
    pickedLabel: '',
    pickedItemId: null,
});

function emptyPattern() {
    return {
        label: '',
        interface_address: '',
        slot: 1,
        kind: 'processing',
        inputs: [],
        outputs: [],
    };
}
function emptyCraft() {
    return {
        client_id: '',
        item_name: '',
        item_damage: 0,
        amount: 1,
        cpu_name: '',
    };
}

function stateColor(state) {
    switch (state) {
        case 'queued': return 'info';
        case 'cancelling': return 'warning';
        case 'done': return 'success';
        case 'failed': return 'danger';
        default: return '';
    }
}

function requestStateLabel(state) {
    const key = `autocraft.requests.state.${state}`;
    const translated = t(key);
    return translated === key ? state : translated;
}

function inferPatternKind(recipeType) {
    const s = (recipeType || '').toLowerCase();
    if (
        (s.includes('minecraft') && (s.includes('shaped') || s.includes('shapeless'))) ||
        (s.includes('rt~minecraft') &&
            (s.includes('shaped') || s.includes('shapeless') || s.includes('crafting')))
    ) {
        return 'crafting';
    }
    return 'processing';
}

function resetWikiDialog() {
    wikiDialog.mode = 'items';
    wikiDialog.query = '';
    wikiDialog.items = [];
    wikiDialog.recipes = [];
    wikiDialog.pickedLabel = '';
    wikiDialog.pickedItemId = null;
    wikiDialog.loading = false;
}

function openWikiFromPattern() {
    resetWikiDialog();
    wikiDialog.visible = true;
}

async function searchWikiItems() {
    wikiDialog.loading = true;
    wikiDialog.items = [];
    try {
        const resp = await nesqlApi.items({ q: wikiDialog.query || '', limit: 80 });
        wikiDialog.items = resp.data?.items || [];
    } catch (err) {
        ElMessage.error(String(err));
    } finally {
        wikiDialog.loading = false;
    }
}

async function wikiPickItem(row) {
    if (!row?.id) return;
    wikiDialog.pickedItemId = row.id;
    wikiDialog.pickedLabel = row.localized_name || row.unlocal_name || String(row.id);
    wikiDialog.mode = 'recipes';
    wikiDialog.loading = true;
    wikiDialog.recipes = [];
    try {
        const resp = await nesqlApi.recipes({ output_item_id: row.id, limit: 60 });
        wikiDialog.recipes = resp.data?.recipes || [];
    } catch (err) {
        ElMessage.error(String(err));
    } finally {
        wikiDialog.loading = false;
    }
}

function wikiBackToItems() {
    wikiDialog.mode = 'items';
    wikiDialog.recipes = [];
    wikiDialog.pickedItemId = null;
    wikiDialog.pickedLabel = '';
}

async function applyWikiRecipe(row) {
    wikiDialog.loading = true;
    let skippedFluids = 0;
    try {
        const resp = await nesqlApi.recipe(row.id);
        const recipe = resp.data;
        if (!recipe) {
            ElMessage.error(t('common.empty_response'));
            return;
        }
        const inputs = [];
        for (const slot of recipe.inputs || []) {
            if (slot.fluid_id) {
                skippedFluids += 1;
                continue;
            }
            if (!slot.item_id) continue;
            const itBody = await nesqlApi.item(slot.item_id);
            const it = itBody.data;
            const reg = itemUtil.nesqlToRegistry(it);
            if (!reg?.name) continue;
            inputs.push({
                name: reg.name,
                damage: reg.damage ?? 0,
                amount: slot.amount ?? 1,
            });
        }
        const outputs = [];
        for (const slot of recipe.outputs || []) {
            if (slot.fluid_id) {
                skippedFluids += 1;
                continue;
            }
            if (!slot.item_id) continue;
            const itBody = await nesqlApi.item(slot.item_id);
            const it = itBody.data;
            const reg = itemUtil.nesqlToRegistry(it);
            if (!reg?.name) continue;
            const out = {
                name: reg.name,
                damage: reg.damage ?? 0,
                amount: slot.amount ?? 1,
            };
            if (slot.chance != null && slot.chance !== 100) {
                out.label = `chance=${slot.chance}`;
            }
            outputs.push(out);
        }
        patternDialog.form.inputs = inputs;
        patternDialog.form.outputs = outputs;
        patternDialog.form.kind = inferPatternKind(recipe.recipe_type);
        if (skippedFluids > 0) {
            ElMessage.warning(t('autocraft.wiki.skipped_fluids'));
        }
        ElMessage.success(t('common.success'));
        wikiDialog.visible = false;
    } catch (err) {
        ElMessage.error(String(err));
    } finally {
        wikiDialog.loading = false;
    }
}

const craftPlan = reactive({
    loading: false,
    root_job_id: null,
    treeText: '',
    form: { goal_alias_id: 1, amount: 1, client_id: '' },
});

async function submitCraftPlan() {
    craftPlan.loading = true;
    try {
        const r = await craftApi.createPlan({
            goal_alias_id: craftPlan.form.goal_alias_id,
            amount: craftPlan.form.amount,
            client_id: craftPlan.form.client_id || null,
        });
        const d = r.data;
        craftPlan.root_job_id = d?.root_job_id ?? null;
        awaitingChoiceAlertShown.value = false;
        await refreshCraftTree();
        ElMessage.success(t('common.success'));
    } catch (err) {
        ElMessage.error(String(err));
    } finally {
        craftPlan.loading = false;
    }
}

async function refreshCraftTree() {
    if (!craftPlan.root_job_id) return;
    try {
        const r = await craftApi.getPlan(craftPlan.root_job_id);
        craftPlan.treeText = JSON.stringify(r.data, null, 2);
        maybeAlertAwaitingChoice(craftPlan.treeText);
    } catch (err) {
        ElMessage.error(String(err));
    }
}

let planEventsHandle = null;

function stopPlanEvents() {
    if (planEventsHandle) {
        planEventsHandle.close();
        planEventsHandle = null;
    }
}

function apiBaseForEvents() {
    return Setting.get('backendUrl') || import.meta.env.VITE_API_BASE || '';
}

function eventConcernsCurrentPlan(payload, rootId) {
    if (!rootId || !payload || typeof payload !== 'object') return false;
    return payload.root_job_id === rootId || payload.root_id === rootId;
}

function onPlanSseMessage(ev) {
    let outer;
    try {
        outer = JSON.parse(ev.data);
    } catch {
        return;
    }
    if (outer.topic !== 'craft') return;
    const rid = craftPlan.root_job_id;
    if (!eventConcernsCurrentPlan(outer.payload || {}, rid)) {
        return;
    }
    refreshCraftTree();
}

function syncPlanEventsSubscription() {
    stopPlanEvents();
    if (tab.value !== 'plan') return;
    const token = Setting.get('token');
    if (!token) return;
    planEventsHandle = openEventsStream(apiBaseForEvents(), token, onPlanSseMessage, {
        topics: ['craft'],
    });
}

function maybeAlertAwaitingChoice(treeJson) {
    let obj;
    try {
        obj = JSON.parse(treeJson);
    } catch {
        return;
    }
    const jobs = obj.jobs || [];
    const pending = jobs.some((j) => j.state === 'awaiting_choice');
    if (pending) {
        if (!awaitingChoiceAlertShown.value) {
            awaitingChoiceAlertShown.value = true;
            ElMessageBox.alert(
                t('autocraft.plan.awaiting_choice_body'),
                t('autocraft.plan.awaiting_choice_title'),
                { type: 'warning' },
            );
        }
    } else {
        awaitingChoiceAlertShown.value = false;
    }
}

async function loadAll() {
    await Promise.all([loadPatterns(), loadRequests()]);
}

async function loadPatterns() {
    loading.patterns = true;
    try {
        const resp = await autocraftApi.listPatterns();
        patterns.value = resp.data || [];
    } catch (err) { ElMessage.error(String(err)); }
    finally { loading.patterns = false; }
}

async function loadRequests() {
    loading.requests = true;
    try {
        const resp = await autocraftApi.requests();
        requests.value = resp.data || [];
    } catch (err) { ElMessage.error(String(err)); }
    finally { loading.requests = false; }
}

function openPatternDialog(row) {
    patternDialog.editing = row || null;
    patternDialog.form = row
        ? {
            label: row.label || '',
            interface_address: row.interface_address,
            slot: row.slot,
            kind: row.kind,
            inputs: [...(row.inputs || [])],
            outputs: [...(row.outputs || [])],
        }
        : emptyPattern();
    patternDialog.visible = true;
}

async function savePattern() {
    try {
        await autocraftApi.upsertPattern({
            label: patternDialog.form.label || null,
            interface_address: patternDialog.form.interface_address,
            slot: patternDialog.form.slot,
            kind: patternDialog.form.kind,
            inputs: patternDialog.form.inputs,
            outputs: patternDialog.form.outputs,
        });
        ElMessage.success(t('common.success'));
        patternDialog.visible = false;
        await loadPatterns();
    } catch (err) {
        ElMessage.error(String(err));
    }
}

async function removePattern(row) {
    try {
        await ElMessageBox.confirm(
            t('autocraft.patterns.confirm_delete', { id: row.id }),
            t('common.confirm'),
            { type: 'warning' },
        );
    } catch { return; }
    try {
        await autocraftApi.deletePattern(row.id);
        await loadPatterns();
    } catch (err) {
        ElMessage.error(String(err));
    }
}

async function programPattern(row) {
    try {
        const { value: clientId } = await ElMessageBox.prompt(
            t('autocraft.patterns.program_prompt'),
            t('autocraft.patterns.program'),
        );
        if (!clientId) return;
        await autocraftApi.programPattern(row.id, clientId);
        ElMessage.success(t('common.success'));
    } catch (err) {
        if (err === 'cancel' || err === 'close') return;
        ElMessage.error(String(err));
    }
}

function openCraftDialog() {
    craftDialog.form = emptyCraft();
    craftDialog.visible = true;
}

async function submitCraft() {
    try {
        await autocraftApi.request({
            client_id: craftDialog.form.client_id,
            item_name: craftDialog.form.item_name,
            item_damage: craftDialog.form.item_damage,
            amount: craftDialog.form.amount,
            cpu_name: craftDialog.form.cpu_name || null,
        });
        ElMessage.success(t('common.success'));
        craftDialog.visible = false;
        await loadRequests();
    } catch (err) { ElMessage.error(String(err)); }
}

async function cancelRequest(row) {
    try {
        await autocraftApi.cancelRequest(row.id);
        await loadRequests();
    } catch (err) { ElMessage.error(String(err)); }
}

function openCpuDialog() {
    cpuDialog.visible = true;
}

async function submitCpuScan() {
    try {
        const resp = await autocraftApi.scanCpus(cpuDialog.form.client_id, cpuDialog.form.detail);
        ElMessage.success(`${t('common.success')} (task ${resp.data.task_id})`);
        cpuDialog.visible = false;
    } catch (err) { ElMessage.error(String(err)); }
}

onMounted(() => {
    loadAll();
    syncPlanEventsSubscription();
});
onUnmounted(stopPlanEvents);
watch(tab, () => {
    syncPlanEventsSubscription();
});
</script>

<style scoped>
.page-autocraft__tabs :deep(.el-tabs__nav-wrap) {
    padding: 0 4px;
}
.page-autocraft__table { width: 100%; }
.page-autocraft__row {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
}
.page-autocraft__col { flex: 1 1 180px; min-width: 0; }
.page-autocraft__wiki-hint { margin-bottom: 12px; }
.page-autocraft__wiki-search {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
    flex-wrap: wrap;
}
.page-autocraft__wiki-search .el-input { flex: 1 1 200px; min-width: 0; }
.page-autocraft__wiki-toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;
    flex-wrap: wrap;
}
.page-autocraft__tree-wrap { margin-top: 12px; }
.page-autocraft__tree-label { font-size: 13px; margin-bottom: 6px; opacity: 0.85; }
.page-autocraft__tree {
    margin: 0;
    font-size: 12px;
    overflow: auto;
    max-height: 420px;
    padding: 10px;
    border-radius: 6px;
    background: var(--el-fill-color-light);
}
</style>
