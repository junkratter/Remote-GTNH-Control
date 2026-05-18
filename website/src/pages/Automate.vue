<template>
    <el-container style="height: 100%;">
        <el-header class="control-header-task">
            <el-card class="control-card" shadow="hover">
                <div class="control-bar">
                    <span>{{ $t('automate_page.last_update') }}: {{ lastUpdate }}</span>
                    <div style="text-align: right;">
                        <el-button type="primary" :size="isMobile ? 'small' : ''"
                            @click="showAutoTaskDialog">{{ $t('automate_page.add_task') }}</el-button>
                        <el-button type="primary" :size="isMobile ? 'small' : ''"
                            @click="loadAutoTasks">{{ $t('automate_page.refresh') }}</el-button>
                    </div>
                </div>
            </el-card>
        </el-header>
        <el-main style="width: 100%; overflow: hidden;" v-loading="mainLoading" :element-loading-text="$t('automate_page.loading')">
            <el-card class="table-box-card">
                <el-table :data="tasks" border stripe style="width: 100%; height: 100%;">
                    <el-table-column type="index" :label="$t('automate_page.col_index')" width="80"  align="center"></el-table-column>
                    <el-table-column prop="id" :label="$t('automate_page.col_id')" width="320" align="center"></el-table-column>
                    <el-table-column prop="type" :label="$t('automate_page.col_type')" min-width="120" align="center">
                        <template #default="{ row }">{{ displayTaskType(row.type) }}</template>
                    </el-table-column>
                    <el-table-column prop="name" :label="$t('automate_page.col_trigger')" min-width="120" align="center">
                        <template #default="{ row }">{{ displayCatalogName(row.name) }}</template>
                    </el-table-column>
                    <el-table-column prop="action.name" :label="$t('automate_page.col_action')" min-width="100" align="center">
                        <template #default="{ row }">{{ displayActionName(row.action) }}</template>
                    </el-table-column>
                    <el-table-column prop="status" :label="$t('automate_page.col_status')" min-width="85" align="center">
                        <template #default="{ row }">
                            <el-tag :type="statusMap[row.status]?.type || 'info'">{{ statusMap[row.status]?.text || row.status }}</el-tag>
                        </template>
                    </el-table-column>
                    <el-table-column :label="$t('automate_page.col_ops')" width="120" align="center" fixed="right">
                        <template #default="{ row }">
                            <div class="op-button-grid">
                                <el-button type="success" size="small" plain
                                    @click="handleStart(row)" :disabled="row.running || row.status === 'completed'">
                                    {{ $t('automate_page.start') }}
                                </el-button>
                                <el-button type="warning" size="small" plain
                                    @click="handleStop(row)" :disabled="!row.running || row.status === 'completed'">
                                    {{ $t('automate_page.stop') }}
                                </el-button>
                                <el-button size="small" plain @click="handleInfo(row)">{{ $t('automate_page.detail_btn') }}</el-button>
                                <el-button type="danger" size="small" plain @click="handleRemove(row)">{{ $t('automate_page.remove_btn') }}</el-button>
                            </div>
                        </template>
                    </el-table-column>
                </el-table>
            </el-card>
        </el-main>
        <!-- Task detail -->
        <el-dialog v-model="showInfoDialog" class="task-dialog" :title="$t('automate_page.detail_title')" fullscreen align-center>
            <el-scrollbar>
                <div class="info-container">
                    <el-space alignment="normal" direction="vertical" style="width: 100%; margin-bottom: 20px;">
                        <el-descriptions :title="$t('automate_page.basic_info')" :column="1" border label-width="80px">
                            <el-descriptions-item :label="$t('automate_page.col_id')">{{ info.id }}</el-descriptions-item>
                            <el-descriptions-item :label="$t('automate_page.col_type')">{{ displayTaskType(info.type) }}</el-descriptions-item>
                            <el-descriptions-item :label="$t('automate_page.col_status')">
                                <el-tag :type="statusMap[info.status]?.type || 'info'">{{ statusMap[info.status]?.text || info.status }}</el-tag>
                            </el-descriptions-item>
                            <el-descriptions-item v-if="info.type === 'trigger'" :label="$t('automate_page.poll_interval')">
                                {{ info.interval }} {{ $t('automate_page.sec') }}
                            </el-descriptions-item>

                        </el-descriptions>

                        <el-divider></el-divider>
                        <el-text size="large">{{ $t('automate_page.lifecycle') }}</el-text>

                        <el-timeline style="margin-top: 20px; width: 100%;">
                            <el-timeline-item :timestamp="info.time.created" size="large" color="#409EFF">
                                {{ $t('automate_page.timeline_created') }}
                            </el-timeline-item>
                            <el-timeline-item v-if="info.time.last_start" :timestamp="info.time.last_start" size="large"
                                color="#67C23A">
                                {{ $t('automate_page.timeline_start') }}
                            </el-timeline-item>
                            <el-timeline-item v-if="info.time.last_monitor" :timestamp="info.time.last_monitor"
                                size="large" color="#E6A23C">
                                {{ $t('automate_page.timeline_monitor') }}
                            </el-timeline-item>
                            <el-timeline-item v-if="info.time.excuted" :timestamp="info.time.excuted" size="large"
                                :color="info.time.completed ? '#E6A23C' : ''">
                                {{ $t('automate_page.timeline_execute') }} {{ info.time.completed ? '' : $t('automate_page.timeline_execute_est') }}
                            </el-timeline-item>
                            <el-timeline-item v-if="info.time.completed" :timestamp="info.time.completed" size="large"
                                color="#F56C6C">
                                {{ $t('automate_page.timeline_done') }}
                            </el-timeline-item>
                        </el-timeline>
                        <el-divider></el-divider>
                        <el-descriptions :title="$t('automate_page.trigger_section')" :column="1" border label-width="150px">
                            <el-descriptions-item :label="$t('automate_page.col_type')">{{ displayCatalogName(info.name) }}</el-descriptions-item>
                            <el-descriptions-item :label="$t('automate_page.template_col_desc')">{{ info.description }}</el-descriptions-item>
                            <el-descriptions-item v-for="arg in info.args" :key="arg.field" :label="arg.description">
                                <el-text>{{ info.kwargs[arg.field] }}</el-text>
                            </el-descriptions-item>
                        </el-descriptions>
                        <el-divider></el-divider>
                        <el-descriptions :title="$t('automate_page.action_section')" :column="1" border label-width="150px">
                            <el-descriptions-item :label="$t('automate_page.col_type')">{{ displayActionName(info.action) }}</el-descriptions-item>
                            <el-descriptions-item :label="$t('automate_page.template_col_desc')">{{ info.action.description }}</el-descriptions-item>
                            <el-descriptions-item v-if="isCraftAction(info.action)" :label="$t('automate_page.craft_target')">
                                <ItemCard class="item-card-container" :item="{
                                    name: info.action.action_kwargs.item_name,
                                    damage: info.action.action_kwargs.item_damage,
                                    amount: info.action.action_kwargs.item_amount,
                                    label: info.action.action_kwargs.label,
                                }" />
                            </el-descriptions-item>
                            <el-descriptions-item v-for="arg in info.action.args" :key="arg.field"
                                :label="arg.description">
                                <el-text>{{ info.action.action_kwargs[arg.field] }}</el-text>
                            </el-descriptions-item>
                        </el-descriptions>
                        <el-divider></el-divider>
                        <el-text size="large">
                            {{ $t('automate_page.result') }}
                            <TaskResult v-if="isCraftAction(info.action) && info.result" :task_id="info.result.data" />
                        </el-text>
                        <el-text size="large" v-if="info.result" style="width: 100%;">
                            <el-scrollbar>
                                <pre>{{ info.result }}</pre>
                            </el-scrollbar>
                        </el-text>
                        <el-text size="large" v-else>
                            {{ $t('automate_page.none') }}
                        </el-text>
                    </el-space>
                </div>
            </el-scrollbar>
        </el-dialog>
        <!-- Add automation -->
        <el-dialog v-model="showAddTaskDialog" class="task-dialog" :title="$t('automate_page.add_title')" fullscreen align-center>
            <el-scrollbar>
                <div class="info-container">
                    <el-form :model="form" label-width="auto">
                        <el-form-item :label="$t('automate_page.form_trigger')" :required="true">
                            <el-select-v2 v-model="form.name" :placeholder="$t('automate_page.form_trigger_ph')" :options="options.name"
                                @change="resetFormAndLoadActions()">
                                <template #default="{ item }">
                                    <div
                                        style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
                                        <span style="flex: 0 0 80px; text-align: left; margin-right: 8px;">
                                            {{ item.label }}
                                        </span>
                                        <span style="flex: 1; color: var(--el-text-color-secondary); font-size: 13px;">
                                            {{ item.desc }}
                                        </span>
                                    </div>
                                </template>
                            </el-select-v2>
                        </el-form-item>
                        <template v-if="form.name === 'cpu_idle'">
                            <el-form-item :label="$t('automate_page.watch_cpu')" :required="true">
                                <CpuSelect status="busy" :footer="$t('automate_page.cpu_busy_footer')" :options="options.cpuList"
                                    :onlyNamed="true" @handleCpuSelected="onTriggerCpuSelected"
                                    @handleLoadCpuList="onLoadCpuList" />
                            </el-form-item>
                            <el-form-item :label="$t('automate_page.client_id')">
                                <el-tooltip effect="dark" :content="$t('automate_page.client_id_tip')" placement="top">
                                    <el-input v-model="form.trigger_kwargs.client_id" :placeholder="$t('automate_page.client_id_ph')" />
                                </el-tooltip>
                            </el-form-item>
                            <el-form-item :label="$t('automate_page.poll_interval')" :required="true">
                                <el-input-number v-model="form.interval" :placeholder="$t('automate_page.poll_interval')" :min="1" :max="3600">
                                    <template #suffix>
                                        {{ $t('automate_page.sec') }}
                                    </template>
                                </el-input-number>
                            </el-form-item>
                        </template>
                        <template v-if="form.name === 'delay_timer'">
                            <el-form-item :label="$t('automate_page.delay_label')" :required="true">
                                <el-input-number v-model="form.trigger_kwargs.delay" :placeholder="$t('automate_page.delay_ph')" :min="60"
                                    :max="604800">
                                    <template #suffix>
                                        {{ $t('automate_page.sec') }}
                                    </template>
                                </el-input-number>
                            </el-form-item>
                        </template>
                        <template v-if="form.name === 'scheduled_timer'">
                            <el-form-item :label="$t('automate_page.schedule_label')" :required="true">
                                <el-date-picker v-model="form.trigger_kwargs.time" type="datetime" :placeholder="$t('automate_page.schedule_ph')"
                                    :editable="false" value-format="YYYY-MM-DD HH:mm:ss" />
                            </el-form-item>
                        </template>

                        <!-- action -->
                        <template v-if="form.name">
                            <el-form-item :label="$t('automate_page.form_action')" :required="true">
                                <el-select-v2 v-model="form.action" :placeholder="$t('automate_page.form_action_ph')" :options="options.actions"
                                    @change="onActionSelected">
                                    <template #default="{ item }">
                                        <div
                                            style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
                                            <span style="flex: 0 0 80px; text-align: left; margin-right: 8px;">
                                                {{ item.label }}
                                            </span>
                                            <span
                                                style="flex: 1; color: var(--el-text-color-secondary); font-size: 13px;">
                                                {{ item.desc }}
                                            </span>
                                        </div>
                                    </template>
                                </el-select-v2>
                            </el-form-item>
                            <template v-if="form.action">

                                <template v-if="form.action === 'craft'">
                                    <el-form-item :label="$t('automate_page.target_item')" :required="true">
                                        <ItemSelect :options="options.itemList" :craft="true" :footer="$t('automate_page.fluid_search_footer')"
                                            @handleLoadItemList="onLoadedItemList"
                                            @handleItemSelected="onActionItemSelected" />
                                    </el-form-item>
                                    <el-form-item :label="$t('automate_page.craft_qty')" :required="true">
                                        <el-input-number v-model="form.action_kwargs.item_amount" :placeholder="$t('automate_page.craft_qty_ph')"
                                            :min="1">
                                            <template #suffix>
                                                {{ $t('automate_page.unit_count') }}
                                            </template>
                                        </el-input-number>
                                    </el-form-item>
                                    <el-form-item :label="$t('automate_page.cpu_optional')">
                                        <el-tooltip effect="dark" :content="$t('automate_page.cpu_busy_tip')" placement="top">
                                            <CpuSelect status="all" footer="" :options="options.cpuList"
                                                :onlyNamed="true" :autoSelect="true"
                                                @handleCpuSelected="onActionCpuSelected"
                                                @handleLoadCpuList="onLoadCpuList" />
                                        </el-tooltip>
                                    </el-form-item>
                                </template>

                                <template v-if="form.action === 'http_request'">
                                    <el-form-item :label="$t('automate_page.http_method')" :required="true">
                                        <el-select v-model="options.action_kwargs.method" :placeholder="$t('automate_page.http_method_ph')">
                                            <el-option label="GET" value="GET" />
                                            <el-option label="POST" value="POST" />
                                            <el-option label="PUT" value="PUT" />
                                            <el-option label="DELETE" value="DELETE" />
                                        </el-select>
                                    </el-form-item>
                                    <el-form-item :label="$t('automate_page.http_url')" :required="true">
                                        <el-input v-model="options.action_kwargs.url" :placeholder="$t('automate_page.http_url_ph')" />
                                    </el-form-item>
                                    <el-form-item :label="$t('automate_page.http_headers')">
                                        <div class="key-value-group"
                                            v-for="(item, index) in options.key_value_group.headers">
                                            <el-input v-model="item.key" :placeholder="$t('automate_page.key_ph')" /> :
                                            <el-input v-model="item.value" :placeholder="$t('automate_page.value_ph')" />
                                            <el-button type="danger"
                                                @click="options.key_value_group.headers.splice(index, 1)">
                                                {{ $t('automate_page.remove_row') }}
                                            </el-button>
                                        </div>
                                        <el-button type="primary" size="small"
                                            @click="options.key_value_group.headers.push({ key: '', value: '' })">
                                            {{ $t('automate_page.add_row') }}
                                        </el-button>
                                    </el-form-item>
                                    <el-form-item :label="$t('automate_page.http_params')">
                                        <div class="key-value-group"
                                            v-for="(item, index) in options.key_value_group.params">
                                            <el-input v-model="item.key" :placeholder="$t('automate_page.key_ph')" /> :
                                            <el-input v-model="item.value" :placeholder="$t('automate_page.value_ph')" />
                                            <el-button type="danger"
                                                @click="options.key_value_group.params.splice(index, 1)">
                                                {{ $t('automate_page.remove_row') }}
                                            </el-button>
                                        </div>
                                        <el-button type="primary" size="small"
                                            @click="options.key_value_group.params.push({ key: '', value: '' })">
                                            {{ $t('automate_page.add_row') }}
                                        </el-button>
                                    </el-form-item>
                                    <el-form-item :label="$t('automate_page.http_body')">
                                        <el-input type="textarea" :autosize="{ minRows: 2, maxRows: 6 }"
                                            v-model="options.action_kwargs.data" :placeholder="$t('automate_page.http_body')" />
                                    </el-form-item>
                                </template>
                            </template>
                        </template>

                        <el-form-item v-if="form.name && form.action">
                            <el-button v-if="showUseTemplateButton" style="margin-right: auto;" type="primary"
                                @click="this.showUseTemplateDialog = true">{{ $t('automate_page.use_template') }}</el-button>
                            <el-button style="margin-left: auto;" type="primary" @click="addAutoTask">{{ $t('automate_page.add_btn') }}</el-button>
                        </el-form-item>
                    </el-form>
                </div>
            </el-scrollbar>
        </el-dialog>
        <!-- Templates -->
        <el-dialog v-model="showUseTemplateDialog" class="template-dialog" style="height: 400px;" :title="$t('automate_page.template_title')"
            align-center>
            <el-table :data="this.options.action_templates.options" :height="340" width="100%">
                <el-table-column property="name" :label="$t('automate_page.template_col_name')" />
                <el-table-column property="description" :label="$t('automate_page.template_col_desc')" />
                <el-table-column :label="$t('automate_page.col_ops')">
                    <template #default="{ row }">
                        <el-button type="primary" size="small" @click="comfirmUseTemplate(row)">{{ $t('automate_page.template_use') }}</el-button>
                    </template>
                </el-table-column>
            </el-table>
        </el-dialog>
    </el-container>
