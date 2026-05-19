import { createRouter, createWebHistory } from 'vue-router';

import Index from '../pages/Index.vue';
import Monitor from '../pages/Monitor.vue';
import Items from '../pages/Items.vue';
import Cpus from '../pages/Cpus.vue';
import Tasks from '../pages/Tasks.vue';
import Automate from '../pages/Automate.vue';
import Settings from '../pages/Settings.vue';
import Info from '../pages/Info.vue';

import Robots from '../pages/Robots.vue';
import Autocraft from '../pages/Autocraft.vue';
import MapPage from '../pages/Map.vue';
import Quests from '../pages/Quests.vue';
import Wiki from '../pages/Wiki.vue';
import Craft from '../pages/Craft.vue';

const routes = [
    { path: '/', name: 'Home', component: Index },
    { path: '/index', name: 'Index', component: Index },
    { path: '/monitor', name: 'Monitor', component: Monitor },
    { path: '/items', name: 'Items', component: Items },
    { path: '/cpus', name: 'Cpus', component: Cpus },
    { path: '/tasks', name: 'Tasks', component: Tasks },
    { path: '/automate', name: 'Automate', component: Automate },
    { path: '/robots', name: 'Robots', component: Robots },
    { path: '/autocraft', name: 'Autocraft', component: Autocraft },
    { path: '/map', name: 'Map', component: MapPage },
    { path: '/quests', name: 'Quests', component: Quests },
    { path: '/wiki', name: 'Wiki', component: Wiki },
    { path: '/craft', name: 'Craft', component: Craft },
    { path: '/settings', name: 'Settings', component: Settings },
    { path: '/info', name: 'Info', component: Info },
];

const router = createRouter({
    history: createWebHistory(),
    routes,
});

export default router;
