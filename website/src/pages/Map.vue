<template>
    <div class="page">
        <header class="page__header">
            <h2>{{ t('map.title') }}</h2>
            <div class="page-map__toolbar">
                <el-input-number
                    v-model="dimension"
                    :min="0"
                    :max="9999"
                    :controls="true"
                    size="small"
                    class="page-map__dim"
                />
                <span class="page-map__dim-label">{{ t('map.dimension') }}</span>
                <el-button size="small" :icon="Refresh" :loading="loading" @click="load">
                    {{ t('map.refresh') }}
                </el-button>
                <el-radio-group v-model="filter" size="small">
                    <el-radio-button label="all">{{ t('map.filters.all') }}</el-radio-button>
                    <el-radio-button label="ore">{{ t('map.filters.ore') }}</el-radio-button>
                    <el-radio-button label="fluid">{{ t('map.filters.fluid') }}</el-radio-button>
                </el-radio-group>
            </div>
        </header>
        <div ref="mapEl" v-loading="loading" class="leaflet-container glass-card"></div>
        <p class="page-map__hint">{{ t('map.settings_hint') }}</p>
        <el-alert v-if="!blocks.length" :title="t('map.empty')" type="info" show-icon />
    </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { Refresh } from '@element-plus/icons-vue';
import { mapApi } from '@/api';
import Setting from '@/utils/setting';

const { t } = useI18n();

function mapOriginX() {
    const v = Number(Setting.get('mapOriginX'));
    return Number.isFinite(v) ? v : 0;
}

function mapOriginZ() {
    const v = Number(Setting.get('mapOriginZ'));
    return Number.isFinite(v) ? v : 0;
}

const blocks = ref([]);
const filter = ref('all');
const dimension = ref(Number(Setting.get('mapDefaultDimension')) || 0);
const loading = ref(false);
const mapEl = ref(null);
let leafletMap = null;
let markerLayer = null;

async function load() {
    loading.value = true;
    try {
        const resp = await mapApi.blocks({ dimension: dimension.value, limit: 5000 });
        blocks.value = resp.data || [];
        drawMarkers();
    } catch {
        blocks.value = [];
    } finally {
        loading.value = false;
    }
}

function drawMarkers() {
    if (!leafletMap || !markerLayer) return;
    markerLayer.clearLayers();
    const L = window.L;
    if (!L) return;
    for (const b of blocks.value) {
        if (filter.value === 'ore' && !b.block_name) continue;
        if (filter.value === 'fluid' && !b.fluid) continue;
        const lat = b.z - mapOriginZ();
        const lng = b.x - mapOriginX();
        const marker = L.circleMarker([lat, lng], {
            radius: 3,
            color: b.fluid ? '#3b82f6' : '#ef4444',
        });
        marker.bindTooltip(`${b.block_name || b.fluid} @ (${b.x}, ${b.y}, ${b.z})`);
        marker.addTo(markerLayer);
    }
}

onMounted(async () => {
    const L = (await import('leaflet')).default;
    window.L = L;
    await import('leaflet/dist/leaflet.css');
    leafletMap = L.map(mapEl.value, { crs: L.CRS.Simple, minZoom: -4 }).setView([0, 0], -1);
    markerLayer = L.layerGroup().addTo(leafletMap);
    await load();
});

watch(filter, drawMarkers);
watch(dimension, load);
</script>

<style scoped>
.page-map__toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
}
.page-map__dim {
    width: 120px;
}
.page-map__dim-label {
    font-size: 13px;
    opacity: 0.85;
    margin-right: 4px;
}
.page-map__hint {
    margin: 8px 0 0;
    font-size: 13px;
    color: var(--el-text-color-secondary);
}
.leaflet-container {
    width: 100%;
    height: clamp(320px, 60vh, 720px);
    padding: 0 !important;
    overflow: hidden;
}
</style>
