<template>
    <el-container style="height: 100%;" v-loading="loading">
        <el-header v-loading="headerLoading" :element-loading-text="headerLoadingText" class="control-header-cpu">
            <el-card class="control-card" shadow="hover">
                <div class="control-bar">
                    <div class="control-info">
                        <span>{{ $t('cpu.last_update') }}: {{ lastCpuUpdate }}</span>
                        <el-button type="primary" @click="getCpuList">{{ $t('cpu.get_info') }}</el-button>
                    </div>
                    <div v-if="isMobile" class="cpu-select-container">
                        <el-select-v2 v-model="selectCpu" :options="cpuList" :props="selectProps"
                            @change="handleCpuSelect" :placeholder="$t('cpu.select')" style="width: 100%">
                            <template #default="{ item }">
                                <CpuItem :item="item" />
                            </template>
                            <template #label>
                                <CpuItem :item="currentCpu" />
                            </template>
                        </el-select-v2>
                    </div>
                </div>
            </el-card>
        </el-header>
        <el-main style="width: 100%;">
            <el-row :gutter="20" class="cpu-container-2">
                <el-col v-if="!isMobile" :span="6" style="height: 100%;">
                    <el-card class="box-card">
                        <el-menu default-active="0" v-model="cpuSelected" @select="handleCpuSelect">
                            <el-menu-item v-for="(cpu, index) in cpuList" :key="index" :index="index.toString()">
                                <template #default>
                                    <div class="cpu-row">
                                        <div class="cpu-info">
                                            <div class="ellipsis">{{ cpu.name }}</div>
                                            <h1>{{ $t('cpu.status') }}:
                                                <el-tag v-if="cpu.busy" type="warning" effect="light">{{ $t('cpu.busy') }}</el-tag>
                                                <el-tag v-else type="success" effect="light">{{ $t('cpu.idle') }}</el-tag>
                                            </h1>
                                            <h1>{{ $t('cpu.storage') }}: {{ cpu.storage / 1024 }} KB</h1>
                                            <h1>{{ $t('cpu.coprocessors') }}: {{ cpu.coprocessors }}</h1>
                                        </div>
                                        <div class="cpu-output">
                                            <img v-if="cpu.output.image" :src="cpu.output.image" alt="output"
                                                class="output-image" />
                                        </div>
                                    </div>
                                </template>
                            </el-menu-item>
                        </el-menu>
                    </el-card>
                </el-col>
                <el-col :span="isMobile ? 24 : 18" class="cpu-detail">
                    <el-card class="box-card">
                        <el-row v-if="currentCpu.items.length" :gutter="20">
                            <el-col v-for="(item, index) in currentCpu.items" :key="index" :span="isMobile ? 24 : 8">
                                <el-card :class="'item-card ' + getItemCardClass(item)" shadow="hover">
                                    <div class="image-wrapper">
                                        <el-image :src="item.image || ''" class="component-image" :alt="item.title"
                                            lazy>
                                            <template #placeholder>
                                                <el-skeleton :loading="true" animated class="component-image">
                                                    <template #template>
                                                        <el-skeleton-item variant="image"
                                                            style="width: 48px; height: 48px" />
                                                    </template>
                                                </el-skeleton>
                                            </template>
                                            <template #error>
                                                <el-icon size="40" class="unknow-icon">
                                                    <QuestionFilled />
                                                </el-icon>
                                            </template>
                                        </el-image>
                                        <div class="item-info">
                                            <div class="ellipsis" style="font-size: 20px;">{{ item.label }}</div>
                                            <div v-if="item.active">{{ $t('cpu.crafting') }}:
                                                <NumberFormat :number="item.active" />
                                            </div>
                                            <div v-if="item.pending">{{ $t('cpu.planned') }}:
                                                <NumberFormat :number="item.pending" />
                                            </div>
                                            <div v-if="item.stored">{{ $t('cpu.stored') }}:
                                                <NumberFormat :number="item.stored" />
                                            </div>
                                        </div>
                                    </div>
                                </el-card>
                            </el-col>
                        </el-row>
                        <el-empty v-else :description="$t('cpu.no_items')" />
                    </el-card>
                </el-col>
            </el-row>
        </el-main>

    </el-container>
</template>

<script>
import bus from 'vue3-eventbus';
import { inject } from 'vue';
import { fetchStatus, addTask, createPollingController } from '@/utils/task'
import itemUtil from "@/utils/items";
import NumberFormat from '@/components/NumberFormat.vue';
import CpuItem from '@/components/CpuItem.vue';

