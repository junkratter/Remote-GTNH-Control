<template>
    <el-config-provider :locale="elementLocale">
    <div class="app-shell" :class="{ 'app-shell--no-aside': isMobile }">
        <header class="app-shell__header">
            <el-icon
                v-if="isMobile"
                class="app-shell__menu-btn"
                :size="22"
                @click="toggleDrawer"
            >
                <Expand />
            </el-icon>

            <div class="app-shell__brand">
                <el-link href="/" :underline="false">
                    <h1 class="app-shell__brand-title">{{ pageTitle }}</h1>
                </el-link>
            </div>

            <div class="app-shell__actions">
                <LangSwitcher v-if="!isMobile" />
                <el-switch
                    v-model="isDark"
                    @change="toggleDark"
                    size="default"
                    inline-prompt
                >
                    <template #active-action>
                        <el-icon><Moon /></el-icon>
                    </template>
                    <template #inactive-action>
                        <el-icon><Sunny /></el-icon>
                    </template>
                </el-switch>
                <el-link
                    :href="`${$defaultLinkPrefix}/${$userName}/${$repoName}`"
                    target="_blank"
                    :underline="false"
                    class="app-shell__github"
                >
                    <el-icon :size="22">
                        <svg viewBox="0 0 1024 1024" version="1.1"
                            xmlns="http://www.w3.org/2000/svg">
                            <path
                                d="M511.6 76.3C264.3 76.2 64 276.4 64 523.5 64 718.9 189.3 885 363.8 946c23.5 5.9 19.9-10.8 19.9-22.2v-77.5c-135.7 15.9-141.2-73.9-150.3-88.9C215 726 171.5 718 184.5 703c30.9-15.9 62.4 4 98.9 57.9 26.4 39.1 77.9 32.5 104 26 5.7-23.5 17.9-44.5 34.7-60.8-140.6-25.2-199.2-111-199.2-213 0-49.5 16.3-95 48.3-131.7-20.4-60.5 1.9-112.3 4.9-120 58.1-5.2 118.5 41.6 123.2 45.3 33-8.9 70.7-13.6 112.9-13.6 42.4 0 80.2 4.9 113.5 13.9 11.3-8.6 67.3-48.8 121.3-43.9 2.9 7.7 24.7 58.3 5.5 118 32.4 36.8 48.9 82.7 48.9 132.3 0 102.2-59 188.1-200 212.9 23.5 23.2 38.1 55.4 38.1 91v112.5c0.8 9 0 17.9 15 17.9 177.1-59.7 304.6-227 304.6-424.1 0-247.2-200.4-447.3-447.5-447.3z" />
                        </svg>
                    </el-icon>
                </el-link>
            </div>
        </header>

        <aside v-if="!isMobile" class="app-shell__aside">
            <PageMenu />
        </aside>

        <main class="app-shell__main">
            <router-view v-if="isDataLoaded" v-slot="{ Component }">
                <keep-alive>
                    <component :is="Component" />
                </keep-alive>
            </router-view>
            <ErrorDisplay v-else-if="loadError" :error-message="errorMessage" />
        </main>

        <el-drawer
            v-if="isMobile"
            v-model="drawerVisible"
            :title="pageTitle"
            direction="ltr"
            :size="drawerSize"
            :with-header="true"
        >
            <PageMenu :close-drawer="closeDrawer" />
            <div class="app-shell__drawer-actions">
                <LangSwitcher />
            </div>
        </el-drawer>

        <el-progress
            v-if="showProgress"
            class="app-shell__progress"
            :percentage="itemProgress + fluidsProgress"
            :status="progressStatus"
            striped
            striped-flow
            :stroke-width="14"
            :text-inside="true"
        />
    </div>
    </el-config-provider>
</template>

<script>
import { ElLoading, ElMessage, ElProgress, ElConfigProvider } from "element-plus";
import { inject, computed } from "vue";
import { useDark, useToggle } from "@vueuse/core";
import { useI18n } from "vue-i18n";
import elementZh from "element-plus/es/locale/lang/zh-cn";
import elementEn from "element-plus/es/locale/lang/en";
import elementRu from "element-plus/es/locale/lang/ru";

