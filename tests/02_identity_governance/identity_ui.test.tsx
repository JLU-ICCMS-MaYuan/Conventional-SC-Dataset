import React from 'react'
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

const baseUser = {
  id: 7,
  email: 'researcher@example.test',
  username: 'Researcher',
  username_change_allowed: true,
  role: 'user' as const,
  is_admin: false,
  is_superadmin: false,
  is_approved: true,
  is_email_verified: true,
  account_status: 'active' as const,
  avatar_url: null,
  created_at: null,
  approved_at: null,
}

let authState: any = {
  user: baseUser,
  token: 'test-token',
  loading: false,
  login: vi.fn(),
  register: vi.fn(),
  updateUsername: vi.fn(),
  replaceUser: vi.fn(),
  verifyEmail: vi.fn(),
  resendVerification: vi.fn(),
  logout: vi.fn(),
}

vi.mock('../../frontend/src/context/AuthContext', () => ({
  useAuth: () => authState,
  getStoredToken: () => 'test-token',
}))

import AppShell from '../../frontend/src/components/AppShell'
import AuthDialog from '../../frontend/src/components/AuthDialog'
import RoleRoute from '../../frontend/src/components/RoleRoute'

afterEach(() => {
  cleanup()
  authState = { ...authState, user: baseUser, loading: false, logout: vi.fn() }
})

describe('身份与工作台导航', () => {
  it('按当前角色显示左侧入口，头像菜单只保留退出登录', () => {
    render(<MemoryRouter initialEntries={['/account']}><Routes><Route element={<AppShell />}><Route path="/account" element={<div>账户内容</div>} /></Route></Routes></MemoryRouter>)
    const navigation = screen.getByRole('navigation', { name: '主导航' })
    expect(navigation).toHaveStyle({
      position: 'sticky',
      top: '72px',
      height: 'calc(100vh - 72px)',
      overflowY: 'auto',
    })
    expect(screen.getByRole('button', { name: '用户' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '打开账户菜单' }))
    expect(screen.getByRole('menuitem', { name: '退出登录' })).toBeInTheDocument()
    expect(screen.queryByText('用户中心')).not.toBeInTheDocument()
    expect(screen.queryByText(baseUser.email)).not.toBeInTheDocument()
  })

  it('普通用户访问超级管理员工作台得到 403', () => {
    render(<MemoryRouter><RoleRoute allow={['superadmin']}><div>超级管理员内容</div></RoleRoute></MemoryRouter>)
    expect(screen.getByText(/403/)).toBeInTheDocument()
    expect(screen.queryByText('超级管理员内容')).not.toBeInTheDocument()
  })

  it('超级管理员访问管理员地址会重定向到超级管理员工作台', () => {
    authState = { ...authState, user: { ...baseUser, role: 'superadmin', is_superadmin: true } }
    render(<MemoryRouter initialEntries={['/admin']}><Routes><Route path="/admin" element={<RoleRoute allow={['admin']} redirectSuperadminFromAdmin><div>管理员页</div></RoleRoute>} /><Route path="/superadmin" element={<div>超级管理员页</div>} /></Routes></MemoryRouter>)
    expect(screen.getByText('超级管理员页')).toBeInTheDocument()
  })
})

describe('注册入口', () => {
  it('取消注册审批选项并明确公开实名与十位密码', () => {
    render(<MemoryRouter><AuthDialog open onClose={() => {}} /></MemoryRouter>)
    fireEvent.click(screen.getByRole('tab', { name: '注册' }))
    expect(screen.getByLabelText('真实姓名（选填，填写后公开）')).toBeInTheDocument()
    expect(screen.getByText('至少 10 位')).toBeInTheDocument()
    expect(screen.queryByText(/申请成为管理员/)).not.toBeInTheDocument()
  })
})
