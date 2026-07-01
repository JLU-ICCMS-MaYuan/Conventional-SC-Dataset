// 全局变量
let elementSymbols = '';
let uploadModal, imageModal;
let selectedFiles = [];
let currentReviewStatus = 'all'; // 当前选择的审核状态筛选
let currentDatabase = 'all';
const paperCache = new Map();
const alexDetailCache = {};
const cifDetailCache = {};
const alexExpandCache = {};

// Jmol 元素颜色（用于 3Dmol 图例）
const _JMOL_COLORS = {
    H:'#ffffff', He:'#d9ffff', Li:'#cc80ff', Be:'#c2ff00', B:'#ffb5b5',
    C:'#909090', N:'#3050f8', O:'#ff0d0d', F:'#90e050', Ne:'#b3e3f5',
    Na:'#ab5cf2', Mg:'#8aff00', Al:'#bfa6a6', Si:'#f0c8a0', P:'#ff8000',
    S:'#ffff30', Cl:'#1ff01f', Ar:'#80d1e3', K:'#8f40d4', Ca:'#3dff00',
    Sc:'#e6e6e6', Ti:'#bfc2c7', V:'#a6a6ab', Cr:'#8a99c7', Mn:'#9c7ac7',
    Fe:'#e06633', Co:'#f090a0', Ni:'#50d050', Cu:'#c88033', Zn:'#7d80b0',
    Ga:'#c28f8f', Ge:'#668f8f', As:'#bd80e3', Se:'#ffa100', Br:'#a62929',
    Kr:'#5cb8d1', Rb:'#702eb0', Sr:'#00ff00', Y:'#94ffff', Zr:'#94e0e0',
    Nb:'#73c2c2', Mo:'#54b5b5', Tc:'#3b9e9e', Ru:'#248f8f', Rh:'#0a7d8c',
    Pd:'#006985', Ag:'#c0c0c0', Cd:'#ffd98f', In:'#a67573', Sn:'#668080',
    Sb:'#9e63bf', Te:'#d47a00', I:'#940094', Xe:'#429eb0', Cs:'#57178f',
    Ba:'#00c900', La:'#70d4ff', Ce:'#ffffc7', Pr:'#d9ffc7', Nd:'#c7ffc7',
    Pm:'#a3ffc7', Sm:'#8fffc7', Eu:'#61ffc7', Gd:'#45ffc7', Tb:'#30ffc7',
    Dy:'#1fffc7', Ho:'#00ff9c', Er:'#00e675', Tm:'#00d452', Yb:'#00bf38',
    Lu:'#00ab24', Hf:'#4dc2ff', Ta:'#4da6ff', W:'#2194d6', Re:'#267dab',
    Os:'#266696', Ir:'#175487', Pt:'#d0d0e0', Au:'#ffd123', Hg:'#b8b8d0',
    Tl:'#a6544d', Pb:'#575961', Bi:'#9e4fb5', Po:'#ab5c00', At:'#754f45',
    Rn:'#428296', Fr:'#420066', Ra:'#007d00', Ac:'#70abfa', Th:'#00baff',
    Pa:'#00a1ff', U:'#008fff', Np:'#0080ff', Pu:'#006bff', Am:'#545cf2',
    Cm:'#785ce3', Bk:'#8a4fe3', Cf:'#a136d4', Es:'#b31fd4', Fm:'#b31fba',
    Md:'#b30da6', No:'#bd0d87', Lr:'#c70066',
};

function _addLegend(containerEl, elements) {
    if (!containerEl || !elements || !elements.length) return;
    var leg = document.createElement('div');
    leg.style.cssText = 'position:absolute;bottom:4px;left:4px;background:rgba(255,255,255,0.9);padding:2px 8px;border-radius:4px;font-size:11px;line-height:1.5;z-index:5;display:flex;flex-wrap:wrap;gap:0 8px;';
    leg.innerHTML = elements.map(function(el) {
        var color = _JMOL_COLORS[el] || '#888';
        return '<span style="display:inline-flex;align-items:center;gap:3px;"><span style="width:10px;height:10px;border-radius:50%;background:' + color + ';flex-shrink:0;"></span>' + el + '</span>';
    }).join('');
    containerEl.appendChild(leg);
}
const urlParams = new URLSearchParams(window.location.search);
const SEARCH_MODE_ALIASES = {
    only: 'elements_exact_search',
    combination: 'elements_combination_search',
    contains: 'elements_contained_search',
};
let viewMode = SEARCH_MODE_ALIASES[urlParams.get('mode')] || urlParams.get('mode') || 'elements_exact_search';
const ONLY_MODE_PAGE_SIZE = 50;
const currentSearchParams = {};
const onlyModePagination = {
    page: 1,
    pageSize: ONLY_MODE_PAGE_SIZE,
    total: 0,
    totalPages: 0,
};
const multiModePagination = {
    page: 1,
    pageSize: ONLY_MODE_PAGE_SIZE,
    total: 0,
    totalPages: 0,
};
const allDbPagination = { page: 1, pageSize: 30, total: 0, totalPages: 0 };
if (!['elements_exact_search', 'elements_combination_search', 'elements_contained_search', 'formula_search'].includes(viewMode)) {
    viewMode = 'elements_exact_search';
}

function getAuthState() {
    return window.authState ? window.authState.get() : null;
}

function sanitizeFilename(name) {
    if (!name) return 'paper';
    return name.replace(/[\\/:*?"<>|]+/g, '_');
}

function getSelectedElementsFromPath() {
    return elementSymbols ? elementSymbols.split('-').filter(Boolean) : [];
}

function getModeDescription(mode = viewMode) {
    const map = {
        elements_exact_search: I18N.t('compound.mode_desc_only'),
        elements_combination_search: I18N.t('compound.mode_desc_combination'),
        elements_contained_search: I18N.t('compound.mode_desc_contains'),
        formula_search: I18N.t('compound.mode_desc_only')
    };
    return map[mode] || map.elements_exact_search;
}

function updateModeSubtitle(extraText) {
    const subtitleEl = document.getElementById('compound-subtitle');
    if (!subtitleEl) return;
    const desc = getModeDescription();
    subtitleEl.innerHTML = extraText ? `${desc} · ${extraText}` : desc;
}

function calculateSFactor(tcValue, pressureValue) {
    const tc = parseFloat(tcValue);
    const pressure = parseFloat(pressureValue);
    if (!Number.isFinite(tc) || !Number.isFinite(pressure)) {
        return null;
    }
    return tc / Math.sqrt(1521 + Math.pow(pressure, 2));
}

function formatDataCell(value, unit = '') {
    if (value === null || value === undefined || value === '') {
        return 'null';
    }
    return `${value}${unit ? ` ${unit}` : ''}`;
}

function formatRangeCell(values, unit = '') {
    if (!Array.isArray(values) || values.length === 0) {
        return 'null';
    }
    return `${values.join(' - ')}${unit ? ` ${unit}` : ''}`;
}

function renderPhysicalDataTable(dataRows) {
    const rows = (dataRows || []).filter(d => d != null && d.tc_max != null);
    if (rows.length === 0) {
        return `<span class="text-muted">${I18N.t('compound.no_physical_data')}</span>`;
    }

    const articleLabel = (d) => d.article_type === 'e' ? I18N.t('common.yes') : (d.article_type === 't' ? I18N.t('common.no') : '—');
    const f = (v, u) => v != null ? `${Number(v).toFixed(1)} ${u || ''}`.trim() : '—';

    const rowHtml = rows.map(d => `
        <tr>
            <td>${d.chemical_formula || '—'}</td>
            <td style="max-width:120px;white-space:normal;font-size:0.85rem;">${d.space_group_symbol || '—'}</td>
            <td>${articleLabel(d)}</td>
            <td>${f(d.tc_max, 'K')}</td>
            <td>${f(d.pressure_gpa, 'GPa')}</td>
            <td>${f(d.lambda_value)}</td>
            <td>${f(d.omega_log)}</td>
            <td>${f(d.n_ef_total)}</td>
        </tr>
    `).join('');

    return `
        <div class="table-responsive mt-1 mb-2">
            <table class="table table-sm table-bordered align-middle mb-0">
                <thead class="table-light">
                    <tr>
                        <th>${I18N.t('compound.chemical_formula')}</th>
                        <th>${I18N.t('compound.crystal_structure')}</th>
                        <th>${I18N.t('compound.is_experimental')}</th>
                        <th>${I18N.t('compound.superconducting_temp')}</th>
                        <th>${I18N.t('compound.superconducting_pressure')}</th>
                        <th>λ</th>
                        <th>ω_log</th>
                        <th>N(E_F)</th>
                    </tr>
                </thead>
                <tbody>${rowHtml}</tbody>
            </table>
        </div>
    `;
}

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    // 从URL获取元素组合
    const pathParts = window.location.pathname.split('/');
    elementSymbols = pathParts[pathParts.length - 1];

    // 初始化模态框
    uploadModal = new bootstrap.Modal(document.getElementById('uploadModal'));
    imageModal = new bootstrap.Modal(document.getElementById('imageModal'));

    // 加载页面数据
    loadCompoundInfo();
    loadPapers();
    loadCrystalStructures();

    const state = getAuthState();

    if (state && state.user && state.user.is_admin) {
        const adminOnlyLabel = document.getElementById('label-status-admin-only');
        if (adminOnlyLabel) adminOnlyLabel.style.display = 'inline-block';
    }

    // ?upload=1 自动弹出上传框
    if (urlParams.get('upload') === '1') {
        const auth = getAuthState();
        if (auth && auth.token) {
            uploadModal.show();
        }
    }
});

// 加载元素组合信息
async function loadCompoundInfo() {
    if (!elementSymbols) return;
    document.getElementById('compound-title').textContent = `${elementSymbols} ${I18N.t('compound.system_sc')}`;
    updateModeSubtitle();
}

// 加载文献列表
async function loadPapers(searchParams = null) {
    const container = document.getElementById('papers-container');
    container.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div><p class="mt-3">加载中...</p></div>';
    if (searchParams !== null) {
        Object.keys(currentSearchParams).forEach(key => delete currentSearchParams[key]);
        Object.assign(currentSearchParams, searchParams);
    }

    try {
        if (currentDatabase === 'all')        { await loadAllDatabases(container); return; }
        if (currentDatabase === 'alexandria') { await loadAlexandriaMaterials(container); return; }
        if (currentDatabase === 'htsc2025')  { await loadHTSC2025Materials(container); return; }
        const queryString = buildQueryString(currentSearchParams);
        if (viewMode === 'elements_exact_search') {
            const payload = await fetchPapersForCombination(elementSymbols, queryString);
            renderSingleCombination(container, payload);
            updateModeSubtitle(`共 ${payload.total} 篇文献`);
            renderPagination(payload, 'paper');
        } else {
            await renderMultipleCombinations(container, queryString);
        }
    } catch (error) {
        console.error('加载文献失败:', error);
        container.innerHTML = `<div class="alert alert-danger">加载失败：${error.message}</div>`;
        clearPaginationUi();
    }
}

// 审核状态筛选
function filterByReviewStatus(status) {
    currentReviewStatus = status;
    resetCurrentPage();
    loadPapers(currentSearchParams);
}

function getActivePaginationState() {
    return viewMode === 'elements_exact_search' ? onlyModePagination : multiModePagination;
}

function getApiBase() {
    return '';
}

function resetCurrentPage() {
    getActivePaginationState().page = 1;
}

function buildQueryString(searchParams = {}) {
    const params = new URLSearchParams();
    if (searchParams.keyword) params.append('keyword', searchParams.keyword);
    if (searchParams.year_min) params.append('year_min', searchParams.year_min);
    if (searchParams.year_max) params.append('year_max', searchParams.year_max);
    if (currentReviewStatus !== 'all') params.append('review_status', currentReviewStatus);
    const pagination = getActivePaginationState();
    params.append('limit', pagination.pageSize);
    params.append('offset', (pagination.page - 1) * pagination.pageSize);
    return params.toString();
}

