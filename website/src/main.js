import { createApp, ref } from 'vue'
import App from './App.vue'

import router from './router/index'
import { i18n } from './i18n'

import eventBus from 'vue3-eventbus'

import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'

const app = createApp(App);

app.use(router);
app.use(i18n);
app.use(eventBus);
app.use(ElementPlus);

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
}

app.provide('detailManageTable', ref(true));


// Reactive viewport flag. The 900px breakpoint matches the one in
// public/css/liquid-glass.css where the aside collapses into a drawer.
const MOBILE_BREAKPOINT = 900;
const isMobile = ref(window.innerWidth <= MOBILE_BREAKPOINT);
function updateDeviceType() {
  isMobile.value = window.innerWidth <= MOBILE_BREAKPOINT;
}
window.addEventListener('resize', updateDeviceType, { passive: true });
app.provide('isMobile', isMobile);

// Global: upstream repository URL (legacy / about page)
app.config.globalProperties.$defaultLinkPrefix = "https://github.com";
app.config.globalProperties.$userName = "z5882852";
app.config.globalProperties.$repoName = "RemoteOC-GTNH-AE2";
app.config.globalProperties.$gameVersion = "2.8.4";

app.mount('#app')

export default app;