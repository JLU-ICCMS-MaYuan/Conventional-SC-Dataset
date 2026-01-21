// 完整的118元素周期表数据（参考ptable.com布局）
const ELEMENTS_DATA = [
    // 第1周期
    { symbol: 'H', number: 1, row: 1, col: 1, category: 'nonmetal', exist: 'natural' },
    { symbol: 'He', number: 2, row: 1, col: 18, category: 'noble-gas', exist: 'natural' },

    // 第2周期
    { symbol: 'Li', number: 3, row: 2, col: 1, category: 'alkali-metal', exist: 'natural' },
    { symbol: 'Be', number: 4, row: 2, col: 2, category: 'alkaline-earth', exist: 'natural' },
    { symbol: 'B', number: 5, row: 2, col: 13, category: 'metalloid', exist: 'natural' },
    { symbol: 'C', number: 6, row: 2, col: 14, category: 'nonmetal', exist: 'natural' },
    { symbol: 'N', number: 7, row: 2, col: 15, category: 'nonmetal', exist: 'natural' },
    { symbol: 'O', number: 8, row: 2, col: 16, category: 'nonmetal', exist: 'natural' },
    { symbol: 'F', number: 9, row: 2, col: 17, category: 'halogen', exist: 'natural' },
    { symbol: 'Ne', number: 10, row: 2, col: 18, category: 'noble-gas', exist: 'natural' },

    // 第3周期
    { symbol: 'Na', number: 11, row: 3, col: 1, category: 'alkali-metal', exist: 'natural' },
    { symbol: 'Mg', number: 12, row: 3, col: 2, category: 'alkaline-earth', exist: 'natural' },
    { symbol: 'Al', number: 13, row: 3, col: 13, category: 'post-transition', exist: 'natural' },
    { symbol: 'Si', number: 14, row: 3, col: 14, category: 'metalloid', exist: 'natural' },
    { symbol: 'P', number: 15, row: 3, col: 15, category: 'nonmetal', exist: 'natural' },
    { symbol: 'S', number: 16, row: 3, col: 16, category: 'nonmetal', exist: 'natural' },
    { symbol: 'Cl', number: 17, row: 3, col: 17, category: 'halogen', exist: 'natural' },
    { symbol: 'Ar', number: 18, row: 3, col: 18, category: 'noble-gas', exist: 'natural' },

    // 第4周期
    { symbol: 'K', number: 19, row: 4, col: 1, category: 'alkali-metal', exist: 'natural' },
    { symbol: 'Ca', number: 20, row: 4, col: 2, category: 'alkaline-earth', exist: 'natural' },
    { symbol: 'Sc', number: 21, row: 4, col: 3, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Ti', number: 22, row: 4, col: 4, category: 'transition-metal', exist: 'natural' },
    { symbol: 'V', number: 23, row: 4, col: 5, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Cr', number: 24, row: 4, col: 6, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Mn', number: 25, row: 4, col: 7, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Fe', number: 26, row: 4, col: 8, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Co', number: 27, row: 4, col: 9, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Ni', number: 28, row: 4, col: 10, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Cu', number: 29, row: 4, col: 11, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Zn', number: 30, row: 4, col: 12, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Ga', number: 31, row: 4, col: 13, category: 'post-transition', exist: 'natural' },
    { symbol: 'Ge', number: 32, row: 4, col: 14, category: 'metalloid', exist: 'natural' },
    { symbol: 'As', number: 33, row: 4, col: 15, category: 'metalloid', exist: 'natural' },
    { symbol: 'Se', number: 34, row: 4, col: 16, category: 'nonmetal', exist: 'natural' },
    { symbol: 'Br', number: 35, row: 4, col: 17, category: 'halogen', exist: 'natural' },
    { symbol: 'Kr', number: 36, row: 4, col: 18, category: 'noble-gas', exist: 'natural' },

    // 第5周期
    { symbol: 'Rb', number: 37, row: 5, col: 1, category: 'alkali-metal', exist: 'natural' },
    { symbol: 'Sr', number: 38, row: 5, col: 2, category: 'alkaline-earth', exist: 'natural' },
    { symbol: 'Y', number: 39, row: 5, col: 3, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Zr', number: 40, row: 5, col: 4, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Nb', number: 41, row: 5, col: 5, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Mo', number: 42, row: 5, col: 6, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Tc', number: 43, row: 5, col: 7, category: 'transition-metal', exist: 'synthetic'},
    { symbol: 'Ru', number: 44, row: 5, col: 8, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Rh', number: 45, row: 5, col: 9, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Pd', number: 46, row: 5, col: 10, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Ag', number: 47, row: 5, col: 11, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Cd', number: 48, row: 5, col: 12, category: 'transition-metal', exist: 'natural' },
    { symbol: 'In', number: 49, row: 5, col: 13, category: 'post-transition', exist: 'natural' },
    { symbol: 'Sn', number: 50, row: 5, col: 14, category: 'post-transition', exist: 'natural' },
    { symbol: 'Sb', number: 51, row: 5, col: 15, category: 'metalloid', exist: 'natural' },
    { symbol: 'Te', number: 52, row: 5, col: 16, category: 'metalloid', exist: 'natural' },
    { symbol: 'I', number: 53, row: 5, col: 17, category: 'halogen', exist: 'natural' },
    { symbol: 'Xe', number: 54, row: 5, col: 18, category: 'noble-gas', exist: 'natural' },

    // 第6周期
    { symbol: 'Cs', number: 55, row: 6, col: 1, category: 'alkali-metal', exist: 'natural' },
    { symbol: 'Ba', number: 56, row: 6, col: 2, category: 'alkaline-earth', exist: 'natural' },
    { symbol: 'La-Lu', number: 57, row: 6, col: 3, category: 'lanthanide', exist: 'natural', radi: true },
    { symbol: 'Hf', number: 72, row: 6, col: 4, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Ta', number: 73, row: 6, col: 5, category: 'transition-metal', exist: 'natural' },
    { symbol: 'W', number: 74, row: 6, col: 6, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Re', number: 75, row: 6, col: 7, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Os', number: 76, row: 6, col: 8, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Ir', number: 77, row: 6, col: 9, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Pt', number: 78, row: 6, col: 10, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Au', number: 79, row: 6, col: 11, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Hg', number: 80, row: 6, col: 12, category: 'transition-metal', exist: 'natural' },
    { symbol: 'Tl', number: 81, row: 6, col: 13, category: 'post-transition', exist: 'natural' },
    { symbol: 'Pb', number: 82, row: 6, col: 14, category: 'post-transition', exist: 'natural' },
    { symbol: 'Bi', number: 83, row: 6, col: 15, category: 'post-transition', exist: 'natural' },
    { symbol: 'Po', number: 84, row: 6, col: 16, category: 'metalloid', exist: 'natural', radi: true },
    { symbol: 'At', number: 85, row: 6, col: 17, category: 'halogen', exist: 'natural', radi: true },
    { symbol: 'Rn', number: 86, row: 6, col: 18, category: 'noble-gas', exist: 'natural', radi: true },

    // 第7周期
    { symbol: 'Fr', number: 87, row: 7, col: 1, category: 'alkali-metal', exist: 'natural', radi: true },
    { symbol: 'Ra', number: 88, row: 7, col: 2, category: 'alkaline-earth', exist: 'natural', radi: true },
    { symbol: 'Ac-Lr', number: 89, row: 7, col: 3, category: 'actinide', exist: 'natural', radi: true },
    { symbol: 'Rf', number: 104, row: 7, col: 4, category: 'transition-metal', exist: 'synthetic', radi: true },
    { symbol: 'Db', number: 105, row: 7, col: 5, category: 'transition-metal', exist: 'synthetic', radi: true },
    { symbol: 'Sg', number: 106, row: 7, col: 6, category: 'transition-metal', exist: 'synthetic', radi: true },
    { symbol: 'Bh', number: 107, row: 7, col: 7, category: 'transition-metal', exist: 'synthetic', radi: true },
    { symbol: 'Hs', number: 108, row: 7, col: 8, category: 'transition-metal', exist: 'synthetic', radi: true },
    { symbol: 'Mt', number: 109, row: 7, col: 9, category: 'transition-metal', exist: 'synthetic', radi: true },
    { symbol: 'Ds', number: 110, row: 7, col: 10, category: 'transition-metal', exist: 'synthetic', radi: true },
    { symbol: 'Rg', number: 111, row: 7, col: 11, category: 'transition-metal', exist: 'synthetic', radi: true },
    { symbol: 'Cn', number: 112, row: 7, col: 12, category: 'transition-metal', exist: 'synthetic', radi: true },
    { symbol: 'Nh', number: 113, row: 7, col: 13, category: 'post-transition', exist: 'synthetic', radi: true },
    { symbol: 'Fl', number: 114, row: 7, col: 14, category: 'post-transition', exist: 'synthetic', radi: true },
    { symbol: 'Mc', number: 115, row: 7, col: 15, category: 'post-transition', exist: 'synthetic', radi: true },
    { symbol: 'Lv', number: 116, row: 7, col: 16, category: 'post-transition', exist: 'synthetic', radi: true },
    { symbol: 'Ts', number: 117, row: 7, col: 17, category: 'halogen', exist: 'synthetic', radi: true },
    { symbol: 'Og', number: 118, row: 7, col: 18, category: 'noble-gas', exist: 'synthetic', radi: true },

    // 镧系元素（La系，原子序数58-71）- 放在第9行
    { symbol: 'La', number: 57, row: 6, col: 3, category: 'lanthanide', exist: 'natural' },
    { symbol: 'Ce', number: 58, row: 9, col: 4, category: 'lanthanide', exist: 'natural' },
    { symbol: 'Pr', number: 59, row: 9, col: 5, category: 'lanthanide', exist: 'natural' },
    { symbol: 'Nd', number: 60, row: 9, col: 6, category: 'lanthanide', exist: 'natural' },
    { symbol: 'Pm', number: 61, row: 9, col: 7, category: 'lanthanide', exist: 'synthetic' },
    { symbol: 'Sm', number: 62, row: 9, col: 8, category: 'lanthanide', exist: 'natural' },
    { symbol: 'Eu', number: 63, row: 9, col: 9, category: 'lanthanide', exist: 'natural' },
    { symbol: 'Gd', number: 64, row: 9, col: 10, category: 'lanthanide', exist: 'natural' },
    { symbol: 'Tb', number: 65, row: 9, col: 11, category: 'lanthanide', exist: 'natural' },
    { symbol: 'Dy', number: 66, row: 9, col: 12, category: 'lanthanide', exist: 'natural' },
    { symbol: 'Ho', number: 67, row: 9, col: 13, category: 'lanthanide', exist: 'natural' },
    { symbol: 'Er', number: 68, row: 9, col: 14, category: 'lanthanide', exist: 'natural' },
    { symbol: 'Tm', number: 69, row: 9, col: 15, category: 'lanthanide', exist: 'natural' },
    { symbol: 'Yb', number: 70, row: 9, col: 16, category: 'lanthanide', exist: 'natural' },
    { symbol: 'Lu', number: 71, row: 9, col: 17, category: 'lanthanide', exist: 'natural' },

    // 锕系元素（Ac系，原子序数90-103）- 放在第10行
    { symbol: 'Ac', number: 89, row: 7, col: 3, category: 'actinide', exist: 'natural' },
    { symbol: 'Th', number: 90, row: 10, col: 4, category: 'actinide', exist: 'natural' },
    { symbol: 'Pa', number: 91, row: 10, col: 5, category: 'actinide', exist: 'natural' },
    { symbol: 'U', number: 92, row: 10, col: 6, category: 'actinide', exist: 'natural' },
    { symbol: 'Np', number: 93, row: 10, col: 7, category: 'actinide', exist: 'synthetic' },
    { symbol: 'Pu', number: 94, row: 10, col: 8, category: 'actinide', exist: 'synthetic' },
    { symbol: 'Am', number: 95, row: 10, col: 9, category: 'actinide', exist: 'synthetic', radi: true },
    { symbol: 'Cm', number: 96, row: 10, col: 10, category: 'actinide', exist: 'synthetic', radi: true },
    { symbol: 'Bk', number: 97, row: 10, col: 11, category: 'actinide', exist: 'synthetic', radi: true },
    { symbol: 'Cf', number: 98, row: 10, col: 12, category: 'actinide', exist: 'synthetic', radi: true },
    { symbol: 'Es', number: 99, row: 10, col: 13, category: 'actinide', exist: 'synthetic', radi: true },
    { symbol: 'Fm', number: 100, row: 10, col: 14, category: 'actinide', exist: 'synthetic', radi: true },
    { symbol: 'Md', number: 101, row: 10, col: 15, category: 'actinide', exist: 'synthetic', radi: true },
    { symbol: 'No', number: 102, row: 10, col: 16, category: 'actinide', exist: 'synthetic', radi: true },
    { symbol: 'Lr', number: 103, row: 10, col: 17, category: 'actinide', exist: 'synthetic', radi: true },
];

// 全局变量
let selectedElements = new Set();
const MODE_STORAGE_KEY = 'element_selection_mode';
let selectionMode = localStorage.getItem(MODE_STORAGE_KEY) || 'combination';

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    renderPeriodicTable();
    setupEventListeners();
    initSelectionModeControls();
});