// 全数据库聚合加载（后端合并+缓存）
async function loadAllDatabases(container) {
    const elements = getSelectedElementsFromPath();
    if (!elements.length) { container.innerHTML = '<div class="alert alert-warning text-center">请先选择元素</div>'; return; }
    const pg = allDbPagination;
    const ps = pg.pageSize;

    try {
        const resp = await fetch('/api/papers/search/all', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ elements, mode: viewMode, limit: ps, offset: (pg.page - 1) * ps }),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || '搜索失败');

        pg.total = data.total || 0;
        pg.totalPages = data.total_pages || 1;

        const items = data.items || [];
        let html = `<p class="text-muted mb-3"><strong>全部数据库 · 元素：</strong>${elements.join(' · ')}</p>`;
        let currentSection = null;
        let itemCount = 0;

        items.forEach(item => {
            if (item._type === 'section') {
                if (currentSection) html += '</section>';
                html += `<section class="mb-4"><h4 class="mb-2">${item.key}<span class="badge bg-secondary ms-2">${item.count} 条</span></h4>`;
                currentSection = item;
                return;
            }
            if (item._source === 'alexandria') html += renderAlexandriaCard(item);
            else if (item._source === 'htsc2025') html += renderHTSC2025Card(item);
            else html += renderPaperCard(item);
            itemCount++;
        });
        if (currentSection) html += '</section>';

        if (items.length === 0) html += '<div class="alert alert-warning text-center"><p class="mb-0">未找到匹配数据</p></div>';
        container.innerHTML = html;

        const start = pg.total > 0 ? (pg.page - 1) * ps + 1 : 0;
        const end = Math.min(start + itemCount - 1, pg.total);
        updateModeSubtitle(`全部数据库 · 第 ${start}-${end} 条，共 ${pg.total} 条`);

        // 分页
        const pagEl = document.getElementById('papers-pagination');
        const sumEl = document.getElementById('papers-summary');
        if (sumEl) sumEl.style.display = 'none';
        if (!pagEl || pg.totalPages <= 1) { if (pagEl) pagEl.innerHTML = ''; return; }
        pagEl.style.display = 'block';
        let pagesHtml = '';
        const maxShow = 10;
        let pStart = Math.max(1, pg.page - Math.floor(maxShow / 2));
        let pEnd = Math.min(pg.totalPages, pStart + maxShow - 1);
        if (pEnd - pStart < maxShow - 1) pStart = Math.max(1, pEnd - maxShow + 1);
        for (let i = pStart; i <= pEnd; i++) {
            pagesHtml += `<li class="page-item ${i === pg.page ? 'active' : ''}"><button class="page-link" onclick="changeAllDbPage(${i})">${i}</button></li>`;
        }
        pagEl.innerHTML = `<nav><ul class="pagination justify-content-center flex-wrap mb-0">
            <li class="page-item ${pg.page <= 1 ? 'disabled' : ''}"><button class="page-link" onclick="changeAllDbPage(${pg.page - 1})">上一页</button></li>
            ${pagesHtml}
            <li class="page-item ${pg.page >= pg.totalPages ? 'disabled' : ''}"><button class="page-link" onclick="changeAllDbPage(${pg.page + 1})">下一页</button></li>
        </ul></nav>`;
    } catch (err) {
        console.error('聚合搜索失败:', err);
        container.innerHTML = `<div class="alert alert-danger">加载失败：${err.message}</div>`;
    }
}

function onDatabaseChange() {
    currentDatabase = document.getElementById('db-select').value;
    allDbPagination.page = 1;
    resetCurrentPage();
    loadPapers(currentSearchParams);
}

