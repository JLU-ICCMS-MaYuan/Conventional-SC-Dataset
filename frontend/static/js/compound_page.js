// 全局变量
let elementSymbols = '';
let uploadModal, imageModal;
let selectedFiles = [];
let currentReviewStatus = 'all'; // 当前选择的审核状态筛选
let currentDatabase = 'local'; // 'local' 或 'alexandria'
const paperCache = new Map();
const alexDetailCache = {};
const urlParams = new URLSearchParams(window.location.search);
const PAPERS_PER_PAGE = 30;
let currentPage = 1;
let currentSearchParams = {};
let viewMode = urlParams.get('mode') || 'only';
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
if (!['only', 'combination', 'contains'].includes(viewMode)) {
    viewMode = 'only';
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
        only: I18N.t('compound.mode_desc_only'),
        combination: I18N.t('compound.mode_desc_combination'),
        contains: I18N.t('compound.mode_desc_contains')
    };
    return map[mode] || map.only;
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
    const completeRows = (dataRows || []).filter(d => Array.isArray(d.tc) && d.tc.length > 0 && Array.isArray(d.tc_press) && d.tc_press.length > 0);
    if (completeRows.length === 0) {
        return `<span class="text-muted">${I18N.t('compound.no_physical_data')}</span>`;
    }

    const synthesizedText = (d) => {
        if (d.article_type === 'experimental' || d.article_type === 'e') return I18N.t('common.yes');
        if (d.article_type === 'theoretical' || d.article_type === 't') return I18N.t('common.no');
        return 'null';
    };

    const rows = completeRows.map(d => `
        <tr>
            <td>${d.chemical_formula || 'null'}</td>
            <td>${d.crystal_structure || 'null'}</td>
            <td>${synthesizedText(d)}</td>
            <td>${formatRangeCell(d.tc, 'K')}</td>
            <td>${formatRangeCell(d.tc_press, 'GPa')}</td>
            <td>${formatDataCell(d.lambda_val)}</td>
            <td>${formatDataCell(d.omega_log)}</td>
            <td>${formatDataCell(d.n_ef)}</td>
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
                <tbody>${rows}</tbody>
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

    // 初始化数据库描述
    const descEl = document.getElementById('db-desc');
    if (descEl) descEl.textContent = I18N.t('compound.local_db_desc');

    // 设置图片上传预览
    document.getElementById('images-input').addEventListener('change', handleImageSelection);

    const uploadBtn = document.getElementById('open-upload-btn');
    const state = getAuthState();

    if (state && state.user && state.user.is_admin) {
        const adminOnlyLabel = document.getElementById('label-status-admin-only');
        if (adminOnlyLabel) adminOnlyLabel.style.display = 'inline-block';
    }

    if (uploadBtn) {
        uploadBtn.addEventListener('click', function() {
            const auth = getAuthState();
            const token = auth && auth.token;
            if (!token) {
                if (confirm('只有注册用户可以上传文献。是否立即前往登录/注册？')) {
                    window.location.href = '/login';
                }
            } else {
                uploadModal.show();
            }
        });
    }
});

// 加载元素组合信息
async function loadCompoundInfo() {
    try {
        const response = await fetch(`/api${getApiBase()}/compounds/${elementSymbols}`);
        if (response.ok) {
            const data = await response.json();
            document.getElementById('compound-title').textContent = `${data.element_symbols} ${I18N.t('compound.system_sc')}`;
            if (viewMode === 'only') {
                updateModeSubtitle(`当前组合共收录 ${data.paper_count} 篇文献`);
            } else {
                updateModeSubtitle('正在汇总相关组合文献…');
            }
        } else {
            document.getElementById('compound-title').textContent = I18N.t('compound.combination_not_found');
        }
    } catch (error) {
        console.error('加载元素组合信息失败:', error);
    }
}

// 加载文献列表
async function loadPapers(searchParams = null) {
    const container = document.getElementById('papers-container');
    const paginationContainer = document.getElementById('pagination-container');
    container.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div><p class="mt-3">加载中...</p></div>';
    if (searchParams !== null) {
        Object.keys(currentSearchParams).forEach(key => delete currentSearchParams[key]);
        Object.assign(currentSearchParams, searchParams);
    }

    if (currentDatabase === 'alexandria') {
        await loadAlexandriaMaterials(container);
        return;
    }

    if (currentDatabase === 'htsc2025') {
        await loadHTSC2025Materials(container);
        return;
    }

    try {
        const queryString = buildQueryString(currentSearchParams);
        if (viewMode === 'only') {
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

// 数据库切换
function onDatabaseChange() {
    currentDatabase = document.getElementById('db-select').value;
    const isLocalOrAi = currentDatabase === 'local' || currentDatabase === 'ai';
    const showReviewFilter = currentDatabase === 'local';

    // 显示/隐藏 Alexandria/HTSC 专属筛选控件
    document.querySelectorAll('.alexandria-filter').forEach(el => el.style.display = isLocalOrAi ? 'none' : '');
    // 批量导出：本地和AI数据库可用
    document.getElementById('export-dropdown').style.display = isLocalOrAi ? '' : 'none';

    // 审核状态筛选只对本地数据库有效
    const reviewGroup = document.querySelector('.btn-group[role="group"]');
    if (reviewGroup) {
        reviewGroup.closest('.col-auto').style.display = showReviewFilter ? '' : 'none';
    }

    // 更新数据库描述
    const descEl = document.getElementById('db-desc');
    if (descEl) {
        const descKey = `compound.${currentDatabase}_db_desc`;
        descEl.textContent = I18N.t(descKey);
    }

    resetCurrentPage();
    loadPapers(currentSearchParams);
}

// 审核状态筛选
function filterByReviewStatus(status) {
    currentReviewStatus = status;
    resetCurrentPage();
    loadPapers(currentSearchParams);
}

function getActivePaginationState() {
    return viewMode === 'only' ? onlyModePagination : multiModePagination;
}

function getApiBase() {
    return currentDatabase === 'ai' ? '/ai' : '';
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

// Alexandria 搜索和渲染
async function loadAlexandriaMaterials(container) {
    const elements = getSelectedElementsFromPath();
    const pagination = getActivePaginationState();

    try {
        const body = {
            elements,
            mode: viewMode,
            min_tc: parseFloat(document.getElementById('min-tc-input').value) || null,
            stable_only: document.getElementById('stable-only-input').checked,
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
    const elements = item.elements || [];
    const elementsText = elements.join(' · ');
    const tcStr = item.tc_max != null ? `${item.tc_max} K` : '—';
    const lambdaStr = item.lambda_val != null ? item.lambda_val.toFixed(4) : '—';
    const spgStr = item.spg != null ? item.spg : '—';
    const nsitesStr = item.nsites != null ? item.nsites : '—';
    const bgStr = item.band_gap != null ? `${item.band_gap.toFixed(3)} eV` : '—';
    const dosStr = item.dos_ef != null ? item.dos_ef.toFixed(3) : '—';
    const stabilityBadge = item.imag
        ? `<span class="badge bg-warning">${I18N.t('compound.unstable')}</span>`
        : `<span class="badge bg-success">${I18N.t('compound.stable')}</span>`;

    return `
        <div class="card mb-3">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h5 class="card-title mb-1">${item.formula || '未知'}</h5>
                        <p class="text-muted small mb-1">${elementsText} · mat_id: ${item.mat_id} · ${stabilityBadge}</p>
                    </div>
                    <div class="text-end">
                        <span class="fs-4 fw-bold text-primary">${tcStr}</span>
                        <br><small class="text-muted">Tc 最大</small>
                    </div>
                </div>
                <hr class="my-2">
                <div class="row text-center small">
                    <div class="col"><strong>λ</strong><br>${lambdaStr}</div>
                    <div class="col"><strong>空间群</strong><br>${spgStr}</div>
                    <div class="col"><strong>原子数</strong><br>${nsitesStr}</div>
                    <div class="col"><strong>带隙</strong><br>${bgStr}</div>
                    <div class="col"><strong>N(Ef)</strong><br>${dosStr}</div>
                </div>
                <div class="mt-2">
                    <button class="btn btn-outline-primary btn-sm" onclick="toggleAlexandriaDetail('${item.mat_id}')">
                        查看原始数据
                    </button>
                    <a class="btn btn-outline-secondary btn-sm ms-1" href="/api/alexandria/material/${item.mat_id}/download" download>
                        下载完整数据
                    </a>
                    <div id="alex-detail-${item.mat_id}" class="mt-2" style="display: none;">
                        <div class="text-center text-muted small py-2">
                            <div class="spinner-border spinner-border-sm"></div> 加载中...
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
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

function toggleAlexandriaDetail(matId) {
    const detailEl = document.getElementById(`alex-detail-${matId}`);
    if (!detailEl) return;

    if (detailEl.style.display === 'none') {
        detailEl.style.display = 'block';
        if (alexDetailCache[matId]) {
            return;
        }
        fetch(`/api/alexandria/material/${matId}`)
            .then(r => r.json())
            .then(data => {
                const tc = data.tc || {};
                const html = `
                    <div class="bg-light p-3 rounded small">
                        <div class="row">
                            <div class="col-md-6">
                                <strong>λ:</strong> ${(tc.lambda || '—').toFixed ? tc.lambda.toFixed(4) : (tc.lambda || '—')}<br>
                                <strong>ω_log:</strong> ${tc.wlog != null ? tc.wlog.toFixed(2) + ' K' : '—'}<br>
                                <strong>μ*:</strong> ${tc.mustr ? '[' + tc.mustr.join(', ') + ']' : '—'}<br>
                            </div>
                            <div class="col-md-6">
                                <strong>Tc McMillan:</strong> ${tc.TcMcMillan ? '[' + tc.TcMcMillan.join(', ') + ']' : '—'}<br>
                                <strong>Tc Allen-Dynes:</strong> ${tc.TcAllenDynes ? '[' + tc.TcAllenDynes.join(', ') + ']' : '—'}<br>
                                <strong>能量:</strong> ${data.energy_total != null ? data.energy_total.toFixed(4) + ' eV' : '—'}<br>
                            </div>
                        </div>
                    </div>
                `;
                detailEl.innerHTML = html;
                alexDetailCache[matId] = true;
            })
            .catch(err => {
                detailEl.innerHTML = `<div class="text-danger small">加载失败: ${err.message}</div>`;
            });
    } else {
        detailEl.style.display = 'none';
    }
}

// HTSC-2025 搜索和渲染
async function loadHTSC2025Materials(container) {
    const elements = getSelectedElementsFromPath();
    const pagination = getActivePaginationState();

    try {
        const body = {
            elements,
            mode: viewMode,
            min_tc: parseFloat(document.getElementById('min-tc-input').value) || null,
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
    const cc = item.composition || {};
    const compStr = Object.entries(cc).map(([el, n]) => `${el}${n > 1 ? '<sub>' + n.toFixed(1).replace(/\.0$/, '') + '</sub>' : ''}`).join('');
    const tcColor = item.tc > 77 ? 'text-danger fw-bold' : item.tc > 30 ? 'text-warning' : 'text-info';

    return `
        <div class="card mb-3">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h5 class="card-title mb-1">${item.formula || item.name}</h5>
                        <p class="text-muted small mb-1">${compStr} · ${item.class || '未知类别'} · ${item.elements.join(' · ')}</p>
                    </div>
                    <div class="text-end">
                        <span class="fs-4 fw-bold ${tcColor}">${item.tc} K</span>
                        <br><small class="text-muted">Tc</small>
                    </div>
                </div>
                <div class="mt-2">
                    <button class="btn btn-outline-primary btn-sm" onclick="toggleCIFDetail('${item.name}')">
                        ${I18N.t('compound.view_cif')}
                    </button>
                    <div id="cif-detail-${item.name.replace(/[^a-zA-Z0-9-]/g, '_')}" class="mt-2" style="display: none;">
                        <pre class="bg-light p-3 rounded small" style="max-height: 400px; overflow-y: auto;"></pre>
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
        fetch(`/api/htsc2025/detail/${encodeURIComponent(name)}`)
            .then(r => r.json())
            .then(data => {
                const pre = detailEl.querySelector('pre');
                if (pre) pre.textContent = data.cif || '(无 CIF 数据)';
            })
            .catch(err => {
                detailEl.innerHTML = `<div class="text-danger small">加载失败: ${err.message}</div>`;
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
        'unreviewed': I18N.t('compound.review_status_unreviewed'),
        'rejected': I18N.t('compound.review_status_rejected')
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
    const authors = paper.authors ? JSON.parse(paper.authors) : [];
    const firstAuthor = authors.length > 0 ? authors[0] : '未知作者';
    const correspondingAuthor = authors.length > 0 ? authors[authors.length - 1] : '未知作者';

    // 物理数据处理
    const mainData = paper.data && paper.data.length > 0 ? paper.data[0] : null;
    const tcSummary = mainData ? `${mainData.tc} K` : '未知';

    const physicalDataHtml = renderPhysicalDataTable(paper.data);

    // 标签映射
    const articleTypeBadge = paper.article_type === 'theoretical' ?
        '<span class="badge bg-info">⚛️ 理论</span>' :
        '<span class="badge bg-success">🔬 实验</span>';

    const scTypeBadges = {
        'cuprate': '<span class="badge" style="background-color: rgba(255, 99, 132, 0.8);">🔴 铜基</span>',
        'iron_based': '<span class="badge" style="background-color: rgba(75, 192, 192, 0.8);">🟤 铁基</span>',
        'nickel_based': '<span class="badge" style="background-color: rgba(75, 239, 58, 0.8);">🟠 镍基</span>',
        'hydride': '<span class="badge" style="background-color: rgba(153, 102, 255, 0.8);">💧 高压氢化物</span>',
        'carbon': '<span class="badge" style="background-color: rgba(54, 162, 235, 0.8);">🔵 碳基</span>',
        'organic': '<span class="badge" style="background-color: rgba(255, 206, 86, 0.8);">🟢 有机</span>',
        'others': '<span class="badge" style="background-color: rgba(204, 70, 70, 0.8);">⚪ 其他超导</span>'
    };

    const scTypeBadge = scTypeBadges[paper.superconductor_type] || legacyScTypeBadges[paper.superconductor_type] || scTypeBadges.others;

    // 审核状态徽章（从后端数据获取）
    const statusMap = {
        'unreviewed': { text: '⏳ 未审核', class: 'bg-warning' },
        'approved': { text: '✅ 已审核', class: 'bg-success' },
        'reviewed': { text: '✅ 已审核', class: 'bg-success' }, // 兼容旧数据
        'rejected': { text: '❌ 已拒绝', class: 'bg-danger' },
        'modifying': { text: '🛠️ 待修改', class: 'bg-info' },
        'admin_only': { text: '🔒 仅管理员可见', class: 'bg-dark' }
    };
    const statusInfo = statusMap[paper.review_status] || statusMap['unreviewed'];
    let reviewBadge = `<span class="badge ${statusInfo.class}">${statusInfo.text}${paper.reviewer_name && paper.review_status !== 'unreviewed' ? ` (${paper.reviewer_name})` : ''}</span>`;
    
    if (paper.review_comment && paper.review_status !== 'unreviewed') {
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
                            ${paper.chemical_formula || '未知体系'} |
                            Tc: ${tcSummary} |
                            ${articleTypeBadge}
                            ${scTypeBadge}
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

                            ${paper.abstract ? `
                                <div class="mb-3">
                                    <strong>摘要:</strong>
                                    <p class="mt-2 mb-0">${paper.abstract}</p>
                                </div>
                            ` : ''}

                            <div class="mb-2">
                                <strong>物理参数:</strong>
                                ${physicalDataHtml}
                            </div>

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
    const authors = paper.authors ? JSON.parse(paper.authors) : [];
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

        if (!pressure || !tc) {
            isValidData = false;
            return;
        }

        physicalData.push({
            chemical_formula: formula || null,
            crystal_structure: structure || null,
            tc_press: [parseFloat(pressure)],
            tc: [parseFloat(tc)],
            s_factor: calculateSFactor(tc, pressure),
            lambda_val: lambda_val ? parseFloat(lambda_val) : null,
            omega_log: omega_log ? parseFloat(omega_log) : null,
            n_ef: n_ef ? parseFloat(n_ef) : null
        });
    });

    if (!isValidData || physicalData.length === 0) {
        alert('请完整填写所有数据的压强和Tc');
        return;
    }

    if (selectedFiles.length > 5) {
        alert('最多允许上传5张文献截图');
        return;
    }

    // 构建FormData
    const formData = new FormData();
    formData.append('doi', doi);
    formData.append('element_symbols', JSON.stringify(elementSymbols.split('-')));
    formData.append('article_type', articleType.value);
    formData.append('superconductor_type', superconductorType);
    formData.append('physical_data', JSON.stringify(physicalData));

    const contributorName = document.getElementById('contributor-name-input').value.trim();
    if (contributorName) formData.append('contributor_name', contributorName);

    const contributorAff = document.getElementById('contributor-affiliation-input').value.trim();
    if (contributorAff) formData.append('contributor_affiliation', contributorAff);

    const notes = document.getElementById('notes-input').value.trim();
    if (notes) formData.append('notes', notes);

    // 添加图片
    selectedFiles.forEach(file => {
        formData.append('images', file);
    });

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
