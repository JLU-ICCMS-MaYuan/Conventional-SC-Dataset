// 全局文献管理页面 - JavaScript

let token = '';
let currentUser = null;
let editModal = null;
let selectedPapers = new Set();
let currentPage = 0;
let totalPapers = 0;
const pageSize = 20;
const SUPER_TYPES = ['cuprate', 'iron_based', 'nickel_based', 'hydride', 'carbon', 'organic', 'others'];
const LEGACY_SUPER_TYPES = {
    'carbon_organic': 'carbon',
    'conventional': 'others',
    'other_conventional': 'others',
    'unconventional': 'others',
    'other_unconventional': 'others',
    'unknown': 'others'
};

function getSelectedDatabase() {
    const el = document.getElementById('filterDatabase');
    return el ? el.value : 'local';
}

function normalizeSuperconductorType(value) {
    if (!value) return 'others';
    const normalized = LEGACY_SUPER_TYPES[value] || value;
    return SUPER_TYPES.includes(normalized) ? normalized : 'others';
}

function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value ?? '';
    return div.innerHTML;
}

function normalizeArticleType(value) {
    if (value === 'e') return 'experimental';
    if (value === 't') return 'theoretical';
    return value || '';
}

function synthesizedLabel(value) {
    const normalized = normalizeArticleType(value);
    if (normalized === 'experimental') return '是';
    if (normalized === 'theoretical') return '否';
    return '-';
}

function formatDataValue(value, suffix = '') {
    return value !== null && value !== undefined && value !== '' ? `${escapeHtml(value)}${suffix}` : '-';
}

function formatRangeValue(values, suffix = '') {
    if (!Array.isArray(values) || values.length === 0) {
        return '-';
    }
    return `${escapeHtml(values.join(' - '))}${suffix}`;
}

