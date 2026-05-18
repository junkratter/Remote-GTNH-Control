<template>
    <div class="statistic-container">
        <StatisticCard
            :title="$t('monitor.eu_stored')"
            :displayValue="statisticTransition.EUStored"
            :change="statistic.EUStored.change"
            :formatter="formatNumber"
        />
        <StatisticCard
            :title="$t('monitor.wireless_eu')"
            :displayValue="statisticTransition.totalWirelessEU"
            :change="statistic.totalWirelessEU.change"
            :formatter="formatNumber"
            :tooltip="$t('monitor.wireless_eu_tooltip')"
        />
    </div>

    <TrendChart
        :historyData="chartHistoryData"
        v-model:timeRange="timeRange"
        v-model:granularity="granularity"
        v-model:customStartTime="customStartTime"
        v-model:customEndTime="customEndTime"
        :loading="chartLoading"
    />

    <el-button class="refresh-button" size="large" :loading="loading" circle @click="refreshAll">
        <template #loading>
            <div class="custom-loading">
                <el-icon size="large">
                    <i class="el-icon is-loading"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">
                            <path fill="currentColor"
                                d="M512 64a32 32 0 0 1 32 32v192a32 32 0 0 1-64 0V96a32 32 0 0 1 32-32m0 640a32 32 0 0 1 32 32v192a32 32 0 1 1-64 0V736a32 32 0 0 1 32-32m448-192a32 32 0 0 1-32 32H736a32 32 0 1 1 0-64h192a32 32 0 0 1 32 32m-640 0a32 32 0 0 1-32 32H96a32 32 0 0 1 0-64h192a32 32 0 0 1 32 32M195.2 195.2a32 32 0 0 1 45.248 0L376.32 331.008a32 32 0 0 1-45.248 45.248L195.2 240.448a32 32 0 0 1 0-45.248zm452.544 452.544a32 32 0 0 1 45.248 0L828.8 783.552a32 32 0 0 1-45.248 45.248L647.744 692.992a32 32 0 0 1 0-45.248zM828.8 195.264a32 32 0 0 1 0 45.184L692.992 376.32a32 32 0 0 1-45.248-45.248l135.808-135.808a32 32 0 0 1 45.248 0m-452.544 452.48a32 32 0 0 1 0 45.248L240.448 828.8a32 32 0 0 1-45.248-45.248l135.808-135.808a32 32 0 0 1 45.248 0z">
                            </path>
                        </svg></i>
                </el-icon>
            </div>
        </template>
        <el-icon v-if="!loading" size="large">
            <RefreshRight />
        </el-icon>
    </el-button>
</template>

<script>
import { fetchHistory } from '@/utils/task'
import { useTransition, useDark } from '@vueuse/core'
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import StatisticCard from '@/components/monitor/StatisticCard.vue'
import TrendChart from '@/components/monitor/TrendChart.vue'

