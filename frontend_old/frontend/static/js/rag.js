function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value == null ? '' : String(value);
    return div.innerHTML;
}

function setAlert(el, type, message) {
    el.className = `alert alert-${type}`;
    el.textContent = message;
    el.classList.remove('d-none');
}

function clearAlert(el) {
    el.textContent = '';
    el.classList.add('d-none');
}

let chatHistory = [];
const paperCache = JSON.parse(localStorage.getItem('ragPaperCache') || '{}');

function savePaperCache() {
    try {
        localStorage.setItem('ragPaperCache', JSON.stringify(paperCache));
    } catch (_) {
        // localStorage may be unavailable in private mode.
    }
}

function updatePaperCache(papers) {
    if (!papers) return;
    let changed = false;
    Object.entries(papers).forEach(([paperId, info]) => {
        if (info && info.title && !paperCache[paperId]) {
            paperCache[paperId] = info;
            changed = true;
        }
    });
    if (changed) savePaperCache();
}

function setControlsEnabled(searchEnabled, chatEnabled = searchEnabled) {
    document.getElementById('rag-search-submit').disabled = !searchEnabled;
    document.getElementById('rag-chat-submit').disabled = !chatEnabled;
    document.getElementById('rag-upload-submit').disabled = !chatEnabled;
}

async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        const detail = data.detail || data;
        const message = detail.message || detail.detail || data.message || `请求失败：HTTP ${response.status}`;
        throw new Error(message);
    }
    return data;
}

async function loadStats() {
    try {
        const payload = await fetchJson('/api/rag/stats');
        const data = payload.data || {};
        document.getElementById('rag-stat-papers').textContent = data.papers ?? '-';
        document.getElementById('rag-stat-superconductors').textContent = data.superconductors ?? '-';
        document.getElementById('rag-stat-records').textContent = data.records ?? '-';
        document.getElementById('rag-stat-chunks').textContent = data.chunks ?? '-';
        document.getElementById('rag-stat-chroma').textContent = data.chroma_chunks ?? '-';
        document.getElementById('rag-stat-systems').textContent = data.chemical_systems ?? '-';
    } catch (_) {
        // health will show the actionable error.
    }
}

async function checkRagHealth() {
    const statusEl = document.getElementById('rag-status');
    setControlsEnabled(false, false);
    try {
        const payload = await fetchJson('/api/rag/health');
        if (!payload.available) {
            setAlert(statusEl, 'warning', payload.message || 'AI 文献助手数据不可用');
            setControlsEnabled(false, false);
            return;
        }
        await loadStats();
        if (payload.chat_available === false) {
            setAlert(statusEl, 'warning', payload.message || 'RAG 检索可用，LLM 问答未配置');
            setControlsEnabled(true, false);
            return;
        }
        setAlert(statusEl, 'success', payload.message || 'AI 文献助手已就绪');
        setControlsEnabled(true, true);
    } catch (error) {
        setAlert(statusEl, 'warning', `AI 文献助手数据不可用：${error.message}`);
        setControlsEnabled(false, false);
    }
}

function resolvePaperIds(text) {
    return escapeHtml(text).replace(/\[paper_id=(\d+(?:,\s*\d+)*)\]/g, (match, idText) => {
        return idText.split(/\s*,\s*/).map((id) => {
            const info = paperCache[id];
            if (info && info.title) {
                return ` <span class="badge text-bg-info rag-citation-badge" title="${escapeHtml(info.title)}">📄 ${escapeHtml(info.title)}</span>`;
            }
            return ` <span class="badge text-bg-secondary">paper_id=${escapeHtml(id)}</span>`;
        }).join('');
    });
}

function appendChatMessage(role, content) {
    const box = document.getElementById('rag-chat-box');
    const placeholder = box.querySelector('.text-muted.text-center');
    if (placeholder) placeholder.remove();

    const wrapper = document.createElement('div');
    wrapper.className = role === 'user' ? 'mb-3 text-primary fw-semibold' : 'mb-3 rag-answer';
    wrapper.innerHTML = role === 'user' ? `🙋 ${escapeHtml(content)}` : content;
    box.appendChild(wrapper);
    box.scrollTop = box.scrollHeight;
    return wrapper;
}

function renderCitations(container, citations) {
    if (!Array.isArray(citations) || citations.length === 0) return;
    const ids = [...new Set(citations.map((item) => item.paper_id).filter(Boolean))];
    if (ids.length === 0) return;
    const items = ids.map((id) => {
        const info = paperCache[String(id)];
        const label = info && info.title
            ? `[${id}] ${info.title} (${info.journal || '?'}, ${info.year || '?'})`
            : `[${id}] paper_id=${id}`;
        return `<li>${escapeHtml(label)}</li>`;
    }).join('');
    container.innerHTML += `<div class="border-top mt-3 pt-2 small text-muted"><strong>📚 引用论文</strong><ul class="mb-0">${items}</ul></div>`;
}

