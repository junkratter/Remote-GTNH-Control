import Requests from './requests';
import { ElMessage } from 'element-plus';
import { i18n } from '@/i18n';

function t(key, params) {
    return i18n.global.t(key, params);
}

function automateErr(actionKey, data, error) {
    const action = t(`errors.automate.actions.${actionKey}`);
    if (error) {
        ElMessage.error(t('errors.automate.http_throw', { action, detail: String(error) }));
        return;
    }
    ElMessage.error(
        t('errors.automate.http_error', {
            action,
            code: data.code,
            detail: data.message ? data.message : JSON.stringify(data),
        }),
    );
}

const trigger = {
    async getTriggerConfig(callback) {
        try {
            const response = await Requests.get('/api/automate/trigger/config');
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                automateErr('trigger_config', data, null);
                console.error(data);
            }
        } catch (error) {
            automateErr('trigger_config', null, error);
            console.error('Error fetching trigger config:', error);
        }
    },
    async addTrigger(trigger, callback) {
        try {
            const response = await Requests.post('/api/automate/trigger/add', trigger);
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                automateErr('trigger_add', data, null);
            }
        } catch (error) {
            automateErr('trigger_add', null, error);
            console.error('Error adding trigger:', error);
        }
    },
    async removeTrigger(trigger_task_id, callback) {
        try {
            const response = await Requests.post('/api/automate/trigger/remove', { trigger_task_id });
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                automateErr('trigger_remove', data, null);
            }
        } catch (error) {
            automateErr('trigger_remove', null, error);
            console.error('Error removing trigger:', error);
        }
    },
    async getTriggerList(callback) {
        try {
            const response = await Requests.get('/api/automate/trigger/list');
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                automateErr('trigger_list', data, null);
                console.error(data);
            }
        } catch (error) {
            automateErr('trigger_list', null, error);
            console.error('Error fetching trigger list:', error);
        }
    },
    async startTrigger(trigger_task_id, callback) {
        try {
            const response = await Requests.post('/api/automate/trigger/start', { trigger_task_id });
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                automateErr('trigger_start', data, null);
            }
        } catch (error) {
            automateErr('trigger_start', null, error);
            console.error('Error starting trigger:', error);
        }
    },
    async stopTrigger(trigger_task_id, callback) {
        try {
            const response = await Requests.post('/api/automate/trigger/stop', { trigger_task_id });
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                automateErr('trigger_stop', data, null);
            }
        } catch (error) {
            automateErr('trigger_stop', null, error);
            console.error('Error stopping trigger:', error);
        }
    },
};

const timer = {
    async getTimerConfig(callback) {
        try {
            const response = await Requests.get('/api/automate/timer/config');
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                automateErr('timer_config', data, null);
                console.error(data);
            }
        } catch (error) {
            automateErr('timer_config', null, error);
            console.error('Error fetching timer config:', error);
        }
    },
    async addTimer(timer, callback) {
        try {
            const response = await Requests.post('/api/automate/timer/add', timer);
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                automateErr('timer_add', data, null);
            }
        } catch (error) {
            automateErr('timer_add', null, error);
            console.error('Error adding timer:', error);
        }
    },
    async removeTimer(timer_id, callback) {
        try {
            const response = await Requests.post('/api/automate/timer/remove', { timer_id });
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                automateErr('timer_remove', data, null);
            }
        } catch (error) {
            automateErr('timer_remove', null, error);
            console.error('Error removing timer:', error);
        }
    },
    async getTimerList(callback) {
        try {
            const response = await Requests.get('/api/automate/timer/list');
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                automateErr('timer_list', data, null);
                console.error(data);
            }
        } catch (error) {
            automateErr('timer_list', null, error);
            console.error('Error fetching timer list:', error);
        }
    },
    async startTimer(timer_id, callback) {
        try {
            const response = await Requests.post('/api/automate/timer/start', { timer_id });
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                automateErr('timer_start', data, null);
            }
        } catch (error) {
            automateErr('timer_start', null, error);
            console.error('Error starting timer:', error);
        }
    },
    async stopTimer(timer_id, callback) {
        try {
            const response = await Requests.post('/api/automate/timer/stop', { timer_id });
            const data = response.data;
            if (data.code === 200) {
                if (callback) callback(data.data);
            } else {
                automateErr('timer_stop', data, null);
            }
        } catch (error) {
            automateErr('timer_stop', null, error);
            console.error('Error stopping timer:', error);
        }
    },
};

const getActionTemplats = async (callback) => {
    try {
        const response = await Requests.get('/api/automate/action/template');
        const data = response.data;
        if (data.code === 200) {
            if (callback) callback(data.data);
        } else {
            automateErr('action_template', data, null);
            console.error(data);
        }
    } catch (error) {
        automateErr('action_template', null, error);
        console.error('Error fetching action templates:', error);
    }
};

export { trigger, timer, getActionTemplats };