function renderPhysicalDataTable(paper) {
    const records = Array.isArray(paper.records) && paper.records.length > 0 ? paper.records : [];
    const rows = records.length > 0 ? records : [paper];
    return `
        <div class="table-responsive">
            <table class="table table-sm table-bordered align-middle mb-0">
                <thead class="table-light">
                    <tr>
                        <th>化学式</th>
                        <th>空间群</th>
                        <th>合成</th>
                        <th>Tc</th>
                        <th>P(GPa)</th>
                        <th>λ</th>
                        <th>ω_log</th>
                        <th>N(Ef)</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.map(r => `
                        <tr>
                            <td>${formatDataValue(r.chemical_formula || paper.chemical_formula)}</td>
                            <td>${formatDataValue(r.space_group_symbol)}</td>
                            <td>${synthesizedLabel(r.article_type)}</td>
                            <td>${formatDataValue(r.tc_max || r.mcmillan_tc || r.allen_dynes_tc || r.experimental_tc, ' K')}</td>
                            <td>${formatDataValue(r.pressure_gpa)}</td>
                            <td>${formatDataValue(r.lambda_value)}</td>
                            <td>${formatDataValue(r.omega_log)}</td>
                            <td>${formatDataValue(r.n_ef_total)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

function nullableFloat(value) {
    return value === '' || value === null || value === undefined ? null : parseFloat(value);
}

function dataInputValue(data, field) {
    if (!data) return '';
    const value = data[field];
    if (Array.isArray(value)) {
        return value.length > 0 && value[0] !== null && value[0] !== undefined ? escapeHtml(value[0]) : '';
    }
    return value !== null && value !== undefined ? escapeHtml(value) : '';
}

function calculateSFactor(tcValue, pressureValue) {
    const tc = parseFloat(tcValue);
    const pressure = parseFloat(pressureValue);
    if (!Number.isFinite(tc) || !Number.isFinite(pressure)) {
        return null;
    }
    return tc / Math.sqrt(1521 + Math.pow(pressure, 2));
}

// ========== 初始化 ==========

// 检查登录状态
function checkAuth() {
    if (!window.authState) {
        alert('无法获取登录状态，请刷新后重试');
        return false;
    }

    const state = window.authState.get();
    if (!state || !state.token || !state.user) {
        alert('请先登录');
        window.location.href = '/admin/login';
        return false;
    }

    if (!state.user.is_admin) {
        alert('当前账号没有管理员权限');
        window.location.href = '/';
        return false;
    }

    token = state.token;
    currentUser = state.user;
    document.getElementById('userName').textContent = currentUser.real_name;

    document.querySelectorAll('#batchStatusSelect option[data-superadmin-only="true"]').forEach(option => {
        if (currentUser.is_superadmin) {
            option.hidden = false;
            option.disabled = false;
        } else {
            option.remove();
        }
    });

    return true;
}

// 退出登录
function logout() {
    if (window.authState) {
        window.authState.clear();
    }
    window.location.href = '/admin/login';
}

// ========== 加载文献列表 ==========

async function loadPapers(page = 0) {
    const isPageChange = page !== currentPage;
    currentPage = page;

    if (isPageChange) {
        selectedPapers.clear();
        updateBatchActionsVisibility();
    }

    // 获取筛选条件
    const filters = {
        review_status: document.getElementById('filterReviewStatus').value,
        article_type: document.getElementById('filterArticleType').value,
        superconductor_type: document.getElementById('filterSuperconductorType').value,
        show_in_chart: document.getElementById('filterShowInChart').value,
        year_min: document.getElementById('filterYearMin').value,
        year_max: document.getElementById('filterYearMax').value,
        keyword: document.getElementById('filterKeyword').value,
        limit: pageSize,
        offset: page * pageSize
    };

    // 构建查询字符串
    const queryParams = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
        if (value) queryParams.append(key, value);
    }

    try {
        const response = await fetch(`/api/admin/papers/all?${queryParams}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('加载失败');
        }

        const data = await response.json();
        totalPapers = data.total;
        renderPapers(data.items || data.papers || []);
        renderPagination();
    } catch (error) {
        console.error('加载文献失败:', error);
        document.getElementById('papersList').innerHTML = `
            <div class="alert alert-danger">加载失败: ${error.message}</div>
        `;
    }
}

// 渲染文献列表
function renderPapers(papers) {
    const container = document.getElementById('papersList');

    if (papers.length === 0) {
        container.innerHTML = `
            <div class="alert alert-info text-center">
                <h4>没有找到匹配的文献</h4>
                <p class="mb-0">请尝试调整筛选条件</p>
            </div>
        `;
        return;
    }

    const allCheckedOnPage = papers.length > 0 && papers.every(p => selectedPapers.has(p.id));

    let html = `
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th width="40">
                            <input type="checkbox" id="selectAllTable" class="paper-checkbox"
                                   ${allCheckedOnPage ? 'checked' : ''} onchange="toggleSelectAll()">
                        </th>
                        <th>标题</th>
                        <th>元素组合</th>
                        <th>年份</th>
                        <th>数据点</th>
                        <th>s_factor</th>
                        <th>类型</th>
                        <th>图表</th>
                        <th>审核状态</th>
                        <th>详细信息</th>
                        <th width="280">操作</th>
                    </tr>
                </thead>
                <tbody>
    `;

    papers.forEach(paper => {
        const safeTitle = escapeHtml(paper.title);
        const isSelected = selectedPapers.has(paper.id);

        // 审核状态徽章
        let reviewBadge = '';
        const statusMap = {
            'pending': { text: '未审核', class: 'bg-warning' },
            'approved': { text: '已通过', class: 'bg-success' },
            'reviewed': { text: '已通过', class: 'bg-success' },
            'rejected': { text: '已拒绝', class: 'bg-danger' },
            'needs_revision': { text: '需修改', class: 'bg-info' }
        };
        
        const statusInfo = statusMap[paper.review_status] || statusMap['pending'];
        reviewBadge = `<span class="badge ${statusInfo.class}">${statusInfo.text}</span>`;
        
        if (paper.reviewer_name && paper.review_status !== 'pending') {
            reviewBadge += `<br><small class="text-muted">${escapeHtml(paper.reviewer_name)}</small>`;
        }
        
        if (paper.review_comment) {
            reviewBadge += `<br><small class="text-muted text-truncate d-inline-block" style="max-width: 150px;" title="${escapeHtml(paper.review_comment)}">${escapeHtml(paper.review_comment)}</small>`;
        }

        // 文章类型标签 — 从聚合数组取
        const articleTypes = Array.isArray(paper.article_types) ? paper.article_types : [];
        const articleTypeLabel = articleTypes.includes('e') ? '实验' : (articleTypes.includes('t') ? '理论' : '-');
        const scTypeLabelMap = {
            'h': '高压氢化物', 'c': '碳基', 'cb': '铜基', 'ot': '其他超导',
            'cuprate': '铜基', 'iron_based': '铁基', 'nickel_based': '镍基',
            'hydride': '高压氢化物', 'carbon': '碳基', 'organic': '有机', 'others': '其他超导'
        };
        const scTypes = Array.isArray(paper.superconductor_types) ? paper.superconductor_types : [];
        const scLabel = scTypes.map(t => scTypeLabelMap[t] || t).filter(Boolean).join('/') || '-';

        html += `
            <tr ${isSelected ? 'class="table-active"' : ''}>
                <td>
                    <input type="checkbox" class="paper-checkbox" data-paper-id="${paper.id}"
                           ${isSelected ? 'checked' : ''} onchange="togglePaperSelection(${paper.id})">
                </td>
                <td>
                    <strong>${safeTitle}</strong><br>
                    <small class="text-muted">DOI: ${paper.doi}</small>
                </td>
                <td><span class="badge bg-info">${paper.compound_symbols}</span></td>
                <td>${paper.year || '-'}</td>
                <td>${renderPhysicalDataTable(paper)}</td>
                <td>
                    <small>
                        ${(paper.s_factor !== undefined && paper.s_factor !== null) ?
                        Number(paper.s_factor).toFixed(2) : '-'}
                    </small>
                </td>
                <td>
                    <small>${articleTypeLabel} / ${scLabel}</small>
                </td>
                <td>
                    ${paper.show_in_chart ?
                        '<span class="badge bg-success">显示</span>' :
                        '<span class="badge bg-secondary">隐藏</span>'}
                </td>
                <td>${reviewBadge}</td>
                <td><span class="badge bg-info">${paper.record_count || 0} 条记录</span></td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <a href="https://doi.org/${paper.doi}" target="_blank" class="btn btn-outline-primary">原文</a>
                        <button class="btn btn-warning" onclick="openEditModal(${paper.id})">编辑</button>
                        ${currentUser.is_superadmin ?
                            `<button class="btn btn-danger" onclick="deleteSinglePaper(${paper.id}, '${paper.doi}', '${safeTitle}')">删除</button>`
                            : ''}
                    </div>
                </td>
            </tr>
        `;
    });

    html += `
                </tbody>
            </table>
        </div>
    `;

    container.innerHTML = html;
    updateBatchActionsVisibility();
    updateSelectAllCheckbox();
}

// 渲染分页
function renderPagination() {
    const totalPages = Math.ceil(totalPapers / pageSize);
    if (totalPages <= 1) {
        document.getElementById('pagination').style.display = 'none';
        return;
    }

    let html = '';

    // 上一页
    html += `
        <li class="page-item ${currentPage === 0 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="loadPapers(${currentPage - 1}); return false;">上一页</a>
        </li>
    `;

    // 页码
    for (let i = 0; i < totalPages; i++) {
        if (i === 0 || i === totalPages - 1 || (i >= currentPage - 2 && i <= currentPage + 2)) {
            html += `
                <li class="page-item ${i === currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="loadPapers(${i}); return false;">${i + 1}</a>
                </li>
            `;
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
    }

    // 下一页
    html += `
        <li class="page-item ${currentPage === totalPages - 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="loadPapers(${currentPage + 1}); return false;">下一页</a>
        </li>
    `;

    document.getElementById('pagination').querySelector('.pagination').innerHTML = html;
    document.getElementById('pagination').style.display = 'block';
}

// ========== 操作 ==========

function togglePaperSelection(paperId) {
    if (selectedPapers.has(paperId)) {
        selectedPapers.delete(paperId);
    } else {
        selectedPapers.add(paperId);
    }
    updateBatchActionsVisibility();
    updateSelectAllCheckbox();
}

function toggleSelectAll() {
    const checkboxes = document.querySelectorAll('.paper-checkbox[data-paper-id]');
    const selectAllMain = document.getElementById('selectAll');
    const selectAllTable = document.getElementById('selectAllTable');
    const selectAllChecked = (selectAllMain && selectAllMain.checked) ||
                             (selectAllTable && selectAllTable.checked);

    checkboxes.forEach(cb => {
        const paperId = parseInt(cb.getAttribute('data-paper-id'));
        if (selectAllChecked) {
            selectedPapers.add(paperId);
            cb.checked = true;
        } else {
            selectedPapers.delete(paperId);
            cb.checked = false;
        }
    });

    if (selectAllMain) selectAllMain.checked = selectAllChecked && checkboxes.length > 0;
    if (selectAllTable) selectAllTable.checked = selectAllChecked && checkboxes.length > 0;

    updateBatchActionsVisibility();
}

function clearSelection() {
    selectedPapers.clear();
    document.querySelectorAll('.paper-checkbox').forEach(cb => cb.checked = false);
    const selectAllMain = document.getElementById('selectAll');
    const selectAllTable = document.getElementById('selectAllTable');
    if (selectAllMain) selectAllMain.checked = false;
    if (selectAllTable) selectAllTable.checked = false;
    updateBatchActionsVisibility();
}

function updateBatchActionsVisibility() {
    const batchActions = document.getElementById('batchActions');
    const selectedCount = document.getElementById('selectedCount');

    selectedCount.textContent = selectedPapers.size;

    if (selectedPapers.size > 0) {
        batchActions.classList.add('active');
    } else {
        batchActions.classList.remove('active');
    }
}

function updateSelectAllCheckbox() {
    const checkboxes = document.querySelectorAll('.paper-checkbox[data-paper-id]');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);

    const selectAllMain = document.getElementById('selectAll');
    const selectAllTable = document.getElementById('selectAllTable');

    if (selectAllMain) selectAllMain.checked = allChecked && checkboxes.length > 0;
    if (selectAllTable) selectAllTable.checked = allChecked && checkboxes.length > 0;
}

async function batchReview() {
    if (selectedPapers.size === 0) {
        alert('请先选择要操作的文献');
        return;
    }

    const status = document.getElementById('batchStatusSelect').value;

    if (status === 'delete') {
        await batchDelete();
        return;
    }

    if (status === 'chart_show' || status === 'chart_hide') {
        await batchChartVisibility(status === 'chart_show');
        return;
    }

    const statusText = document.getElementById('batchStatusSelect').options[document.getElementById('batchStatusSelect').selectedIndex].text;

    if (!confirm(`确定要将选中的 ${selectedPapers.size} 篇文献设置为 ${statusText} 吗？`)) {
        return;
    }

    try {
        const response = await fetch(`/api/admin/papers/batch-review`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                paper_ids: Array.from(selectedPapers),
                status: status
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert(data.message || '操作成功！');
            clearSelection();
            loadPapers(currentPage);
        } else {
            alert('操作失败: ' + (data.detail || '未知错误'));
        }
    } catch (error) {
        console.error('操作失败:', error);
        alert('操作失败，请检查网络连接');
    }
}

async function batchChartVisibility(show) {
    if (selectedPapers.size === 0) {
        alert('请先选择要操作的文献');
        return;
    }

    const actionText = show ? '显示在图表中' : '从图表隐藏';
    if (!confirm(`确定要将选中的 ${selectedPapers.size} 篇文献设为“${actionText}”吗？`)) {
        return;
    }

    try {
        const response = await fetch(`/api/admin/papers/batch-chart-visibility`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                paper_ids: Array.from(selectedPapers),
                show
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert(data.message || '操作成功！');
            clearSelection();
            loadPapers(currentPage);
        } else {
            alert('操作失败: ' + (data.detail || '未知错误'));
        }
    } catch (error) {
        console.error('设置图表显示失败:', error);
        alert('操作失败，请检查网络连接');
    }
}

async function batchDelete() {
    if (selectedPapers.size === 0) {
        alert('请先选择要删除的文献');
        return;
    }

    // 三重确认
    if (!confirm(`⚠️ 警告：确定要删除 ${selectedPapers.size} 篇文献吗？\n\n此操作将删除所有选中文献及其截图，且不可撤销！`)) {
        return;
    }

    const confirmText = prompt(`请输入 "确认删除" 以继续：`);
    if (confirmText !== '确认删除') {
        alert('删除已取消');
        return;
    }

    if (!confirm(`最后确认：真的要删除这 ${selectedPapers.size} 篇文献吗？\n\n⚠️ 此操作不可撤销！`)) {
        return;
    }

    try {
        const response = await fetch(`/api/admin/papers/batch-delete`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                paper_ids: Array.from(selectedPapers)
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert(`删除完成！\n已删除：${data.deleted_count}篇文献`);
            clearSelection();
            loadPapers(currentPage);
        } else {
            alert('删除失败: ' + (data.detail || '未知错误'));
        }
    } catch (error) {
        console.error('删除失败:', error);
        alert('删除失败，请检查网络连接');
    }
}

// ========== 编辑文献 ==========

// ========== 编辑文献助手函数 ==========

function addEditDataRow(data = null) {
    const container = document.getElementById('editDataPointsContainer');
    const row = document.createElement('div');
    row.className = 'edit-data-row card p-2 mb-2 bg-light';
    const articleType = (data ? data.article_type : '') || document.getElementById('editArticleType').value || 't';
    row.innerHTML = `
        <div class="row g-2">
            <div class="col-md-6 col-lg-2">
                <input type="text" class="form-control form-control-sm edit-formula" placeholder="化学式" value="${dataInputValue(data, 'chemical_formula')}">
            </div>
            <div class="col-md-6 col-lg-2">
                <input type="text" class="form-control form-control-sm edit-structure" placeholder="空间群" value="${dataInputValue(data, 'space_group_symbol')}">
            </div>
            <div class="col-md-6 col-lg-2">
                <select class="form-select form-select-sm edit-article-type" title="是否实验合成">
                    <option value="e" ${articleType === 'e' ? 'selected' : ''}>实验合成：是</option>
                    <option value="t" ${articleType === 't' ? 'selected' : ''}>实验合成：否</option>
                </select>
            </div>
            <div class="col-md-6 col-lg-1">
                <input type="number" step="any" class="form-control form-control-sm edit-pressure" placeholder="P (GPa)" value="${dataInputValue(data, 'pressure_gpa')}">
            </div>
            <div class="col-md-6 col-lg-1">
                <input type="number" step="any" class="form-control form-control-sm edit-tc" placeholder="Tc (K)" value="${dataInputValue(data, 'experimental_tc') || dataInputValue(data, 'mcmillan_tc') || dataInputValue(data, 'tc_max')}">
            </div>
            <div class="col-md-6 col-lg-1">
                <input type="number" step="any" class="form-control form-control-sm edit-lambda" placeholder="λ" value="${dataInputValue(data, 'lambda_value')}">
            </div>
            <div class="col-md-6 col-lg-1">
                <input type="number" step="any" class="form-control form-control-sm edit-omega" placeholder="ω" value="${dataInputValue(data, 'omega_log')}">
            </div>
            <div class="col-md-6 col-lg-1">
                <input type="number" step="any" class="form-control form-control-sm edit-nef" placeholder="N" value="${dataInputValue(data, 'n_ef_total')}">
            </div>
            <div class="col-12 col-lg-1">
                <button type="button" class="btn btn-outline-danger btn-sm w-100" onclick="removeEditDataRow(this)">×</button>
            </div>
        </div>
    `;
    container.appendChild(row);
}

function removeEditDataRow(button) {
    const container = document.getElementById('editDataPointsContainer');
    if (container.querySelectorAll('.edit-data-row').length > 1) {
        button.closest('.edit-data-row').remove();
    } else {
        alert('至少需要保留一组数据');
    }
}

async function openEditModal(paperId) {
    console.log('Opening edit modal for paper:', paperId);
    try {
        const response = await fetch(`/api/admin/papers/${paperId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('获取文献信息失败');
        }

        const paper = await response.json();
        console.log('Paper data received:', paper);

        // 安全填充工具函数
        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) {
                el.value = val !== null && val !== undefined ? val : '';
            } else {
                console.warn(`[DOM Missing] Element #${id} not found in current page.`);
            }
        };

        // 全部字段填充
        setVal('editPaperId', paper.id);
        setVal('editDoi', paper.doi);
        setVal('editTitle', paper.title);
        setVal('editJournal', paper.journal);
        setVal('editYear', paper.year);
        setVal('editVolume', paper.volume);
        setVal('editPages', paper.pages);
        let authorsStr = paper.authors || '';
        if (Array.isArray(authorsStr)) authorsStr = authorsStr.join(', ');
        setVal('editAuthors', authorsStr);
        setVal('editAbstract', paper.abstract);
        setVal('editArticleType', (Array.isArray(paper.article_types) ? paper.article_types[0] : null) || 't');
        setVal('editSuperconductorType', (Array.isArray(paper.superconductor_types) ? paper.superconductor_types[0] : null) || 'h');
        setVal('editNotes', paper.review_comment || '');

        // 物理数据
        const dataContainer = document.getElementById('editDataPointsContainer');
        if (dataContainer) {
            dataContainer.innerHTML = '';
            const records = Array.isArray(paper.records) ? paper.records : [];
            if (records.length > 0) {
                records.forEach(r => addEditDataRow(r));
            } else {
                addEditDataRow();
            }
        }

        // 摘要信息
        const setHtml = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val !== null && val !== undefined ? val : '-'; };
        setHtml('detailRecordCount', paper.record_count);
        setHtml('detailUploader', paper.uploader_name || '-');
        setHtml('detailCreatedAt', paper.created_at ? new Date(paper.created_at).toLocaleString('zh-CN') : '-');

        // 3. 审核信息
        setVal('editReviewStatus', paper.review_status || 'pending');
        setVal('editReviewComment', paper.review_comment || '');
        const statusMap = {
            'pending': '<span class="badge bg-warning">未审核</span>',
            'approved': '<span class="badge bg-success">已通过</span>',
            'rejected': '<span class="badge bg-danger">已拒绝</span>',
            'needs_revision': '<span class="badge bg-info">需修改</span>'
        };
        const statusDisplay = document.getElementById('currentReviewStatusDisplay');
        if (statusDisplay) statusDisplay.innerHTML = statusMap[paper.review_status] || statusMap['pending'];

        // show_in_chart 复选框
        const chartCb = document.getElementById('editShowInChart');
        if (chartCb) chartCb.checked = !!paper.show_in_chart;

        // 4. 详细信息 records 表格
        const tbody = document.getElementById('recordsTableBody');
        if (tbody) {
            const records = Array.isArray(paper.records) ? paper.records : [];
            tbody.innerHTML = records.map((r, i) => `
                <tr>
                    <td>${i+1}</td>
                    <td>${escapeHtml(r.chemical_formula)}</td>
                    <td>${escapeHtml(r.source_label)}</td>
                    <td>${r.pressure_gpa != null ? Number(r.pressure_gpa).toFixed(1) : '-'}</td>
                    <td>${escapeHtml(r.space_group_symbol)}</td>
                    <td>${escapeHtml(r.crystal_structure)}</td>
                    <td>${r.mcmillan_tc != null ? Number(r.mcmillan_tc).toFixed(1) : '-'}</td>
                    <td>${r.allen_dynes_tc != null ? Number(r.allen_dynes_tc).toFixed(1) : '-'}</td>
                    <td>${r.isotropic_eliashberg_tc != null ? Number(r.isotropic_eliashberg_tc).toFixed(1) : '-'}</td>
                    <td>${r.anisotropic_eliashberg_tc != null ? Number(r.anisotropic_eliashberg_tc).toFixed(1) : '-'}</td>
                    <td>${r.experimental_tc != null ? Number(r.experimental_tc).toFixed(1) : '-'}</td>
                    <td>${r.lambda_value != null ? Number(r.lambda_value).toFixed(2) : '-'}</td>
                    <td>${r.omega_log != null ? Number(r.omega_log).toFixed(1) : '-'}</td>
                    <td>${r.n_ef_total != null ? Number(r.n_ef_total).toFixed(2) : '-'}</td>
                    <td>${r.energy_cutoff_value != null ? Number(r.energy_cutoff_value).toFixed(1) : '-'}</td>
                    <td>${r.thermodynamically_stable ? '✅' : (r.thermodynamically_stable === false ? '❌' : '-')}</td>
                    <td>${r.dynamically_stable ? '✅' : (r.dynamically_stable === false ? '❌' : '-')}</td>
                    <td>${r.energy_above_hull != null ? Number(r.energy_above_hull).toFixed(3) : '-'}</td>
                    <td>${r.show_in_chart ? '✅' : '—'}</td>
                    <td>${r.article_type === 'e' ? '实验' : (r.article_type === 't' ? '理论' : '-')}</td>
                    <td>${escapeHtml(r.superconductor_type)}</td>
                    <td>${r.s_factor != null ? Number(r.s_factor).toFixed(2) : '-'}</td>
                    <td>${escapeHtml(r.method)}</td>
                    <td>${escapeHtml(r.note)}</td>
                </tr>
            `).join('') || '<tr><td colspan="25" class="text-center text-muted">无记录</td></tr>';
        }

        // 5. 显示模态框
        if (!editModal) {
            editModal = new bootstrap.Modal(document.getElementById('editPaperModal'));
        }
        editModal.show();

    } catch (error) {
        console.error('打开编辑框具体错误:', error);
        alert('无法打开编辑框，请检查控制台输出');
    }
}

