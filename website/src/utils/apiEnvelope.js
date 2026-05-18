/** Extract `data` from backend `{ code, message, data }` envelopes. */

export function envelopePayload(body) {
    if (!body || typeof body !== 'object') {
        return null;
    }
    if (Array.isArray(body.detail)) {
        const detail = body.detail.map((d) => d.msg).filter(Boolean).join('; ');
        throw new Error(detail || 'API validation error');
    }
    if (body.code !== undefined && body.code !== 200) {
        throw new Error(body.message || `API error ${body.code}`);
    }
    if (body.code === 200) {
        return body.data ?? null;
    }
    return body.data ?? body;
}

export function envelopeList(body) {
    const payload = envelopePayload(body);
    if (Array.isArray(payload)) {
        return payload;
    }
    return [];
}
