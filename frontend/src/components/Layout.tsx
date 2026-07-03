import React from 'react'
import { Button, Separator } from '@heroui/react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useI18n } from '../context/I18nContext'

const navItems = [
  { to: '/', labelKey: 'nav.hotspot' },
  { to: '/elements', labelKey: 'nav.explore' },
  { to: '/share', labelKey: 'nav.share' },
  { to: '/rag', labelKey: 'nav.chat' },
  { to: '/tc-pre', labelKey: 'nav.predict' },
]

const adminItems = [
  { to: '/admin/dashboard', labelKey: 'nav.admin_dashboard' },
  { to: '/admin/papers', labelKey: 'nav.admin_papers' },
  { to: '/admin/users', labelKey: 'nav.admin_users' },
]

const Layout: React.FC = () => {
  const { user, logout } = useAuth()
  const { t, toggleLang } = useI18n()
  const navigate = useNavigate()

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">SC</div>
          <div>
            <div className="brand-title">{t('nav.title')}</div>
            <div className="brand-subtitle">{t('nav.subtitle')}</div>
          </div>
        </div>
        <nav className="nav-list">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === '/'} className="contents">
              {({ isActive }) => (
                <Button
                  className="nav-item"

                  variant={isActive ? 'secondary' : 'ghost'}

                  fullWidth
                >
                  {t(item.labelKey)}
                </Button>
              )}
            </NavLink>
          ))}
        </nav>
        {user && (
          <div className="admin-nav">
            <div className="admin-nav-title">{t('nav.admin')}</div>
            <nav className="nav-list compact">
              {adminItems.map((item) => (
                <NavLink key={item.to} to={item.to} className="contents">
                  {({ isActive }) => (
                    <Button
                      className="nav-item"

                      variant={isActive ? 'secondary' : 'ghost'}

                      fullWidth
                    >
                      {t(item.labelKey)}
                    </Button>
                  )}
                </NavLink>
              ))}
            </nav>
          </div>
        )}
        <div className="grid sidebar-footer">
          <Separator />
          <Button variant="outline"  onPress={toggleLang}>{t('common.language')}</Button>
          {user ? (
            <>
              <div className="muted">{user.username || user.email}</div>
              <Button variant="outline"  onPress={() => { logout(); navigate('/') }}>{t('common.logout')}</Button>
            </>
          ) : (
            <Button variant="outline"  onPress={() => navigate('/login')}>{t('common.login')}</Button>
          )}
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}

export default Layout