async function submitReviewAction() {
    const paperIdEl = document.getElementById('editPaperId');
    const statusEl = document.getElementById('editReviewStatus');
    const commentEl = document.getElementById('editReviewComment');

    if (!paperIdEl || !statusEl || !commentEl) {
        alert('无法提交：表单元素缺失');
        return;
    }

    const paperId = paperIdEl.value;
    const status = statusEl.value;
    const comment = commentEl.value;

    try {
        const response = await fetch(`/api/admin/papers/${paperId}/review`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                status: status,
                comment: comment
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert('审核状态已更新！');
            // 更新当前显示的 Badge
            const statusMap = {
                'pending': '<span class="badge bg-warning">未审核</span>',
                'approved': '<span class="badge bg-success">已通过</span>',
                'rejected': '<span class="badge bg-danger">已拒绝</span>',
                'needs_revision': '<span class="badge bg-info">需修改</span>'
            };
            const statusDisplay = document.getElementById('currentReviewStatusDisplay');
            if (statusDisplay) {
                statusDisplay.innerHTML = statusMap[status];
            }
            loadPapers(currentPage);
        } else {
            alert('更新审核状态失败: ' + (data.detail || '未知错误'));
        }
    } catch (error) {
        console.error('提交审核失败:', error);
        alert('提交失败，请检查网络连接');
    }
}

