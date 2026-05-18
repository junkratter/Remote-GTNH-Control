<template>
    <template v-if="formatType !== 'short' || !showTooltip">
        {{ formatNumber(number) }}
    </template>
    <template v-else>
        <el-tooltip effect="dark" placement="top" raw-content :content="number.toLocaleString()">
            {{ formatNumber(number) }}
        </el-tooltip>
    </template>
</template>

<script>
import Setting from '@/utils/setting';

// Backwards compat for users who saved the old Chinese values in localStorage.
const LEGACY_FORMAT_MAP = {
    '原始': 'original',
    '千分': 'thousand',
    '简化': 'short',
};

export default {
    props: {
        number: {
            type: Number,
            required: true,
        },
    },
    data() {
        return {
            formatType: null,
            showTooltip: false,
        };
    },
    created() {
        if (this.$root.formatType) {
            this.formatType = this.$root.formatType;
        } else {
            const raw = Setting.get("numberFormatting");
            this.formatType = LEGACY_FORMAT_MAP[raw] || raw || 'short';
            this.$root.formatType = this.formatType;
        }
    },
    methods: {
        formatNumber(number) {
            if (this.formatType === "original") {
                return number.toString();
            } else if (this.formatType === "thousand") {
                return number.toLocaleString();
            } else if (this.formatType === "short") {
                if (number < 10000) {
                    return number;
                } else if (number < 1000000) {
                    this.showTooltip = true;
                    return Math.floor(number / 1000) + "K";
                } else if (number < 1000000000) {
                    this.showTooltip = true;
                    return Math.floor(number / 1000000) + "M";
                } else {
                    this.showTooltip = true;
                    return Math.floor(number / 1000000000) + "G";
                }
            }
            return number;
        },
    },
};
</script>