</template>

<script>
import { inject } from 'vue';
import { trigger, timer, getActionTemplats } from '@/utils/automate'
import ItemCard from "@/components/ItemCard.vue";
import TaskResult from "@/components/TaskResult.vue";
import CpuSelect from "@/components/CpuSelect.vue";
import ItemSelect from "@/components/ItemSelect.vue";
import { ElMessage, ElTag, ElButton } from 'element-plus'
import Setting from '@/utils/setting';

export default {
    name: 'Automate',
    components: {
        ItemCard,
        TaskResult,
        CpuSelect,
        ItemSelect,
    },
    data() {
        return {
            backendUrl: Setting.get('backendUrl'),
            tasks: [],
            lastUpdate: "",
            mainLoading: false,
            showInfoDialog: false,
            showAddTaskDialog: false,
            showUseTemplateDialog: false,
            showUseTemplateButton: false,
            info: null,
            config: [],
            options: {
                name: [],
                cpuList: [],
                actions: [],
                itemList: [],
                action_kwargs: {},
                key_value_group: {
                    headers: [],
                    params: [],
                },
                action_templates: {
                    data: null,
                    options: [],
                }
            },
            args: {
                trigger: {},
                action: {},
            },
            form: {
                name: "",
                action: "",
                trigger_kwargs: {},
                action_kwargs: {},
            }
        };
    },
    setup() {
        const isMobile = inject('isMobile');
        return {
            isMobile,
        };
    },
    computed: {
        statusMap() {
            return {
                ready: { text: this.$t('automate_page.status.ready'), type: 'primary' },
                pending: { text: this.$t('automate_page.status.pending'), type: 'success' },
                completed: { text: this.$t('automate_page.status.completed'), type: 'warning' },
            };
        },
    },
    methods: {
        displayTaskType(type) {
            if (type === 'trigger') return this.$t('automate_page.types.trigger');
            if (type === 'timer') return this.$t('automate_page.types.timer');
            return type || '';
        },
        displayCatalogName(name) {
            if (!name) return '';
            const key = `automate_page.names.${name}`;
            const msg = this.$t(key);
            return msg !== key ? msg : name;
        },
        translateCatalogDesc(item) {
            if (!item || !item.name) return '';
            const prefix = item.type === 'timer' ? 'automate_page.timer_desc.' : 'automate_page.trigger_desc.';
            const key = `${prefix}${item.name}`;
            const msg = this.$t(key);
            if (msg !== key) return msg;
            return item.description || '';
        },
        displayActionName(action) {
            if (!action) return '';
            const id = action.id;
            if (id === 'craft' || id === 'http_request') {
                const key = `automate_page.action_kind.${id}`;
                const msg = this.$t(key);
                if (msg !== key) return msg;
            }
            return action.name || '';
        },
        isCraftAction(action) {
            if (!action || !action.action_kwargs) return false;
            if (action.action_kwargs.item_name) return true;
            return action.name === 'Craft item' || action.id === 'craft';
        },
        async loadAutoTasks() {
            if (!this.backendUrl) {
                this.$message.warning(this.$t('info.backend_not_configured'));
                return;
            }

            this.mainLoading = true;
            this.lastUpdate = '';

            try {
                const [triggers, timers] = await Promise.all([
                    new Promise((resolve, reject) => {
                        trigger.getTriggerList((data) => {
                            if (!data) {
                                reject(new Error(this.$t('automate_page.errors.trigger_list')));
                                return;
                            }
                            const triggerList = Object.entries(data).map(([key, value]) => ({
                                ...value,
                                id: key,
                                type: "trigger"
                            }));
                            resolve(triggerList);
                        });
                    }),
                    new Promise((resolve, reject) => {
                        timer.getTimerList((data) => {
                            if (!data) {
                                reject(new Error(this.$t('automate_page.errors.timer_list')));
                                return;
                            }
                            const timerList = Object.entries(data).map(([key, value]) => ({
                                ...value,
                                id: key,
                                type: "timer"
                            }));
                            resolve(timerList);
                        });
                    })
                ]);

                this.tasks = [...triggers, ...timers].sort((a, b) => {
                    return new Date(a.time.created) - new Date(b.time.created);
                });
                this.lastUpdate = new Date().toLocaleString().replace(/\//g, '-');
            } catch (error) {
                ElMessage.error(this.$t('automateUi.load_tasks_failed', { detail: error.message || error }));
                console.error('Error loading tasks:', error);
                this.tasks = [];
            } finally {
                this.mainLoading = false;
            }
        },
        showAutoTaskDialog() {
            this.showAddTaskDialog = true;
            this.fetchAutoTaskConfig();
            this.fetchActionTemplates();
        },
        addAutoTask() {
            // Basic validation
            if (!this.form.name || !this.form.action) {
                ElMessage.error(this.$t('automateUi.fill_condition_action'));
                return;
            }

            // Per-trigger-type validation
            if (this.form.name === 'cpu_idle') {
                if (!this.form.trigger_kwargs.cpu_name) {
                    ElMessage.error(this.$t('automateUi.pick_cpu'));
                    return;
                }
                if (!this.form.interval || this.form.interval < 1) {
                    ElMessage.error(this.$t('automateUi.interval_seconds'));
                    return;
                }
            }

            if (this.form.name === 'delay_timer') {
                if (!this.form.trigger_kwargs.delay || this.form.trigger_kwargs.delay < 60) {
                    ElMessage.error(this.$t('automateUi.delay_min_60'));
                    return;
                }
            }

            if (this.form.name === 'scheduled_timer') {
                if (!this.form.trigger_kwargs.time) {
                    ElMessage.error(this.$t('automateUi.pick_schedule_time'));
                    return;
                }
                const selectedTime = new Date(this.form.trigger_kwargs.time);
                const now = new Date();
                if (selectedTime <= now) {
                    ElMessage.warning(this.$t('automateUi.schedule_future'));
                    return;
                }
            }

            // Action-specific validation
            if (this.form.action === 'craft') {
                if (!this.form.action_kwargs.item_name) {
                    ElMessage.error(this.$t('automateUi.pick_craft_item'));
                    return;
                }
                if (!this.form.action_kwargs.item_amount || this.form.action_kwargs.item_amount < 1) {
                    ElMessage.error(this.$t('automateUi.craft_amount_min'));
                    return;
                }
            }

            if (this.form.action === 'http_request') {
                // JSON body validation
                if (this.options.action_kwargs.data && this.options.action_kwargs.data.trim()) {
                    try {
                        this.form.action_kwargs.data = JSON.parse(this.options.action_kwargs.data);
                    } catch (error) {
                        ElMessage.error(this.$t('automateUi.json_body_invalid'));
                        console.error('Error parsing JSON:', error);
                        return;
                    }
                }

                // Normalize headers
                if (this.options.key_value_group.headers && this.options.key_value_group.headers.length) {
                    const headers = {};
                    const invalidHeaders = [];

                    this.options.key_value_group.headers.forEach(item => {
                        if (item.key && item.key.trim() && item.value !== undefined) {
                            headers[item.key.trim()] = item.value;
                        } else if (item.key || item.value) {
                            invalidHeaders.push(item);
                        }
                    });

                    if (invalidHeaders.length > 0) {
                        ElMessage.warning(this.$t('automateUi.invalid_headers', { n: invalidHeaders.length }));
                    }

                    if (Object.keys(headers).length > 0) {
                        this.form.action_kwargs.headers = headers;
                    }
                }

                // Normalize query params
                if (this.options.key_value_group.params && this.options.key_value_group.params.length) {
                    const params = {};
                    const invalidParams = [];

                    this.options.key_value_group.params.forEach(item => {
                        if (item.key && item.key.trim() && item.value !== undefined) {
                            params[item.key.trim()] = item.value;
                        } else if (item.key || item.value) {
                            invalidParams.push(item);
                        }
                    });

                    if (invalidParams.length > 0) {
                        ElMessage.warning(this.$t('automateUi.invalid_params', { n: invalidParams.length }));
                    }

                    if (Object.keys(params).length > 0) {
                        this.form.action_kwargs.params = params;
                    }
                }

                // Required field checks
                if (!this.options.action_kwargs.url) {
                    ElMessage.error(this.$t('automateUi.url_required'));
                    return;
                }

                if (!this.options.action_kwargs.method) {
                    ElMessage.error(this.$t('automateUi.method_required'));
                    return;
                }

                // URL shape sanity check
                try {
                    new URL(this.options.action_kwargs.url);
                } catch (e) {
                    ElMessage.warning(this.$t('automateUi.url_suspicious'));
                }

                this.form.action_kwargs.method = this.options.action_kwargs.method;
                this.form.action_kwargs.url = this.options.action_kwargs.url;
            }

            // Resolve trigger type metadata
            const configItem = this.config.find(item => item.name === this.form.name);
            if (!configItem) {
                ElMessage.error(this.$t('automateUi.invalid_trigger'));
                return;
            }

            // Submit to API
            const type = configItem.type;
            ElMessage.info(this.$t('automateUi.adding_wait'));
            this.submitTask(type, this.form);
        },
        submitTask(type, form) {
            if (type === 'trigger') {
                trigger.addTrigger(form, (res) => {
                    ElMessage.success(this.$t('automateUi.task_added'));
                    this.showAddTaskDialog = false;
                    this.loadAutoTasks();
                });
            } else {
                timer.addTimer(form, (res) => {
                    ElMessage.success(this.$t('automateUi.task_added'));
                    this.showAddTaskDialog = false;
                    this.loadAutoTasks();
                });
            }
        },
        fetchAutoTaskConfig() {
            Promise.all([
                new Promise((resolve, reject) => {
                    trigger.getTriggerConfig((data) => {
                        if (!data) {
                            reject(new Error(this.$t('automate_page.errors.trigger_cfg')));
                            return;
                        }
                        const triggerConfig = data.map(item => ({ ...item, type: 'trigger' }));
                        resolve(triggerConfig);
                    });
                }),
                new Promise((resolve, reject) => {
                    timer.getTimerConfig((data) => {
                        if (!data) {
                            reject(new Error(this.$t('automate_page.errors.timer_cfg')));
                            return;
                        }
                        const timerConfig = data.map(item => ({ ...item, type: 'timer' }));
                        resolve(timerConfig);
                    });
                })
            ])
            .then(([triggerConfig, timerConfig]) => {
                this.config = [...triggerConfig, ...timerConfig];
                
                // Build select options from template
                this.options.name = [
                    {
                        label: this.$t('automate_page.group.trigger'),
                        options: triggerConfig.map(item => ({
                            label: this.displayCatalogName(item.name),
                            value: item.name,
                            desc: this.translateCatalogDesc(item),
                        }))
                    },
                    {
                        label: this.$t('automate_page.group.timer'),
                        options: timerConfig.map(item => ({
                            label: this.displayCatalogName(item.name),
                            value: item.name,
                            desc: this.translateCatalogDesc(item),
                        }))
                    }
                ];

                // Default kwargs from template
                this.args.trigger = {};
                this.args.action = {};
                
                this.config.forEach(item => {
                    // Persist trigger defaults
                    this.args.trigger[item.name] = {};
                    if (item.args && Array.isArray(item.args)) {
                        item.args.forEach(arg => {
                            if (arg.default !== undefined && arg.default !== null) {
                                this.args.trigger[item.name][arg.field] = arg.default;
                            }
                        });
                    }
                    
                    // Persist action defaults
                    this.args.action[item.name] = {};
                    if (item.actions && Array.isArray(item.actions)) {
                        item.actions.forEach(action => {
                            this.args.action[item.name][action.id] = {};
                            if (action.args && Array.isArray(action.args)) {
                                action.args.forEach(arg => {
                                    if (arg.default !== undefined && arg.default !== null) {
                                        this.args.action[item.name][action.id][arg.field] = arg.default;
                                    }
                                });
                            }
                        });
                    }
                });
            })
            .catch((error) => {
                ElMessage.error(this.$t('automateUi.load_config_failed', { detail: error.message || error }));
                console.error('Error loading task config:', error);
            });
        },
        fetchActionTemplates() {
            getActionTemplats((data) => {
                if (!data) {
                    ElMessage.warning(this.$t('automateUi.template_fetch_warn'));
                    return;
                }
                
                this.options.action_templates.data = data;
                
                // Map template rows to option list
                const options = [];
                for (const trigger_name in data) {
                    for (const action_name in data[trigger_name]) {
                        if (data[trigger_name][action_name]) {
                            options.push({
                                trigger_name,
                                action_name,
                                template_name: action_name,
                                description: data[trigger_name][action_name].description || this.$t('automate_page.none'),
                                name: action_name
                            });
                        }
                    }
                }
                
                this.options.action_templates.options = options;
            });
        },
        handleStart(data) {
            if (!data || !data.id) {
                ElMessage.error(this.$t('automateUi.task_invalid'));
                return;
            }
            
            if (data.type === 'timer') {
                timer.startTimer(data.id, (res) => {
                    ElMessage.success(this.$t('automateUi.task_started'));
                    this.loadAutoTasks();
                });
            } else {
                trigger.startTrigger(data.id, (res) => {
                    ElMessage.success(this.$t('automateUi.task_started'));
                    this.loadAutoTasks();
                });
            }
        },
        handleStop(data) {
            if (!data || !data.id) {
                ElMessage.error(this.$t('automateUi.task_invalid'));
                return;
            }

            if (data.type === 'timer') {
                timer.stopTimer(data.id, (res) => {
                    ElMessage.success(this.$t('automateUi.task_stopped'));
                    this.loadAutoTasks();
                });
            } else {
                trigger.stopTrigger(data.id, (res) => {
                    ElMessage.success(this.$t('automateUi.task_stopped'));
                    this.loadAutoTasks();
                });
            }
        },
        handleInfo(data) {
            if (!data) {
                ElMessage.error(this.$t('automateUi.task_invalid'));
                return;
            }
            
            // Format timeline fields defensively
            try {
                const formattedData = { ...data };
                
                // Clone before mutating dates for display
                if (formattedData.time) {
                    formattedData.time = { ...formattedData.time };
                    Object.keys(formattedData.time).forEach(key => {
                        if (!formattedData.time[key]) {
                            return;
                        }
                        try {
                            formattedData.time[key] = new Date(formattedData.time[key])
                                .toLocaleString()
                                .replace(/\//g, '-');
                        } catch (e) {
                            console.warn(`Could not format time field ${key}:`, e);
                        }
                    });
                }
                
                this.info = formattedData;
                this.showInfoDialog = true;
            } catch (error) {
                console.error('Task detail handling failed:', error);
                ElMessage.error(this.$t('automateUi.task_detail_unavailable'));
            }
        },
        handleRemove(data) {
            if (data.type === 'timer') {
                timer.removeTimer(data.id, (res) => {
                    ElMessage.success(this.$t('automateUi.task_removed'));
                    this.loadAutoTasks();
                });
            } else {
                trigger.removeTrigger(data.id, (res) => {
                    ElMessage.success(this.$t('automateUi.task_removed'));
                    this.loadAutoTasks();
                });
            }
        },
        resetFormAndLoadActions(clearName = false) {
            this.form = {
                name: clearName ? "" : this.form.name,
                action: "",
                trigger_kwargs: {},
                action_kwargs: {},
            };
            if (this.form.name) {
                if (this.config.find(item => item.name === this.form.name).type === 'trigger') {
                    this.form.interval = 180;
                }
                this.loadDefaultTriggerArgs(this.form.name);
                this.options.actions = this.config.find(item => item.name === this.form.name).actions.map(action => ({
                    label: this.displayActionName(action),
                    value: action.id,
                    desc: action.description,
                }));
            }
            this.showUseTemplateButton = false;
        },
        loadDefaultTriggerArgs(name) {
            let defaultArg = this.args.trigger[name];
            if (defaultArg) {
                this.form.trigger_kwargs = defaultArg;
            }
        },
        onActionSelected(action) {
            this.form.action = action;
            this.loadDefaultActionArgs(this.form.name, action);
            if (!this.options.action_templates.data[this.form.name]) {
                this.showUseTemplateButton = false;
                this.options.action_templates.options = [];
                return;
            }
            let template = this.options.action_templates.data[this.form.name][action];
            if (template && template.length > 0) {
                this.showUseTemplateButton = true;
                this.options.action_templates.options = template;
            } else {
                this.showUseTemplateButton = false;
                this.options.action_templates.options = [];
            }
        },
        loadDefaultActionArgs(trigger_name, action) {
            let defaultArg = this.args.action[trigger_name];
            if (defaultArg[action]) {
                this.form.action_kwargs = defaultArg[action];
            }
        },
        onTriggerCpuSelected(cpu) {
            this.form.trigger_kwargs.cpu_name = cpu;
        },
        onActionCpuSelected(cpu) {
            this.form.action_kwargs.cpu_name = cpu;
        },
        onLoadCpuList(cpuList) {
            this.options.cpuList = cpuList;
        },
        onActionItemSelected(item) {
            this.form.action_kwargs.item_name = item.name;
            this.form.action_kwargs.item_damage = item.damage;
            if (item.name === 'ae2fc:fluid_drop') {
                this.form.action_kwargs.label = item.label;
            }
        },
        onLoadedItemList(itemList) {
            this.options.itemList = itemList;
        },
        comfirmUseTemplate(template) {
            if (!template) {
                ElMessage.warning(this.$t('automateUi.template_invalid'));
                return;
            }
            
            try {
                // Key/value template branch
                const key_value_fields = template.args && template.args.key_values;
                
                // Reset key/value groups
                if (this.options.key_value_group) {
                    Object.keys(this.options.key_value_group).forEach(field => {
                        this.options.key_value_group[field] = [];
                    });
                }
                
                // Merge template key_value into options.key_value_group when present
                if (key_value_fields && Array.isArray(key_value_fields)) {
                    key_value_fields.forEach(field => {
                        if (!this.options.key_value_group[field]) {
                            this.options.key_value_group[field] = [];
                        }
                        
                        const key_value_content = template.action_kwargs[field];
                        if (key_value_content) {
                            for (const key in key_value_content) {
                                this.options.key_value_group[field].push({ 
                                    key: key, 
                                    value: key_value_content[key] 
                                });
                            }
                            
                            // Drop key_value from template.action_kwargs after merge
                            delete template.action_kwargs[field];
                        }
                    });
                }
                
                // Copy remaining template kwargs into the form
                this.options.action_kwargs = { ...template.action_kwargs };
                ElMessage.success(this.$t('automateUi.template_applied'));
            } catch (error) {
                console.error('Apply template failed:', error);
                ElMessage.error(this.$t('automateUi.template_apply_failed'));
            }
            
            this.showUseTemplateDialog = false;
        },
    },
    created() {
        this.loadAutoTasks();
    },
    activated() {

    },
};
</script>

<style>
.control-header-task {
    width: 100%;
    margin-top: 10px;
}

.control-header-task .el-loading-spinner .circular {
    height: 24px;
    width: 24px;
}

.control-header-task .el-card__body {
    padding: 0;
}

.el-popper {
    max-width: 400px;
}

.el-select__popper {
    max-width: none;
}

.table-box-card {
    height: 100%;
}

.table-box-card .el-card__body {
    padding: 16px;
    height: calc(100% - 32px);
}

.task-dialog .el-dialog__body {
    width: 100%;
    height: calc(100% - 50px);
}

.info-container .el-row {
    margin-bottom: 10px;
}

@media screen and (max-width: 768px) {
    .template-dialog {
        width: 100% !important;
        max-width: 400px;
    }
}

.op-button-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px; 
}

.op-button-grid > .el-button+.el-button {
    margin-left: 0;
}
</style>

<style scoped>
.el-container {
    height: 100%;
}

.card-container {
    overflow-y: auto;
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    justify-content: flex-start;
    height: calc(100% - 50px);
}

.control-card {
    padding: 10px;
    margin-bottom: 10px;
}

.control-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

@media screen and (max-width: 768px) {
    .control-bar {
        height: 46px;
        flex-direction: column;
        align-items: flex-start;
    }


}

.words {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    width: 100%;
}

.info-container {
    height: 100%;
    margin: 10px auto;
    /* overflow-y: auto; */
    /* background-color: black; */
}

.key-value-group {
    display: flex;
    gap: 5px;
    margin-bottom: 5px;
    width: 100%;
}

@media screen and (min-width: 768px) {
    .info-container {
        width: 50%;
        min-width: 768px;
    }

    .item-card-container {
        width: calc(50vw - 200px);
        min-width: 548px;
    }
}

@media screen and (max-width: 768px) {
    .info-container {
        width: 100%;
        max-width: 768px;
    }

    .item-card-container {
        width: calc(100vw - 200px);
    }
}
</style>