function changeAllDbPage(p) {
    if (p < 1 || p > allDbPagination.totalPages) return;
    allDbPagination.page = p;
    loadPapers();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Alexandria 搜索和渲染
function _alexMode(vm) { const m = { elements_exact_search: 'only', elements_combination_search: 'combination', elements_contained_search: 'contains' }; return m[vm] || vm; }
async function loadAlexandriaMaterials(container) {
    const elements = getSelectedElementsFromPath();
    const pagination = getActivePaginationState();

    try {
        const body = {
            elements,
            mode: _alexMode(viewMode),
            min_tc: (parseFloat(document.getElementById('min-tc-input')?.value) || null),
            stable_only: (document.getElementById('stable-only-input')?.checked || false),
            limit: pagination.pageSize,
            offset: (pagination.page - 1) * pagination.pageSize,
        };

        const response = await fetch('/api/alexandria/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            throw new Error((await response.json()).detail || '查询失败');
        }

        const data = await response.json();
        const items = data.items || [];

        // 更新分页状态
        pagination.total = data.total || 0;
        pagination.totalPages = Math.ceil(pagination.total / pagination.pageSize) || 1;

        if (items.length === 0) {
            container.innerHTML = `<div class="alert alert-warning text-center"><p class="mb-0">Alexandria 数据库中未找到匹配的电声耦合材料数据</p></div>`;
            clearPaginationUi();
            return;
        }

        // 渲染材料卡片
        container.innerHTML = items.map(item => renderAlexandriaCard(item)).join('');
        window._alexandriaItems = items;

        // 更新标题显示数据库名和数量
        const subtitleEl = document.getElementById('compound-subtitle');
        if (subtitleEl) {
            subtitleEl.innerHTML = `${I18N.t('compound.alexandria_title')} · ${I18N.t(viewMode === 'only' ? 'index.mode_only' : viewMode === 'contains' ? 'index.mode_contains' : 'index.mode_combination')} · ${data.total} ${I18N.t('compound.material_count')}`;
        }

        // 渲染分页
        renderAlexandriaPagination(data);
    } catch (error) {
        console.error('Alexandria 查询失败:', error);
        container.innerHTML = `<div class="alert alert-danger">Alexandria 查询失败：${error.message}</div>`;
        clearPaginationUi();
    }
}

function renderAlexandriaCard(item) {
    const safeId = (item.mat_id || '').replace(/[^a-zA-Z0-9-]/g, '_');
    const tcVal = item.tc_allen_dynes != null ? item.tc_allen_dynes.toFixed(2) + ' K' : (item.tc_max != null ? item.tc_max.toFixed(2) + ' K' : '—');
    const tcColor = (item.tc_allen_dynes || item.tc_max || 0) > 77 ? 'text-danger fw-bold' : '';
    const lambdaStr = item.lambda_val != null ? item.lambda_val.toFixed(4) : '—';
    const isExpanded = alexExpandCache[item.mat_id] || false;

    return `
        <div class="card paper-card mb-3">
            <div class="card-body">
                <!-- 折叠栏（点击展开） -->
                <div class="paper-summary" style="cursor: pointer;" onclick="toggleAlexandriaCard('${item.mat_id}')">
                    <div class="d-flex align-items-center justify-content-between">
                        <div class="flex-grow-1">
                            <strong class="${tcColor}">${item.formula || I18N.t('compound.unknown_formula')}</strong> |
                            Tc: ${tcVal} |
                            λ: ${lambdaStr} |
                            <span class="badge bg-info">Alexandria</span>
                        </div>
                        <div>
                            <i class="bi bi-chevron-down" id="alex-chevron-${safeId}">${isExpanded ? '▲' : '▼'}</i>
                        </div>
                    </div>
                </div>

                <!-- 展开区域（结构图 + 详情） -->
                <div id="alex-details-${safeId}" class="paper-details mt-3" style="display: ${isExpanded ? 'block' : 'none'};">
                    <div class="row">
                        <div class="col-md-7">
                            <div id="struct-viewer-alex-${safeId}"
                                 style="position:relative;width:100%;height:400px;border:1px solid #dee2e6;border-radius:4px;background:#f8f9fa;">
                                <div class="text-center text-muted py-5">
                                    <div class="spinner-border spinner-border-sm" role="status"></div>
                                    <br><small>加载结构图中...</small>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-5">
                            <h5 class="card-title mb-1 ${tcColor}">${item.formula || I18N.t('compound.unknown_formula')}</h5>
                            <p class="text-muted small mb-1">
                                ${(item.elements || []).join(' · ')} ·
                                ${item.imag
                                    ? '<span class="badge bg-warning">' + I18N.t('compound.unstable') + '</span>'
                                    : '<span class="badge bg-success">' + I18N.t('compound.stable') + '</span>'}
                                · mat_id: ${item.mat_id}
                            </p>

                            <div class="mb-2">
                                <strong>物理参数:</strong>
                                <div class="row text-center small g-1 mt-1">
                                    ${[
                                        ['压力', item.pressure != null ? item.pressure.toFixed(1) + ' GPa' : '—'],
                                        ['Tc<sub>McM</sub>', item.tc_mcmillan != null ? item.tc_mcmillan.toFixed(2) + ' K' : '—'],
                                        ['Tc<sub>AD</sub>', item.tc_allen_dynes != null ? item.tc_allen_dynes.toFixed(2) + ' K' : '—'],
                                        ['Tc<sub>El</sub>', item.tc_eliashberg != null ? item.tc_eliashberg.toFixed(2) + ' K' : '—'],
                                        ['λ', lambdaStr],
                                        ['ω<sub>log</sub>', item.wlog != null ? item.wlog.toFixed(2) + ' K' : '—'],
                                        ['费米能级', item.dos_ef != null ? item.dos_ef.toFixed(3) + ' eV' : '—'],
                                    ].map(([label, val]) =>
                                        `<div class="col-4 p-1"><div class="bg-light rounded p-1"><div class="text-muted" style="font-size:0.65rem;">${label}</div><strong style="font-size:0.8rem;">${val}</strong></div></div>`
                                    ).join('')}
                                </div>
                            </div>

                            <div class="mt-2 d-flex gap-2">
                                <a class="btn btn-outline-secondary btn-sm"
                                   href="/api/alexandria/material/${item.mat_id}/download" download>
                                    📥 ${I18N.t('compound.download_data')}
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

async function loadTestDatabase(container) {
    const elements = getSelectedElementsFromPath();
    const elementsText = elements.join(' · ');
    container.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div><p class="mt-3">加载中...</p></div>';

    const [aiPapers, alexMaterials] = await Promise.all([
        Promise.resolve([]),
        fetchTestAlexandriaMaterials(elements),
    ]);

    const savedDb = currentDatabase;

    // 1. AI 论文分组（按组合）
    const sections = groupPapersByCompound(aiPapers || []);
    const sectionMap = new Map();
    sections.forEach(s => sectionMap.set(s.combo.element_symbols, s));

    // 2. Alexandria 材料归入已有组合或新建组合
    (alexMaterials || []).forEach(m => {
        const key = [...(m.elements || [])].sort().join('-');
        if (sectionMap.has(key)) {
            sectionMap.get(key).papers.push({ _isAlexandria: true, _data: m });
        } else {
            const ns = {
                combo: { element_symbols: key, element_list: [...(m.elements || [])].sort() },
                papers: [{ _isAlexandria: true, _data: m }],
            };
            sections.push(ns);
            sectionMap.set(key, ns);
        }
    });

    currentDatabase = savedDb;
    if (alexMaterials && alexMaterials.length > 0) window._alexandriaItems = alexMaterials;

    // 3. 渲染：每组中先 AI 后 Alexandria，各自按 Tc 排序
    let html = `<p class="text-muted mb-3"><strong>元素：</strong>${elementsText}</p>`;
    let totalCount = 0;

    sections.forEach(sec => {
        const papers = sec.papers || [];
        if (papers.length === 0) return;

        // 分组内排序：按 Tc 降序
        papers.sort((a, b) => {
            let tcA = 0, tcB = 0;
            if (a._isAlexandria && a._data) tcA = a._data.tc_allen_dynes || a._data.tc_max || 0;
            else if (a.data && a.data[0]) tcA = parseFloat(a.data[0].tc) || 0;
            if (b._isAlexandria && b._data) tcB = b._data.tc_allen_dynes || b._data.tc_max || 0;
            else if (b.data && b.data[0]) tcB = parseFloat(b.data[0].tc) || 0;
            return tcB - tcA;
        });

        totalCount += papers.length;
        const content = papers.map(p => {
            if (p._isAlexandria) {
                try { return renderAlexandriaCard(p._data); } catch(e) { return ''; }
            }
            currentDatabase = 'ai';
            const html = renderPaperCard(p);
            currentDatabase = savedDb;
            return html;
        }).join('');

        html += `
            <section class="mb-5">
                <div class="d-flex justify-content-between align-items-center mb-2 flex-wrap gap-2">
                    <div>
                        <h4 class="mb-0">${sec.combo.element_symbols}<span class="badge bg-secondary ms-2">${papers.length} ${I18N.t('index.chart_papers')}</span></h4>
                        <small class="text-muted">元素：${(sec.combo.element_list || []).join(' · ')}</small>
                    </div>
                </div>
                ${content}
            </section>
        `;
    });

    if (totalCount === 0) {
        html += '<div class="alert alert-warning text-center"><p class="mb-0">未找到匹配数据</p></div>';
    }
    container.innerHTML = html;

    const sub = document.getElementById('compound-subtitle');
    if (sub) {
        const modeLabel = viewMode === 'only' ? I18N.t('index.mode_only')
            : viewMode === 'contains' ? I18N.t('index.mode_contains')
            : I18N.t('index.mode_combination');
        sub.innerHTML = `${I18N.t('compound.test_db')} · ${modeLabel} · ${elements.join('-')} · ${totalCount} 条结果`;
    }
}

async function fetchTestAlexandriaMaterials(elements) {
    try {
        const body = {
            elements, mode: _alexMode(viewMode),
            min_tc: (parseFloat(document.getElementById('min-tc-input')?.value) || null),
            stable_only: (document.getElementById('stable-only-input')?.checked || false),
            limit: 50, offset: 0,
        };
        const resp = await fetch('/api/alexandria/search', {
            method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body),
        });
        const data = await resp.json();
        return data.items || [];
    } catch (e) {
        console.error('Alexandria 材料加载失败:', e);
        return [];
    }
}


function toggleAlexandriaCard(matId) {
    const safeId = (matId || '').replace(/[^a-zA-Z0-9-]/g, '_');
    const detailEl = document.getElementById(`alex-details-${safeId}`);
    const chevron = document.getElementById(`alex-chevron-${safeId}`);
    if (!detailEl) return;

    const isNowVisible = detailEl.style.display !== 'none' && detailEl.style.display !== '';
    if (isNowVisible) {
        detailEl.style.display = 'none';
        if (chevron) chevron.textContent = '▼';
        alexExpandCache[matId] = false;
        return;
    }

    detailEl.style.display = 'block';
    if (chevron) chevron.textContent = '▲';
    alexExpandCache[matId] = true;

    // 首次展开才加载数据
    if (alexDetailCache[matId]) return;
    alexDetailCache[matId] = true;

    const item = window._alexandriaItems ? window._alexandriaItems.find(i => i.mat_id === matId) : null;

    // 加载 CIF 结构图
    const vEl = document.getElementById(`struct-viewer-alex-${safeId}`);
    if (vEl) {
        fetch(`/api/alexandria/material/${matId}/cif`)
            .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.text(); })
            .then(cif => {
                if (!cif || cif.length < 10) throw new Error('空数据');
                vEl.innerHTML = '';
                if (typeof $3Dmol !== 'undefined') {
                    const viewer = $3Dmol.createViewer(vEl, {defaultcolors: $3Dmol.elementColors.Jmol});
                    viewer.addModel(cif, 'cif');
                    viewer.setStyle({}, {
                        stick: {radius: 0.12, colorscheme: 'Jmol'},
                        sphere: {scale: 0.3, colorscheme: 'Jmol'},
                    });
                    viewer.addUnitCell({line: {color: '#888', width: 2}});
                    viewer.zoomTo();
                    viewer.render();
                    if (item && item.elements) _addLegend(vEl, [...new Set(item.elements)]);
                } else {
                    vEl.innerHTML = '<div class="text-center text-muted py-5"><small>$3Dmol 未加载</small></div>';
                }
            })
            .catch(() => {
                vEl.innerHTML = '<div class="text-center text-muted py-5"><small>无结构数据</small></div>';
            });
    }

}

function renderAlexandriaPagination(data) {
    const summaryEl = document.getElementById('papers-summary');
    const paginationEl = document.getElementById('papers-pagination');
    if (!summaryEl || !paginationEl) return;

    const pagination = getActivePaginationState();
    const total = data.total || 0;
    const pageSize = pagination.pageSize;
    const totalPages = Math.ceil(total / pageSize) || 1;
    const page = pagination.page;

    if (total === 0) {
        clearPaginationUi();
        return;
    }

    const start = (page - 1) * pageSize + 1;
    const end = Math.min(start + (data.items ? data.items.length : 0) - 1, total);
    summaryEl.style.display = 'block';
    summaryEl.textContent = I18N.t('compound.page_material_info', { start, end, total });

    if (totalPages <= 1) {
        paginationEl.innerHTML = '';
        paginationEl.style.display = 'none';
        return;
    }

    paginationEl.style.display = 'block';
    paginationEl.innerHTML = `
        <nav aria-label="分页导航">
            <ul class="pagination justify-content-center flex-wrap mb-0">
                <li class="page-item ${data.has_prev ? '' : 'disabled'}">
                    <button class="page-link" type="button" onclick="changeAlexandriaPage(${page - 1})" ${data.has_prev ? '' : 'disabled'}>${I18N.t('compound.prev_page')}</button>
                </li>
                ${renderAlexandriaPageNumbers(page, totalPages)}
                <li class="page-item ${data.has_next ? '' : 'disabled'}">
                    <button class="page-link" type="button" onclick="changeAlexandriaPage(${page + 1})" ${data.has_next ? '' : 'disabled'}>${I18N.t('compound.next_page')}</button>
                </li>
            </ul>
        </nav>
    `;
}

function renderAlexandriaPageNumbers(current, total) {
    const maxVisible = 5;
    const half = Math.floor(maxVisible / 2);
    let start = Math.max(1, current - half);
    let end = Math.min(total, start + maxVisible - 1);
    start = Math.max(1, end - maxVisible + 1);
    let html = '';
    for (let p = start; p <= end; p++) {
        html += `<li class="page-item ${p === current ? 'active' : ''}">
            <button class="page-link" type="button" onclick="changeAlexandriaPage(${p})">${p}</button>
        </li>`;
    }
    return html;
}

function changeAlexandriaPage(page) {
    const pagination = getActivePaginationState();
    if (page < 1 || page === pagination.page) return;
    pagination.page = page;
    loadPapers(currentSearchParams);
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// HTSC-2025 搜索和渲染
async function loadHTSC2025Materials(container) {
    const elements = getSelectedElementsFromPath();
    const pagination = getActivePaginationState();

    try {
        const body = {
            elements,
            mode: _alexMode(viewMode),
            min_tc: (parseFloat(document.getElementById('min-tc-input')?.value) || null),
            limit: pagination.pageSize,
            offset: (pagination.page - 1) * pagination.pageSize,
        };

        const response = await fetch('/api/htsc2025/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            throw new Error((await response.json()).detail || '查询失败');
        }

        const data = await response.json();
        const items = data.items || [];

        pagination.total = data.total || 0;
        pagination.totalPages = Math.ceil(pagination.total / pagination.pageSize) || 1;

        if (items.length === 0) {
            container.innerHTML = `<div class="alert alert-warning text-center"><p class="mb-0">HTSC-2025 数据集中未找到匹配的材料</p></div>`;
            clearPaginationUi();
            return;
        }

        container.innerHTML = items.map(item => renderHTSC2025Card(item)).join('');

        const subtitleEl = document.getElementById('compound-subtitle');
        if (subtitleEl) {
            subtitleEl.innerHTML = `${I18N.t('compound.htsc2025_title')} · ${I18N.t(viewMode === 'only' ? 'index.mode_only' : viewMode === 'contains' ? 'index.mode_contains' : 'index.mode_combination')} · ${data.total} ${I18N.t('compound.material_count')}`;
        }

        renderHTSC2025Pagination(data);
    } catch (error) {
        console.error('HTSC-2025 查询失败:', error);
        container.innerHTML = `<div class="alert alert-danger">HTSC-2025 查询失败：${error.message}</div>`;
        clearPaginationUi();
    }
}

function renderHTSC2025Card(item) {
    const safeId = (item.name || '').replace(/[^a-zA-Z0-9-]/g, '_');
    const tcVal = item.tc != null ? item.tc.toFixed(1) + ' K' : '—';
    const tcColor = item.tc > 77 ? 'text-danger fw-bold' : '';
    const cc = item.composition || {};
    const compEntries = Object.entries(cc).map(([el, n]) => `${el}${n > 1 ? '<sub>' + n.toFixed(1).replace(/\.0$/, '') + '</sub>' : ''}`).join('');
    const isExpanded = alexExpandCache[item.name] || false;

    return `
        <div class="card paper-card mb-3">
            <div class="card-body">
                <div class="paper-summary" style="cursor: pointer;" onclick="toggleAlexandriaCard('${item.name}')">
                    <div class="d-flex align-items-center justify-content-between">
                        <div class="flex-grow-1">
                            <strong class="${tcColor}">${item.formula || item.name}</strong> |
                            Tc: ${tcVal} |
                            ${item.class ? item.class + ' |' : ''}
                            <span class="badge bg-info">HTSC-2025</span>
                        </div>
                        <div>
                            <i class="bi bi-chevron-down" id="alex-chevron-${safeId}">${isExpanded ? '▲' : '▼'}</i>
                        </div>
                    </div>
                </div>

                <div id="alex-details-${safeId}" class="paper-details mt-3" style="display: ${isExpanded ? 'block' : 'none'};">
                    <div class="row">
                        <div class="col-md-7">
                            <div id="struct-viewer-htsc-${safeId}"
                                 style="position:relative;width:100%;height:380px;border:1px solid #dee2e6;border-radius:4px;background:#f8f9fa;">
                                <div class="text-center text-muted py-5">
                                    <small>点击「查看 CIF」加载结构图</small>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-5">
                            <h5 class="card-title mb-1 ${tcColor}">${item.formula || item.name}</h5>
                            <p class="text-muted small mb-1">
                                ${(item.elements || []).join(' · ')} ·
                                <span class="badge bg-secondary">${item.class || '未知类别'}</span>
                            </p>
                            ${compEntries ? `<p class="text-muted small mb-1">组成: ${compEntries}</p>` : ''}
                            <div class="mb-2">
                                <strong>物理参数:</strong>
                                <div class="row text-center small g-1 mt-1">
                                    ${[
                                        ['Tc', tcVal],
                                        ['类别', item.class || '—'],
                                    ].map(([label, val]) =>
                                        `<div class="col-4 p-1"><div class="bg-light rounded p-1"><div class="text-muted" style="font-size:0.65rem;">${label}</div><strong style="font-size:0.8rem;">${val}</strong></div></div>`
                                    ).join('')}
                                </div>
                            </div>
                            <div class="mt-2">
                                <button class="btn btn-outline-primary btn-sm" onclick="toggleCIFDetail('${item.name}')">
                                    📐 ${I18N.t('compound.view_cif')}
                                </button>
                            </div>
                        </div>
                    </div>
                    <div id="cif-detail-${safeId}" class="mt-2" style="display: none;" data-elements="${(item.elements||[]).join(',')}">
                        <pre class="bg-light p-2 rounded small mb-0" style="max-height: 380px; overflow-y: auto; font-size: 0.7rem;"></pre>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function renderHTSC2025Pagination(data) {
    const summaryEl = document.getElementById('papers-summary');
    const paginationEl = document.getElementById('papers-pagination');
    if (!summaryEl || !paginationEl) return;

    const pagination = getActivePaginationState();
    const total = data.total || 0;
    const pageSize = pagination.pageSize;
    const totalPages = Math.ceil(total / pageSize) || 1;
    const page = pagination.page;

    if (total === 0) { clearPaginationUi(); return; }

    const start = (page - 1) * pageSize + 1;
    const end = Math.min(start + (data.items ? data.items.length : 0) - 1, total);
    summaryEl.style.display = 'block';
    summaryEl.textContent = I18N.t('compound.page_material_info', { start, end, total });

    if (totalPages <= 1) { paginationEl.innerHTML = ''; paginationEl.style.display = 'none'; return; }

    paginationEl.style.display = 'block';
    paginationEl.innerHTML = `
        <nav aria-label="分页导航">
            <ul class="pagination justify-content-center flex-wrap mb-0">
                <li class="page-item ${data.has_prev ? '' : 'disabled'}">
                    <button class="page-link" type="button" onclick="changePage('htsc2025', ${page - 1})" ${data.has_prev ? '' : 'disabled'}>${I18N.t('compound.prev_page')}</button>
                </li>
                <li class="page-item ${data.has_next ? '' : 'disabled'}">
                    <button class="page-link" type="button" onclick="changePage('htsc2025', ${page + 1})" ${data.has_next ? '' : 'disabled'}>${I18N.t('compound.next_page')}</button>
                </li>
            </ul>
        </nav>
    `;
}

function toggleCIFDetail(name) {
    const safeId = name.replace(/[^a-zA-Z0-9-]/g, '_');
    const detailEl = document.getElementById(`cif-detail-${safeId}`);
    if (!detailEl) return;

    if (detailEl.style.display === 'none') {
        detailEl.style.display = 'block';
        if (cifDetailCache[name]) return;
        fetch(`/api/htsc2025/detail/${encodeURIComponent(name)}`)
            .then(r => r.json())
            .then(data => {
                const cif = data.cif || '';
                const pre = detailEl.querySelector('pre');
                if (pre) pre.textContent = cif || '(无 CIF 数据)';
                const uniqEls = (detailEl.dataset.elements || '').split(',').filter(Boolean);
                if (cif && typeof $3Dmol !== 'undefined') {
                    setTimeout(() => {
                        const vEl = document.getElementById(`struct-viewer-htsc-${safeId}`);
                        if (!vEl) return;
                        const viewer = $3Dmol.createViewer(vEl, {defaultcolors: $3Dmol.elementColors.Jmol});
                        viewer.addModel(cif, 'cif');
                        viewer.setStyle({}, {
                            stick: {radius: 0.12, colorscheme: 'Jmol'},
                            sphere: {scale: 0.3, colorscheme: 'Jmol'},
                        });
                        viewer.addUnitCell({line: {color: '#888', width: 2}});
                        viewer.zoomTo();
                        viewer.render();
                        _addLegend(vEl, uniqEls);
                    }, 100);
                }
                cifDetailCache[name] = true;
            })
            .catch(err => {
                infoEl.innerHTML = `<div class="text-danger small">加载失败: ${err.message}</div>`;
            });
    } else {
        detailEl.style.display = 'none';
    }
}

function normalizePaperListPayload(data) {
    if (Array.isArray(data)) {
        return {
            items: data,
            total: data.length,
            page: 1,
            page_size: data.length,
            total_pages: data.length > 0 ? 1 : 0,
            has_prev: false,
            has_next: false,
        };
    }

    return {
        items: Array.isArray(data?.items) ? data.items : [],
        total: Number.isFinite(data?.total) ? data.total : (Array.isArray(data?.items) ? data.items.length : 0),
        page: Number.isFinite(data?.page) ? data.page : 1,
        page_size: Number.isFinite(data?.page_size) ? data.page_size : ONLY_MODE_PAGE_SIZE,
        total_pages: Number.isFinite(data?.total_pages) ? data.total_pages : 0,
        has_prev: Boolean(data?.has_prev),
        has_next: Boolean(data?.has_next),
    };
}

function groupPapersByCompound(papers) {
    const grouped = new Map();
    for (const paper of papers) {
        const key = paper.compound_symbols || paper.chemical_formula || '未知组合';
        if (!grouped.has(key)) {
            grouped.set(key, {
                combo: {
                    element_symbols: key,
                    element_list: key.split('-').filter(Boolean),
                },
                papers: [],
            });
        }
        grouped.get(key).papers.push(paper);
    }
    return Array.from(grouped.values()).sort((a, b) => a.combo.element_symbols.localeCompare(b.combo.element_symbols));
}

async function fetchPapersForCombination(symbols, queryString) {
    const url = queryString ? `/api${getApiBase()}/papers/compound/${symbols}?${queryString}` : `/api${getApiBase()}/papers/compound/${symbols}`;
    const response = await fetch(url);
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.detail || '加载失败');
    }
    return normalizePaperListPayload(data);
}

