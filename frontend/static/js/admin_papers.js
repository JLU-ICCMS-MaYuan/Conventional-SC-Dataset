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

function normalizeSuperconductorType(value) {
    if (!value) return 'others';
    const normalized = LEGACY_SUPER_TYPES[value] || value;
    return SUPER_TYPES.includes(normalized) ? normalized : 'others';
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
    currentPage = page;

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
        renderPapers(data.papers);
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

    let html = `
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th width="40">
                        </th>
                        <th>标题</th>
                        <th>元素组合</th>
                        <th>年份</th>
                        <th>Tc / P</th>
                        <th>s_factor</th>
                        <th>类型</th>
                        <th>图表</th>
                        <th>审核状态</th>
                        <th>图片</th>
                        <th width="280">操作</th>
                    </tr>
                </thead>
                <tbody>
    `;

    papers.forEach(paper => {
        const escapeHtml = (str) => {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        };

        const safeTitle = escapeHtml(paper.title);
        const isSelected = selectedPapers.has(paper.id);

        // 审核状态徽章
        let reviewBadge = '';
        const statusMap = {
            'unreviewed': { text: '⏳ 未审核', class: 'bg-warning' },
            'approved': { text: '✅ 已通过', class: 'bg-success' },
            'reviewed': { text: '✅ 已通过', class: 'bg-success' }, // 兼容旧数据
            'rejected': { text: '❌ 已拒绝', class: 'bg-danger' },
            'modifying': { text: '🛠️ 待修改', class: 'bg-info' },
            'admin_only': { text: '🔒 仅管理员可见', class: 'bg-dark' }
        };
        
        const statusInfo = statusMap[paper.review_status] || statusMap['unreviewed'];
        reviewBadge = `<span class="badge ${statusInfo.class}">${statusInfo.text}</span>`;
        
        if (paper.reviewer_name && paper.review_status !== 'unreviewed') {
            reviewBadge += `<br><small class="text-muted">${escapeHtml(paper.reviewer_name)}</small>`;
        }
        
        if (paper.review_comment) {
            reviewBadge += `<br><small class="text-muted text-truncate d-inline-block" style="max-width: 150px;" title="${escapeHtml(paper.review_comment)}">${escapeHtml(paper.review_comment)}</small>`;
        }

        // 文章类型标签
        const articleTypeLabel = paper.article_type === 'theoretical' ? '理论' : '实验';
        const scTypeLabelMap = {
            'cuprate': '铜基',
            'iron_based': '铁基',
            'nickel_based': '镍基',
            'hydride': '高压氢化物',
            'carbon': '碳基',
            'organic': '有机',
            'others': '其他超导'
        };
        const normalizedType = normalizeSuperconductorType(paper.superconductor_type);
        const scTypeLabel = scTypeLabelMap[normalizedType] || '其他超导';

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
                <td>
                    <small>
                        ${paper.tc ? paper.tc + ' K' : '-'} / 
                        ${paper.pressure ? paper.pressure + ' GPa' : '-'}
                    </small>
                </td>
                <td>
                    <small>
                        ${(paper.s_factor !== undefined && paper.s_factor !== null) ?
                        Number(paper.s_factor).toFixed(2) : '-'}
                    </small>
                </td>
                <td>
                    <small>${articleTypeLabel} / ${scTypeLabel}</small>
                </td>
                <td>
                    ${paper.show_in_chart ?
                        '<span class="badge bg-success">显示</span>' :
                        '<span class="badge bg-secondary">隐藏</span>'}
                </td>
                <td>${reviewBadge}</td>
                <td><span class="badge bg-secondary">${paper.images_count}张</span></td>
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
    const selectAllChecked = document.getElementById('selectAll').checked ||
                            document.getElementById('selectAllTable').checked;

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

    updateBatchActionsVisibility();
}

function clearSelection() {
    selectedPapers.clear();
    document.querySelectorAll('.paper-checkbox').forEach(cb => cb.checked = false);
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
        const response = await fetch('/api/admin/papers/batch-review', {
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
        const response = await fetch('/api/admin/papers/batch-chart-visibility', {
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
        const response = await fetch('/api/admin/papers/batch-delete', {
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
    row.innerHTML = `
        <div class="row g-2">
            <div class="col-md-4 col-lg-2">
                <input type="number" step="any" class="form-control form-control-sm edit-pressure" placeholder="P (GPa)" value="${data ? data.pressure || '' : ''}">
            </div>
            <div class="col-md-4 col-lg-2">
                <input type="number" step="any" class="form-control form-control-sm edit-tc" placeholder="Tc (K)" value="${data ? data.tc || '' : ''}">
            </div>
            <div class="col-md-4 col-lg-2">
                <input type="number" step="any" class="form-control form-control-sm edit-lambda" placeholder="λ" value="${data ? data.lambda_val || '' : ''}">
            </div>
            <div class="col-md-4 col-lg-2">
                <input type="number" step="any" class="form-control form-control-sm edit-omega" placeholder="ω" value="${data ? data.omega_log || '' : ''}">
            </div>
            <div class="col-md-4 col-lg-2">
                <input type="number" step="any" class="form-control form-control-sm edit-nef" placeholder="N" value="${data ? data.n_ef || '' : ''}">
            </div>
            <div class="col-12 col-lg-2">
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

        // 1. 基础信息
        setVal('editPaperId', paper.id);
        setVal('editDoi', paper.doi);
        setVal('editTitle', paper.title);
        setVal('editJournal', paper.journal);
        setVal('editYear', paper.year);
        setVal('editVolume', paper.volume);
        
        // 作者处理
        let authorsStr = paper.authors || '';
        if (Array.isArray(authorsStr)) authorsStr = authorsStr.join(', ');
        setVal('editAuthors', authorsStr);
        
        setVal('editArticleType', paper.article_type || 'experimental');
        setVal('editSuperconductorType', normalizeSuperconductorType(paper.superconductor_type));
        setVal('editChemicalFormula', paper.chemical_formula || '');
        setVal('editCrystalStructure', paper.crystal_structure || '');
        
        // 2. 物理数据 (动态行处理)
        const dataContainer = document.getElementById('editDataPointsContainer');
        if (dataContainer) {
            dataContainer.innerHTML = '';
            if (paper.data && paper.data.length > 0) {
                paper.data.forEach(d => addEditDataRow(d));
            } else {
                // 如果没有数据，且 paper 本身有 tc/pressure (兼容旧数据结构)
                if (paper.tc || paper.pressure) {
                    addEditDataRow({
                        tc: paper.tc,
                        pressure: paper.pressure,
                        lambda_val: paper.lambda_val,
                        omega_log: paper.omega_log,
                        n_ef: paper.n_ef
                    });
                } else {
                    addEditDataRow();
                }
            }
        }

        setVal('editContributorName', paper.contributor_name);
        setVal('editContributorAffiliation', paper.contributor_affiliation);
        setVal('editNotes', paper.notes);

        // 3. 审核信息
        setVal('editReviewStatus', paper.review_status || 'unreviewed');
        setVal('editReviewComment', paper.review_comment || '');
        
        const statusMap = {
            'unreviewed': '<span class="badge bg-warning">⏳ 未审核</span>',
            'approved': '<span class="badge bg-success">✅ 已通过</span>',
            'rejected': '<span class="badge bg-danger">❌ 已拒绝</span>',
            'modifying': '<span class="badge bg-info">🛠️ 待修改</span>',
            'admin_only': '<span class="badge bg-dark">🔒 仅管理员可见</span>'
        };
        const statusDisplay = document.getElementById('currentReviewStatusDisplay');
        if (statusDisplay) {
            statusDisplay.innerHTML = statusMap[paper.review_status] || statusMap['unreviewed'];
        }

        // 4. 加载图片
        if (typeof loadPaperImages === 'function') {
            loadPaperImages(paperId);
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
                'unreviewed': '<span class="badge bg-warning">⏳ 未审核</span>',
                'approved': '<span class="badge bg-success">✅ 已通过</span>',
                'rejected': '<span class="badge bg-danger">❌ 已拒绝</span>',
                'modifying': '<span class="badge bg-info">🛠️ 待修改</span>',
                'admin_only': '<span class="badge bg-dark">🔒 仅管理员可见</span>'
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
        const pressure = row.querySelector('.edit-pressure').value;
        const tc = row.querySelector('.edit-tc').value;
        if (pressure && tc) {
            const parsedPressure = parseFloat(pressure);
            const parsedTc = parseFloat(tc);
            physicalData.push({
                pressure: parsedPressure,
                tc: parsedTc,
                s_factor: calculateSFactor(parsedTc, parsedPressure),
                lambda_val: row.querySelector('.edit-lambda').value ? parseFloat(row.querySelector('.edit-lambda').value) : null,
                omega_log: row.querySelector('.edit-omega').value ? parseFloat(row.querySelector('.edit-omega').value) : null,
                n_ef: row.querySelector('.edit-nef').value ? parseFloat(row.querySelector('.edit-nef').value) : null
            });
        }
    });

    const getVal = (id) => {
        const el = document.getElementById(id);
        return el ? el.value : '';
    };

    const updateData = {
        title: getVal('editTitle'),
        journal: getVal('editJournal'),
        year: getVal('editYear') ? parseInt(getVal('editYear')) : null,
        volume: getVal('editVolume'),
        authors: getVal('editAuthors'),
        article_type: getVal('editArticleType'),
        superconductor_type: getVal('editSuperconductorType'),
        chemical_formula: getVal('editChemicalFormula'),
        crystal_structure: getVal('editCrystalStructure'),
        physical_data: physicalData,
        contributor_name: getVal('editContributorName'),
        contributor_affiliation: getVal('editContributorAffiliation'),
        notes: getVal('editNotes')
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
