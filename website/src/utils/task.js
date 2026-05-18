import Requests from './requests';
import { ElMessage, ElNotification } from 'element-plus';
import Setting from '@/utils/setting';
import pako from 'pako';
import { i18n } from '@/i18n';

function t(key, values) {
    return i18n.global.t(key, values);
}

function unwrapEnvelope(response) {
    const body = response?.data;
    if (!body || typeof body !== 'object') {
        return { ok: false, code: 0, detail: t('errors.tasks.bad_response') };
    }
    if (Array.isArray(body.detail)) {
        const detail = body.detail.map((d) => d.msg).filter(Boolean).join('; ');
        return {
            ok: false,
            code: 422,
            detail: detail || t('errors.tasks.missing_token'),
        };
    }
    const { code, message, data } = body;
    if (code === 200) {
        return { ok: true, data, message };
    }
    return {
        ok: false,
        code: code ?? 0,
        detail: message || JSON.stringify(body),
        payload: data,
    };
}

// Poll task status until terminal state
const fetchStatus = async (task_id, handleResult, handleUploading, handleComplete, interval = 1000, pollingController = createPollingController()) => {
    try {
        const response = await Requests.get('/api/task/status', { task_id, remove: false, use_gzip: Setting.get('useTaskGzip') });
        const parsed = unwrapEnvelope(response);
        if (!parsed.ok) {
            if (parsed.code === 404) {
                console.warn(`task ${task_id} not found yet, polling stopped`);
                if (pollingController) {
                    pollingController.stop();
                }
                return;
            }
            if (pollingController) {
                pollingController.stop();
            }
            ElMessage.error(
                t('errors.tasks.status_fail', {
                    code: parsed.code,
                    detail: parsed.detail,
                }),
            );
            console.error(response.data);
            return;
        }
        const payload = parsed.data;
        if (!payload) {
            return;
        }
        if (payload.result && payload.status !== 'uploading') {
            if (payload.gzip) {
                const binaryString = atob(payload.result);
                const binaryData = new Uint8Array(binaryString.length);
                for (let i = 0; i < binaryString.length; i++) {
                    binaryData[i] = binaryString.charCodeAt(i);
                }
                const result = pako.inflate(binaryData, { to: 'string' });
                payload.result = JSON.parse(result);
            }
            if (handleResult) handleResult(payload);
        }
        if (payload.status === 'uploading') {
            if (handleUploading) handleUploading(payload);
        }
        if (payload.status === 'completed') {
            if (handleComplete) handleComplete(payload);
            if (pollingController) {
                pollingController.stop();
            }
        } else if (pollingController && pollingController.running) {
            pollingController.timeoutId = setTimeout(() => {
                fetchStatus(task_id, handleResult, handleUploading, handleComplete, interval, pollingController);
            }, interval);
        }
    } catch (error) {
        if (pollingController) {
            pollingController.stop();
        }
        ElMessage.error(t('errors.tasks.status_catch', { detail: String(error) }));
        console.error(`Error fetching task status: ${error}`);
    }
};

// One-shot task status fetch (no polling)
const fetchStatusOnce = async (task_id, handleResult) => {
    try {
        const response = await Requests.get('/api/task/status', { task_id, remove: false, use_gzip: Setting.get('useTaskGzip') });
        const parsed = unwrapEnvelope(response);
        if (!parsed.ok) {
            if (parsed.code === 404) {
                console.warn(`task ${task_id} not found yet`);
                return;
            }
            ElMessage.error(
                t('errors.tasks.status_fail', {
                    code: parsed.code,
                    detail: parsed.detail,
                }),
            );
            console.error(response.data);
            return;
        }
        const payload = parsed.data;
        if (!payload) {
            return;
        }
        if (payload.result && payload.gzip) {
            const binaryString = atob(payload.result);
            const binaryData = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                binaryData[i] = binaryString.charCodeAt(i);
            }
            const result = pako.inflate(binaryData, { to: 'string' });
            payload.result = JSON.parse(result);
        }
        if (handleResult) handleResult(payload);
    } catch (error) {
        ElMessage.error(t('errors.tasks.status_catch', { detail: String(error) }));
        console.error(`Error fetching task status: ${error}`);
    }
};

const addTask = async (task_id, client_id, handleResult) => {
    try {
        if (!task_id) {
            ElMessage.error(t('errors.tasks.submit_no_id'));
            return;
        }
        const response = await Requests.post('/api/task/task', {
            task_id: task_id,
            client_id: client_id,
        });
        const parsed = unwrapEnvelope(response);
        if (parsed.ok) {
            const taskId = parsed.data?.taskId ?? task_id;
            console.log(`Task '${taskId}' added successfully.`);
            if (handleResult) handleResult(parsed.data ?? { taskId });
        } else {
            ElMessage.error(
                t('errors.tasks.submit_fail', {
                    code: parsed.code,
                    detail: parsed.detail,
                }),
            );
        }
    } catch (error) {
        ElMessage.error(t('errors.tasks.submit_catch', { detail: String(error) }));
        console.error('Error adding task:', error);
    }
};

const addCommands = async (task_id, client_id, commands, handleResult) => {
    try {
        const response = await Requests.post('/api/task/add', {
            task_id: task_id,
            client_id: client_id,
            commands: commands,
        });
        const parsed = unwrapEnvelope(response);
        if (parsed.ok) {
            const taskId = parsed.data?.taskId ?? task_id;
            console.log(`Task '${taskId}' added successfully.`);
            if (handleResult) handleResult(parsed.data ?? { taskId });
        } else {
            ElMessage.error(
                t('errors.tasks.submit_fail', {
                    code: parsed.code,
                    detail: parsed.detail,
                }),
            );
        }
    } catch (error) {
        ElMessage.error(t('errors.tasks.submit_catch', { detail: String(error) }));
        console.error('Error adding task:', error);
    }
};