function renderSingleCombination(container, payload) {
    const papers = Array.isArray(payload?.items) ? payload.items : [];
    if (papers.length === 0) {
        container.innerHTML = renderEmptyState();
        return;
    }
    container.innerHTML = papers.map(paper => renderPaperCard(paper)).join('');
}

function clearPaginationUi() {
    const summaryEl = document.getElementById('papers-summary');
    const paginationEl = document.getElementById('papers-pagination');
    if (summaryEl) {
        summaryEl.innerHTML = '';
        summaryEl.style.display = 'none';
    }
    if (paginationEl) {
        paginationEl.innerHTML = '';
        paginationEl.style.display = 'none';
    }
}

function renderPagination(payload, mode = 'paper') {
    const summaryEl = document.getElementById('papers-summary');
    const paginationEl = document.getElementById('papers-pagination');
    if (!summaryEl || !paginationEl) return;

    const pagination = mode === 'paper' ? getActivePaginationState() : multiModePagination;
    pagination.page = payload.page || 1;
    pagination.pageSize = payload.page_size || ONLY_MODE_PAGE_SIZE;
    pagination.total = payload.total || 0;
    pagination.totalPages = payload.total_pages || 0;

    if (pagination.total === 0) {
        clearPaginationUi();
        return;
    }

    const start = (pagination.page - 1) * pagination.pageSize + 1;
    const itemCount = Array.isArray(payload.items) ? payload.items.length : 0;
    const end = Math.min(start + itemCount - 1, pagination.total);
    summaryEl.style.display = 'block';
    summaryEl.textContent = mode === 'paper'
        ? `第 ${start}-${end} 条，共 ${pagination.total} 条`
        : `第 ${start}-${end} 个组合，共 ${pagination.total} 个组合`;

    if (pagination.totalPages <= 1) {
        paginationEl.innerHTML = '';
        paginationEl.style.display = 'none';
        return;
    }

    paginationEl.style.display = 'block';
    paginationEl.innerHTML = `
        <nav aria-label="分页导航">
            <ul class="pagination justify-content-center flex-wrap mb-0">
                <li class="page-item ${payload.has_prev ? '' : 'disabled'}">
                    <button class="page-link" type="button" onclick="changePage('${mode}', ${pagination.page - 1})" ${payload.has_prev ? '' : 'disabled'}>${I18N.t('compound.prev_page')}</button>
                </li>
                ${renderPageNumberItems(pagination.page, pagination.totalPages, mode)}
                <li class="page-item ${payload.has_next ? '' : 'disabled'}">
                    <button class="page-link" type="button" onclick="changePage('${mode}', ${pagination.page + 1})" ${payload.has_next ? '' : 'disabled'}>${I18N.t('compound.next_page')}</button>
                </li>
            </ul>
        </nav>
    `;
}

function renderPageNumberItems(currentPage, totalPages, mode = 'paper') {
    const maxVisiblePages = 5;
    const halfWindow = Math.floor(maxVisiblePages / 2);
    let start = Math.max(1, currentPage - halfWindow);
    let end = Math.min(totalPages, start + maxVisiblePages - 1);
    start = Math.max(1, end - maxVisiblePages + 1);

    let html = '';
    for (let page = start; page <= end; page++) {
        html += `
            <li class="page-item ${page === currentPage ? 'active' : ''}">
                <button class="page-link" type="button" onclick="changePage('${mode}', ${page})">${page}</button>
            </li>
        `;
    }
    return html;
}

