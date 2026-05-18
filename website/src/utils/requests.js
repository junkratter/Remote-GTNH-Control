import axios from 'axios';
import Setting from '@/utils/setting';

function requestConfig() {
    const configured = (Setting.get('backendUrl') || '').replace(/\/$/, '');
    const baseURL =
        configured || (typeof window !== 'undefined' ? window.location.origin : '');
    const headers = { 'Content-Type': 'application/json' };
    const token = Setting.get('token');
    if (token) {
        headers['X-Server-Token'] = token;
    }
    return { baseURL, headers };
}

class Requests {
    get(url, params = {}) {
        const { baseURL, headers } = requestConfig();
        return axios.get(url, { params, baseURL, headers });
    }

    post(url, data = {}) {
        const { baseURL, headers } = requestConfig();
        return axios.post(url, data, { baseURL, headers });
    }
}

export default new Requests();
