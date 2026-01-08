(function() {
    const TOKEN_KEY = 'auth_token';
    const USER_KEY = 'auth_user';

    function save(token, user) {
        if (!token || !user) {
            throw new Error('登录信息不完整');
        }
        localStorage.setItem(TOKEN_KEY, token);
        localStorage.setItem(USER_KEY, JSON.stringify(user));
    }

    function get() {
        const token = localStorage.getItem(TOKEN_KEY);
        const rawUser = localStorage.getItem(USER_KEY);
        if (!token || !rawUser) {
            return null;
        }
        try {
            return { token, user: JSON.parse(rawUser) };
        } catch (error) {
            console.warn('无法解析登录信息，已清理缓存', error);
            clear();
            return null;
        }
    }

    function clear() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
    }

    function ensureState() {
        return get();
    }

    window.authState = {
        save,
        get: ensureState,
        clear,
        isAdmin() {
            const state = get();
            return Boolean(state && state.user && state.user.is_admin);
        },
        isSuperAdmin() {
            const state = get();
            return Boolean(state && state.user && state.user.is_superadmin);
        }
    };
})();
