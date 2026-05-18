<template>
    <div class="page">
        <header class="page__header">
            <h2>{{ t('robots.list.title') }}</h2>
            <el-button :icon="Refresh" @click="reloadAll">{{ t('common.refresh') }}</el-button>
        </header>

        <el-tabs v-model="tab" class="robots-tabs">
            <el-tab-pane name="registry" :label="t('robots.tabs.registry')">
                <div class="page__filters glass-card">
                    <el-form :inline="true" :model="regForm" class="robots-form">
                        <el-form-item :label="t('robots.register.client_id')">
                            <el-input v-model="regForm.client_id" :placeholder="t('robots.register.client_ph')" />
                        </el-form-item>
                        <el-form-item :label="t('robots.register.kind')">
                            <el-select v-model="regForm.kind" style="min-width: 160px">
                                <el-option value="ae" :label="t('robots.kind.ae')" />
                                <el-option value="crop" :label="t('robots.kind.crop')" />
                                <el-option value="miner" :label="t('robots.kind.miner')" />
                                <el-option value="power" :label="t('robots.kind.power')" />
                                <el-option value="scanner" :label="t('robots.kind.scanner')" />
                                <el-option value="generic" :label="t('robots.kind.generic')" />
                            </el-select>
                        </el-form-item>
                        <el-form-item :label="t('robots.register.label')">
                            <el-input v-model="regForm.label" :placeholder="t('robots.register.label_ph')" />
                        </el-form-item>
                        <el-form-item>
                            <el-button type="primary" @click="doRegister">{{ t('robots.register.submit') }}</el-button>
                        </el-form-item>
                        <el-form-item :label="t('robots.register.presets')">
                            <el-button size="small" @click="applyPreset('client_01', 'ae', 'OC ME controller')">
                                {{ t('robots.register.preset_ae') }}
                            </el-button>
                            <el-button size="small" @click="applyPreset('robot_miner_01', 'miner', '')">
                                {{ t('robots.register.preset_miner') }}
                            </el-button>
                        </el-form-item>
                    </el-form>
                </div>

                <el-empty v-if="!loading.robots && robots.length === 0" :description="t('robots.list.empty')" />

                <el-table v-else :data="robots" stripe v-loading="loading.robots" class="robots-table">
                    <el-table-column prop="client_id" :label="t('robots.list.columns.client_id')" min-width="180" />
                    <el-table-column :label="t('robots.list.columns.kind')" min-width="140">
                        <template #default="{ row }">{{ t(`robots.kind.${row.kind}`) || row.kind }}</template>
                    </el-table-column>
                    <el-table-column :label="t('robots.list.columns.state')" min-width="120">
                        <template #default="{ row }">
                            <el-tag :type="stateColor(row.state)">{{ t(`robots.state.${row.state}`) || row.state }}</el-tag>
                        </template>
                    </el-table-column>
                    <el-table-column prop="last_message" :label="t('robots.list.columns.last_message')" min-width="200" show-overflow-tooltip />
                    <el-table-column :label="t('common.actions')" width="220" fixed="right">
                        <template #default="{ row }">
                            <el-button size="small" @click="enqueueCropHarvest(row)">{{ t('robots.actions.harvest') }}</el-button>
                            <el-button size="small" @click="enqueueMinerPing(row)">{{ t('robots.actions.ping') }}</el-button>
                            <el-button size="small" @click="enqueuePowerPing(row)">{{ t('robots.actions.power_ping') }}</el-button>
                        </template>
                    </el-table-column>
                </el-table>
            </el-tab-pane>

            <el-tab-pane name="mining" :label="t('robots.tabs.mining')">
                <div class="page__filters glass-card">
                    <el-form :model="jobForm" label-position="top" class="robots-job-form">
                        <el-row :gutter="16">
                            <el-col :xs="24" :sm="8">
                                <el-form-item :label="t('robots.mining.robot_client')">
                                    <el-select
                                        v-model="jobForm.robot_client_id"
                                        filterable
                                        allow-create
                                        default-first-option
                                        :placeholder="t('robots.mining.robot_ph')"
                                        style="width: 100%"
                                    >
                                        <el-option
                                            v-for="r in robots"
                                            :key="r.client_id"
                                            :value="r.client_id"
                                            :label="robotOptionLabel(r)"
                                        />
                                    </el-select>
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="8">
                                <el-form-item :label="t('robots.mining.miner_kind')">
                                    <el-input v-model="jobForm.miner_kind" />
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="8">
                                <el-form-item :label="t('robots.mining.dimension')">
                                    <el-input-number v-model="jobForm.dimension" :min="0" style="width: 100%" />
                                </el-form-item>
                            </el-col>
                        </el-row>
                        <el-row :gutter="16">
                            <el-col :xs="24" :sm="8">
                                <el-form-item label="X">
                                    <el-input-number v-model="jobForm.x" style="width: 100%" />
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="8">
                                <el-form-item label="Y">
                                    <el-input-number v-model="jobForm.y" style="width: 100%" />
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="8">
                                <el-form-item label="Z">
                                    <el-input-number v-model="jobForm.z" style="width: 100%" />
                                </el-form-item>
                            </el-col>
                        </el-row>
                        <el-form-item :label="t('robots.mining.note')">
                            <el-input v-model="jobForm.note" type="textarea" :rows="2" />
                        </el-form-item>
                        <el-button type="primary" @click="createJob">{{ t('robots.mining.create') }}</el-button>
                    </el-form>
                </div>

                <el-table :data="jobs" stripe v-loading="loading.jobs" class="robots-table">
                    <el-table-column prop="id" label="ID" width="70" />
                    <el-table-column prop="robot_client_id" :label="t('robots.mining.robot_client')" min-width="140" />
                    <el-table-column prop="miner_kind" :label="t('robots.mining.miner_kind')" width="140" />
                    <el-table-column :label="t('robots.mining.coords')" min-width="140">
                        <template #default="{ row }">{{ row.x }}, {{ row.y }}, {{ row.z }} (d{{ row.dimension }})</template>
                    </el-table-column>
                    <el-table-column prop="state" :label="t('robots.mining.state')" width="110" />
                    <el-table-column :label="t('common.actions')" width="320" fixed="right">
                        <template #default="{ row }">
                            <el-button size="small" type="primary" @click="enqueueMinerJob(row, false)">{{ t('robots.mining.queue_accept') }}</el-button>
                            <el-button size="small" @click="enqueueMinerJob(row, true)">{{ t('robots.mining.queue_deploy') }}</el-button>
                            <el-button size="small" type="warning" @click="patchJob(row.id, 'done')">{{ t('robots.mining.mark_done') }}</el-button>
                        </template>
                    </el-table-column>
                </el-table>
            </el-tab-pane>

            <el-tab-pane name="power" :label="t('robots.tabs.power')">
                <div class="page__filters glass-card">
                    <el-form :model="powerForm" label-position="top" class="robots-job-form">
                        <el-row :gutter="16">
                            <el-col :xs="24" :sm="8">
                                <el-form-item :label="t('robots.power.robot_client')">
                                    <el-select
                                        v-model="powerForm.robot_client_id"
                                        filterable
                                        allow-create
                                        default-first-option
                                        :placeholder="t('robots.power.robot_ph')"
                                        style="width: 100%"
                                    >
                                        <el-option
                                            v-for="r in robots"
                                            :key="r.client_id"
                                            :value="r.client_id"
                                            :label="robotOptionLabel(r)"
                                        />
                                    </el-select>
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="8">
                                <el-form-item :label="t('robots.power.generator_kind')">
                                    <el-select v-model="powerForm.generator_kind" style="width: 100%">
                                        <el-option value="combustion_generator" label="combustion_generator" />
                                        <el-option value="advanced_combustion_generator" label="advanced_combustion_generator" />
                                        <el-option value="gas_turbine" label="gas_turbine" />
                                    </el-select>
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="8">
                                <el-form-item :label="t('robots.power.fuel_kind')">
                                    <el-select v-model="powerForm.fuel_kind" style="width: 100%">
                                        <el-option value="diesel" label="diesel" />
                                        <el-option value="gasoline" label="gasoline" />
                                        <el-option value="gas" label="gas" />
                                        <el-option value="ethanol" label="ethanol" />
                                    </el-select>
                                </el-form-item>
                            </el-col>
                        </el-row>
                        <el-row :gutter="16">
                            <el-col :xs="24" :sm="6">
                                <el-form-item :label="t('robots.power.capsule_count')">
                                    <el-input-number v-model="powerForm.capsule_count" :min="1" :max="16" style="width: 100%" />
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="6">
                                <el-form-item :label="t('robots.mining.dimension')">
                                    <el-input-number v-model="powerForm.dimension" :min="0" style="width: 100%" />
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="4">
                                <el-form-item label="X">
                                    <el-input-number v-model="powerForm.x" style="width: 100%" />
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="4">
                                <el-form-item label="Y">
                                    <el-input-number v-model="powerForm.y" style="width: 100%" />
                                </el-form-item>
                            </el-col>
                            <el-col :xs="24" :sm="4">
                                <el-form-item label="Z">
                                    <el-input-number v-model="powerForm.z" style="width: 100%" />
                                </el-form-item>
                            </el-col>
                        </el-row>
                        <el-form-item :label="t('robots.mining.note')">
                            <el-input v-model="powerForm.note" type="textarea" :rows="2" />
                        </el-form-item>
                        <el-button type="primary" @click="createPowerJob">{{ t('robots.power.create') }}</el-button>
                    </el-form>
                </div>

                <el-table :data="powerJobs" stripe v-loading="loading.power" class="robots-table">
                    <el-table-column prop="id" label="ID" width="70" />
                    <el-table-column prop="robot_client_id" :label="t('robots.power.robot_client')" min-width="120" />
                    <el-table-column prop="generator_kind" :label="t('robots.power.generator_kind')" width="200" />
                    <el-table-column prop="fuel_kind" :label="t('robots.power.fuel_kind')" width="100" />
                    <el-table-column :label="t('robots.mining.coords')" min-width="140">
                        <template #default="{ row }">{{ row.x }}, {{ row.y }}, {{ row.z }} (d{{ row.dimension }})</template>
                    </el-table-column>
                    <el-table-column prop="state" :label="t('robots.mining.state')" width="100" />
                    <el-table-column :label="t('common.actions')" width="280" fixed="right">
                        <template #default="{ row }">
                            <el-button size="small" type="primary" @click="enqueuePowerDeploy(row)">{{ t('robots.power.queue_deploy') }}</el-button>
                            <el-button size="small" type="success" @click="patchPowerJob(row.id, 'running')">{{ t('robots.mining.mark_running') }}</el-button>
                            <el-button size="small" type="warning" @click="patchPowerJob(row.id, 'done')">{{ t('robots.mining.mark_done') }}</el-button>
                        </template>
                    </el-table-column>
                </el-table>
            </el-tab-pane>
        </el-tabs>

        <p class="robots-hint">{{ t('robots.hint') }}</p>
    </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import { Refresh } from '@element-plus/icons-vue';