// 渲染元素周期表
function renderPeriodicTable() {
    const container = document.getElementById('periodic-table');
    container.innerHTML = '';

    // 计算需要的网格尺寸（10行以容纳镧系和锕系）
    const maxRow = Math.max(...ELEMENTS_DATA.map(e => e.row));
    const maxCol = 18;

    // 创建网格（包含空白格子）
    const grid = [];
    for (let row = 1; row <= maxRow; row++) {
        for (let col = 1; col <= maxCol; col++) {
            const element = ELEMENTS_DATA.find(e => e.row === row && e.col === col);
            if (element) {
                grid.push(createElementDiv(element));
            } else {
                // 空白格子
                const emptyDiv = document.createElement('div');
                emptyDiv.className = 'element empty';
                grid.push(emptyDiv);
            }
        }
    }

    // 添加到容器
    grid.forEach(el => container.appendChild(el));
}

// 创建元素div
function createElementDiv(element) {
    const div = document.createElement('div');
    div.className = `element ${element.category}`;
    if (element.exist === 'synthetic') div.classList.add('synthetic');
    if (element.radi) div.classList.add('radioactive');
    
    div.dataset.symbol = element.symbol;
    div.dataset.number = element.number;

    div.innerHTML = `
        <div class="atomic-number">${element.number}</div>
        <div class="symbol">${element.symbol}</div>
    `;

    // 点击事件
    div.addEventListener('click', function() {
        toggleElementSelection(element.symbol);
    });

    return div;
}