async function savePaperEdits() {
    const paperIdEl = document.getElementById('editPaperId');
    if (!paperIdEl) {
        alert('无法保存：ID 元素缺失');
        return;
    }
    const paperId = paperIdEl.value;

    // 收集物理数据
    const physicalData = [];
    document.querySelectorAll('.edit-data-row').forEach(row => {
        const formula = row.querySelector('.edit-formula').value.trim();
        const structure = row.querySelector('.edit-structure').value.trim();
        const pressure = nullableFloat(row.querySelector('.edit-pressure').value);
        const tc = nullableFloat(row.querySelector('.edit-tc').value);
        const lambdaVal = nullableFloat(row.querySelector('.edit-lambda').value);
        const omegaLog = nullableFloat(row.querySelector('.edit-omega').value);
        const nEf = nullableFloat(row.querySelector('.edit-nef').value);
        if (formula || structure || pressure !== null || tc !== null) {
            physicalData.push({
                chemical_formula: formula || null,
                space_group_symbol: structure || null,
                article_type: row.querySelector('.edit-article-type').value,
                pressure_gpa: pressure,
                experimental_tc: tc,
                lambda_value: lambdaVal,
                omega_log: omegaLog,
                n_ef_total: nEf
            });
        }
    });

    const getVal = (id) => {
        const el = document.getElementById(id);
        return el ? el.value : '';
    };

    const updateData = {
        doi: getVal('editDoi') || null,
        title: getVal('editTitle'),
        journal: getVal('editJournal'),
        year: getVal('editYear') ? parseInt(getVal('editYear')) : null,
        volume: getVal('editVolume'),
        pages: getVal('editPages') || null,
        authors: getVal('editAuthors'),
        abstract: getVal('editAbstract'),
        review_comment: getVal('editNotes'),
        review_status: getVal('editReviewStatus'),
        show_in_chart: document.getElementById('editShowInChart')?.checked ?? false,
        records: physicalData
    };

    try {
        const response = await fetch(`/api/admin/papers/${paperId}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updateData)
        });

        const data = await response.json();

        if (response.ok) {
            alert('文献信息已更新！');
            editModal.hide();
            loadPapers(currentPage);
        } else {
            alert('保存失败: ' + (data.detail || '未知错误'));
        }
    } catch (error) {
        console.error('保存失败:', error);
        alert('保存失败，请检查网络连接');
    }
}

// ========== 图片管理 ==========

async function loadPaperImages(paperId) {
    try {
        const response = await fetch(`/api/admin/papers/${paperId}/images`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            throw new Error('获取图片列表失败');
        }

        const data = await response.json();
        renderImagesList(paperId, data.images);

    } catch (error) {
        console.error('加载图片失败:', error);
        document.getElementById('imagesList').innerHTML = `
            <div class="alert alert-danger">加载图片失败: ${error.message}</div>
        `;
    }
}

function renderImagesList(paperId, images) {
    const container = document.getElementById('imagesList');

    if (images.length === 0) {
        container.innerHTML = '<div class="alert alert-warning">没有图片</div>';
        return;
    }

    let html = '';
    images.forEach((img, index) => {
        const canDelete = images.length > 1; // 至少保留一张图片
        html += `
            <div class="col-md-4 mb-3">
                <div class="card">
                    <img src="/api/papers/images/${img.id}?thumbnail=true" class="card-img-top" alt="截图${img.order}">
                    <div class="card-body">
                        <h6 class="card-title">图片 ${img.order}</h6>
                        <p class="card-text">
                            <small class="text-muted">
                                大小: ${(img.file_size / 1024).toFixed(2)} KB<br>
                                创建: ${new Date(img.created_at).toLocaleString('zh-CN')}
                            </small>
                        </p>
                        ${canDelete ?
                            `<button class="btn btn-danger btn-sm" onclick="deleteImage(${paperId}, ${img.id})">删除此图片</button>`
                            : '<small class="text-muted">最后一张图片，无法删除</small>'}
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

async function deleteImage(paperId, imageId) {
    if (!confirm('确定要删除这张图片吗？')) {
        return;
    }

    try {
        const response = await fetch(`/api/admin/papers/${paperId}/images/${imageId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();

        if (response.ok) {
            alert('图片已删除！');
            loadPaperImages(paperId); // 重新加载图片列表
        } else {
            alert('删除失败: ' + (data.detail || '未知错误'));
        }
    } catch (error) {
        console.error('删除图片失败:', error);
        alert('删除失败，请检查网络连接');
    }
}

// ========== 单个删除 ==========

async function deleteSinglePaper(paperId, paperDoi, paperTitle) {
    // 三重确认
    if (!confirm(`⚠️ 警告：确定要删除文献《${paperTitle}》吗？\n\n此操作将删除该文献及其所有截图，且不可撤销！`)) {
        return;
    }

    const inputDoi = prompt(`请输入该文献的DOI以确认删除：\n\n${paperDoi}`);
    if (inputDoi !== paperDoi) {
        alert('DOI不匹配，删除已取消');
        return;
    }

    if (!confirm(`最后确认：真的要删除《${paperTitle}》吗？\n\n⚠️ 此操作不可撤销！`)) {
        return;
    }

    try {
        const response = await fetch(`/api/admin/papers/${paperId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();

        if (response.ok) {
            alert('文献已删除！');
            loadPapers(currentPage);
        } else {
            alert('删除失败: ' + (data.detail || '未知错误'));
        }
    } catch (error) {
        console.error('删除失败:', error);
        alert('删除失败，请检查网络连接');
    }
}

// ========== 页面初始化 ==========

if (checkAuth()) {
    loadPapers();
}
