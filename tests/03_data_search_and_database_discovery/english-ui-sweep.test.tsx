/**
 * Feature #74：英文界面全站巡检（SC-001、FR-021）
 * Spec: docs/specs/74-site-wide-i18n/spec.md（US1 验收场景 5）
 *
 * 英文模式下渲染各页面主视图，断言用户可见文本不出现中日韩字符。
 * Spec 允许的两类例外（论文原文、自建家族中文名回退）在本测试的
 * mock 数据中被刻意规避（数据一律英文、目录项带 name_en），
 * 因此任何中文出现都意味着界面文案漏翻译。
 *
 * 额外对英文字典做静态巡检：`dictionaries.en` 任意字符串值不得含中日韩字符。
 */

import '@testing-library/jest-dom/vitest'
import React from 'react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { cleanup, render, waitFor } from '@testing-library/react'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'

import { LanguageProvider } from '../../frontend/src/context/LanguageContext'
import { dictionaries } from '../../frontend/src/i18n'
import SearchPage from '../../frontend/src/pages/SearchPage'
import KnowledgeGraphPage from '../../frontend/src/pages/KnowledgeGraphPage'
import TcPredictPage from '../../frontend/src/pages/TcPredictPage'
import SharePage from '../../frontend/src/pages/share'
import NewsPage from '../../frontend/src/pages/NewsPage'
import UploadPage from '../../frontend/src/pages/UploadPage'
import RagPage from '../../frontend/src/pages/RagPage'
import PaperDetailPage from '../../frontend/src/pages/PaperDetailPage'
import AccountPage from '../../frontend/src/pages/AccountPage'
import PublicUserPage from '../../frontend/src/pages/PublicUserPage'
import AdminPage from '../../frontend/src/pages/AdminPage'
import NotFoundPage from '../../frontend/src/pages/NotFoundPage'

/* ── 共享 mock 状态（vi.hoisted 保证在 vi.mock 工厂中可用） ── */
const { authMock } = vi.hoisted(() => ({
  authMock: {
    user: null,
    logout: vi.fn(),
    replaceUser: vi.fn(),
    updateUsername: vi.fn(),
  },
}))

const PROFILE = {
  username: 'tester', role: 'admin', email_verified: true,
  username_change_allowed: false, affiliation: 'Test Lab', research_interests: [],
  avatar_url: '', real_name: 'Test User',
}

const PAPER = {
  id: 1, title: 'High-pressure superconductivity in lanthanum hydride',
  doi: '10.1038/s41586-000', journal: 'Nature', year: 2019,
  abstract: 'Test abstract in English.', review_status: 'approved',
  summary: 'English summary.', keywords_tags: ['hydride', 'high pressure'],
  methodology: ['particle swarm optimization'], key_finding: 'Tc reaches 250 K.',
  research_motivation: 'Search for room-temperature superconductors.',
  knowledge_graph_title: 'Discovery of Superconductivity in Mercury',
  material_states: [], key_properties: [],
}