function changePage(mode, page) {
    const pagination = mode === 'paper' ? getActivePaginationState() : multiModePagination;
    pagination.page = page;
    loadPapers(currentSearchParams);
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function renderMultipleCombinations(container, queryString) {
    const payload = await fetchPapersByMode(viewMode);
    const papers = payload.items || [];
    if (papers.length === 0) {
        container.innerHTML = `
            <div class="alert alert-warning text-center">
                <p class="mb-0">当前筛选条件下没有可展示的文献，请尝试切换筛选模式或放宽筛选条件。</p>
            </div>
        `;
        updateModeSubtitle('暂无符合条件的文献');
        clearPaginationUi();
        return;
    }

    const sections = groupPapersByCompound(papers);
    updateModeSubtitle(`当前页共 ${papers.length} 篇文献，总计 ${payload.total} 篇`);
    container.innerHTML = sections.map(section => renderCombinationSection(section)).join('');
    renderPagination(payload, 'paper');
}

async function fetchPapersByMode(mode) {
    const elements = getSelectedElementsFromPath();
    if (!elements.length) return { items: [], total: 0, page: 1, page_size: 50, total_pages: 0, has_prev: false, has_next: false };
    const pagination = multiModePagination;
    const body = {
        elements,
        mode,
        keyword: currentSearchParams.keyword || null,
        year_min: currentSearchParams.year_min || null,
        year_max: currentSearchParams.year_max || null,
        review_status: currentReviewStatus !== 'all' ? currentReviewStatus : null,
        limit: pagination.pageSize,
        offset: (pagination.page - 1) * pagination.pageSize,
        sort_by: 'year',
        sort_order: 'desc',
    };

    const response = await fetch(`/api${getApiBase()}/papers/search-by-mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.detail || '文献检索失败');
    }
    return normalizePaperListPayload(data);
}

async function fetchCombinationList(mode) {
    const elements = getSelectedElementsFromPath();
    if (!elements.length) return { items: [], total: 0 };
    const pagination = multiModePagination;
    const response = await fetch('/api/compounds/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            elements,
            mode,
            limit: pagination.pageSize,
            offset: (pagination.page - 1) * pagination.pageSize,
        })
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.detail || '组合检索失败');
    }
    return data;
}

function renderCombinationSection(section) {
    const combo = section.combo;
    const papers = section.papers || [];
    const title = combo.element_symbols;
    const elementsText = combo.element_list.join(' · ');
    const countBadge = `<span class="badge bg-secondary ms-2">${papers.length} ${I18N.t('index.chart_papers')}</span>`;

    let content = '';
    if (section.error) {
        content = `<div class="alert alert-danger">加载失败：${section.error}</div>`;
    } else if (papers.length === 0) {
        content = renderEmptyState(`${I18N.t('compound.system_sc')} ${title} ${I18N.t('compound.no_papers')}`);
    } else {
        content = papers.map(paper => renderPaperCard(paper)).join('');
    }

    return `
        <section class="mb-5">
            <div class="d-flex justify-content-between align-items-center mb-2 flex-wrap gap-2">
                <div>
                    <h4 class="mb-0">${title}${countBadge}</h4>
                    <small class="text-muted">元素：${elementsText}</small>
                </div>
            </div>
            ${content}
        </section>
    `;
}

function renderEmptyState(customText) {
    const statusMap = {
        'approved': I18N.t('compound.review_status_approved'),
        'pending': I18N.t('compound.review_status_unreviewed'),
        'rejected': I18N.t('compound.review_status_rejected'),
        'needs_revision': '需修改'
    };
    const statusText = statusMap[currentReviewStatus] || '';
    const message = customText || `这个元素组合还没有${statusText}文献记录${currentReviewStatus === 'all' ? '，<strong>成为第一个贡献者吧！</strong>' : ''}`;
    return `
        <div class="text-center py-5">
            <div class="alert alert-warning" role="alert">
                <h4 class="alert-heading">🎉 暂无${statusText}文献</h4>
                <p class="mb-0">${message}</p>
                ${currentReviewStatus === 'all' && !customText ? '<hr><p class="mb-0">点击上方的 <strong>"上传文献"</strong> 按钮即可添加第一篇文献</p>' : ''}
            </div>
        </div>
    `;
}

// 渲染文献卡片（简化版，点击展开）
function renderPaperCard(paper) {
    paperCache.set(paper.id, paper);
    const authors = Array.isArray(paper.authors) ? paper.authors : (paper.authors ? JSON.parse(paper.authors) : []);
    const firstAuthor = authors.length > 0 ? authors[0] : '未知作者';
    const correspondingAuthor = authors.length > 0 ? authors[authors.length - 1] : '未知作者';

    // Tc 数据 — 按优先级取第一个有值的
    const tcValue = paper.experimental_tc
        || paper.anisotropic_eliashberg_tc
        || paper.isotropic_eliashberg_tc
        || paper.allen_dynes_tc
        || paper.mcmillan_tc;
    const hasTc = tcValue != null;
    // 压强摘要
    const pressures = Array.isArray(paper.pressures_gpa) && paper.pressures_gpa.length > 0
        ? paper.pressures_gpa : [];
    const pressureStr = pressures.length > 0
        ? (pressures.length === 1 ? ` @ ${pressures[0]} GPa` : ` @ ${pressures[0]}–${pressures[pressures.length-1]} GPa`)
        : '';
    const tcSummary = hasTc ? `${Number(tcValue).toFixed(1)} K` : '';
    const tcWithPressure = hasTc
        ? `Tc: ${tcSummary}${pressureStr}`
        : '';

    const records = Array.isArray(paper.records) ? paper.records : [];
    const physicalDataHtml = records.length > 0 ? renderPhysicalDataTable(records) : '';
    const hasRecords = records.length > 0;

    // 文章类型标签 — 从聚合数组生成
    const articleTypeMap = { e: '🔬 实验', t: '⚛️ 理论' };
    const articleTypes = Array.isArray(paper.article_types) ? paper.article_types : [];
    const articleTypeBadges = articleTypes.length > 0
        ? articleTypes.map(t => `<span class="badge ${t === 'e' ? 'bg-success' : 'bg-info'}">${articleTypeMap[t] || t}</span>`).join(' ')
        : '';

    // 超导类型标签 — 从聚合数组生成
    const scTypeMap = {
        'h':  '<span class="badge" style="background-color: rgba(153, 102, 255, 0.8);">💧 高压氢化物</span>',
        'c':  '<span class="badge" style="background-color: rgba(54, 162, 235, 0.8);">🔵 碳基</span>',
        'cb': '<span class="badge" style="background-color: rgba(255, 99, 132, 0.8);">🔴 铜基</span>',
        'ot': '<span class="badge" style="background-color: rgba(204, 70, 70, 0.8);">⚪ 其他超导</span>',
    };
    const scTypes = Array.isArray(paper.superconductor_types) ? paper.superconductor_types : [];
    const scTypeBadges = scTypes.length > 0
        ? scTypes.map(t => scTypeMap[t] || '').filter(Boolean).join(' ')
        : '';

    // 审核状态徽章（从后端数据获取）
    const statusMap = {
        'pending': { text: '未审核', class: 'bg-warning' },
        'approved': { text: '已通过', class: 'bg-success' },
        'reviewed': { text: '已通过', class: 'bg-success' },
        'rejected': { text: '已拒绝', class: 'bg-danger' },
        'needs_revision': { text: '需修改', class: 'bg-info' }
    };
    const statusInfo = statusMap[paper.review_status] || statusMap['pending'];
    let reviewBadge = `<span class="badge ${statusInfo.class}">${statusInfo.text}${paper.reviewer_name && paper.review_status !== 'pending' ? ` (${paper.reviewer_name})` : ''}</span>`;
    
    if (paper.review_comment && paper.review_status !== 'pending') {
        reviewBadge += `<br><small class="text-muted" title="${paper.review_comment}">备注: ${paper.review_comment}</small>`;
    }

    return `
        <div class="card paper-card mb-3">
            <div class="card-body">
                <!-- 简化的一行信息 -->
                <div class="paper-summary" style="cursor: pointer;" onclick="togglePaperDetails(${paper.id})">
                    <div class="d-flex align-items-center justify-content-between">
                        <div class="flex-grow-1">
                            <strong>${paper.year || '未知年份'}</strong> |
                            ${firstAuthor} |
                            通讯: ${correspondingAuthor} |
                            ${paper.title} |
                            ${paper.chemical_formula || '未知体系'}${tcWithPressure ? ` | ${tcWithPressure}` : ''} |
                            ${articleTypeBadges} ${scTypeBadges}
                            ${reviewBadge}
                        </div>
                        <div>
                            <i class="bi bi-chevron-down" id="chevron-${paper.id}">▼</i>
                        </div>
                    </div>
                </div>

                <div id="details-${paper.id}" class="paper-details mt-3" style="display: none;">
                    <div class="row">
                        <!-- 左侧：详细文献信息 -->
                        <div class="col-md-${paper.image_count > 0 ? '8' : '12'}">
                            <h5 class="card-title">
                                <a href="https://doi.org/${paper.doi}" target="_blank">${paper.title}</a>
                            </h5>

                            <p class="text-muted mb-2">
                                <strong>作者:</strong> ${authors.join(', ')}<br>
                                <strong>期刊:</strong> ${paper.journal || '未知'} ${paper.volume ? `Vol. ${paper.volume}` : ''}
                                ${paper.pages ? `p. ${paper.pages}` : ''} (${paper.year || '未知年份'})<br>
                                <strong>DOI:</strong> <code>${paper.doi}</code>
                                <div class="mt-2">
                                    <button class="btn btn-outline-secondary btn-sm" type="button" onclick="downloadPaperRIS(${paper.id})">
                                        RIS导出
                                    </button>
                                </div>
                            </p>

                            <!-- 元数据块 -->
                            <div class="row g-2 mb-3">
                                ${articleTypes.length > 0 ? `
                                <div class="col-auto"><span class="text-muted small">类型:</span> ${articleTypeBadges}</div>
                                ` : ''}
                                ${scTypes.length > 0 ? `
                                <div class="col-auto"><span class="text-muted small">超导:</span> ${scTypeBadges}</div>
                                ` : ''}
                                ${paper.chemical_formula ? `
                                <div class="col-auto"><span class="text-muted small">化学式:</span> <code>${paper.chemical_formula}</code></div>
                                ` : ''}
                                ${hasTc && pressures.length > 0 ? `
                                <div class="col-auto"><span class="text-muted small">压强:</span> ${pressures.join(', ')} GPa</div>
                                ` : ''}
                                ${hasTc && Array.isArray(paper.space_groups) && paper.space_groups.length > 0 ? `
                                <div class="col-auto"><span class="text-muted small">空间群:</span> ${paper.space_groups.join(', ')}</div>
                                ` : ''}
                            </div>

                            ${hasRecords ? `
                            <div class="mb-2">
                                <strong>物理参数:</strong>
                                ${physicalDataHtml}
                            </div>
                            ` : ''}

                            ${paper.abstract ? `
                                <div class="mb-3">
                                    <strong>摘要:</strong>
                                    <p class="mt-2 mb-0">${paper.abstract}</p>
                                </div>
                            ` : ''}

                            <div class="mt-3 text-muted small">
                                贡献者: ${paper.contributor_name} (${paper.contributor_affiliation}) |
                                提交时间: ${new Date(paper.created_at).toLocaleDateString('zh-CN')}
                            </div>
                        </div>

                        <!-- 右侧：第一张大图（点击展开后才加载） -->
                        ${paper.image_count > 0 ? `
                        <div class="col-md-4">
                            <img data-src="/api${getApiBase()}/papers/${paper.id}/images/1"
                                 class="img-fluid paper-main-image lazy-image"
                                 onclick="viewImage('/api${getApiBase()}/papers/${paper.id}/images/1')"
                                 alt="主图"
                                 style="cursor: pointer; border-radius: 8px; max-height: 400px; width: 100%; object-fit: contain; border: 2px solid #dee2e6;">
                        </div>
                        ` : ''}
                    </div>

                    <!-- 其他截图（缩略图） -->
                    ${paper.image_count > 1 ? `
                    <div class="mt-3">
                        <strong>其他截图:</strong>
                        <div class="paper-images">
                            ${renderOtherImages(paper.id, paper.image_count)}
                        </div>
                    </div>
                    ` : ''}
                </div>
            </div>
        </div>
    `;
}

// 切换文献详情显示（点击展开后才加载图片）
function togglePaperDetails(paperId) {
    const details = document.getElementById(`details-${paperId}`);
    const chevron = document.getElementById(`chevron-${paperId}`);

    if (!details || !chevron) {
        return;
    }

    if (details.style.display === 'none') {
        details.style.display = 'block';
        chevron.textContent = '▲';

        // 展开时加载懒加载图片（将 data-src 赋给 src）
        details.querySelectorAll('.lazy-image').forEach(img => {
            if (!img.src && img.dataset.src) {
                img.src = img.dataset.src;
            }
        });
    } else {
        details.style.display = 'none';
        chevron.textContent = '▼';
    }
}

// 渲染其他截图（从第2张开始，点击展开后才加载）
function renderOtherImages(paperId, count) {
    if (count <= 1) return '';

    let html = '';
    for (let i = 2; i <= count; i++) {
        html += `<img data-src="/api${getApiBase()}/papers/${paperId}/images/${i}?thumbnail=true"
                      class="paper-image-thumbnail lazy-image"
                      onclick="viewImage('/api${getApiBase()}/papers/${paperId}/images/${i}')"
                      alt="截图${i}">`;
    }
    return html;
}

// 渲染图片占位符
function renderImagePlaceholders(paperId, count) {
    if (count === 0) return '<span class="text-muted">暂无截图</span>';

    let html = '';
    for (let i = 1; i <= count; i++) {
        // 注意：实际应该从API获取图片ID，这里简化处理
        html += `<img src="/api${getApiBase()}/papers/${paperId}/images/${i}?thumbnail=true"
                      class="paper-image-thumbnail"
                      onclick="viewImage('/api${getApiBase()}/papers/${paperId}/images/${i}')"
                      alt="截图${i}">`;
    }
    return html;
}

// 查看大图
function viewImage(imageUrl) {
    document.getElementById('modal-image').src = imageUrl;
    imageModal.show();
}

function buildRISContent(paper) {
    const lines = ['TY  - JOUR'];
    const authors = Array.isArray(paper.authors) ? paper.authors : (paper.authors ? JSON.parse(paper.authors) : []);
    authors.forEach(author => {
        if (author) {
            lines.push(`AU  - ${author}`);
        }
    });
    if (paper.title) {
        lines.push(`TI  - ${paper.title}`);
    }
    if (paper.journal) {
        lines.push(`JO  - ${paper.journal}`);
    }
    if (paper.year) {
        lines.push(`PY  - ${paper.year}`);
    }
    if (paper.volume) {
        lines.push(`VL  - ${paper.volume}`);
    }
    if (paper.issue) {
        lines.push(`IS  - ${paper.issue}`);
    }
    if (paper.pages) {
        lines.push(`SP  - ${paper.pages}`);
    }
    if (paper.doi) {
        lines.push(`DO  - ${paper.doi}`);
    }
    if (paper.chemical_formula) {
        lines.push(`N1  - 化学式 ${paper.chemical_formula}`);
    }
    lines.push('ER  - ');
    return lines.join('\n');
}

function downloadPaperRIS(paperId) {
    const paper = paperCache.get(paperId);
    if (!paper) {
        alert('未找到对应的文献信息');
        return;
    }

    const risContent = buildRISContent(paper);
    const blob = new Blob([risContent], { type: 'application/x-research-info-systems' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const fileBase = sanitizeFilename(paper.title || paper.doi || `paper-${paperId}`);
    link.href = url;
    link.download = `${fileBase}.ris`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// 搜索文献
function searchPapers() {
    const keyword = document.getElementById('keyword-input').value.trim();
    const yearMin = document.getElementById('year-min-input').value;
    const yearMax = document.getElementById('year-max-input').value;

    const searchParams = {};
    if (keyword) searchParams.keyword = keyword;
    if (yearMin) searchParams.year_min = parseInt(yearMin);
    if (yearMax) searchParams.year_max = parseInt(yearMax);

    resetCurrentPage();
    loadPapers(searchParams);
}

// 重置搜索
function resetSearch() {
    document.getElementById('keyword-input').value = '';
    document.getElementById('year-min-input').value = '';
    document.getElementById('year-max-input').value = '';
    resetCurrentPage();
    loadPapers({});
}

// 处理图片选择
function handleImageSelection(event) {
    const files = Array.from(event.target.files);

    if (files.length > 5) {
        alert('最多只能选择5张图片');
        event.target.value = '';
        return;
    }

    selectedFiles = files;

    // 预览图片
    const container = document.getElementById('image-preview');
    container.innerHTML = '';

    files.forEach((file, index) => {
        const reader = new FileReader();
        reader.onload = function(e) {
            const div = document.createElement('div');
            div.className = 'image-preview';
            div.innerHTML = `
                <img src="${e.target.result}" alt="预览${index + 1}">
                <button type="button" class="remove-image-btn" onclick="removeImage(${index})">×</button>
            `;
            container.appendChild(div);
        };
        reader.readAsDataURL(file);
    });
}

// 移除图片
function removeImage(index) {
    selectedFiles.splice(index, 1);
    const input = document.getElementById('images-input');

    // 重新触发change事件
    const dt = new DataTransfer();
    selectedFiles.forEach(file => dt.items.add(file));
    input.files = dt.files;

    handleImageSelection({ target: input });
}

// 添加物理数据行
function addDataRow() {
    const container = document.getElementById('data-points-container');
    const rowCount = container.querySelectorAll('.data-row').length;
    
    if (rowCount >= 20) {
        alert('最多允许添加20组数据');
        return;
    }

    const newRow = document.createElement('div');
    newRow.className = 'data-row card p-3 mb-2 bg-light';
    newRow.innerHTML = `
        <div class="row g-2">
            <div class="col-md-2">
                <label class="small">${I18N.t('compound.chemical_formula')}</label>
                <input type="text" class="form-control form-control-sm formula-val" required placeholder="e.g. LaH10">
            </div>
            <div class="col-md-2">
                <label class="small">${I18N.t('compound.crystal_structure')}</label>
                <input type="text" class="form-control form-control-sm structure-val" list="structure-datalist" placeholder="e.g. Perovskite" autocomplete="off">
            </div>
            <div class="col-md-1">
                <label class="small">${I18N.t('compound.pressure_gpa')}</label>
                <input type="number" step="any" class="form-control form-control-sm pressure-val" required placeholder="0.0">
            </div>
            <div class="col-md-1">
                <label class="small">${I18N.t('compound.tc_k')}</label>
                <input type="number" step="any" class="form-control form-control-sm tc-val" required placeholder="0.0">
            </div>
            <div class="col-md-1">
                <label class="small">λ</label>
                <input type="number" step="any" class="form-control form-control-sm lambda-val" placeholder="λ">
            </div>
            <div class="col-md-1">
                <label class="small">ω_log</label>
                <input type="number" step="any" class="form-control form-control-sm omega-val" placeholder="ω">
            </div>
            <div class="col-md-1">
                <label class="small">N(Ef)</label>
                <input type="number" step="any" class="form-control form-control-sm nef-val" placeholder="N">
            </div>
            <div class="col-md-3 d-flex align-items-end">
                <button type="button" class="btn btn-outline-danger btn-sm w-100" onclick="removeDataRow(this)">×</button>
            </div>
        </div>
    `;
    container.appendChild(newRow);
}

// 移除物理数据行
function removeDataRow(button) {
    const container = document.getElementById('data-points-container');
    if (container.querySelectorAll('.data-row').length > 1) {
        button.closest('.data-row').remove();
    } else {
        alert('至少需要保留一组数据');
    }
}

// 加载晶体结构类型列表（用于自动补全）
async function loadCrystalStructures() {
    try {
        const response = await fetch(`/api${getApiBase()}/papers/crystal-structures`);
        if (response.ok) {
            const structures = await response.json();
            const datalist = document.getElementById('structure-datalist');
            datalist.innerHTML = '';

            structures.forEach(structure => {
                const option = document.createElement('option');
                option.value = structure;
                datalist.appendChild(option);
            });
        }
    } catch (error) {
        console.error('加载晶体结构类型失败:', error);
    }
}

// 提交文献
async function submitPaper() {
    // 验证表单
    const doi = document.getElementById('doi-input').value.trim();

    if (!doi) {
        alert('请输入DOI');
        return;
    }

    // 验证文章类型
    const articleType = document.querySelector('input[name="article-type"]:checked');
    if (!articleType) {
        alert('请选择文章类型（理论文章或实验文章）');
        return;
    }

    // 验证超导体类型
    const superconductorType = document.getElementById('superconductor-type-input').value;
    if (!superconductorType) {
        alert('请选择超导体类型');
        return;
    }

    // 收集并验证物理数据
    const dataRows = document.querySelectorAll('.data-row');
    const physicalData = [];
    let isValidData = true;

    dataRows.forEach((row, index) => {
        const pressureInput = row.querySelector('.pressure-val');
        const tcInput = row.querySelector('.tc-val');

        const pressure = pressureInput.value;
        const tc = tcInput.value;
        const formula = row.querySelector('.formula-val').value.trim();
        const structure = row.querySelector('.structure-val').value.trim();
        const lambda_val = row.querySelector('.lambda-val').value;
        const omega_log = row.querySelector('.omega-val').value;
        const n_ef = row.querySelector('.nef-val').value;

        if (!formula || !pressure || !tc) {
            isValidData = false;
            return;
        }

        const tcValue = parseFloat(tc);
        const record = {
            chemical_formula: formula,
            crystal_structure: structure || null,
            pressure_gpa: parseFloat(pressure),
            s_factor: calculateSFactor(tc, pressure),
            lambda_value: lambda_val ? parseFloat(lambda_val) : null,
            omega_log: omega_log ? parseFloat(omega_log) : null,
            n_ef_total: n_ef ? parseFloat(n_ef) : null
        };
        if (articleType.value === 'experimental') {
            record.experimental_tc = tcValue;
        } else {
            record.mcmillan_tc = tcValue;
        }
        physicalData.push(record);
    });

    if (!isValidData || physicalData.length === 0) {
        alert('请完整填写所有数据的化学式、压强和Tc');
        return;
    }

    // 构建FormData
    const formData = new FormData();
    formData.append('doi', doi);
    formData.append('element_symbols', JSON.stringify(elementSymbols.split('-')));
    formData.append('article_type', articleType.value);
    formData.append('superconductor_type', superconductorType);
    formData.append('records', JSON.stringify(physicalData));

    const contributorName = document.getElementById('contributor-name-input').value.trim();
    if (contributorName) formData.append('contributor_name', contributorName);

    const contributorAff = document.getElementById('contributor-affiliation-input').value.trim();
    if (contributorAff) formData.append('contributor_affiliation', contributorAff);

    const notes = document.getElementById('notes-input').value.trim();
    if (notes) formData.append('notes', notes);

    // 获取提交按钮
    const submitBtn = document.querySelector('#uploadModal .btn-primary[onclick="submitPaper()"]');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = '提交中...';
    }

    try {
        const auth = getAuthState();
        if (!auth || !auth.token) {
            alert('登录状态已失效，请重新登录');
            window.location.href = '/login';
            return;
        }
        const token = auth.token;
        const response = await fetch('/api/papers/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            alert('文献上传成功！');
            uploadModal.hide();
            // 重置表单
            document.getElementById('uploadForm').reset();
            document.getElementById('image-preview').innerHTML = '';
            // 重置物理数据行
            document.getElementById('data-points-container').innerHTML = `
                <div class="data-row card p-3 mb-2 bg-light">
                    <div class="row g-2">
                        <div class="col-md-2">
                            <label class="small">${I18N.t('compound.chemical_formula')}</label>
                            <input type="text" class="form-control form-control-sm formula-val" placeholder="e.g. YBa₂Cu₃O₇">
                        </div>
                        <div class="col-md-2">
                            <label class="small">${I18N.t('compound.crystal_structure')}</label>
                            <input type="text" class="form-control form-control-sm structure-val" list="structure-datalist" placeholder="e.g. Perovskite" autocomplete="off">
                        </div>
                        <div class="col-md-2">
                            <label class="small">${I18N.t('compound.pressure_gpa')}</label>
                            <input type="number" step="any" class="form-control form-control-sm pressure-val" required placeholder="0.0">
                        </div>
                        <div class="col-md-2">
                            <label class="small">${I18N.t('compound.tc_k')}</label>
                            <input type="number" step="any" class="form-control form-control-sm tc-val" required placeholder="0.0">
                        </div>
                        <div class="col-md-1">
                            <label class="small">λ</label>
                            <input type="number" step="any" class="form-control form-control-sm lambda-val" placeholder="λ">
                        </div>
                        <div class="col-md-1">
                            <label class="small">ω_log</label>
                            <input type="number" step="any" class="form-control form-control-sm omega-val" placeholder="ω">
                        </div>
                        <div class="col-md-1">
                            <label class="small">N(Ef)</label>
                            <input type="number" step="any" class="form-control form-control-sm nef-val" placeholder="N">
                        </div>
                        <div class="col-md-1 d-flex align-items-end">
                            <button type="button" class="btn btn-outline-danger btn-sm w-100" onclick="removeDataRow(this)">×</button>
                        </div>
                    </div>
                </div>
            `;
            selectedFiles = [];
            // 重新加载文献列表
            loadCompoundInfo();
            loadPapers();
        } else {
            alert('上传失败: ' + (data.detail || JSON.stringify(data)));
        }
    } catch (error) {
        console.error('上传失败:', error);
        alert('上传失败，请检查网络连接');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = '提交';
        }
    }
}

/**
 * 批量导出当前显示的文献
 * @param {string} format 'ris' 或 'json'
 */
async function exportAllDisplayedPapers(format) {
    const papers = Array.from(paperCache.values());
    if (papers.length === 0) {
        alert('当前没有可导出的文献');
        return;
    }

    const fileNameBase = `export_${elementSymbols || 'papers'}`;

    if (format === 'ris') {
        // 合并所有文献的 RIS 内容，中间用换行分隔
        const risContent = papers.map(p => buildRISContent(p)).join('\n');
        downloadFile(risContent, `${fileNameBase}.ris`, 'application/x-research-info-systems');
    } else if (format === 'json') {
        const exportData = {
            papers: [],
            paper_data: [],
            paper_images: []
        };

        papers.forEach(p => {
            // 1. 文献基本信息 (克隆并清理)
            const paperCopy = { ...p };
            const physicalParams = paperCopy.data || [];
            delete paperCopy.data; // 移除嵌套数据，符合规范的 papers 列表格式
            exportData.papers.push(paperCopy);

            // 2. 物理数据点
            physicalParams.forEach(d => {
                exportData.paper_data.push({
                    ...d,
                    paper_id: p.id
                });
            });

            // 3. 图片信息 (由于前端限制，导出元数据和访问链接)
            for (let i = 1; i <= p.image_count; i++) {
                exportData.paper_images.push({
                    paper_id: p.id,
                    image_order: i,
                    url: `${window.location.origin}/api${getApiBase()}/papers/${p.id}/images/${i}`
                });
            }
        });

        const jsonContent = JSON.stringify(exportData, null, 2);
        downloadFile(jsonContent, `${fileNameBase}.json`, 'application/json');
    }
}

/**
 * 通用文件下载函数
 */
function downloadFile(content, fileName, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// 语言切换时重新加载数据以更新动态文本
document.addEventListener('langChange', () => {
    loadCompoundInfo();
    loadPapers();
    const descEl = document.getElementById('db-desc');
    if (descEl) descEl.textContent = I18N.t(`compound.${currentDatabase}_db_desc`);
});
async function loadAlexandriaMaterials(container) {
    const elements = getSelectedElementsFromPath();
    const pagination = getActivePaginationState();

    try {
        const body = {
            elements,
            mode: _alexMode(viewMode),
            min_tc: (parseFloat(document.getElementById('min-tc-input')?.value) || null),
            stable_only: (document.getElementById('stable-only-input')?.checked || false),
            limit: pagination.pageSize,
            offset: (pagination.page - 1) * pagination.pageSize,
        };

        const response = await fetch('/api/alexandria/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            throw new Error((await response.json()).detail || '查询失败');
        }

        const data = await response.json();
        const items = data.items || [];

        // 更新分页状态
        pagination.total = data.total || 0;
        pagination.totalPages = Math.ceil(pagination.total / pagination.pageSize) || 1;

        if (items.length === 0) {
            container.innerHTML = `<div class="alert alert-warning text-center"><p class="mb-0">Alexandria 数据库中未找到匹配的电声耦合材料数据</p></div>`;
            clearPaginationUi();
            return;
        }

        // 渲染材料卡片
        container.innerHTML = items.map(item => renderAlexandriaCard(item)).join('');
        window._alexandriaItems = items;

        // 更新标题显示数据库名和数量
        const subtitleEl = document.getElementById('compound-subtitle');
        if (subtitleEl) {
            subtitleEl.innerHTML = `${I18N.t('compound.alexandria_title')} · ${I18N.t(viewMode === 'only' ? 'index.mode_only' : viewMode === 'contains' ? 'index.mode_contains' : 'index.mode_combination')} · ${data.total} ${I18N.t('compound.material_count')}`;
        }

        // 渲染分页
        renderAlexandriaPagination(data);
    } catch (error) {
        console.error('Alexandria 查询失败:', error);
        container.innerHTML = `<div class="alert alert-danger">Alexandria 查询失败：${error.message}</div>`;
        clearPaginationUi();
    }
}

function renderAlexandriaCard(item) {
    const safeId = (item.mat_id || '').replace(/[^a-zA-Z0-9-]/g, '_');
    const tcVal = item.tc_allen_dynes != null ? item.tc_allen_dynes.toFixed(2) + ' K' : (item.tc_max != null ? item.tc_max.toFixed(2) + ' K' : '—');
    const tcColor = (item.tc_allen_dynes || item.tc_max || 0) > 77 ? 'text-danger fw-bold' : '';
    const lambdaStr = item.lambda_val != null ? item.lambda_val.toFixed(4) : '—';
    const isExpanded = alexExpandCache[item.mat_id] || false;

    return `
        <div class="card paper-card mb-3">
            <div class="card-body">
                <!-- 折叠栏（点击展开） -->
                <div class="paper-summary" style="cursor: pointer;" onclick="toggleAlexandriaCard('${item.mat_id}')">
                    <div class="d-flex align-items-center justify-content-between">
                        <div class="flex-grow-1">
                            <strong class="${tcColor}">${item.formula || I18N.t('compound.unknown_formula')}</strong> |
                            Tc: ${tcVal} |
                            λ: ${lambdaStr} |
                            <span class="badge bg-info">Alexandria</span>
                        </div>
                        <div>
                            <i class="bi bi-chevron-down" id="alex-chevron-${safeId}">${isExpanded ? '▲' : '▼'}</i>
                        </div>
                    </div>
                </div>

                <!-- 展开区域（结构图 + 详情） -->
                <div id="alex-details-${safeId}" class="paper-details mt-3" style="display: ${isExpanded ? 'block' : 'none'};">
                    <div class="row">
                        <div class="col-md-7">
                            <div id="struct-viewer-alex-${safeId}"
                                 style="position:relative;width:100%;height:400px;border:1px solid #dee2e6;border-radius:4px;background:#f8f9fa;">
                                <div class="text-center text-muted py-5">
                                    <div class="spinner-border spinner-border-sm" role="status"></div>
                                    <br><small>加载结构图中...</small>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-5">
                            <h5 class="card-title mb-1 ${tcColor}">${item.formula || I18N.t('compound.unknown_formula')}</h5>
                            <p class="text-muted small mb-1">
                                ${(item.elements || []).join(' · ')} ·
                                ${item.imag
                                    ? '<span class="badge bg-warning">' + I18N.t('compound.unstable') + '</span>'
                                    : '<span class="badge bg-success">' + I18N.t('compound.stable') + '</span>'}
                                · mat_id: ${item.mat_id}
                            </p>

                            <div class="mb-2">
                                <strong>物理参数:</strong>
                                <div class="row text-center small g-1 mt-1">
                                    ${[
                                        ['压力', item.pressure != null ? item.pressure.toFixed(1) + ' GPa' : '—'],
                                        ['Tc<sub>McM</sub>', item.tc_mcmillan != null ? item.tc_mcmillan.toFixed(2) + ' K' : '—'],
                                        ['Tc<sub>AD</sub>', item.tc_allen_dynes != null ? item.tc_allen_dynes.toFixed(2) + ' K' : '—'],
                                        ['Tc<sub>El</sub>', item.tc_eliashberg != null ? item.tc_eliashberg.toFixed(2) + ' K' : '—'],
                                        ['λ', lambdaStr],
                                        ['ω<sub>log</sub>', item.wlog != null ? item.wlog.toFixed(2) + ' K' : '—'],
                                        ['费米能级', item.dos_ef != null ? item.dos_ef.toFixed(3) + ' eV' : '—'],
                                    ].map(([label, val]) =>
                                        `<div class="col-4 p-1"><div class="bg-light rounded p-1"><div class="text-muted" style="font-size:0.65rem;">${label}</div><strong style="font-size:0.8rem;">${val}</strong></div></div>`
                                    ).join('')}
                                </div>
                            </div>

                            <div class="mt-2 d-flex gap-2">
                                <a class="btn btn-outline-secondary btn-sm"
                                   href="/api/alexandria/material/${item.mat_id}/download" download>
                                    📥 ${I18N.t('compound.download_data')}
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

async function loadTestDatabase(container) {
    const elements = getSelectedElementsFromPath();
    const elementsText = elements.join(' · ');
    container.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div><p class="mt-3">加载中...</p></div>';

    const [aiPapers, alexMaterials] = await Promise.all([
        Promise.resolve([]),
        fetchTestAlexandriaMaterials(elements),
    ]);

    const savedDb = currentDatabase;

    // 1. AI 论文分组（按组合）
    const sections = groupPapersByCompound(aiPapers || []);
    const sectionMap = new Map();
    sections.forEach(s => sectionMap.set(s.combo.element_symbols, s));

    // 2. Alexandria 材料归入已有组合或新建组合
    (alexMaterials || []).forEach(m => {
        const key = [...(m.elements || [])].sort().join('-');
        if (sectionMap.has(key)) {
            sectionMap.get(key).papers.push({ _isAlexandria: true, _data: m });
        } else {
            const ns = {
                combo: { element_symbols: key, element_list: [...(m.elements || [])].sort() },
                papers: [{ _isAlexandria: true, _data: m }],
            };
            sections.push(ns);
            sectionMap.set(key, ns);
        }
    });

    currentDatabase = savedDb;
    if (alexMaterials && alexMaterials.length > 0) window._alexandriaItems = alexMaterials;

    // 3. 渲染：每组中先 AI 后 Alexandria，各自按 Tc 排序
    let html = `<p class="text-muted mb-3"><strong>元素：</strong>${elementsText}</p>`;
    let totalCount = 0;

    sections.forEach(sec => {
        const papers = sec.papers || [];
        if (papers.length === 0) return;

        // 分组内排序：按 Tc 降序
        papers.sort((a, b) => {
            let tcA = 0, tcB = 0;
            if (a._isAlexandria && a._data) tcA = a._data.tc_allen_dynes || a._data.tc_max || 0;
            else if (a.data && a.data[0]) tcA = parseFloat(a.data[0].tc) || 0;
            if (b._isAlexandria && b._data) tcB = b._data.tc_allen_dynes || b._data.tc_max || 0;
            else if (b.data && b.data[0]) tcB = parseFloat(b.data[0].tc) || 0;
            return tcB - tcA;
        });

        totalCount += papers.length;
        const content = papers.map(p => {
            if (p._isAlexandria) {
                try { return renderAlexandriaCard(p._data); } catch(e) { return ''; }
            }
            currentDatabase = 'ai';
            const html = renderPaperCard(p);
            currentDatabase = savedDb;
            return html;
        }).join('');

        html += `
            <section class="mb-5">
                <div class="d-flex justify-content-between align-items-center mb-2 flex-wrap gap-2">
                    <div>
                        <h4 class="mb-0">${sec.combo.element_symbols}<span class="badge bg-secondary ms-2">${papers.length} ${I18N.t('index.chart_papers')}</span></h4>
                        <small class="text-muted">元素：${(sec.combo.element_list || []).join(' · ')}</small>
                    </div>
                </div>
                ${content}
            </section>
        `;
    });

    if (totalCount === 0) {
        html += '<div class="alert alert-warning text-center"><p class="mb-0">未找到匹配数据</p></div>';
    }
    container.innerHTML = html;

    const sub = document.getElementById('compound-subtitle');
    if (sub) {
        const modeLabel = viewMode === 'only' ? I18N.t('index.mode_only')
            : viewMode === 'contains' ? I18N.t('index.mode_contains')
            : I18N.t('index.mode_combination');
        sub.innerHTML = `${I18N.t('compound.test_db')} · ${modeLabel} · ${elements.join('-')} · ${totalCount} 条结果`;
    }
}

async function fetchTestAlexandriaMaterials(elements) {
    try {
        const body = {
            elements, mode: _alexMode(viewMode),
            min_tc: (parseFloat(document.getElementById('min-tc-input')?.value) || null),
            stable_only: (document.getElementById('stable-only-input')?.checked || false),
            limit: 50, offset: 0,
        };
        const resp = await fetch('/api/alexandria/search', {
            method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body),
        });
        const data = await resp.json();
        return data.items || [];
    } catch (e) {
        console.error('Alexandria 材料加载失败:', e);
        return [];
    }
}

function toggleAlexandriaCard(matId) {
    const safeId = (matId || '').replace(/[^a-zA-Z0-9-]/g, '_');
    const detailEl = document.getElementById(`alex-details-${safeId}`);
    const chevron = document.getElementById(`alex-chevron-${safeId}`);
    if (!detailEl) return;

    const isNowVisible = detailEl.style.display !== 'none' && detailEl.style.display !== '';
    if (isNowVisible) {
        detailEl.style.display = 'none';
        if (chevron) chevron.textContent = '▼';
        alexExpandCache[matId] = false;
        return;
    }

    detailEl.style.display = 'block';
    if (chevron) chevron.textContent = '▲';
    alexExpandCache[matId] = true;

    // 首次展开才加载数据
    if (alexDetailCache[matId]) return;
    alexDetailCache[matId] = true;

    const item = window._alexandriaItems ? window._alexandriaItems.find(i => i.mat_id === matId) : null;

    // 加载 CIF 结构图
    const vEl = document.getElementById(`struct-viewer-alex-${safeId}`);
    if (vEl) {
        fetch(`/api/alexandria/material/${matId}/cif`)
            .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.text(); })
            .then(cif => {
                if (!cif || cif.length < 10) throw new Error('空数据');
                vEl.innerHTML = '';
                if (typeof $3Dmol !== 'undefined') {
                    const viewer = $3Dmol.createViewer(vEl, {defaultcolors: $3Dmol.elementColors.Jmol});
                    viewer.addModel(cif, 'cif');
                    viewer.setStyle({}, {
                        stick: {radius: 0.12, colorscheme: 'Jmol'},
                        sphere: {scale: 0.3, colorscheme: 'Jmol'},
                    });
                    viewer.addUnitCell({line: {color: '#888', width: 2}});
                    viewer.zoomTo();
                    viewer.render();
                    if (item && item.elements) _addLegend(vEl, [...new Set(item.elements)]);
                } else {
                    vEl.innerHTML = '<div class="text-center text-muted py-5"><small>$3Dmol 未加载</small></div>';
                }
            })
            .catch(() => {
                vEl.innerHTML = '<div class="text-center text-muted py-5"><small>无结构数据</small></div>';
            });
    }

}