import { robotsApi, taskApi } from '@/api';

const { t } = useI18n();

const tab = ref('registry');
const robots = ref([]);
const jobs = ref([]);
const powerJobs = ref([]);
const loading = reactive({ robots: false, jobs: false, power: false });

const regForm = reactive({
    client_id: '',
    kind: 'crop',
    label: '',
});

const jobForm = reactive({
    robot_client_id: '',
    miner_kind: 'advanced_miner',
    dimension: 0,
    x: 0,
    y: 64,
    z: 0,
    note: '',
});

const powerForm = reactive({
    robot_client_id: '',
    generator_kind: 'advanced_combustion_generator',
    fuel_kind: 'diesel',
    capsule_count: 4,
    dimension: 0,
    x: 0,
    y: 64,
    z: 0,
    note: '',
});

function robotOptionLabel(row) {
    const kind = t(`robots.kind.${row.kind}`) || row.kind;
    return row.label ? `${row.client_id} — ${row.label} (${kind})` : `${row.client_id} (${kind})`;
}

function applyPreset(clientId, kind, label) {
    regForm.client_id = clientId;
    regForm.kind = kind;
    regForm.label = label;
}

function stateColor(state) {
    switch (state) {
        case 'idle': return 'info';
        case 'working':
        case 'moving':
        case 'returning':
        case 'unloading':
            return 'success';
        case 'error': return 'danger';
        default: return '';
    }
}

