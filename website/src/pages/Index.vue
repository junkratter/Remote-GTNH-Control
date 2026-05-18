<template>
    <div class="page page-home">
        <ErrorDisplay v-if="hasLoadError" :error-message="getErrorMessage" />

        <template v-else>
            <section class="page-home__hero glass-card">
                <div class="page-home__logos">
                    <el-image src="/img/gtnh.png" alt="GTNH" class="page-home__logo" fit="contain" />
                    <el-image src="/img/oc.png" alt="OpenComputers" class="page-home__logo" fit="contain" />
                </div>

                <h1 class="page-home__title">{{ $t('app.title') }}</h1>
                <p class="page-home__subtitle">{{ $t('home.subtitle') }}</p>

                <el-tag size="large" round class="page-home__version">
                    GTNH {{ $gameVersion }}
                </el-tag>

                <div class="page-home__links">
                    <el-link
                        :href="`${$defaultLinkPrefix}/${$userName}/${$repoName}`"
                        target="_blank"
                        :underline="false"
                        class="page-home__link"
                    >
                        <el-icon :size="22"><Link /></el-icon>
                        <span>{{ $t('home.repo') }}</span>
                    </el-link>
                    <el-link
                        :href="`${$defaultLinkPrefix}/${$userName}`"
                        target="_blank"
                        :underline="false"
                        class="page-home__link"
                    >
                        <el-icon :size="22"><User /></el-icon>
                        <span>{{ $t('home.author') }}</span>
                    </el-link>
                </div>
            </section>

            <section v-if="isMobile" class="glass-card page-home__hint">
                <el-icon><InfoFilled /></el-icon>
                <span>{{ $t('home.mobile_hint') }}</span>
            </section>
        </template>
    </div>
</template>

<script>
import { inject } from 'vue';
import ErrorDisplay from '@/components/ErrorDisplay.vue';

export default {
    name: 'Index',
    components: { ErrorDisplay },
    setup() {
        const isMobile = inject('isMobile');
        const loadError = inject('loadError');
        const errorMessage = inject('errorMessage');
        return { isMobile, loadError, errorMessage };
    },
    computed: {
        hasLoadError() { return this.loadError(); },
        getErrorMessage() { return this.errorMessage(); },
    },
};
</script>

<style scoped>
.page-home {
    align-items: center;
}

.page-home__hero {
    width: 100%;
    max-width: 720px;
    margin: clamp(12px, 4vh, 48px) auto 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 16px;
    padding: clamp(20px, 4vw, 40px) clamp(16px, 4vw, 40px);
}

.page-home__logos {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: clamp(16px, 4vw, 48px);
    margin-bottom: 8px;
}

.page-home__logo {
    width: clamp(80px, 16vw, 140px);
    height: clamp(80px, 16vw, 140px);
}

.page-home__title {
    font-size: clamp(22px, 3vw, 32px);
    font-weight: 700;
    letter-spacing: 0.3px;
    margin: 0;
}

.page-home__subtitle {
    margin: 0;
    color: var(--el-text-color-secondary);
    font-size: clamp(13px, 1.4vw, 16px);
    max-width: 540px;
    line-height: 1.5;
}

.page-home__version { margin-top: 4px; }

.page-home__links {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 12px;
    margin-top: 12px;
}

.page-home__link {
    display: inline-flex !important;
    align-items: center;
    gap: 8px;
    padding: 10px 18px;
    border-radius: 999px;
    background: var(--glass-bg-weak);
    border: 1px solid var(--glass-border-soft);
    transition: transform 0.18s ease, background 0.18s ease;
}
.page-home__link:hover {
    transform: translateY(-1px);
    background: var(--glass-bg);
}

.page-home__hint {
    display: flex;
    align-items: center;
    gap: 8px;
    max-width: 480px;
    margin: 0 auto;
    font-size: 13px;
    color: var(--el-text-color-secondary);
}
</style>
