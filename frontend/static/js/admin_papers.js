// 全局文献管理页面 - JavaScript

let token = '';
let currentUser = null;
let editModal = null;
let selectedPapers = new Set();
let currentPage = 0;
let totalPapers = 0;
const pageSize = 20;

// ========== 初始化 ==========

// 检查登录状态
function checkAuth() {
    token = localStorage.getItem('admin_token');
    const userStr = localStorage.getItem('admin_user');

    if (!token || !userStr) {
        alert('请先登录');
        window.location.href = '/admin/login';
        return false;
    }

    currentUser = JSON.parse(userStr);
    document.getElementById('userName').textContent = currentUser.real_name;

    // 如果是超级管理员，显示批量删除按钮
    if (currentUser.is_superadmin) {
        document.getElementById('batchDeleteBtn').style.display = 'inline-block';
    }

    return true;
}

// 退出登录
function logout() {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
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
                            <input type="checkbox" id="selectAllTable" class="paper-checkbox" onchange="toggleSelectAll()">
                        </th>
                        <th>标题</th>
                        <th>元素组合</th>
                        <th>年份</th>
                        <th>Tc / P</th>
                        <th>类型</th>
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
        if (paper.review_status === 'reviewed') {
            reviewBadge = `<span class="badge bg-success">✓ 已审核</span>`;
            if (paper.reviewer_name) {
                reviewBadge += `<br><small class="text-muted">${escapeHtml(paper.reviewer_name)}</small>`;
            }
        } else {
            reviewBadge = `<span class="badge bg-warning">⏳ 未审核</span>`;
        }

        // 文章类型标签
        const articleTypeLabel = paper.article_type === 'theoretical' ? '理论' : '实验';
        const scTypeLabel = {
            'conventional': '常规',
            'unconventional': '非常规',
            'unknown': '未知'
        }[paper.superconductor_type] || '未知';

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
                    <small>${articleTypeLabel} / ${scTypeLabel}</small>
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

// ========== 批量操作 ==========

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
        alert('请先选择要审核的文献');
        return;
    }

    if (!confirm(`确定要批量审核 ${selectedPapers.size} 篇文献吗？`)) {
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
                paper_ids: Array.from(selectedPapers)
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert(`批量审核完成！\n已审核：${data.reviewed_count}篇\n已跳过：${data.skipped_count}篇`);
            clearSelection();
            loadPapers(currentPage);
        } else {
            alert('批量审核失败: ' + (data.detail || '未知错误'));
        }
    } catch (error) {
        console.error('批量审核失败:', error);
        alert('批量审核失败，请检查网络连接');
    }
}

async function batchDelete() {
    if (selectedPapers.size === 0) {
        alert('请先选择要删除的文献');
        return;
    }

    // 三重确认
    if (!confirm(`⚠️ 警告：确定要批量删除 ${selectedPapers.size} 篇文献吗？\n\n此操作将删除所有选中文献及其截图，且不可撤销！`)) {
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
            alert(`批量删除完成！\n已删除：${data.deleted_count}篇文献`);
            clearSelection();
            loadPapers(currentPage);
        } else {
            alert('批量删除失败: ' + (data.detail || '未知错误'));
        }
    } catch (error) {
        console.error('批量删除失败:', error);
        alert('批量删除失败，请检查网络连接');
    }
}

// ========== 编辑文献 ==========

async function openEditModal(paperId) {
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

        // 填充表单
        document.getElementById('editPaperId').value = paper.id;
        document.getElementById('editDoi').value = paper.doi;
        document.getElementById('editTitle').value = paper.title || '';
        document.getElementById('editJournal').value = paper.journal || '';
        document.getElementById('editYear').value = paper.year || '';
        document.getElementById('editVolume').value = paper.volume || '';
        document.getElementById('editAuthors').value = paper.authors || '';
        document.getElementById('editArticleType').value = paper.article_type || 'experimental';
        document.getElementById('editSuperconductorType').value = paper.superconductor_type || 'unknown';
        document.getElementById('editChemicalFormula').value = paper.chemical_formula || '';
        document.getElementById('editCrystalStructure').value = paper.crystal_structure || '';
        document.getElementById('editTc').value = paper.tc || '';
        document.getElementById('editPressure').value = paper.pressure || '';
        document.getElementById('editLambda').value = paper.lambda_val || '';
        document.getElementById('editOmegaLog').value = paper.omega_log || '';
        document.getElementById('editNEf').value = paper.n_ef || '';
        document.getElementById('editContributorName').value = paper.contributor_name || '';
        document.getElementById('editContributorAffiliation').value = paper.contributor_affiliation || '';
        document.getElementById('editNotes').value = paper.notes || '';

        // 加载图片列表
        loadPaperImages(paperId);

        // 显示模态框
        if (!editModal) {
            editModal = new bootstrap.Modal(document.getElementById('editPaperModal'));
        }
        editModal.show();

    } catch (error) {
        console.error('打开编辑框失败:', error);
        alert('无法打开编辑框: ' + error.message);
    }
}

async function savePaperEdits() {
    const paperId = document.getElementById('editPaperId').value;

    const updateData = {
        title: document.getElementById('editTitle').value,
        journal: document.getElementById('editJournal').value,
        year: document.getElementById('editYear').value ? parseInt(document.getElementById('editYear').value) : null,
        volume: document.getElementById('editVolume').value,
        authors: document.getElementById('editAuthors').value,
        article_type: document.getElementById('editArticleType').value,
        superconductor_type: document.getElementById('editSuperconductorType').value,
        chemical_formula: document.getElementById('editChemicalFormula').value,
        crystal_structure: document.getElementById('editCrystalStructure').value,
        tc: document.getElementById('editTc').value ? parseFloat(document.getElementById('editTc').value) : null,
        pressure: document.getElementById('editPressure').value ? parseFloat(document.getElementById('editPressure').value) : null,
        lambda_val: document.getElementById('editLambda').value ? parseFloat(document.getElementById('editLambda').value) : null,
        omega_log: document.getElementById('editOmegaLog').value ? parseFloat(document.getElementById('editOmegaLog').value) : null,
        n_ef: document.getElementById('editNEf').value ? parseFloat(document.getElementById('editNEf').value) : null,
        contributor_name: document.getElementById('editContributorName').value,
        contributor_affiliation: document.getElementById('editContributorAffiliation').value,
        notes: document.getElementById('editNotes').value
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