async function loadRobots() {
    loading.robots = true;
    try {
        robots.value = await robotsApi.list();
    } catch (e) {
        ElMessage.error(String(e));
    } finally {
        loading.robots = false;
    }
}

async function loadJobs() {
    loading.jobs = true;
    try {
        jobs.value = await robotsApi.miningJobsList();
    } catch (e) {
        ElMessage.error(String(e));
    } finally {
        loading.jobs = false;
    }
}

async function loadPowerJobs() {
    loading.power = true;
    try {
        powerJobs.value = await robotsApi.powerJobsList();
    } catch (e) {
        ElMessage.error(String(e));
    } finally {
        loading.power = false;
    }
}

async function reloadAll() {
    await Promise.all([loadRobots(), loadJobs(), loadPowerJobs()]);
}

async function doRegister() {
    if (!regForm.client_id.trim()) {
        ElMessage.warning(t('robots.register.need_id'));
        return;
    }
    try {
        await robotsApi.register({
            client_id: regForm.client_id.trim(),
            kind: regForm.kind,
            label: regForm.label.trim() || null,
        });
        ElMessage.success(t('common.success'));
        regForm.label = '';
        await loadRobots();
    } catch (e) {
        ElMessage.error(String(e));
    }
}

async function createJob() {
    if (!jobForm.robot_client_id.trim()) {
        ElMessage.warning(t('robots.mining.need_robot'));
        return;
    }
    try {
        const job = await robotsApi.miningJobCreate({
            robot_client_id: jobForm.robot_client_id.trim(),
            miner_kind: jobForm.miner_kind,
            dimension: jobForm.dimension,
            x: jobForm.x,
            y: jobForm.y,
            z: jobForm.z,
            note: jobForm.note || null,
        });
        const state = job?.state;
        if (state === 'running') {
            ElMessage.success(t('robots.mining.queued_on_create'));
        } else {
            ElMessage.success(t('common.success'));
        }
        await loadJobs();
    } catch (e) {
        ElMessage.error(String(e));
    }
}