export default {
    name: 'Monitor',
    components: {
        StatisticCard,
        TrendChart,
    },
    data() {
        return {
            loading: false,
            statistic: {
                EUStored: {
                    change: 0,
                },
                totalWirelessEU: {
                    change: 0,
                },
            },
            // Chart filters
            timeRange: 4, // default: last 4 hours
            granularity: 'none', // no aggregation bucket
            customStartTime: null, // Unix start (custom range)
            customEndTime: null, // Unix end (custom range)
            chartHistoryData: [],
            chartLoading: false,
        };
    },
    setup() {
        const EUStoredValue = ref(0)
        const totalWirelessEUValue = ref(0)

        const statisticTransition = {
            EUStored: useTransition(EUStoredValue, { duration: 800, }),
            totalWirelessEU: useTransition(totalWirelessEUValue, { duration: 800, }),
        }

        const formatNumber = (num) => {
            return num.value.toLocaleString('zh-CN', { maximumFractionDigits: 0 })
        }

        const isDark = useDark()

        return {
            EUStoredValue,
            totalWirelessEUValue,
            statisticTransition,
            formatNumber,
            isDark,
        }
    },
    watch: {
        timeRange(newVal) {
            // Preset range: fetch immediately
            if (newVal !== 'custom') {
                this.fetchChartData();
            }
        },
        granularity() {
            // Granularity change: refetch so TrendChart recomputes
            this.fetchChartData();
        },
        customStartTime() {
            // Custom window changed → refetch
            if (this.timeRange === 'custom') {
                this.fetchChartData();
            }
        },
        customEndTime() {
            // Custom window changed → refetch
            if (this.timeRange === 'custom') {
                this.fetchChartData();
            }
        },
    },
    methods: {
        async refreshAll() {
            this.loading = true;
            try {
                await Promise.all([
                    this.fetchStatisticData(),
                    this.fetchChartData(),
                ]);
            } finally {
                this.loading = false;
            }
        },
        async fetchStatisticData() {
            try {
                const data = await fetchHistory('monitor');
                if (data) {
                    this.handleStatisticData(data);
                }
            } catch (error) {
                console.error('Error fetching statistic data:', error);
            }
        },
        handleStatisticData(data) {
            if (!data || !data.history || data.history.length === 0) {
                ElMessage.warning(this.$t('monitor.no_history'));
                return;
            }

            try {
                const history = data.history;
                const currentRecord = history[history.length - 1];
                const lastRecord = history.length > 1 ? history[history.length - 2] : null;

                const currentEUStored = currentRecord.results.eu_stored;
                const currentTotalWirelessEU = currentRecord.results.total_wireless_eu;

                if (lastRecord && lastRecord.results.eu_stored) {
                    const lastEUStored = lastRecord.results.eu_stored;
                    this.statistic.EUStored.change = (currentEUStored - lastEUStored) / lastEUStored;
                } else {
                    this.statistic.EUStored.change = 0;
                }
                this.EUStoredValue = currentEUStored;

                if (lastRecord && lastRecord.results.total_wireless_eu) {
                    const lastTotalWirelessEU = lastRecord.results.total_wireless_eu;
                    this.statistic.totalWirelessEU.change = (currentTotalWirelessEU - lastTotalWirelessEU) / lastTotalWirelessEU;
                } else {
                    this.statistic.totalWirelessEU.change = 0;
                }
                this.totalWirelessEUValue = currentTotalWirelessEU;

            } catch (e) {
                console.error('Error parsing statistic data:', e, data);
                ElMessage.warning(this.$t('monitor.parse_failed'));
            }
        },
        async fetchChartData() {
            this.chartLoading = true;
            try {
                let startTime, endTime;
                
                if (this.timeRange === 'custom') {
                    // Explicit custom range
                    if (!this.customStartTime || !this.customEndTime) {
                        this.chartLoading = false;
                        return;
                    }
                    startTime = this.customStartTime;
                    endTime = this.customEndTime;
                } else {
                    // Preset relative range
                    endTime = Math.floor(Date.now() / 1000);
                    startTime = endTime - this.timeRange * 3600;
                }

                const data = await fetchHistory('monitor', {
                    start_time: startTime,
                    end_time: endTime,
                });

                if (data && data.history && data.history.length > 0) {
                    this.chartHistoryData = data.history;
                } else {
                    this.chartHistoryData = [];
                }
            } catch (error) {
                console.error('Error fetching chart data:', error);
                this.chartHistoryData = [];
            } finally {
                this.chartLoading = false;
            }
        },
    },
    mounted() {
        this.refreshAll();
    },
};
</script>

<style scoped>
.refresh-button {
    position: absolute !important;
    right: 36px;
    top: 75px;
}

.statistic-container {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-around;
    gap: 20px;
}

.statistic-container > * {
    flex: 1 1 20%;
    min-width: 300px;
}

@media (max-width: 1400px) {
    .statistic-container > * {
        flex: 1 1 45%;
    }
}

@media (max-width: 900px) {
    .statistic-container > * {
        flex: 1 1 100%;
    }
}

:global(h2#card-usage ~ .example .example-showcase) {
    background-color: var(--el-fill-color) !important;
}

.el-statistic {
    --el-statistic-content-font-size: 28px;
}
</style>