export default {
    name: 'Cpus',
    components: {
        NumberFormat,
        CpuItem,
    },
    data() {
        return {
            loading: true,
            headerLoading: false,
            headerLoadingText: "",
            lastCpuUpdate: "",
            cpuList: [],
            currentCpu: { items: [] },
            selectCpu: "",
            cpuSelected: 0,
            pollingController: null,
            selectProps: {
                label: 'name',
                value: 'id',
            },
        };
    },
    created() {
    },
    setup() {
        const isMobile = inject('isMobile');
        return {
            isMobile,
        };
    },
    mounted() {
        this.headerLoadingText = this.$t('cpu.request_sent', { task: 'getCpuDetailList' });
        this.getCpuList();
        bus.on('refreshCpuList', this.handleTaskResult);
    },
    beforeUnmount() {
        bus.off('refreshCpuList', this.handleTaskResult);
    },
    methods: {
        handleCpuSelect(index) {
            console.log("CPU selected:", index, this.cpuList[index]);
            this.currentCpu = this.cpuList[index];
        },
        getItemCardClass(item) {
            if (item.active) {
                return 'active-card';
            } else if (item.pending) {
                return 'pending-card';
            } else if (item.stored) {
                return 'stored-card';
            } else {
                return '';
            }
        },
        startPolling(taskId) {
            this.pollingController = createPollingController();
            fetchStatus(taskId, this.handleTaskResult, null, this.handleTaskComplete, 1000, this.pollingController);
        },
        stopPolling() {
            if (this.pollingController) {
                this.pollingController.stop();
                console.log('Polling stopped.');
            }
        },
        parseItemStack(data) {
            const itemArray = [];

            // Merge identical items for display
            const mergeItems = (array, newItem) => {
                const existingItem = array.find(item =>
                    item.label === newItem.label &&
                    item.damage === newItem.damage &&
                    item.name === newItem.name);
                if (existingItem) {
                    existingItem.active += newItem.active;
                    existingItem.pending += newItem.pending;
                    existingItem.stored += newItem.stored;
                } else {
                    array.push(newItem);
                }
            };

            // activeItems
            data.activeItems.forEach(item => {
                let item_ = itemUtil.getItem(item);
                mergeItems(itemArray, {
                    label: itemUtil.getName(item_, item),
                    name: item.name,
                    damage: item.damage,
                    active: item.size,
                    pending: 0,
                    stored: 0,
                    image: itemUtil.getItemIcon(item_)
                });
            });

            // pendingItems
            data.pendingItems.forEach(item => {
                let item_ = itemUtil.getItem(item);
                mergeItems(itemArray, {
                    label: itemUtil.getName(item_, item),
                    name: item.name,
                    damage: item.damage,
                    active: 0,
                    pending: item.size,
                    stored: 0,
                    image: itemUtil.getItemIcon(item_)
                });
            });

            // storedItems
            data.storedItems.forEach(item => {
                let item_ = itemUtil.getItem(item);
                mergeItems(itemArray, {
                    label: itemUtil.getName(item_, item),
                    name: item.name,
                    damage: item.damage,
                    active: 0,
                    pending: 0,
                    stored: item.size,
                    image: itemUtil.getItemIcon(item_)
                });
            });

            return itemArray;
        },
        parseOutputItem(item) {
            let item_ = itemUtil.getItem(item);
            item['image'] = itemUtil.getItemIcon(item_);
            item['title'] = itemUtil.getName(item_, item);
            return item;
        },
        handleTaskResult(data) {
            // console.log('Task result:', data);
            this.loading = false;

            if (data.result) {
                try {
                    let result = JSON.parse(data.result[0]);

                    if (result.message === undefined || result.message !== 'success') {
                        this.$message.warning(result.message ? result.message : this.$t('common.unknown_error'));
                        return
                    }

                    this.lastCpuUpdate = data.completed_time ? data.completed_time.split(".")[0].replace("T", " ") : this.$t('common.unknown');

                    const previousCpuName = this.currentCpu?.name;
                    this.currentCpu = { name: undefined, items: [] };

                    let cpuIndex = 0;
                    let cpus = result.data;
                    let cpuList = [];
                    for (let cpu of cpus) {
                        let name = cpu.name;
                        if (name === "") {
                            name = `CPU #${cpuIndex + 1}`;
                            cpuIndex++;
                        }
                        cpuList.push({
                            name: name,
                            busy: cpu.busy,
                            coprocessors: cpu.coprocessors,
                            storage: cpu.storage,
                            output: cpu.cpu && cpu.cpu.finalOutput ? this.parseOutputItem(cpu.cpu.finalOutput) : {},
                            items: this.parseItemStack(cpu.cpu),
                        });
                    }

                    // Sort CPUs by name
                    cpuList.sort((a, b) => a.name.localeCompare(b.name));
                    // Stable row ids
                    cpuList.forEach((cpu, index) => {
                        cpu.id = index;
                        // Restore previous selection when possible
                        if (previousCpuName && previousCpuName === cpu.name) {
                            this.currentCpu = cpu;
                            this.cpuSelected = index;
                            this.selectCpu = index;
                        }
                    });

                    // Default to first CPU if selection missing
                    if (!this.currentCpu.name) {
                        this.currentCpu = cpuList[0];
                        this.cpuSelected = 0;
                        this.selectCpu = 0;
                    }
                    this.cpuList = cpuList;
                } catch (e) {
                    console.error(e, data);
                    this.$message.warning(e);
                }
            } else {
                this.$message.warning(this.$t('common.empty_response'));
            }
        },
        handleTaskComplete() {
            this.loading = false;
            this.headerLoading = false;
        },
        getCpuList() {
            this.headerLoading = true;
            addTask("getCpuDetailList", null, () => {
                this.startPolling("getCpuDetailList")
            })
        },
        refreshCpuList() {
            this.startPolling("getCpuDetailList");
        }
    }
};
</script>

