/** BetterQuesting RU strings from resource pack (lazy-loaded when locale is ru). */

let cache = null;
let loading = null;

export async function ensureBqRuLoaded() {
    if (cache) return cache;
    if (loading) return loading;
    loading = fetch('/bq-ru.json')
        .then((r) => (r.ok ? r.json() : {}))
        .catch(() => ({}))
        .then((data) => {
            cache = data;
            return cache;
        });
    return loading;
}

export function bqQuestName(bqId, fallback, locale) {
    if (!bqId || locale !== 'ru' || !cache) return fallback;
    return cache[`betterquesting.quest.${bqId}.name`] || fallback;
}

export function bqQuestDesc(bqId, fallback, locale) {
    if (!bqId || locale !== 'ru' || !cache) return fallback;
    return cache[`betterquesting.quest.${bqId}.desc`] || fallback;
}

export function bqLineName(bqId, fallback, locale) {
    if (!bqId || locale !== 'ru' || !cache) return fallback;
    return cache[`betterquesting.questline.${bqId}.name`] || fallback;
}

export function bqLineDesc(bqId, fallback, locale) {
    if (!bqId || locale !== 'ru' || !cache) return fallback;
    return cache[`betterquesting.questline.${bqId}.desc`] || fallback;
}
