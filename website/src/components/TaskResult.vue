<template>
    <el-tooltip effect="dark" :content="$t('tasks.click_for_details')" placement="top">
        <el-check-tag :checked="true" :type="statusType(info.data.status)"
            @click="showInfoDialog = !showInfoDialog">
            {{ $t('tasks.status.' + info.data.status) }}
        </el-check-tag>
    </el-tooltip>

    <el-dialog v-model="showInfoDialog" :title="$t('tasks.details')" align-center class="info-dialog">
        <el-text>{{ $t('tasks.task_id') }}: <span>{{ info.id }}</span></el-text>
        <div class="info-container">
            <code>
            <pre>{{ info.data_text }}</pre>
        </code>
        </div>
    </el-dialog>
</template>

<script>
import { fetchStatusOnce } from '@/utils/task'

const statusTypeMap = {
    ready: 'primary',
    pending: 'warning',
    completed: 'success',
    unknown: 'danger',
}

export default {
    props: {
        task_id: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            showInfoDialog: false,
            info: {
                id: "",
                data: {
                    status: "unknown",
                },
                data_text: "",
            }
        };
    },
    methods: {
        statusType(status) {
            return statusTypeMap[status] || 'info';
        },
        fetchTaskInfo(task_id) {
            fetchStatusOnce(task_id, (res) => {
                this.info.id = task_id;
                this.info.data = res;
                this.info.data_text = JSON.stringify(res, null, 4);
            });
        },
    },
    watch: {
        task_id: {
            handler(new_task_id) {
                this.fetchTaskInfo(new_task_id);
            },
            deep: true,
        },
    },
    created() {
        this.fetchTaskInfo(this.task_id);
    },
};
</script>

<style>
@media screen and (max-width: 768px) {
    .info-dialog {
        width: 100% !important;
        max-width: 500px;
    }
}
</style>

<style scoped>
pre {
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow: auto;
    max-height: 400px;
}

.words {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    width: 100%;
}

.info-container {
    width: 100%;
    height: 400px;
    margin: 10px 0;
    overflow-y: auto;
}
</style>