function renderAlexandriaPagination(data) {
    const summaryEl = document.getElementById('papers-summary');
    const paginationEl = document.getElementById('papers-pagination');
    if (!summaryEl || !paginationEl) return;

    const pagination = getActivePaginationState();
    const total = data.total || 0;
    const pageSize = pagination.pageSize;
    const totalPages = Math.ceil(total / pageSize) || 1;
    const page = pagination.page;

    if (total === 0) {
        clearPaginationUi();
        return;
    }

    const start = (page - 1) * pageSize + 1;
    const end = Math.min(start + (data.items ? data.items.length : 0) - 1, total);
    summaryEl.style.display = 'block';
    summaryEl.textContent = I18N.t('compound.page_material_info', { start, end, total });

    if (totalPages <= 1) {
        paginationEl.innerHTML = '';
        paginationEl.style.display = 'none';
        return;
    }

    paginationEl.style.display = 'block';
    paginationEl.innerHTML = `
        <nav aria-label="分页导航">
            <ul class="pagination justify-content-center flex-wrap mb-0">
                <li class="page-item ${data.has_prev ? '' : 'disabled'}">
                    <button class="page-link" type="button" onclick="changeAlexandriaPage(${page - 1})" ${data.has_prev ? '' : 'disabled'}>${I18N.t('compound.prev_page')}</button>
                </li>
                ${renderAlexandriaPageNumbers(page, totalPages)}
                <li class="page-item ${data.has_next ? '' : 'disabled'}">
                    <button class="page-link" type="button" onclick="changeAlexandriaPage(${page + 1})" ${data.has_next ? '' : 'disabled'}>${I18N.t('compound.next_page')}</button>
                </li>
            </ul>
        </nav>
    `;
}

