// 导航栏登录状态展示 & 通用登出

function getAuthStateSafely() {
    if (typeof window === 'undefined' || !window.authState) {
        return null;
    }
    return window.authState.get();
}

function initUserNavbar() {
    const userNav = document.getElementById('user-nav');
    if (!userNav) return;

    const state = getAuthStateSafely();
    if (state && state.user) {
        renderLoggedInNav(userNav, state.user);
    } else {
        renderLoggedOutNav(userNav);
    }
}

function renderLoggedInNav(container, user) {
    const isAdmin = Boolean(user.is_admin);
    const dashboardLink = isAdmin ? `<li><a class="dropdown-item" href="/admin/dashboard">管理面板</a></li>` : '';

    container.innerHTML = `
        <div class="dropdown">
            <button class="btn btn-outline-light dropdown-toggle" type="button" id="userDropdown" data-bs-toggle="dropdown" aria-expanded="false">
                👤 ${user.real_name}
            </button>
            <ul class="dropdown-menu dropdown-menu-end shadow" aria-labelledby="userDropdown">
                ${dashboardLink}
                <li><a class="dropdown-item text-danger" href="#" onclick="handleLogout()">退出登录</a></li>
            </ul>
        </div>
    `;
}

function renderLoggedOutNav(container) {
    container.innerHTML = `
        <div class="btn-group">
            <a href="/login" class="btn btn-outline-light">登录</a>
            <a href="/register" class="btn btn-light">注册</a>
        </div>
    `;
}

function handleLogout() {
    if (window.authState) {
        window.authState.clear();
    } else {
        localStorage.clear();
    }
    alert('已退出登录');
    window.location.reload();
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initUserNavbar);
