<template>
    <el-select v-model="current" size="small" @change="onChange" style="width: 110px;">
        <el-option v-for="opt in options" :key="opt.value" :value="opt.value" :label="opt.label" />
    </el-select>
</template>

<script setup>
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { SUPPORTED_LOCALES, setLocale } from '@/i18n';

const { locale, t } = useI18n();
const current = ref(locale.value);
const options = SUPPORTED_LOCALES.map((value) => ({ value, label: t(`lang.${value}`) }));

function onChange(value) {
    setLocale(value);
    current.value = value;
}
</script>
