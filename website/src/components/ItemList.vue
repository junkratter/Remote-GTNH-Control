<template>
    <div class="item-list">
        <div
            v-for="(row, idx) in items"
            :key="idx"
            class="item-list__row"
        >
            <el-input
                v-model="row.name"
                :placeholder="t('autocraft.item.name')"
                class="item-list__name"
            />
            <el-input-number
                v-model="row.damage"
                :min="0"
                :controls="false"
                :placeholder="t('autocraft.item.damage')"
                class="item-list__damage"
            />
            <el-input-number
                v-model="row.amount"
                :min="1"
                :controls="false"
                :placeholder="t('autocraft.item.amount')"
                class="item-list__amount"
            />
            <el-button
                size="small"
                :icon="Delete"
                circle
                @click="remove(idx)"
            />
        </div>
        <el-button
            size="small"
            :icon="Plus"
            class="item-list__add"
            @click="add"
        >
            {{ t('common.add') }}
        </el-button>
    </div>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { Plus, Delete } from '@element-plus/icons-vue';

const props = defineProps({
    modelValue: { type: Array, default: () => [] },
});
const emit = defineEmits(['update:modelValue']);
const { t } = useI18n();

const items = computed({
    get: () => props.modelValue,
    set: (v) => emit('update:modelValue', v),
});

function add() {
    items.value = [...items.value, { name: '', damage: 0, amount: 1 }];
}

function remove(idx) {
    const next = items.value.slice();
    next.splice(idx, 1);
    items.value = next;
}
</script>

<style scoped>
.item-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    width: 100%;
}
.item-list__row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 100px 100px auto;
    gap: 8px;
    align-items: center;
}
.item-list__name { min-width: 0; }
.item-list__damage,
.item-list__amount { width: 100px; }
.item-list__add { align-self: flex-start; }

@media (max-width: 640px) {
    .item-list__row {
        grid-template-columns: minmax(0, 1fr) 80px 80px auto;
    }
}
</style>