// 切换元素选择状态
function toggleElementSelection(symbol) {
    if (selectedElements.has(symbol)) {
        selectedElements.delete(symbol);
        document.querySelector(`[data-symbol="${symbol}"]`).classList.remove('selected');
    } else {
        selectedElements.add(symbol);
        document.querySelector(`[data-symbol="${symbol}"]`).classList.add('selected');
    }

    updateSelectedDisplay();
}

// 更新已选元素显示
function updateSelectedDisplay() {
    const display = document.getElementById('selected-elements');
    const btn = document.getElementById('enter-compound-btn');

    if (selectedElements.size === 0) {
        display.textContent = '未选择';
        display.className = 'badge bg-secondary';
        btn.disabled = true;
    } else {
        const sortedElements = Array.from(selectedElements).sort();
        display.textContent = sortedElements.join(', ');
        display.className = 'badge bg-primary';
        btn.disabled = false;
    }
}

// 设置事件监听器
function setupEventListeners() {
    // 进入化合物页面按钮
    document.getElementById('enter-compound-btn').addEventListener('click', function() {
        if (selectedElements.size > 0) {
            enterCompoundPage();
        }
    });

    // 清除选择按钮
    document.getElementById('clear-selection-btn').addEventListener('click', function() {
        clearSelection();
    });

    // Enter键快捷键
    document.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && selectedElements.size > 0) {
            enterCompoundPage();
        }
    });
}

