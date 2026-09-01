import '@testing-library/jest-dom/vitest'
import React from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import AppShell from '../../frontend/src/components/AppShell'
import { LanguageProvider, useLanguage } from '../../frontend/src/context/LanguageContext'

/**
 * Feature #74：顶栏中英文切换控件与语言偏好持久化
 * Spec: docs/specs/74-site-wide-i18n/spec.md（US1）
 * 契约: docs/specs/74-site-wide-i18n/contracts/i18n-frontend.md（F1、F6、F7）
 */

vi.mock('../../frontend/src/context/AuthContext', () => ({
  useAuth: () => ({ user: null, logout: vi.fn() }),
}))

vi.mock('../../frontend/src/components/AuthDialog', () => ({ default: () => null }))

const STORAGE_KEY = 'sc-wiki.language'

const renderShell = () => render(
  <MemoryRouter initialEntries={['/news']}>
    <LanguageProvider>
      <AppShell />
    </LanguageProvider>
  </MemoryRouter>,
)

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  cleanup()
  localStorage.clear()
  vi.restoreAllMocks()
})

describe('语言切换控件', () => {
  it('未选择过语言时默认中文，且中文侧为按下状态', () => {
    renderShell()
    const zhButton = screen.getByRole('button', { name: /切换为简体中文|中文/ })
    expect(zhButton).toHaveAttribute('aria-pressed', 'true')
  })

  it('控件是带无障碍标签的按钮组，两个按钮都可聚焦', () => {
    renderShell()
    const group = screen.getByRole('group', { name: /语言|language/i })
    expect(group).toBeInTheDocument()
    const buttons = screen.getAllByRole('button').filter(b => b.getAttribute('aria-pressed') !== null)
    expect(buttons).toHaveLength(2)
    // 仅靠颜色高亮对读屏用户不可达，aria-pressed 是必需项
    expect(buttons.filter(b => b.getAttribute('aria-pressed') === 'true')).toHaveLength(1)
    for (const button of buttons) expect(button).not.toBeDisabled()
  })

  it('点击 EN 后导航文案立即变为英文，无需刷新', async () => {
    const user = userEvent.setup()
    renderShell()
    expect(screen.getByRole('button', { name: '热点' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /切换为英文|English/i }))

    expect(screen.getByRole('button', { name: 'News' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '热点' })).not.toBeInTheDocument()
  })

  it('切换语言写入 localStorage', async () => {
    const user = userEvent.setup()
    renderShell()
    await user.click(screen.getByRole('button', { name: /切换为英文|English/i }))
    expect(localStorage.getItem(STORAGE_KEY)).toBe('en')
  })

  it('重新挂载后沿用已保存的语言', () => {
    localStorage.setItem(STORAGE_KEY, 'en')
    renderShell()
    expect(screen.getByRole('button', { name: 'News' })).toBeInTheDocument()
  })

  it('存储值非法时回退中文，不抛错', () => {
    localStorage.setItem(STORAGE_KEY, 'klingon')
    renderShell()
    expect(screen.getByRole('button', { name: '热点' })).toBeInTheDocument()
  })

  it('localStorage 读取抛异常时仍渲染且默认中文', () => {
    // 隐私模式或配额耗尽会使存取抛异常；未捕获会导致 Provider 初始化失败并白屏
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage disabled')
    })
    renderShell()
    expect(screen.getByRole('button', { name: '热点' })).toBeInTheDocument()
  })

  it('localStorage 写入抛异常时切换在当前会话内仍生效', async () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota exceeded')
    })
    const user = userEvent.setup()
    renderShell()
    await user.click(screen.getByRole('button', { name: /切换为英文|English/i }))
    expect(screen.getByRole('button', { name: 'News' })).toBeInTheDocument()
  })

  it('切换语言同步 document.documentElement.lang', async () => {
    const user = userEvent.setup()
    renderShell()
    expect(document.documentElement.lang).toBe('zh-CN')
    await user.click(screen.getByRole('button', { name: /切换为英文|English/i }))
    expect(document.documentElement.lang).toBe('en')
  })
})

describe('t() 文案解析', () => {
  const Probe: React.FC<{ tKey: string; vars?: Record<string, string | number> }> = ({ tKey, vars }) => {
    const { t } = useLanguage()
    return <span data-testid="out">{t(tKey, vars)}</span>
  }

  it('按点分键取值', () => {
    render(<LanguageProvider><Probe tKey="common.save" /></LanguageProvider>)
    expect(screen.getByTestId('out')).toHaveTextContent('保存')
  })

  it('替换 {name} 占位符', () => {
    render(<LanguageProvider><Probe tKey="enums.paperType.review" /></LanguageProvider>)
    expect(screen.getByTestId('out')).toHaveTextContent('综述文章')
  })

  it('两侧都缺键时返回键名本身，不抛错', () => {
    render(<LanguageProvider><Probe tKey="nonexistent.deep.key" /></LanguageProvider>)
    expect(screen.getByTestId('out')).toHaveTextContent('nonexistent.deep.key')
  })
})
