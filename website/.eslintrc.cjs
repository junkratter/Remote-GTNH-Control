// ESLint configuration for the gtnh-cyber website.
//
// The custom rule below catches literal Cyrillic/CJK strings in <template>
// to enforce vue-i18n discipline. To temporarily allow a literal, prefix
// the file with `/* eslint-disable @intlify/vue-i18n/no-raw-text */`.

module.exports = {
    root: true,
    parserOptions: { ecmaVersion: 2022, sourceType: 'module' },
    env: { browser: true, es2022: true, node: true },
    extends: [
        'plugin:vue/vue3-recommended',
    ],
    rules: {
        // High-noise rules turned off for the legacy pages — re-enable per-file when refactoring.
        'vue/multi-word-component-names': 'off',
        'vue/html-self-closing': 'off',
        'vue/singleline-html-element-content-newline': 'off',
        'vue/max-attributes-per-line': 'off',
        'vue/attribute-hyphenation': 'off',
        'vue/v-on-event-hyphenation': 'off',

        // Custom heuristic: deny raw Cyrillic / CJK strings in templates.
        // Use `t('module.key')` from vue-i18n instead.
        'no-restricted-syntax': [
            'warn',
            {
                selector: "VText[value=/[\\u0400-\\u04FF\\u3400-\\u9FFF\\u3040-\\u30FF]/]",
                message: 'Use $t(\'module.key\') from vue-i18n; never write raw localized strings in templates.',
            },
        ],
    },
    overrides: [
        {
            files: ['src/api/generated/**/*'],
            rules: { 'no-restricted-syntax': 'off' },
        },
    ],
};