function initSelectionModeControls() {
    const modeRadios = document.querySelectorAll('input[name="selection-mode"]');
    let hasMatch = false;
    modeRadios.forEach(radio => {
        if (radio.value === selectionMode) {
            radio.checked = true;
            hasMatch = true;
        }
        radio.addEventListener('change', () => {
            if (radio.checked) {
                selectionMode = radio.value;
                localStorage.setItem(MODE_STORAGE_KEY, selectionMode);
            }
        });
    });

    if (!hasMatch) {
        selectionMode = 'combination';
        localStorage.setItem(MODE_STORAGE_KEY, selectionMode);
        const defaultRadio = document.getElementById('mode-combination');
        if (defaultRadio) defaultRadio.checked = true;
    }
}

// 进入化合物页面
function enterCompoundPage() {
    const elements = Array.from(selectedElements).sort();
    if (elements.length === 0) return;

    const params = new URLSearchParams();
    if (selectionMode) {
        params.set('mode', selectionMode);
    }
    const query = params.toString();
    const target = query ? `/compound/${elements.join('-')}?${query}` : `/compound/${elements.join('-')}`;
    window.location.href = target;
}

// 清除选择
function clearSelection() {
    selectedElements.clear();
    document.querySelectorAll('.element.selected').forEach(el => {
        el.classList.remove('selected');
    });
    updateSelectedDisplay();
}