vi.mock('../../frontend/src/lib/api', () => ({
  api: {
    get: vi.fn((url: string) => {
      if (url.includes('/api/classification-catalogs')) {
        return Promise.resolve({
          material_families: [{ id: 1, name: '氢基超导体', name_zh: '氢基超导体', name_en: 'Hydrogen-based superconductor', aliases: [] }],
          structure_families: [],
          material_dimensionalities: [],
        })
      }
      if (url.includes('/api/papers/stats/tc-pressure')) {
        return Promise.resolve({ items: [], total: 0, records: [] })
      }
      if (url.includes('/api/papers/stats/tc-year')) {
        return Promise.resolve({ items: [], total: 0, records: [] })
      }
      if (url.includes('/api/community/contributions')) {
        return Promise.resolve({
          upload_leaderboard: [], review_leaderboard: [], participant_count: 0,
          current_user: { upload: null, review: null },
        })
      }
      if (url.includes('/api/knowledge-graph/overview')) {
        return Promise.resolve({ nodes: [], edges: [], total_edges: 0 })
      }
      if (url.includes('/api/news/feed')) {
        return Promise.resolve({ items: [], total: 0, sources: [] })
      }
      if (url.includes('/api/news')) {
        return Promise.resolve([])
      }
      if (url.includes('/api/upload-tasks/')) {
        return Promise.resolve({ ok: false })
      }
      if (url.includes('/api/account/profile')) {
        return Promise.resolve(PROFILE)
      }
      if (url.includes('/api/users/')) {
        return Promise.resolve({ ...PROFILE, role: 'user' })
      }
      if (url.includes('/api/admin/papers/all')) {
        return Promise.resolve({ items: [], total: 0 })
      }
      if (url.includes('/api/admin/all-users')) {
        return Promise.resolve([])
      }
      if (url.includes('/api/admin/username-audit')) {
        return Promise.resolve([])
      }
      if (url.includes('/api/chart-groups')) {
        return Promise.resolve([])
      }
      if (url.includes('/api/superadmin/')) {
        return Promise.resolve([])
      }
      if (url.includes('/api/rag/papers/')) {
        return Promise.reject(new Error('not found'))
      }
      if (url.includes('/api/papers/')) {
        return Promise.resolve(PAPER)
      }
      return Promise.resolve({})
    }),
    post: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    put: vi.fn().mockResolvedValue({}),
    patch: vi.fn().mockResolvedValue({}),
    del: vi.fn().mockResolvedValue({}),
    download: vi.fn().mockResolvedValue(new Blob()),
    postStream: vi.fn().mockResolvedValue(new Response(JSON.stringify({}))),
  },
}))

vi.mock('../../frontend/src/context/AuthContext', () => ({
  useAuth: () => authMock,
  getStoredToken: () => null,
}))

vi.mock('../../frontend/src/components/StructureViewer3D', () => ({
  default: () => <div data-testid="structure-viewer" />,
}))

/* ── 中日韩字符判定：CJK 统一表意文字 + 扩展 A + 假名 + 谚文 ── */
const CJK_RE = /[\u3400-\u4dbf\u4e00-\u9fff\u3040-\u30ff\u31f0-\u31ff\uac00-\ud7af]/

// jsdom 不实现 ResizeObserver，recharts 的 ResponsiveContainer 需要它。
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as unknown as typeof ResizeObserver

// jsdom 不实现 Element.scrollTo（RagPage 的对话滚动）。
Element.prototype.scrollTo = (() => {}) as never

// vis-network 是 vite 预打包依赖，vi.mock 对预打包模块不生效，真实实现会初始化
// canvas——jsdom 没有 canvas 实现，给 2d context 一个最小可用桩即可让图谱页照常渲染。
const canvasCtx = new Proxy({} as Record<string, unknown>, {
  get: (target, prop: string) => {
    if (prop === 'measureText') return () => ({ width: 10 })
    if (prop === 'createLinearGradient') return () => ({ addColorStop: () => {} })
    if (prop === 'getImageData') return () => ({ data: [] })
    if (prop in target) return target[prop]
    return () => {}
  },
})
HTMLCanvasElement.prototype.getContext = (() => canvasCtx as unknown as CanvasRenderingContext2D) as never

const ORIGINAL_RECT = Element.prototype.getBoundingClientRect
beforeAll(() => {
  Element.prototype.getBoundingClientRect = function () {
    return { width: 800, height: 390, top: 0, left: 0, bottom: 390, right: 800, x: 0, y: 0, toJSON: () => ({}) } as DOMRect
  }
})

afterEach(() => {
  cleanup()
  localStorage.clear()
  vi.clearAllMocks()
  authMock.user = null
  Element.prototype.getBoundingClientRect = ORIGINAL_RECT
})

const renderEn = (ui: React.ReactNode) => render(
  <MemoryRouter initialEntries={['/']}>
    <LanguageProvider>{ui}</LanguageProvider>
  </MemoryRouter>,
)

