/**
 * Feature: 多行文本字段保留用户录入的换行 (Issue #65)
 *
 * 论文总结与核心发现由用户按「一个要点一行」录入，换行是内容结构而非排版噪声。
 * HTML 默认折叠空白符，缺少 white-space: pre-wrap 会把分条要点挤成一段连续文本。
 *
 * 详情页 PaperEditView 一直设了 pre-wrap，探索页与社区页此前没有——同一份数据
 * 三个页面呈现不一致。本测试对两个页面的两个字段各自固化该样式。
 */

import '@testing-library/jest-dom/vitest'
import React from 'react'
import { MemoryRouter } from 'react-router-dom'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ThemeProvider } from '@mui/material'

import SearchPage from '../../frontend/src/pages/SearchPage'
import theme from '../../frontend/src/theme'
import { api } from '../../frontend/src/lib/api'

vi.mock('../../frontend/src/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn().mockResolvedValue({ items: [], total: 0 }) },
}))

vi.mock('../../frontend/src/components/StructureViewer3D', () => ({
  default: () => <div data-testid="structure-viewer" />,
}))

const mockedApi = vi.mocked(api)

// Hg 论文（papers id=9）的真实字段：用户按行录入的分条要点
const SUMMARY = '1. Comm.120b｜1911-04-28\n2. Comm.122b｜1911-05-27'
const KEY_FINDING = '昂内斯利用新建成的液氦低温实验装置。\n1. 在 4.2 K 附近电阻陡峭突变\n2. 在 3 K 乃至 1.5 K 区间维持零电阻'

const HG_PAPER = {
  id: 9,
  title: 'Further experiments with liquid helium. V.',
  journal: 'Commun. Phys. Lab. Univ. Leiden',
  year: 1911,
  review_status: 'approved',
  summary: SUMMARY,
  key_finding: KEY_FINDING,
  methodology: '["电阻测量"]',
  key_properties: [],
  material_states: [],
}

beforeEach(() => {
  vi.clearAllMocks()
  mockedApi.get.mockResolvedValue(HG_PAPER)
})

afterEach(() => cleanup())

// 字号字重断言必须在项目主题下测量：MUI 默认 body2 是 14px，
// 项目主题覆盖为 13px、caption 为 12px/600。不套 ThemeProvider 会量到默认值。
const renderDetail = () =>
  render(
    <ThemeProvider theme={theme}>
      <MemoryRouter initialEntries={['/search?paper_id=9']}><SearchPage /></MemoryRouter>
    </ThemeProvider>,
  )

// Testing Library 默认会归一化空白符，多行文本因此匹配不到；关掉归一化才能按原文查找。
const findExact = (text: string) =>
  waitFor(() => screen.getByText(text, { normalizer: value => value }))

// 标签与正文的层级：标签是 caption(12px/600)，正文是 body2(13px/400)。
// 正文若落到默认 body1(14px) 且显式加粗，就会比自己的标签更大更粗，层级颠倒。
const px = (value: string) => parseFloat(value)

describe('探索页详情的正文字号字重不压过标签（Issue #69）', () => {
  it('核心发现正文不加粗', async () => {
    renderDetail()

    const node = await findExact(KEY_FINDING)
    const weight = getComputedStyle(node).fontWeight
    // 400 或 normal 都算未加粗；600/700/bold 视为加粗
    expect(['400', 'normal', '']).toContain(weight)
  })

  it('核心发现正文字号不大于「核心发现」标签', async () => {
    renderDetail()

    const body = await findExact(KEY_FINDING)
    const label = screen.getByText('核心发现')

    expect(px(getComputedStyle(body).fontSize)).toBeLessThanOrEqual(
      px(getComputedStyle(label).fontSize),
    )
  })

  it('核心发现与同区块的论文总结字号字重一致', async () => {
    renderDetail()

    const keyFinding = await findExact(KEY_FINDING)
    const summary = await findExact(SUMMARY)

    const styleOf = (node: Element) => {
      const style = getComputedStyle(node)
      return { fontSize: style.fontSize, fontWeight: style.fontWeight }
    }
    expect(styleOf(keyFinding)).toEqual(styleOf(summary))
  })
})

describe('探索页详情保留多行文本的换行（Issue #65）', () => {
  it('论文总结以 pre-wrap 渲染，分条要点不被挤成一段', async () => {
    renderDetail()

    const node = await findExact(SUMMARY)
    expect(getComputedStyle(node).whiteSpace).toBe('pre-wrap')
  })

  it('核心发现以 pre-wrap 渲染——用户按「一个要点一行」录入', async () => {
    renderDetail()

    const node = await findExact(KEY_FINDING)
    expect(getComputedStyle(node).whiteSpace).toBe('pre-wrap')
  })

  it('换行文本原样进入 DOM，不被前端改写为空格', async () => {
    renderDetail()

    const node = await findExact(KEY_FINDING)
    expect(node.textContent).toContain('\n')
    // 若换行被替换为空格，两个要点会紧邻同一行
    expect(node.textContent).not.toContain('突变 2.')
  })
})
