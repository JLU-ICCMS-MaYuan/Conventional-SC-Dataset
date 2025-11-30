// 全局变量
let elementSymbols = '';
let uploadModal, imageModal;
let selectedFiles = [];
let currentReviewStatus = 'all'; // 当前选择的审核状态筛选

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

    // 设置图片上传预览
    document.getElementById('images-input').addEventListener('change', handleImageSelection);
});

// 加载元素组合信息
async function loadCompoundInfo() {
    try {
        const response = await fetch(`/api/compounds/${elementSymbols}`);
        if (response.ok) {
            const data = await response.json();
            document.getElementById('compound-title').textContent = `${data.element_symbols} 系统超导体`;
            document.getElementById('compound-subtitle').textContent = `共收录 ${data.paper_count} 篇文献`;
        } else {
            document.getElementById('compound-title').textContent = '元素组合不存在';
        }
    } catch (error) {
        console.error('加载元素组合信息失败:', error);
    }
}

// 加载文献列表
async function loadPapers(searchParams = {}) {
    const container = document.getElementById('papers-container');
    container.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div><p class="mt-3">加载中...</p></div>';

    try {
        // 构建查询参数
        const params = new URLSearchParams();
        if (searchParams.keyword) params.append('keyword', searchParams.keyword);
        if (searchParams.year_min) params.append('year_min', searchParams.year_min);
        if (searchParams.year_max) params.append('year_max', searchParams.year_max);
        if (currentReviewStatus !== 'all') params.append('review_status', currentReviewStatus);

        const response = await fetch(`/api/papers/compound/${elementSymbols}?${params}`);

        if (!response.ok) {
            throw new Error('加载失败');
        }

        const papers = await response.json();

        if (papers.length === 0) {
            const statusText = currentReviewStatus === 'reviewed' ? '已审核' :
                              currentReviewStatus === 'unreviewed' ? '未审核' : '';
            container.innerHTML = `
                <div class="text-center py-5">
                    <div class="alert alert-warning" role="alert">
                        <h4 class="alert-heading">🎉 暂无${statusText}文献</h4>
                        <p class="mb-0">这个元素组合还没有${statusText}文献记录${currentReviewStatus === 'all' ? '，<strong>成为第一个贡献者吧！</strong>' : ''}</p>
                        ${currentReviewStatus === 'all' ? '<hr><p class="mb-0">点击上方的 <strong>"上传文献"</strong> 按钮即可添加第一篇文献</p>' : ''}
                    </div>
                </div>
            `;
            return;
        }

        // 渲染文献列表
        container.innerHTML = papers.map(paper => renderPaperCard(paper)).join('');

    } catch (error) {
        console.error('加载文献失败:', error);
        container.innerHTML = '<div class="alert alert-danger">加载失败，请稍后重试</div>';
    }
}

// 审核状态筛选
function filterByReviewStatus(status) {
    currentReviewStatus = status;
    loadPapers();
}

