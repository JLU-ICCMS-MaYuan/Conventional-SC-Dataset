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

    // 同步更新管理员导航标签
    if (window.updateAdminNav) {
        window.updateAdminNav();
    }
}

function renderLoggedInNav(container, user) {
    const isAdmin = Boolean(user.is_admin);
    const isSuperAdmin = Boolean(user.is_superadmin);
    let adminLinks = '';
    if (isAdmin || isSuperAdmin) {
        adminLinks += `<li><a class="dropdown-item" href="#" onclick="switchPage('/admin/papers'); return false;">📄 文献管理</a></li>`;
    }
    if (isSuperAdmin) {
        adminLinks += `<li><a class="dropdown-item" href="#" onclick="switchPage('/admin/users'); return false;">👥 用户管理</a></li>`;
    }
    if (adminLinks) {
        adminLinks += '<li><hr class="dropdown-divider"></li>';
    }

    container.innerHTML = `
        <div class="dropdown">
            <button class="btn btn-outline-light dropdown-toggle" type="button" id="userDropdown" data-bs-toggle="dropdown" aria-expanded="false">
                👤 ${user.real_name}
            </button>
            <ul class="dropdown-menu dropdown-menu-end shadow" aria-labelledby="userDropdown">
                ${adminLinks}
                <li><a class="dropdown-item text-danger" href="#" onclick="handleLogout()">${I18N.t('common.logout')}</a></li>
            </ul>
        </div>
    `;
}

function renderLoggedOutNav(container) {
    container.innerHTML = `
        <div class="btn-group">
            <a href="/login" class="btn btn-outline-light">${I18N.t('login.submit')}</a>
            <a href="/register" class="btn btn-outline-light">${I18N.t('register.title')}</a>
        </div>
    `;
}

function handleLogout() {
    if (window.authState) {
        window.authState.clear();
    } else {
        localStorage.clear();
    }
    alert(I18N.t('auth.logged_out'));
    window.location.reload();
}

document.addEventListener('langChange', initUserNavbar);

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initUserNavbar);
