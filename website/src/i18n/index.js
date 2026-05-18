// vue-i18n initialisation. The active locale is persisted in localStorage
// under the key `lang`. Supported locales: ru, en, zh (source = zh).

import { createI18n } from 'vue-i18n';
import en from './en.json';
import ru from './ru.json';
import zh from './zh.json';

const STORAGE_KEY = 'lang';
export const SUPPORTED_LOCALES = ['ru', 'en', 'zh'];
const DEFAULT_LOCALE = 'ru';

function detectLocale() {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && SUPPORTED_LOCALES.includes(stored)) return stored;
    const browser = (navigator.language || '').slice(0, 2);
    if (SUPPORTED_LOCALES.includes(browser)) return browser;
    return DEFAULT_LOCALE;
}

export const i18n = createI18n({
    legacy: false,
    locale: detectLocale(),
    fallbackLocale: 'en',
    messages: { en, ru, zh },
    globalInjection: true,
});

export function setLocale(locale) {
    if (!SUPPORTED_LOCALES.includes(locale)) return;
    i18n.global.locale.value = locale;
    localStorage.setItem(STORAGE_KEY, locale);
    document.documentElement.lang = locale;
}

export default i18n;