<style>
.box-card .el-card__body {
    padding: 16px;
}

.box-card .el-menu-item {
    padding-top: 4px;
    padding-bottom: 4px;
    line-height: 15px;
    height: auto;
    border: 1px solid var(--el-menu-border-color);
    border-radius: 5px;
    margin-bottom: 5px;
}

.box-card .el-menu-item.is-active {
    color: var(--el-menu-text-color);
    background-color: var(--el-color-primary-light-9);
}

.box-card .el-menu {
    border: none;
}

.item-card {
    height: 116px;
}

.item-card .el-card__body {
    height: 100%;
    padding: 8px;
}

@media screen and (min-width: 768px) {
    .control-header-cpu {
        width: calc(100% - 20px);
        margin-top: 10px;
    }
}

@media screen and (max-width: 768px) {
    .control-header-cpu {
        width: 100%;
        margin-top: 10px;
        height: 120px !important;
    }
}

.control-header-cpu .el-card__body {
    height: 100%;
    padding: 8px;
}

.control-header-cpu .el-loading-spinner .circular {
    height: 24px;
    width: 24px;
}
</style>

<style scoped>
@media screen and (min-width: 768px) {
    .cpu-container-2 {
        width: 100%;
        height: 100%;
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
}

@media screen and (max-width: 768px) {
    .cpu-container-2 {
        height: 100%;
    }

    .control-card {
        padding: 10px;
        margin-bottom: 10px;
        height: 96px;
    }

    .control-bar {
        height: calc(100% - 16px);
        display: flex;
        justify-content: space-between;
        flex-direction: column;
        align-items: center;
    }
}

.control-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
}

.cpu-select-container {
    width: 100%;
}

.cpu-detail {
    height: 100%;
}

.el-container {
    height: 100%;
}


.box-card {
    height: 100%;
    overflow-y: auto;
}

.box-card::-webkit-scrollbar {
    display: none;
    /* Hide scrollbar */
}

.cpu-row {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
}

.cpu-info {
    width: calc(100% - 74px);
    padding-right: 10px;
    font-size: 14px;
}

.cpu-output {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    flex-grow: 1;
    width: 64px;
    height: 64px;
}

@media (max-width: 1300px) {
    .cpu-output .output-image {
        display: none;
        /* Hide cpu-output on narrow viewports */
    }
}

.output-image {
    width: 64px;
    height: 64px;
}

.cpu-info h1 {
    margin-bottom: 4px;
}

.ellipsis {
    font-size: 20px;
    line-height: 25px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    width: 100%;
}

.image-wrapper {
    display: flex;
    /* align-items: center; */
    height: calc(100% - 32px);
}

.unknow-icon {
    /* Center */
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);

}

.item-card {
    margin-bottom: 8px;
}

.component-image {
    margin: auto 0;
    width: 48px;
    height: 48px;
    margin-right: 12px;
}

.item-info {
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    /* Align info blocks to the top */
    width: calc(100% - 60px);
    line-height: 1.5;
}

.stored-card {
    background-color: none;
}

.pending-card {
    background-color: var(--pending-bg-color);
}

.active-card {
    background-color: var(--active-bg-color);
}
</style>