<template>
    <el-menu :default-active="activeRoute" class="el-menu-vertical-page" @select="handleSelect" style="height: 100%;">
        <el-menu-item index="Index"><el-icon><House /></el-icon>{{ t('menu.home') }}</el-menu-item>
        <el-menu-item v-if="showMoniter" index="Monitor"><el-icon><DataLine /></el-icon>{{ t('menu.monitor') }}</el-menu-item>
        <el-menu-item index="Items"><el-icon><MessageBox /></el-icon>{{ t('menu.items') }}</el-menu-item>
        <el-menu-item index="Cpus"><el-icon><Cpu /></el-icon>{{ t('menu.cpus') }}</el-menu-item>
        <el-menu-item index="Tasks"><el-icon><Tickets /></el-icon>{{ t('menu.tasks') }}</el-menu-item>
        <el-menu-item index="Automate"><el-icon><AlarmClock /></el-icon>{{ t('menu.automate') }}</el-menu-item>
        <el-menu-item index="Robots"><el-icon><Avatar /></el-icon>{{ t('menu.robots') }}</el-menu-item>
        <el-menu-item index="Autocraft"><el-icon><Operation /></el-icon>{{ t('menu.autocraft') }}</el-menu-item>
        <el-menu-item index="Map"><el-icon><MapLocation /></el-icon>{{ t('menu.map') }}</el-menu-item>
        <el-menu-item index="Quests"><el-icon><Collection /></el-icon>{{ t('menu.quests') }}</el-menu-item>
        <el-menu-item index="Wiki"><el-icon><Reading /></el-icon>{{ t('menu.wiki') }}</el-menu-item>
        <el-menu-item index="Craft"><el-icon><Goods /></el-icon>{{ t('menu.craft') }}</el-menu-item>
        <el-menu-item index="Settings"><el-icon><Setting /></el-icon>{{ t('menu.settings') }}</el-menu-item>
        <el-menu-item index="Info"><el-icon><Warning /></el-icon>{{ t('menu.info') }}</el-menu-item>
    </el-menu>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import Setting from '@/utils/setting';

defineProps({
    closeDrawer: { type: Function, default: null },
});

const { t } = useI18n();
const router = useRouter();
const route = useRoute();
const showMoniter = ref(Setting.get('showMoniter'));
const activeRoute = computed(() => route.name || 'Index');

function handleSelect(index, _path, _instance) {
    router.push({ name: index }).catch(() => {});
}
</script>