/**
 * 触发快速上传文件选择
 */
function triggerFastUpload() {
    const auth = window.authState ? window.authState.get() : null;
    if (!auth || !auth.token) {
        if (confirm('只有注册用户可以批量上传文献。是否立即前往登录？')) {
            window.location.href = '/login';
        }
        return;
    }
    document.getElementById('fast-upload-input').click();
}

/**
 * 下载快速上传示例文件
 */
function downloadFastUploadExample() {
    window.location.href = '/api/papers/batch-upload-example';
}

/**
 * 处理选中的快速上传文件
 */
async function handleFastUpload(input) {
    const file = input.files[0];
    if (!file) return;

    const auth = window.authState ? window.authState.get() : null;
    const token = auth ? auth.token : null;

    if (!token) {
        alert('登录状态已失效，请重新登录');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    // 显示进度提示
    const originalBtn = document.getElementById('fastUploadDropdown');
    const originalHtml = originalBtn.innerHTML;
    originalBtn.disabled = true;
    originalBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> 上传中...';

    try {
        const response = await fetch('/api/papers/batch-upload', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            alert(`🎉 ${result.message}`);
            // 清除选中状态并重置输入框
            input.value = '';
            // 刷新页面数据
            window.location.reload();
        } else {
            alert(`❌ 上传失败: ${result.detail || JSON.stringify(result)}`);
        }
    } catch (error) {
        console.error('批量上传出错:', error);
        alert('❌ 网络请求失败，请检查连接');
    } finally {
        originalBtn.disabled = false;
        originalBtn.innerHTML = originalHtml;
    }
}
