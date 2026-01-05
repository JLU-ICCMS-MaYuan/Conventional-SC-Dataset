// 认证助手 - 处理用户登录状态和导航栏显示

function initUserNavbar() {
    const userNav = document.getElementById('user-nav');
    if (!userNav) return;

    // 检查普通用户登录状态
    const userToken = localStorage.getItem('user_token');
    const userInfoStr = localStorage.getItem('user_info');
    
    // 同时也检查管理员登录状态（管理员也可以作为普通用户使用）
    const adminToken = localStorage.getItem('admin_token');
    const adminUserStr = localStorage.getItem('admin_user');

    if (userToken && userInfoStr) {
        const userInfo = JSON.parse(userInfoStr);
        renderLoggedInNav(userNav, userInfo, 'user');
    } else if (adminToken && adminUserStr) {
        const adminInfo = JSON.parse(adminUserStr);
        renderLoggedInNav(userNav, adminInfo, 'admin');
    } else {
        renderLoggedOutNav(userNav);
    }
}

function renderLoggedInNav(container, user, type) {
    let adminLink = '';
    if (user.is_admin || type === 'admin') {
        adminLink = `<li><a class="dropdown-item" href="/admin/dashboard">管理面板</a></li>`;
    }

    container.innerHTML = `
        <div class="dropdown">
            <button class="btn btn-outline-light dropdown-toggle" type="button" id="userDropdown" data-bs-toggle="dropdown" aria-expanded="false">
                👤 ${user.real_name}
            </button>
            <ul class="dropdown-menu dropdown-menu-end shadow" aria-labelledby="userDropdown">
                <li><h6 class="dropdown-header">账户设置</h6></li>
                ${adminLink}
                <li><hr class="dropdown-divider"></li>
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
    localStorage.removeItem('user_token');
    localStorage.removeItem('user_info');
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    alert('已退出登录');
    window.location.reload();
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initUserNavbar);