async function enqueueMinerJob(row, deploy) {
    if (!row.robot_client_id) {
        ElMessage.warning(t('robots.mining.need_robot'));
        return;
    }
    try {
        await robotsApi.miningJobEnqueue(row.id, deploy);
        ElMessage.success(t('robots.actions.task_queued'));
        await loadJobs();
    } catch (e) {
        ElMessage.error(String(e));
    }
}

async function patchJob(id, state) {
    try {
        await robotsApi.miningJobPatch(id, { state });
        ElMessage.success(t('common.success'));
        await loadJobs();
    } catch (e) {
        ElMessage.error(String(e));
    }
}

async function createPowerJob() {
    if (!powerForm.robot_client_id.trim()) {
        ElMessage.warning(t('robots.power.need_robot'));
        return;
    }
    try {
        await robotsApi.powerJobCreate({
            robot_client_id: powerForm.robot_client_id.trim(),
            generator_kind: powerForm.generator_kind,
            fuel_kind: powerForm.fuel_kind,
            capsule_count: powerForm.capsule_count,
            dimension: powerForm.dimension,
            x: powerForm.x,
            y: powerForm.y,
            z: powerForm.z,
            note: powerForm.note || null,
        });
        ElMessage.success(t('common.success'));
        await loadPowerJobs();
    } catch (e) {
        ElMessage.error(String(e));
    }
}

async function patchPowerJob(id, state) {
    try {
        await robotsApi.powerJobPatch(id, { state });
        ElMessage.success(t('common.success'));
        await loadPowerJobs();
    } catch (e) {
        ElMessage.error(String(e));
    }
}

function buildPowerDeployCommand(job) {
    const gk = String(job.generator_kind).replace(/"/g, '\\"');
    const fk = String(job.fuel_kind).replace(/"/g, '\\"');
    return `return robot_power.deploy({ job_id=${job.id}, x=${job.x}, y=${job.y}, z=${job.z}, dim=${job.dimension}, generator_kind="${gk}", fuel_kind="${fk}", capsule_count=${job.capsule_count}, generator_slot=1, fuel_slots={2,3,4,5,6} })`;
}

/** Enqueue OC task: harvest below (see oc-client/plugins/robot_crop.lua). */
async function enqueueCropHarvest(row) {
    try {
        await taskApi.add({
            client_id: row.client_id,
            commands: ['return robot_crop.harvestBelow()'],
        });
        ElMessage.success(t('robots.actions.task_queued'));
    } catch (e) {
        ElMessage.error(String(e));
    }
}

async function enqueueMinerPing(row) {
    try {
        await taskApi.add({
            client_id: row.client_id,
            commands: ['return robot_miner.ping()'],
        });
        ElMessage.success(t('robots.actions.task_queued'));
    } catch (e) {
        ElMessage.error(String(e));
    }
}

async function enqueuePowerPing(row) {
    try {
        await taskApi.add({
            client_id: row.client_id,
            commands: ['return robot_power.ping()'],
        });
        ElMessage.success(t('robots.actions.task_queued'));
    } catch (e) {
        ElMessage.error(String(e));
    }
}

async function enqueuePowerDeploy(row) {
    if (!row.robot_client_id) {
        ElMessage.warning(t('robots.power.need_robot'));
        return;
    }
    try {
        await taskApi.add({
            client_id: row.robot_client_id,
            commands: [buildPowerDeployCommand(row)],
        });
        ElMessage.success(t('robots.actions.task_queued'));
    } catch (e) {
        ElMessage.error(String(e));
    }
}

reloadAll();
</script>

<style scoped>
.robots-tabs {
    margin-top: 8px;
}
.robots-table {
    width: 100%;
    margin-top: 12px;
}
.robots-hint {
    margin-top: 16px;
    font-size: 13px;
    color: var(--el-text-color-secondary);
    line-height: 1.5;
}
.robots-form {
    flex-wrap: wrap;
}
.glass-card {
    padding: 12px 16px;
    border-radius: var(--lg-radius, 12px);
    margin-bottom: 12px;
}
</style>
