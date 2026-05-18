/** Turn Minecraft §-color/format codes into simple HTML (quest book style). */

const COLORS = {
    '0': '#000000',
    '1': '#0000AA',
    '2': '#00AA00',
    '3': '#00AAAA',
    '4': '#AA0000',
    '5': '#AA00AA',
    '6': '#FFAA00',
    '7': '#AAAAAA',
    '8': '#555555',
    '9': '#5555FF',
    a: '#55FF55',
    b: '#55FFFF',
    c: '#FF5555',
    d: '#FF55FF',
    e: '#FFFF55',
    f: '#FFFFFF',
};

function escapeHtml(s) {
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

/**
 * @param {string} raw
 * @returns {string} safe HTML fragment
 */
export function mcFormatToHtml(raw) {
    if (raw == null || raw === '') return '';
    const text = String(raw).replace(/\r\n/g, '\n');
    let html = '';
    let color = '#E0E0E0';
    let bold = false;
    let italic = false;
    let underline = false;

    const flush = (chunk) => {
        if (!chunk) return;
        const style = [
            `color:${color}`,
            bold ? 'font-weight:700' : '',
            italic ? 'font-style:italic' : '',
            underline ? 'text-decoration:underline' : '',
        ]
            .filter(Boolean)
            .join(';');
        html += `<span style="${style}">${escapeHtml(chunk)}</span>`;
    };

    let buf = '';
    for (let i = 0; i < text.length; i += 1) {
        const ch = text[i];
        if (ch === '§' && i + 1 < text.length) {
            flush(buf);
            buf = '';
            const code = text[i + 1].toLowerCase();
            i += 1;
            if (code in COLORS) {
                color = COLORS[code];
                bold = false;
                italic = false;
                underline = false;
            } else if (code === 'l') bold = true;
            else if (code === 'o') italic = true;
            else if (code === 'n') underline = true;
            else if (code === 'r') {
                color = '#E0E0E0';
                bold = false;
                italic = false;
                underline = false;
            }
            continue;
        }
        if (ch === '\n') {
            flush(buf);
            buf = '';
            html += '<br/>';
            continue;
        }
        buf += ch;
    }
    flush(buf);
    return html;
}