const createPollingController = () => ({
    running: true,
    timeoutId: null,
    stop() {
        this.running = false;
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
            this.timeoutId = null;
        }
    },
});

const localTask = {
    saveTaskId: (taskId, taskType, data) => {
        const tasks = JSON.parse(localStorage.getItem('tasks')) || [];
        const task = {
            id: taskId,
            type: taskType,
            data: data,
        };
        tasks.push(task);
        localStorage.setItem('tasks', JSON.stringify(tasks));
    },
    getTasks: () => JSON.parse(localStorage.getItem('tasks')) || [],
    getTask: (taskId) => {
        const tasks = JSON.parse(localStorage.getItem('tasks')) || [];
        return tasks.find((task) => task.id === taskId) || null;
    },
    removeTask: (taskId) => {
        let tasks = JSON.parse(localStorage.getItem('tasks')) || [];
        tasks = tasks.filter((task) => task.id !== taskId);
        localStorage.setItem('tasks', JSON.stringify(tasks));
    },
    updateTaskData: (taskId, newData) => {
        const tasks = JSON.parse(localStorage.getItem('tasks')) || [];
        const taskIndex = tasks.findIndex((task) => task.id === taskId);
        if (taskIndex !== -1) {
            tasks[taskIndex].data = newData;
            localStorage.setItem('tasks', JSON.stringify(tasks));
        } else {
            console.error(`Task with ID ${taskId} not found.`);
        }
    },
};

const createCraftTask = (itemName, ItemDamage, amount = 1, cpuName, label, callback, cpuCallback) => {
    let command;
    if (cpuName) {
        if (label) {
            command = `return ae.requestItem('${itemName}', ${ItemDamage}, ${amount}, '${cpuName}', '${label}')`;
        } else {
            command = `return ae.requestItem('${itemName}', ${ItemDamage}, ${amount}, '${cpuName}')`;
        }
    } else if (label) {
        command = `return ae.requestItem('${itemName}', ${ItemDamage}, ${amount}, nil, '${label}')`;
    } else {
        command = `return ae.requestItem('${itemName}', ${ItemDamage}, ${amount})`;
    }

    const commands = [command];

    const refreshCPU = Setting.get('refreshCPU');
    if (refreshCPU) {
        commands.push('return ae.getCpuList(true)');
    }

    addCommands(null, null, commands, (data) => {
        if (callback) callback(data);
        const task_id = data.taskId;
        localTask.saveTaskId(task_id, 'craft');
        ElNotification({
            title: t('errors.craft.title'),
            message: t('errors.craft.submitted', { taskId: task_id }),
            type: 'info',
            duration: 6000,
        });
        const showErrorNotification = (reason) => {
            ElNotification({
                title: t('errors.craft.title'),
                message: t('errors.craft.failed', { reason, taskId: task_id }),
                type: 'warning',
                duration: 6000,
            });
        };
        fetchStatus(
            task_id,
            null,
            null,
            (taskData) => {
                try {
                    if (taskData && taskData.result && taskData.result[0]) {
                        const result = JSON.parse(taskData.result[0]);
                        if (result.message && result.message === 'success' && result.data) {
                            if (result.data.failed) {
                                if (result.data.done.why === 'request failed (missing resources?)') {
                                    showErrorNotification(t('errors.craft.reason_missing'));
                                } else {
                                    showErrorNotification(t('errors.craft.reason_unknown'));
                                }
                            } else {
                                ElNotification({
                                    title: t('errors.craft.title'),
                                    message: t('errors.craft.success', { taskId: task_id }),
                                    type: 'success',
                                    duration: 6000,
                                });
                            }
                        } else {
                            showErrorNotification(t('errors.craft.reason_unknown'));
                        }
                    } else {
                        showErrorNotification(t('errors.craft.reason_unknown'));
                    }
                    if (refreshCPU && taskData && taskData.result && taskData.result.length > 1 && taskData.result[1]) {
                        try {
                            if (cpuCallback)
                                cpuCallback({
                                    ...taskData,
                                    result: [taskData.result[1]],
                                });
                        } catch (error) {
                            console.error(error);
                            ElMessage.error(t('errors.tasks.refresh_cpu', { detail: String(error) }));
                        }
                    }
                } catch (error) {
                    console.error(error);
                    showErrorNotification(t('errors.craft.reason_unknown'));
                }
            },
            1000,
            createPollingController(),
        );
    });
};

/**
 * Fetch task history from the API.
 */
const fetchHistory = async (task_id, options = {}) => {
    try {
        const params = { task_id, ...options };
        const response = await Requests.get('/api/task/history', params);
        const parsed = unwrapEnvelope(response);
        if (!parsed.ok) {
            if (parsed.code === 404) {
                ElMessage.warning(t('errors.history.empty'));
                return null;
            }
            ElMessage.error(t('errors.history.fail', { detail: parsed.detail }));
            return null;
        }
        const data = parsed.data;
        if (!data) {
            return null;
        }
        if (data.gzip && data.result) {
            const binaryString = atob(data.result);
            const binaryData = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                binaryData[i] = binaryString.charCodeAt(i);
            }
            const result = pako.inflate(binaryData, { to: 'string' });
            return JSON.parse(result);
        }
        return data;
    } catch (error) {
        console.error('Error fetching history data:', error);
        ElMessage.error(t('errors.history.catch', { detail: String(error) }));
        return null;
    }
};

export {
    fetchStatus,
    fetchStatusOnce,
    fetchHistory,
    addTask,
    createPollingController,
    localTask,
    createCraftTask,
};
