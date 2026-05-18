// Setting fields. Display strings live in src/i18n/*.json under
// `settings.fields.<field>.{label,tooltip,placeholder}` so the UI can be
// rendered in any locale. The `name` field is kept for legacy callers but is
// no longer rendered.

// Migrate localStorage values that used to be display strings (CN) into
// canonical keys ('original' / 'thousand' / 'short'). One-shot on import.
const LEGACY_VALUE_MAP = {
    numberFormatting: {
        '原始': 'original',
        '千分': 'thousand',
        '简化': 'short',
    },
};

(function migrateLegacyValues() {
    for (const [field, map] of Object.entries(LEGACY_VALUE_MAP)) {
        const current = localStorage.getItem(field);
        if (current && map[current]) {
            localStorage.setItem(field, map[current]);
        }
    }
})();

function Setting() {
    this.defaultConfigItems = [
        { type: 'title', i18nKey: 'backend' },
        { field: 'backendUrl', type: 'input', defaultValue: '' },
        { field: 'token', type: 'password', defaultValue: '' },

        { type: 'title', i18nKey: 'basic' },
        { field: 'pageTitle', type: 'input', defaultValue: 'GTNH Cyber' },
        {
            field: 'numberFormatting',
            type: 'segmented',
            optionsI18nKey: 'numberFormatting',
            options: ['original', 'thousand', 'short'],
            defaultValue: 'short',
        },
        { field: 'showMoniter', type: 'checkbox', defaultValue: false },
        { field: 'showFluid', type: 'checkbox', defaultValue: true },
        { field: 'refreshCPU', type: 'checkbox', defaultValue: false },

        { type: 'title', i18nKey: 'map' },
        { field: 'mapOriginX', type: 'input', defaultValue: '0' },
        { field: 'mapOriginZ', type: 'input', defaultValue: '0' },
        { field: 'mapDefaultDimension', type: 'input', defaultValue: '0' },

        { type: 'title', i18nKey: 'other' },
        { field: 'useTaskGzip', type: 'checkbox', defaultValue: false },
        { field: 'useGzip', type: 'checkbox', defaultValue: false },
        { field: 'resourceUrl', type: 'input', defaultValue: '' },
    ];
}

Setting.prototype.getAll = function () {
    const initialConfigValues = {};
    this.defaultConfigItems.forEach((config) => {
        if (!config.field) return;
        const savedValue = localStorage.getItem(config.field);
        initialConfigValues[config.field] = savedValue === null
            ? config.defaultValue
            : (config.type === 'checkbox' ? savedValue === 'true' : savedValue);
    });
    return initialConfigValues;
};

Setting.prototype.get = function (key) {
    for (const config of this.defaultConfigItems) {
        if (config.field === key) {
            const savedValue = localStorage.getItem(key);
            return savedValue === null
                ? config.defaultValue
                : (config.type === 'checkbox' ? savedValue === 'true' : savedValue);
        }
    }
    return undefined;
};

Setting.prototype.set = function (key, value) {
    localStorage.setItem(key, value);
};

export default new Setting();
