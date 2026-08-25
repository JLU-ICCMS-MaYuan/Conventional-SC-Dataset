import '@testing-library/jest-dom/vitest'
import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import ClassificationGovernancePanel from '../../frontend/src/components/ClassificationGovernancePanel'
import { api } from '../../frontend/src/lib/api'


vi.mock('../../frontend/src/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), patch: vi.fn() },
}))

vi.mock('../../frontend/src/lib/classifications', () => ({
  loadClassificationCatalogs: vi.fn(async () => ({
    material_families: [
      { id: 1, name: '氢基超导体', aliases: ['hydride'] },
      { id: 3, name: '重费米子超导体', aliases: ['heavy fermion'] },
    ],
    structure_families: [{ id: 2, name: '笼状结构', aliases: ['clathrate'] }],
    material_dimensionalities: [{ value: 'unknown', name: '未知' }],
  })),
  refreshClassificationCatalogs: vi.fn(async () => ({
    material_families: [
      { id: 1, name: '氢基超导体', aliases: ['hydride'] },
      { id: 3, name: '重费米子超导体', aliases: ['heavy fermion'] },
    ],
    structure_families: [{ id: 2, name: '笼状结构', aliases: ['clathrate'] }],
    material_dimensionalities: [{ value: 'unknown', name: '未知' }],
  })),
}))

const mockedApi = vi.mocked(api)

beforeEach(() => {
  mockedApi.get.mockImplementation(async (path: string) => {
    if (path.startsWith('/api/admin/classification-proposals')) {
      return { items: [{ id: 7, dimension: 'material_family', raw_name: '高压氢化物', status: 'proposed' }] }
    }
    if (path === '/api/superadmin/classification-audits') return { items: [] }
    throw new Error(`unexpected GET ${path}`)
  })
  mockedApi.post.mockResolvedValue({ message: 'ok' })
  mockedApi.patch.mockResolvedValue({ message: 'ok' })
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('分类建议分级治理', () => {
  it('普通管理员可以把建议映射到已有目录，但不读取超级管理员审计', async () => {
    render(<ClassificationGovernancePanel isSuper={false} />)

    fireEvent.click(await screen.findByRole('button', { name: '处理建议' }))
    fireEvent.mouseDown(screen.getByLabelText('目标目录项'))
    fireEvent.click(await screen.findByRole('option', { name: '氢基超导体' }))
    fireEvent.change(screen.getByLabelText('处理原因'), { target: { value: '论文明确表述为氢化物' } })
    fireEvent.click(screen.getByRole('button', { name: '确认处理' }))

    await waitFor(() => expect(mockedApi.post).toHaveBeenCalledWith(
      '/api/admin/classification-proposals/7/map',
      { target_id: 1, reason: '论文明确表述为氢化物' },
    ))
    expect(mockedApi.get).not.toHaveBeenCalledWith('/api/superadmin/classification-audits')
    expect(screen.queryByText('材料家族目录')).not.toBeInTheDocument()
  })

  it('超级管理员可以选择映射、批准别名、创建正式项或拒绝', async () => {
    render(<ClassificationGovernancePanel isSuper />)

    fireEvent.click(await screen.findByRole('button', { name: '处理建议' }))
    fireEvent.mouseDown(screen.getByLabelText('处理方式'))

    expect(await screen.findByRole('option', { name: '映射到现有目录' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: '批准为现有项别名' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: '创建正式目录项' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: '拒绝建议' })).toBeInTheDocument()
    expect(mockedApi.get).toHaveBeenCalledWith('/api/superadmin/classification-audits')
  })

  it('超级管理员可以重命名、停用和合并正式目录项', async () => {
    render(<ClassificationGovernancePanel isSuper />)

    fireEvent.click(await screen.findByRole('button', { name: '管理氢基超导体' }))
    fireEvent.change(screen.getByLabelText('新的规范中文名'), { target: { value: '氢基高温超导体' } })
    fireEvent.change(screen.getByLabelText('新的规范英文名'), { target: { value: 'Hydrogen-based superconductor' } })
    fireEvent.change(screen.getByLabelText('修改原因'), { target: { value: '统一论文中的规范名称' } })
    fireEvent.click(screen.getByRole('button', { name: '保存目录项' }))

    await waitFor(() => expect(mockedApi.patch).toHaveBeenCalledWith(
      '/api/superadmin/classification-catalogs/material_family/1',
      {
        name: '氢基高温超导体',
        name_en: 'Hydrogen-based superconductor',
        reason: '统一论文中的规范名称',
      },
    ))

    fireEvent.click(await screen.findByRole('button', { name: '管理氢基超导体' }))
    fireEvent.change(screen.getByLabelText('修改原因'), { target: { value: '暂停新论文选用' } })
    fireEvent.click(screen.getByRole('button', { name: '停用目录项' }))

    await waitFor(() => expect(mockedApi.patch).toHaveBeenCalledWith(
      '/api/superadmin/classification-catalogs/material_family/1',
      { is_active: false, reason: '暂停新论文选用' },
    ))

    fireEvent.click(await screen.findByRole('button', { name: '管理氢基超导体' }))
    fireEvent.mouseDown(screen.getByLabelText('合并到'))
    fireEvent.click(await screen.findByRole('option', { name: '重费米子超导体' }))
    fireEvent.change(screen.getByLabelText('修改原因'), { target: { value: '清理重复目录项' } })
    fireEvent.click(screen.getByRole('button', { name: '合并目录项' }))

    await waitFor(() => expect(mockedApi.post).toHaveBeenCalledWith(
      '/api/superadmin/classification-catalogs/material_family/1/merge',
      { target_id: 3, reason: '清理重复目录项' },
    ))
  })
})
