/**
 * Feature: 探索页默认不预选元素、论文总结保留换行 (Issue #65)
 *
 * 默认选中 La/H 会把检索静默限定在氢化物体系，用户未必察觉自己并非在做全库检索。
 */

import '@testing-library/jest-dom/vitest'
import React from 'react'
import { MemoryRouter } from 'react-router-dom'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import SearchPage from '../../frontend/src/pages/SearchPage'

vi.mock('../../frontend/src/lib/api', () => ({
  api: { get: vi.fn().mockResolvedValue({}), post: vi.fn().mockResolvedValue({ items: [], total: 0 }) },
}))

vi.mock('../../frontend/src/components/StructureViewer3D', () => ({
  default: () => <div data-testid="structure-viewer" />,
}))

afterEach(() => cleanup())

const renderAt = (path: string) =>
  render(<MemoryRouter initialEntries={[path]}><SearchPage /></MemoryRouter>)

describe('探索页元素默认选中（Issue #65）', () => {
  it('无 URL 参数进入探索页时不预选任何元素', () => {
    renderAt('/search')

    expect(screen.getByText('未选择')).toBeInTheDocument()
    // 此前兜底为 'La,H'，会渲染成「H, La」
    expect(screen.queryByText('H, La')).not.toBeInTheDocument()
  })

  it('Formula 输入框默认为空，不预填 LaH', () => {
    renderAt('/search')

    const formulaInput = screen.getByRole('textbox')
    expect(formulaInput).toHaveValue('')
  })

  it('URL 显式带 elements 参数时仍按参数预选', () => {
    renderAt('/search?elements=Nb,Ti')

    // 显式传参是用户主动选择，须保留
    expect(screen.queryByText('未选择')).not.toBeInTheDocument()
  })
})