// 渲染文献卡片（简化版，点击展开）
function renderPaperCard(paper) {
    const authors = paper.authors ? JSON.parse(paper.authors) : [];
    const firstAuthor = authors.length > 0 ? authors[0] : '未知作者';
    const correspondingAuthor = authors.length > 0 ? authors[authors.length - 1] : '未知作者';

    // 标签映射
    const articleTypeBadge = paper.article_type === 'theoretical' ?
        '<span class="badge bg-info">⚛️ 理论</span>' :
        '<span class="badge bg-success">🔬 实验</span>';

    const scTypeBadges = {
        'conventional': '<span class="badge bg-primary">🔵 常规超导</span>',
        'unconventional': '<span class="badge bg-purple" style="background-color: #6f42c1;">🟣 非常规超导</span>',
        'unknown': '<span class="badge bg-secondary">⚪ 未知类型</span>'
    };
    const scTypeBadge = scTypeBadges[paper.superconductor_type] || '';

    // 审核状态徽章（从后端数据获取）
    const reviewBadge = paper.review_status === 'reviewed' ?
        `<span class="badge bg-success">✓ 已审核${paper.reviewer_name ? ` (${paper.reviewer_name})` : ''}</span>` :
        '<span class="badge bg-warning">⏳ 未审核</span>';

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
                            ${articleTypeBadge}
                            ${scTypeBadge}
                            ${reviewBadge}
                        </div>
                        <div>
                            <i class="bi bi-chevron-down" id="chevron-${paper.id}">▼</i>
                        </div>
                    </div>
                </div>

                <!-- 详细信息（默认隐藏） -->
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
                                ${paper.chemical_formula ? `<strong>化学式:</strong> ${paper.chemical_formula}<br>` : ''}
                                ${paper.crystal_structure ? `<strong>晶体结构:</strong> ${paper.crystal_structure}<br>` : ''}
                                <strong>DOI:</strong> <code>${paper.doi}</code>
                            </p>

                            ${paper.abstract ? `
                                <details>
                                    <summary class="text-primary" style="cursor: pointer;">查看摘要</summary>
                                    <p class="mt-2">${paper.abstract}</p>
                                </details>
                            ` : ''}

                            <div class="mt-3">
                                <strong>APS引用格式:</strong>
                                <div class="citation-box position-relative">
                                    ${paper.citation_aps}
                                    <button class="btn btn-sm btn-outline-primary copy-btn" onclick="copyCitation('${paper.id}', 'aps')">复制</button>
                                </div>
                            </div>

                            <div class="mt-3 text-muted small">
                                贡献者: ${paper.contributor_name} (${paper.contributor_affiliation}) |
                                提交时间: ${new Date(paper.created_at).toLocaleDateString('zh-CN')}
                            </div>
                        </div>

                        <!-- 右侧：第一张大图 -->
                        ${paper.image_count > 0 ? `
                        <div class="col-md-4">
                            <img src="/api/papers/${paper.id}/images/1"
                                 class="img-fluid paper-main-image"
                                 onclick="viewImage('/api/papers/${paper.id}/images/1')"
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

// 切换文献详情显示
function togglePaperDetails(paperId) {
    const details = document.getElementById(`details-${paperId}`);
    const chevron = document.getElementById(`chevron-${paperId}`);

    if (details.style.display === 'none') {
        details.style.display = 'block';
        chevron.textContent = '▲';
    } else {
        details.style.display = 'none';
        chevron.textContent = '▼';
    }
}

// 渲染其他截图（从第2张开始）
function renderOtherImages(paperId, count) {
    if (count <= 1) return '';

    let html = '';
    for (let i = 2; i <= count; i++) {
        html += `<img src="/api/papers/${paperId}/images/${i}?thumbnail=true"
                      class="paper-image-thumbnail"
                      onclick="viewImage('/api/papers/${paperId}/images/${i}')"
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
        html += `<img src="/api/papers/${paperId}/images/${i}?thumbnail=true"
                      class="paper-image-thumbnail"
                      onclick="viewImage('/api/papers/${paperId}/images/${i}')"
                      alt="截图${i}">`;
    }
    return html;
}

// 查看大图
function viewImage(imageUrl) {
    document.getElementById('modal-image').src = imageUrl;
    imageModal.show();
}

// 复制引用格式
async function copyCitation(paperId, format) {
    try {
        const response = await fetch('/api/papers/export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                format: format,
                paper_ids: [parseInt(paperId)]
            })
        });

        const text = await response.text();
        await navigator.clipboard.writeText(text);
        alert('引用格式已复制到剪贴板！');
    } catch (error) {
        console.error('复制失败:', error);
        alert('复制失败，请手动复制');
    }
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

    loadPapers(searchParams);
}

// 重置搜索
function resetSearch() {
    document.getElementById('keyword-input').value = '';
    document.getElementById('year-min-input').value = '';
    document.getElementById('year-max-input').value = '';
    loadPapers();
}

// 处理图片选择
function handleImageSelection(event) {
    const files = Array.from(event.target.files);

    if (files.length < 1 || files.length > 5) {
        alert('请选择1-5张图片');
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

// 加载晶体结构类型列表（用于自动补全）
async function loadCrystalStructures() {
    try {
        const response = await fetch('/api/papers/crystal-structures');
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

    if (selectedFiles.length < 1 || selectedFiles.length > 5) {
        alert('请上传1-5张文献截图');
        return;
    }

    // 构建FormData
    const formData = new FormData();
    formData.append('doi', doi);
    formData.append('element_symbols', JSON.stringify(elementSymbols.split('-')));
    formData.append('article_type', articleType.value);
    formData.append('superconductor_type', superconductorType);

    const formula = document.getElementById('formula-input').value.trim();
    if (formula) formData.append('chemical_formula', formula);

    const structure = document.getElementById('structure-input').value.trim();
    if (structure) formData.append('crystal_structure', structure);

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

    // 显示loading
    const submitBtn = event.target;
    submitBtn.disabled = true;
    submitBtn.textContent = '提交中...';

    try {
        const response = await fetch('/api/papers/', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            alert('文献上传成功！');
            uploadModal.hide();
            // 重置表单
            document.getElementById('uploadForm').reset();
            document.getElementById('image-preview').innerHTML = '';
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
        submitBtn.disabled = false;
        submitBtn.textContent = '提交';
    }
}