import itemUtil from "@/utils/items";
import PageMenu from "@/components/PageMenu.vue";
import LangSwitcher from "@/components/LangSwitcher.vue";
import ErrorDisplay from "@/components/ErrorDisplay.vue";
import Setting from "@/utils/setting";

export default {
    components: {
        ElConfigProvider,
        ElProgress,
        PageMenu,
        LangSwitcher,
        ErrorDisplay,
    },
    setup() {
        const isDark = useDark();
        const toggleDark = useToggle(isDark);
        const isMobile = inject("isMobile");
        const { locale } = useI18n();
        const elementLocale = computed(() => {
            const map = { zh: elementZh, en: elementEn, ru: elementRu };
            return map[locale.value] || elementEn;
        });
        return { isMobile, isDark, toggleDark, elementLocale };
    },
    data() {
        return {
            pageTitle: "",
            loadingInstance: null,
            itemProgress: 0,
            fluidsProgress: 0,
            progressStatus: "",
            isDataLoaded: false,
            drawerVisible: false,
            showProgress: false,
            loadError: false,
            errorMessage: "",
        };
    },
    computed: {
        drawerSize() {
            if (window.innerWidth < 480) return "82%";
            return "320px";
        },
    },
    provide() {
        return {
            loadError: () => this.loadError,
            errorMessage: () => this.errorMessage,
        };
    },
    created() {
        this.pageTitle = Setting.get("pageTitle") || this.$t("app.title");
        document.title = this.pageTitle;
        this.loadItemData();
    },
    methods: {
        toggleDrawer() {
            this.drawerVisible = !this.drawerVisible;
        },
        closeDrawer() {
            this.drawerVisible = false;
        },
        loadItemData() {
            this.loadingInstance = ElLoading.service({
                fullscreen: true,
                customClass: "custom-loading",
                text: this.$t("app.loading"),
            });

            let itemsLoaded = false;
            let fluidsLoaded = false;
            this.showProgress = true;

            itemUtil.loadItems((percent) => {
                this.itemProgress = percent / 2;
                if (percent === 100) {
                    itemsLoaded = true;
                    if (itemsLoaded && fluidsLoaded) this._finishLoad();
                } else if (percent === -1) {
                    this._failLoad(`Failed to load items data. Source: ${itemUtil.itemsJsonUrl()}`);
                }
            });

            itemUtil.loadFluids((percent) => {
                this.fluidsProgress = percent / 2;
                if (percent === 100) {
                    fluidsLoaded = true;
                    if (itemsLoaded && fluidsLoaded) this._finishLoad();
                } else if (percent === -1) {
                    this._failLoad(`Failed to load fluids data. Source: ${itemUtil.fluidsJsonUrl()}`);
                }
            });
        },
        _finishLoad() {
            this.loadingInstance && this.loadingInstance.close();
            this.isDataLoaded = true;
            this.showProgress = false;
        },
        _failLoad(message) {
            this.errorMessage = message;
            this.loadError = true;
            this.isDataLoaded = true;
            this.loadingInstance && this.loadingInstance.close();
            this.showProgress = false;
            ElMessage.error(this.$t("common.error"));
        },
    },
};
</script>

<style scoped>
.app-shell__menu-btn {
    cursor: pointer;
    color: var(--el-text-color-primary);
    margin-right: 4px;
}

.app-shell__github {
    display: inline-flex;
    align-items: center;
    color: var(--el-text-color-primary);
}
.app-shell__github svg {
    fill: currentColor;
}

.app-shell__drawer-actions {
    margin-top: 16px;
    padding: 0 12px;
}

.app-shell__progress {
    position: fixed;
    bottom: calc(env(safe-area-inset-bottom, 0px) + 18px);
    left: 50%;
    transform: translateX(-50%);
    width: min(80vw, 360px);
    z-index: 9999;
}
</style>

<style>
.custom-loading .el-loading-spinner .circular > circle {
    display: none;
}

.custom-loading .el-loading-spinner .circular {
    width: 80px !important;
    height: 80px !important;
    background: url("./assets/loading.gif") no-repeat center center;
    background-size: contain;
    animation: none;
}

html {
    --pending-bg-color: #f4f2e4;
    --active-bg-color: #d4e5ce;
}

html.dark {
    --pending-bg-color: rgb(41, 34.2, 24);
    --active-bg-color: rgb(28.3, 37.4, 23.8);
}
</style>
