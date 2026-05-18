<template>
    <el-space alignment="center" :size="8">
        <el-tag disable-transitions v-if="item.busy" type="warning" effect="light">{{ $t('cpu.busy') }}</el-tag>
        <el-tag disable-transitions v-else type="success" effect="light">{{ $t('cpu.idle') }}</el-tag>
        <span>{{ item.name }} </span>
        <template v-if="item.output && item.output.name">
            <el-image :src="item.output.image || ''" class="component-image-select" :alt="item.output.title">
                <template #placeholder>
                    <el-skeleton :loading="true" animated class="component-image-select">
                        <template #template>
                            <el-skeleton-item variant="image" style="width: 24px; height: 24px" />
                        </template>
                    </el-skeleton>
                </template>
                <template #error>
                    <el-icon size="24" class="unknow-icon">
                        <QuestionFilled />
                    </el-icon>
                </template>
            </el-image>
            <span>{{ item.output.title }}</span>
        </template>
    </el-space>
</template>

<script>

export default {
    props: {
        item: {
            type: Object,
            required: true,
        },
    },
};
</script>

<style scoped>
.unknow-icon {
    /* Center */
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
}

.component-image-select {
    display: block;
    margin-left: 10px;
    width: 24px;
    height: 24px;
}

</style>