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

function setControlsEnabled(enabled) {
    document.getElementById('rag-chat-submit').disabled = !enabled;
    document.getElementById('rag-search-submit').disabled = !enabled;
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

async function checkRagHealth() {
    const statusEl = document.getElementById('rag-status');
    setControlsEnabled(false);
    try {
        const payload = await fetchJson('/api/rag/health');
        if (payload.available) {
            setAlert(statusEl, 'success', 'AI 文献助手已连接。');
            setControlsEnabled(true);
        } else {
            setAlert(statusEl, 'warning', payload.message || 'AI 文献助手服务暂不可用，请稍后再试。');
            setControlsEnabled(false);
        }
    } catch (error) {
        setAlert(statusEl, 'warning', `AI 文献助手服务暂不可用：${error.message}`);
        setControlsEnabled(false);
    }
}

function renderCitations(citations) {
    if (!Array.isArray(citations) || citations.length === 0) {
        return '';
    }
    const items = citations.map((item) => {
        const title = item.title || item.paper_title || item.doi || item.id || '来源';
        return `<li>${escapeHtml(title)}</li>`;
    }).join('');
    return `<h3 class="h6 mt-3">来源</h3><ul>${items}</ul>`;
}

async function submitChat() {
    const questionEl = document.getElementById('rag-question');
    const errorEl = document.getElementById('rag-chat-error');
    const resultEl = document.getElementById('rag-chat-result');
    const button = document.getElementById('rag-chat-submit');
    const question = questionEl.value.trim();

    clearAlert(errorEl);
    if (!question) {
        setAlert(errorEl, 'danger', '问题不能为空');
        return;
    }

    button.disabled = true;
    resultEl.innerHTML = '<div class="text-muted">正在生成回答...</div>';
    try {
        const payload = await fetchJson('/api/rag/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({question}),
        });
        const data = payload.data || {};
        const answer = data.answer || 'AI 文献助手未返回答案。';
        resultEl.innerHTML = `
            <div class="border rounded p-3 bg-light">
                <div style="white-space: pre-wrap;">${escapeHtml(answer)}</div>
                ${renderCitations(data.citations || data.sources)}
            </div>
        `;
    } catch (error) {
        resultEl.innerHTML = '';
        setAlert(errorEl, 'danger', error.message);
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
    return [
        renderList('超导体', data.superconductors, (item) => `
            <div class="list-group-item">
                <strong>${escapeHtml(item.chemical_formula || item.display_name || item.formula_normalized || '未知材料')}</strong>
                <div class="small text-muted">${escapeHtml(item.formula_normalized || '')}</div>
            </div>
        `),
        renderList('论文', data.papers, (item) => `
            <div class="list-group-item">
                <strong>${escapeHtml(item.title || item.doi || '未知论文')}</strong>
                <div class="small text-muted">${escapeHtml([item.journal, item.year].filter(Boolean).join(' · '))}</div>
            </div>
        `),
        renderList('文本片段', data.chunks, (item) => `
            <div class="list-group-item">
                <div>${escapeHtml(item.content || item.text || item.chunk || '无文本内容')}</div>
                <div class="small text-muted">paper_id: ${escapeHtml(item.paper_id || '-')}</div>
            </div>
        `),
    ].join('');
}

async function submitSearch() {
    const queryEl = document.getElementById('rag-search-query');
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
    resultEl.innerHTML = '<div class="text-muted">正在搜索...</div>';
    try {
        const params = new URLSearchParams({q: query, top_k: '10'});
        const payload = await fetchJson(`/api/rag/search?${params.toString()}`);
        const data = payload.data || {};
        resultEl.innerHTML = renderSearchResults(data);
    } catch (error) {
        resultEl.innerHTML = '';
        setAlert(errorEl, 'danger', error.message);
    } finally {
        button.disabled = false;
    }
}

function initRagPage() {
    document.getElementById('rag-chat-submit').addEventListener('click', submitChat);
    document.getElementById('rag-search-submit').addEventListener('click', submitSearch);
    document.getElementById('rag-search-query').addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            submitSearch();
        }
    });
    checkRagHealth();
}

document.addEventListener('DOMContentLoaded', initRagPage);