/** 渲染后等待异步内容落定，再断言整页无中日韩字符。 */
const assertNoCjk = async () => {
  await waitFor(() => {
    const text = document.body.textContent || ''
    expect(text).not.toMatch(CJK_RE)
  }, { timeout: 5000 })
}

describe('英文字典静态巡检', () => {
  it('en 字典任意字符串值不含中日韩字符', () => {
    const walk = (node: unknown, path: string) => {
      if (typeof node === 'string') {
        expect(node).not.toMatch(CJK_RE)
        return
      }
      if (node && typeof node === 'object') {
        for (const [key, value] of Object.entries(node)) walk(value, `${path}.${key}`)
      }
    }
    walk(dictionaries.en, 'en')
  })
})

describe('英文界面全站巡检（SC-001）', () => {
  it('NewsPage / 快讯页无中日韩字符', async () => {
    localStorage.setItem('sc-wiki.language', 'en')
    renderEn(<NewsPage />)
    await assertNoCjk()
  })

  it('SearchPage / 探索页无中日韩字符', async () => {
    localStorage.setItem('sc-wiki.language', 'en')
    renderEn(<SearchPage />)
    await assertNoCjk()
  })

  it('KnowledgeGraphPage / 脉络页无中日韩字符', async () => {
    localStorage.setItem('sc-wiki.language', 'en')
    renderEn(<KnowledgeGraphPage />)
    await assertNoCjk()
  })

  it('SharePage / 社区页无中日韩字符', async () => {
    localStorage.setItem('sc-wiki.language', 'en')
    renderEn(<SharePage />)
    await assertNoCjk()
  })

  it('UploadPage / 上传页无中日韩字符', async () => {
    localStorage.setItem('sc-wiki.language', 'en')
    renderEn(<UploadPage />)
    await assertNoCjk()
  })

  it('RagPage / 对话页无中日韩字符', async () => {
    localStorage.setItem('sc-wiki.language', 'en')
    renderEn(<RagPage />)
    await assertNoCjk()
  })

  it('TcPredictPage / 预测页无中日韩字符', async () => {
    localStorage.setItem('sc-wiki.language', 'en')
    renderEn(<TcPredictPage />)
    await assertNoCjk()
  })

  it('PaperDetailPage / 论文详情页无中日韩字符', async () => {
    localStorage.setItem('sc-wiki.language', 'en')
    render(
      <MemoryRouter initialEntries={['/papers/1']}>
        <LanguageProvider>
          <Routes>
            <Route path="/papers/:id" element={<PaperDetailPage />} />
          </Routes>
        </LanguageProvider>
      </MemoryRouter>,
    )
    await assertNoCjk()
  })

  it('AccountPage / 账户中心页无中日韩字符', async () => {
    localStorage.setItem('sc-wiki.language', 'en')
    authMock.user = { username: 'tester', role: 'admin' }
    renderEn(<AccountPage />)
    await assertNoCjk()
  })

  it('PublicUserPage / 公开用户页无中日韩字符', async () => {
    localStorage.setItem('sc-wiki.language', 'en')
    render(
      <MemoryRouter initialEntries={['/users/tester']}>
        <LanguageProvider>
          <Routes>
            <Route path="/users/:username" element={<PublicUserPage />} />
          </Routes>
        </LanguageProvider>
      </MemoryRouter>,
    )
    await assertNoCjk()
  })

  it('AdminPage / 管理员工作台无中日韩字符', async () => {
    localStorage.setItem('sc-wiki.language', 'en')
    authMock.user = { username: 'admin', role: 'admin' }
    renderEn(<AdminPage />)
    await assertNoCjk()
  })

  it('NotFoundPage / 404 页无中日韩字符', async () => {
    localStorage.setItem('sc-wiki.language', 'en')
    renderEn(<NotFoundPage />)
    await assertNoCjk()
  })
})