function renderStructuredTable(top10, papers) {
    const container = document.getElementById('rag-chat-box');
    if (!Array.isArray(top10) || top10.length === 0) return;
    updatePaperCache(papers);

    const rows = top10.map((item) => {
        const info = papers && papers[item.paper_id] ? papers[item.paper_id] : paperCache[String(item.paper_id)];
        const paperTitle = info && info.title ? info.title : `PID_${item.paper_id || '?'}`;
        return `
            <tr>
                <td>${escapeHtml(item.subject)}</td>
                <td class="text-end">${escapeHtml(item.object)}</td>
                <td class="small text-muted">${escapeHtml(paperTitle)}</td>
            </tr>
        `;
    }).join('');

    const wrapper = document.createElement('div');
    wrapper.className = 'table-responsive my-3';
    wrapper.innerHTML = `
        <div class="fw-semibold mb-2">📊 超导数据概览</div>
        <table class="table table-sm table-striped rag-record-table">
            <thead><tr><th>化合物</th><th class="text-end">Tc / 数值</th><th>论文</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>
    `;
    container.appendChild(wrapper);
    container.scrollTop = container.scrollHeight;
}

function parseSseEvents(buffer, onEvent) {
    const parts = buffer.split('\n\n');
    const rest = parts.pop() || '';
    parts.forEach((part) => {
        let eventType = 'message';
        const dataLines = [];
        part.split('\n').forEach((line) => {
            if (line.startsWith('event:')) eventType = line.slice(6).trim();
            if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
        });
        if (dataLines.length === 0) return;
        const raw = dataLines.join('\n');
        try {
            onEvent(eventType, JSON.parse(raw));
        } catch (_) {
            onEvent(eventType, raw);
        }
    });
    return rest;
}

async function submitChat() {
    const questionEl = document.getElementById('rag-question');
    const errorEl = document.getElementById('rag-chat-error');
    const statusEl = document.getElementById('rag-chat-status');
    const button = document.getElementById('rag-chat-submit');
    const question = questionEl.value.trim();

    clearAlert(errorEl);
    clearAlert(statusEl);
    if (!question) {
        setAlert(errorEl, 'danger', '问题不能为空');
        return;
    }

    appendChatMessage('user', question);
    const answerEl = appendChatMessage('assistant', '<span class="spinner-border spinner-border-sm me-2"></span>思考中...');
    questionEl.value = '';
    button.disabled = true;

    let fullAnswer = '';
    let doneData = null;
    try {
        const response = await fetch('/api/rag/chat/stream', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                question,
                top_k: 15,
                rerank_top_k: 5,
                history: chatHistory,
            }),
        });
        if (!response.ok || !response.body) {
            const data = await response.json().catch(() => ({}));
            const detail = data.detail || data;
            throw new Error(detail.message || detail.detail || `请求失败：HTTP ${response.status}`);
        }

        answerEl.innerHTML = '';
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const {done, value} = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, {stream: true});
            buffer = parseSseEvents(buffer, (eventType, data) => {
                if (eventType === 'token') {
                    fullAnswer += typeof data === 'string' ? data : String(data || '');
                    answerEl.innerHTML = resolvePaperIds(fullAnswer);
                } else if (eventType === 'kg_data') {
                    setAlert(statusEl, 'info', `📊 已找到 ${data.count || 0} 条超导数据`);
                } else if (eventType === 'fusion') {
                    setAlert(statusEl, 'info', `🔄 正在融合 ${data.kg_count || 0} 条超导数据与 ${data.chunk_count || 0} 篇文献上下文...`);
                } else if (eventType === 'done') {
                    doneData = data;
                    updatePaperCache(data.papers);
                } else if (eventType === 'error') {
                    throw new Error(data.message || data.detail || 'AI 文献助手返回错误');
                }
            });
        }

        if (doneData) {
            renderCitations(answerEl, doneData.citations || []);
            renderStructuredTable(doneData.top10 || [], doneData.papers || {});
        }

        chatHistory.push({role: 'user', content: question});
        chatHistory.push({role: 'assistant', content: fullAnswer});
        if (chatHistory.length > 20) chatHistory = chatHistory.slice(-20);
    } catch (error) {
        answerEl.innerHTML = `<span class="text-danger">❌ ${escapeHtml(error.message)}</span>`;
    } finally {
        button.disabled = false;
    }
}