function renderAlexandriaPageNumbers(current, total) {
    const maxVisible = 5;
    const half = Math.floor(maxVisible / 2);
    let start = Math.max(1, current - half);
    let end = Math.min(total, start + maxVisible - 1);
    start = Math.max(1, end - maxVisible + 1);
    let html = '';
    for (let p = start; p <= end; p++) {
        html += `<li class="page-item ${p === current ? 'active' : ''}">
            <button class="page-link" type="button" onclick="changeAlexandriaPage(${p})">${p}</button>
        </li>`;
    }
    return html;
}

function changeAlexandriaPage(page) {
    const pagination = getActivePaginationState();
    if (page < 1 || page === pagination.page) return;
    pagination.page = page;
    loadPapers(currentSearchParams);
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// HTSC-2025 搜索和渲染
async function loadHTSC2025Materials(container) {
    const elements = getSelectedElementsFromPath();
    const pagination = getActivePaginationState();

    try {
        const body = {
            elements,
            mode: _alexMode(viewMode),
            min_tc: (parseFloat(document.getElementById('min-tc-input')?.value) || null),
            limit: pagination.pageSize,
            offset: (pagination.page - 1) * pagination.pageSize,
        };

        const response = await fetch('/api/htsc2025/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            throw new Error((await response.json()).detail || '查询失败');
        }

        const data = await response.json();
        const items = data.items || [];

        pagination.total = data.total || 0;
        pagination.totalPages = Math.ceil(pagination.total / pagination.pageSize) || 1;

        if (items.length === 0) {
            container.innerHTML = `<div class="alert alert-warning text-center"><p class="mb-0">HTSC-2025 数据集中未找到匹配的材料</p></div>`;
            clearPaginationUi();
            return;
        }

        container.innerHTML = items.map(item => renderHTSC2025Card(item)).join('');

        const subtitleEl = document.getElementById('compound-subtitle');
        if (subtitleEl) {
            subtitleEl.innerHTML = `${I18N.t('compound.htsc2025_title')} · ${I18N.t(viewMode === 'only' ? 'index.mode_only' : viewMode === 'contains' ? 'index.mode_contains' : 'index.mode_combination')} · ${data.total} ${I18N.t('compound.material_count')}`;
        }

        renderHTSC2025Pagination(data);
    } catch (error) {
        console.error('HTSC-2025 查询失败:', error);
        container.innerHTML = `<div class="alert alert-danger">HTSC-2025 查询失败：${error.message}</div>`;
        clearPaginationUi();
    }
}

function renderHTSC2025Card(item) {
    const safeId = (item.name || '').replace(/[^a-zA-Z0-9-]/g, '_');
    const tcVal = item.tc != null ? item.tc.toFixed(1) + ' K' : '—';
    const tcColor = item.tc > 77 ? 'text-danger fw-bold' : '';
    const cc = item.composition || {};
    const compEntries = Object.entries(cc).map(([el, n]) => `${el}${n > 1 ? '<sub>' + n.toFixed(1).replace(/\.0$/, '') + '</sub>' : ''}`).join('');
    const isExpanded = alexExpandCache[item.name] || false;

    return `
        <div class="card paper-card mb-3">
            <div class="card-body">
                <div class="paper-summary" style="cursor: pointer;" onclick="toggleAlexandriaCard('${item.name}')">
                    <div class="d-flex align-items-center justify-content-between">
                        <div class="flex-grow-1">
                            <strong class="${tcColor}">${item.formula || item.name}</strong> |
                            Tc: ${tcVal} |
                            ${item.class ? item.class + ' |' : ''}
                            <span class="badge bg-info">HTSC-2025</span>
                        </div>
                        <div>
                            <i class="bi bi-chevron-down" id="alex-chevron-${safeId}">${isExpanded ? '▲' : '▼'}</i>
                        </div>
                    </div>
                </div>

                <div id="alex-details-${safeId}" class="paper-details mt-3" style="display: ${isExpanded ? 'block' : 'none'};">
                    <div class="row">
                        <div class="col-md-7">
                            <div id="struct-viewer-htsc-${safeId}"
                                 style="position:relative;width:100%;height:380px;border:1px solid #dee2e6;border-radius:4px;background:#f8f9fa;">
                                <div class="text-center text-muted py-5">
                                    <small>点击「查看 CIF」加载结构图</small>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-5">
                            <h5 class="card-title mb-1 ${tcColor}">${item.formula || item.name}</h5>
                            <p class="text-muted small mb-1">
                                ${(item.elements || []).join(' · ')} ·
                                <span class="badge bg-secondary">${item.class || '未知类别'}</span>
                            </p>
                            ${compEntries ? `<p class="text-muted small mb-1">组成: ${compEntries}</p>` : ''}
                            <div class="mb-2">
                                <strong>物理参数:</strong>
                                <div class="row text-center small g-1 mt-1">
                                    ${[
                                        ['Tc', tcVal],
                                        ['类别', item.class || '—'],
                                    ].map(([label, val]) =>
                                        `<div class="col-4 p-1"><div class="bg-light rounded p-1"><div class="text-muted" style="font-size:0.65rem;">${label}</div><strong style="font-size:0.8rem;">${val}</strong></div></div>`
                                    ).join('')}
                                </div>
                            </div>
                            <div class="mt-2">
                                <button class="btn btn-outline-primary btn-sm" onclick="toggleCIFDetail('${item.name}')">
                                    📐 ${I18N.t('compound.view_cif')}
                                </button>
                            </div>
                        </div>
                    </div>
                    <div id="cif-detail-${safeId}" class="mt-2" style="display: none;" data-elements="${(item.elements||[]).join(',')}">
                        <pre class="bg-light p-2 rounded small mb-0" style="max-height: 380px; overflow-y: auto; font-size: 0.7rem;"></pre>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function renderHTSC2025Pagination(data) {
    const summaryEl = document.getElementById('papers-summary');
    const paginationEl = document.getElementById('papers-pagination');
    if (!summaryEl || !paginationEl) return;

    const pagination = getActivePaginationState();
    const total = data.total || 0;
    const pageSize = pagination.pageSize;
    const totalPages = Math.ceil(total / pageSize) || 1;
    const page = pagination.page;

    if (total === 0) { clearPaginationUi(); return; }

    const start = (page - 1) * pageSize + 1;
    const end = Math.min(start + (data.items ? data.items.length : 0) - 1, total);
    summaryEl.style.display = 'block';
    summaryEl.textContent = I18N.t('compound.page_material_info', { start, end, total });

    if (totalPages <= 1) { paginationEl.innerHTML = ''; paginationEl.style.display = 'none'; return; }

    paginationEl.style.display = 'block';
    paginationEl.innerHTML = `
        <nav aria-label="分页导航">
            <ul class="pagination justify-content-center flex-wrap mb-0">
                <li class="page-item ${data.has_prev ? '' : 'disabled'}">
                    <button class="page-link" type="button" onclick="changePage('htsc2025', ${page - 1})" ${data.has_prev ? '' : 'disabled'}>${I18N.t('compound.prev_page')}</button>
                </li>
                <li class="page-item ${data.has_next ? '' : 'disabled'}">
                    <button class="page-link" type="button" onclick="changePage('htsc2025', ${page + 1})" ${data.has_next ? '' : 'disabled'}>${I18N.t('compound.next_page')}</button>
                </li>
            </ul>
        </nav>
    `;
}

function toggleCIFDetail(name) {
    const safeId = name.replace(/[^a-zA-Z0-9-]/g, '_');
    const detailEl = document.getElementById(`cif-detail-${safeId}`);
    if (!detailEl) return;

    if (detailEl.style.display === 'none') {
        detailEl.style.display = 'block';
        if (cifDetailCache[name]) return;
        fetch(`/api/htsc2025/detail/${encodeURIComponent(name)}`)
            .then(r => r.json())
            .then(data => {
                const cif = data.cif || '';
                const pre = detailEl.querySelector('pre');
                if (pre) pre.textContent = cif || '(无 CIF 数据)';
                const uniqEls = (detailEl.dataset.elements || '').split(',').filter(Boolean);
                if (cif && typeof $3Dmol !== 'undefined') {
                    setTimeout(() => {
                        const vEl = document.getElementById(`struct-viewer-htsc-${safeId}`);
                        if (!vEl) return;
                        const viewer = $3Dmol.createViewer(vEl, {defaultcolors: $3Dmol.elementColors.Jmol});
                        viewer.addModel(cif, 'cif');
                        viewer.setStyle({}, {
                            stick: {radius: 0.12, colorscheme: 'Jmol'},
                            sphere: {scale: 0.3, colorscheme: 'Jmol'},
                        });
                        viewer.addUnitCell({line: {color: '#888', width: 2}});
                        viewer.zoomTo();
                        viewer.render();
                        _addLegend(vEl, uniqEls);
                    }, 100);
                }
                cifDetailCache[name] = true;
            })
            .catch(err => {
                infoEl.innerHTML = `<div class="text-danger small">加载失败: ${err.message}</div>`;
            });
    } else {
        detailEl.style.display = 'none';
    }
}
