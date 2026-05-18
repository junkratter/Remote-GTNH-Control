<template>
    <div class="page">
        <header class="page__header">
            <h2>{{ t('settings.title') }}</h2>
        </header>

        <el-alert
            type="info"
            show-icon
            :closable="false"
            :title="t('settings.alert')"
        />

        <el-form
            label-position="top"
            class="page-settings__form glass-card"
        >
            <template v-for="(config, idx) in configItems" :key="idx">
                <el-divider
                    v-if="config.type === 'title'"
                    content-position="left"
                >
                    {{ t(`settings.section.${config.i18nKey}`) }}
                </el-divider>

                <el-form-item
                    v-else
                    :label="t(`settings.fields.${config.field}.label`)"
                >
                    <template v-if="config.type === 'input'">
                        <el-input
                            v-model="configValues[config.field]"
                            :placeholder="te(`settings.fields.${config.field}.placeholder`)
                                ? t(`settings.fields.${config.field}.placeholder`)
                                : ''"
                        />
                    </template>

                    <template v-else-if="config.type === 'password'">
                        <el-input
                            v-model="configValues[config.field]"
                            type="password"
                            show-password
                            :placeholder="te(`settings.fields.${config.field}.placeholder`)
                                ? t(`settings.fields.${config.field}.placeholder`)
                                : ''"
                        />
                    </template>

                    <template v-else-if="config.type === 'segmented'">
                        <el-segmented
                            v-model="configValues[config.field]"
                            :options="segmentedOptions(config)"
                        />
                    </template>

                    <template v-else-if="config.type === 'checkbox'">
                        <el-tooltip
                            v-if="te(`settings.fields.${config.field}.tooltip`)"
                            effect="dark"
                            placement="bottom"
                            raw-content
                            :content="t(`settings.fields.${config.field}.tooltip`)"
                        >
                            <el-checkbox v-model="configValues[config.field]" />
                        </el-tooltip>
                        <el-checkbox v-else v-model="configValues[config.field]" />
                    </template>
                </el-form-item>
            </template>

            <el-form-item :label="t('settings.dark_mode')">
                <el-switch
                    v-model="isDark"
                    @change="toggleDark"
                    inline-prompt
                >
                    <template #active-action>
                        <el-icon><Moon /></el-icon>
                    </template>
                    <template #inactive-action>
                        <el-icon><Sunny /></el-icon>
                    </template>
                </el-switch>
            </el-form-item>

            <el-form-item :label="t('settings.language')">
                <LangSwitcher />
            </el-form-item>

            <el-form-item>
                <el-button type="primary" @click="saveSettings">
                    {{ t('common.save') }}
                </el-button>
            </el-form-item>
        </el-form>
    </div>
</template>

<script setup>
import { reactive } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessageBox } from 'element-plus';
import { useDark, useToggle } from '@vueuse/core';

import Setting from '@/utils/setting';
import LangSwitcher from '@/components/LangSwitcher.vue';

const { t, te } = useI18n();

const isDark = useDark();
const toggleDark = useToggle(isDark);

const configItems = Setting.defaultConfigItems;
const configValues = reactive(Setting.getAll());

function segmentedOptions(config) {
    if (config.optionsI18nKey) {
        return (config.options || []).map((value) => ({
            value,
            label: t(`settings.segments.${config.optionsI18nKey}.${value}`),
        }));
    }
    return config.options || [];
}

async function saveSettings() {
    try {
        await ElMessageBox.confirm(
            t('settings.confirm_reload'),
            t('common.confirm'),
            {
                confirmButtonText: t('common.confirm'),
                cancelButtonText: t('common.cancel'),
                type: 'warning',
            },
        );
    } catch {
        return;
    }
    Object.keys(configValues).forEach((field) => {
        Setting.set(field, configValues[field]);
    });
    location.reload();
}
</script>

<style scoped>
.page-settings__form {
    max-width: 720px;
    width: 100%;
}
</style>
