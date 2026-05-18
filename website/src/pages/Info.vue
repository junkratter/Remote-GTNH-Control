<template>
    <el-descriptions border :column="1" :size="isMobile ? '' : 'large'" :label-width="160" style="margin: 20px;"
        v-loading="loading">
        <el-descriptions-item :label="$t('info.gtnh_version')">{{ $gameVersion }}</el-descriptions-item>
        <el-descriptions-item :label="$t('info.web_version')">{{ version }}</el-descriptions-item>
        <el-descriptions-item :label="$t('info.backend_version')">{{ meta.version }}</el-descriptions-item>
        <el-descriptions-item :label="$t('info.oc_clients')">
            <el-text style="cursor: pointer;" @click="handleClientDialog">
                {{ $t('info.clients_count', { n: meta.device_num }) }}
            </el-text>
        </el-descriptions-item>
        <el-descriptions-item :label="$t('info.source_code')">
            <el-link :href="`${$defaultLinkPrefix}/${$userName}/${$repoName}`" target="_blank" :underline="false">
                {{ $defaultLinkPrefix }}/{{ $userName }}/{{ $repoName }}
            </el-link>
        </el-descriptions-item>
        <el-descriptions-item :label="$t('info.issues')">
            <el-link :href="`${$defaultLinkPrefix}/${$userName}/${$repoName}/issues`" target="_blank"
                :underline="false">
                {{ $defaultLinkPrefix }}/{{ $userName }}/{{ $repoName }}/issues
            </el-link>
        </el-descriptions-item>
        <el-descriptions-item :label="$t('info.api_docs')">
            <el-link :href="backendUrl ? `${backendUrl}/docs` : '#'" target="_blank"
                :underline="false">
                {{ backendUrl ? `${backendUrl}/docs` : '-' }}
            </el-link>
        </el-descriptions-item>
        <el-descriptions-item :label="$t('info.license')">MIT license</el-descriptions-item>
    </el-descriptions>
    <el-dialog v-model="client.show" class="client-dialog" style="height: 400px;" :title="$t('info.client_dialog_title')" align-center>
        <el-table :data="client.data" v-loading="client.loading" :height="340" width="100%" stripe border>
            <el-table-column type="index" :label="$t('common.index')" width="80" align="center"></el-table-column>
            <el-table-column property="id" :label="$t('info.client_id')" align="center" />
            <el-table-column property="last_active_time" :label="$t('info.last_active')" align="center" />
        </el-table>
    </el-dialog>
</template>

<script>
import { inject } from 'vue';
import Setting from '@/utils/setting';
import Requests from '@/utils/requests';

export default {
    name: 'Info',
    data() {
        return {
            loading: false,
            backendUrl: Setting.get('backendUrl'),
            version: __VERSION__,
            meta: {
                version: "-",
                device_num: 0,
            },
            client: {
                show: false,
                loading: false,
                data: [],
            },
            license: "",
        };
    },
    setup() {
        const isMobile = inject('isMobile');
        return {
            isMobile,
        };
    },
    methods: {
        async getMeta() {
            try {
                if (!this.backendUrl) {
                    this.$message.warning(this.$t('info.backend_not_configured'));
                    return;
                }
                this.loading = true;
                const response = await Requests.get('/api/info/meta');
                const data = response.data;
                if (data.code === 200) {
                    this.meta = data.data;
                    this.loading = false;
                } else {
                    this.$message.error(this.$t('info.fetch_meta_failed', { code: data.code, msg: data.message ? data.message : data }));
                    console.error(data);
                    this.loading = false;
                }
            } catch (error) {
                this.$message.error(this.$t('info.fetch_meta_failed', { code: '-', msg: error }));
                console.error('Error fetching meta:', error);
                this.loading = false;
            }
        },
        async getClients() {
            try {
                if (!this.backendUrl) {
                    this.$message.warning(this.$t('info.backend_not_configured'));
                    return;
                }
                this.client.loading = true;
                const response = await Requests.get('/api/info/devices');
                const data = response.data;
                if (data.code === 200) {
                    this.client.data = data.data.map((item) => {
                        return {
                            id: item.id,
                            last_active_time: item.active[item.active.length - 1].time,
                        };
                    });
                    this.client.loading = false;
                } else {
                    this.$message.error(this.$t('info.fetch_clients_failed', { code: data.code, msg: data.message ? data.message : data }));
                    console.error(data);
                    this.client.loading = false;
                }
            } catch (error) {
                this.$message.error(this.$t('info.fetch_clients_failed', { code: '-', msg: error }));
                console.error('Error fetching clients:', error);
                this.client.loading = false;
            }
        },
        handleClientDialog() {
            this.client.show = true;
            this.getClients();
        },
    },
    created() {
        this.getMeta();
    },
    beforeUnmount() {
    },
};
</script>

<style>
@media screen and (max-width: 768px) {
    .client-dialog {
        width: 100% !important;
        max-width: 400px;
    }
}
</style>