function renderList(title, items, formatter) {
    if (!Array.isArray(items) || items.length === 0) {
        return `<section class="mb-3"><h3 class="h6">${escapeHtml(title)}</h3><p class="text-muted mb-0">暂无结果</p></section>`;
    }
    return `
        <section class="mb-3">
            <h3 class="h6">${escapeHtml(title)}</h3>
            <div class="list-group">
                ${items.map(formatter).join('')}
            </div>
        </section>
    `;
}

function renderSearchResults(data) {
    const modeLabel = {
        formula: '化学式',
        elements_exact: '元素体系',
        elements_combination: '元素组合',
        elements_contained: '包含元素',
        semantic: '语义',
        paper: '论文',
    };
    return `
        <div class="small text-muted mb-3">模式：${escapeHtml(modeLabel[data.mode] || data.mode || '-')} · 共 ${escapeHtml(data.total || 0)} 条结果</div>
        ${renderList('超导体', data.superconductors, (item) => `
            <div class="list-group-item">
                <strong>${escapeHtml(item.chemical_formula || item.display_name || item.formula_normalized || '未知材料')}</strong>
                <div class="small text-muted">${escapeHtml(item.formula_normalized || '')}</div>
            </div>
        `)}
        ${renderList('论文', data.papers, (item) => `
            <div class="list-group-item">
                <strong>${escapeHtml(item.title || item.doi || '未知论文')}</strong>
                <div class="small text-muted">${escapeHtml([item.journal, item.year].filter(Boolean).join(' · '))}</div>
                ${item.summary ? `<div class="small mt-1">${escapeHtml(item.summary)}</div>` : ''}
            </div>
        `)}
        ${renderList('文本片段', data.chunks, (item) => `
            <div class="list-group-item">
                <div>${escapeHtml(item.content || item.text || item.chunk || '无文本内容')}</div>
                <div class="small text-muted">paper_id: ${escapeHtml(item.paper_id || '-')} ${item.section_name ? `· ${escapeHtml(item.section_name)}` : ''}</div>
            </div>
        `)}
    `;
}

async function submitSearch() {
    const queryEl = document.getElementById('rag-search-query');
    const modeEl = document.getElementById('rag-search-mode');
    const errorEl = document.getElementById('rag-search-error');
    const resultEl = document.getElementById('rag-search-result');
    const button = document.getElementById('rag-search-submit');
    const query = queryEl.value.trim();

    clearAlert(errorEl);
    if (!query) {
        setAlert(errorEl, 'danger', '搜索内容不能为空');
        return;
    }

    button.disabled = true;
    resultEl.innerHTML = '<div class="text-muted"><span class="spinner-border spinner-border-sm me-2"></span>正在搜索...</div>';
    try {
        const params = new URLSearchParams({q: query, top_k: '10'});
        if (modeEl.value) params.set('mode', modeEl.value);
        const payload = await fetchJson(`/api/rag/search?${params.toString()}`);
        resultEl.innerHTML = renderSearchResults(payload.data || {});
    } catch (error) {
        resultEl.innerHTML = '';
        setAlert(errorEl, 'danger', error.message);
    } finally {
        button.disabled = false;
    }
}

async function uploadPDF() {
    const input = document.getElementById('rag-pdf-input');
    const file = input.files[0];
    const button = document.getElementById('rag-upload-submit');
    const status = document.getElementById('rag-upload-status');

    if (!file) {
        setAlert(status, 'warning', '请选择 PDF 文件');
        return;
    }

    button.disabled = true;
    setAlert(status, 'secondary', '📄 正在上传并提取...');
    try {
        const formData = new FormData();
        formData.append('file', file);
        const payload = await fetchJson('/api/rag/upload-pdf', {method: 'POST', body: formData});
        const data = payload.data || {};
        setAlert(status, 'success', `✅ 提取完成：${data.title || file.name}，发现 ${data.data_points || 0} 个数据点`);
        await loadStats();
    } catch (error) {
        setAlert(status, 'danger', error.message);
    } finally {
        button.disabled = false;
    }
}

function initRagPage() {
    document.getElementById('rag-chat-submit').addEventListener('click', submitChat);
    document.getElementById('rag-chat-clear').addEventListener('click', () => {
        chatHistory = [];
        document.getElementById('rag-chat-box').innerHTML = '<div class="text-muted text-center py-5">💬 上下文已清空，可以开始新对话。</div>';
    });
    document.getElementById('rag-search-submit').addEventListener('click', submitSearch);
    document.getElementById('rag-upload-submit').addEventListener('click', uploadPDF);
    document.getElementById('rag-search-query').addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            submitSearch();
        }
    });
    document.getElementById('rag-question').addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            submitChat();
        }
    });
    checkRagHealth();
}

document.addEventListener('DOMContentLoaded', initRagPage);
