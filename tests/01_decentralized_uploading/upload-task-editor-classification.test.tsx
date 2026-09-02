import '@testing-library/jest-dom/vitest'
import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import UploadTaskEditor from '../../frontend/src/components/UploadTaskEditor'
import { api } from '../../frontend/src/lib/api'

vi.mock('../../frontend/src/lib/api', () => ({
  api: { get: vi.fn(), put: vi.fn(), post: vi.fn() },
}))

vi.mock('../../frontend/src/lib/classifications', async importOriginal => {
  const actual = await importOriginal<typeof import('../../frontend/src/lib/classifications')>()
  return {
    ...actual,
    loadClassificationCatalogs: vi.fn(async () => ({
      material_families: [{ id: 1, name: '氢基超导体', aliases: ['hydride'] }],
      structure_families: [
        { id: 10, name: '笼状结构', aliases: ['clathrate'] },
        { id: 11, name: '层状结构', aliases: ['layered'] },
      ],
      material_dimensionalities: [
        { value: 'three_dimensional', name: '三维' },
        { value: 'unknown', name: '未知' },
      ],
    })),
  }
})

vi.mock('../../frontend/src/components/StructureCandidatePanel', () => ({
  default: () => null,
}))

const mockedApi = vi.mocked(api)

const draft = {
  paper: {
    title: '氢化物研究', authors: [], paper_type: 'experimental',
    research_materials: ['LaH10'],
    material_families: [{ id: 1, name: '氢基超导体', status: 'confirmed' }],
  },
  material_states: [
    {
      material: 'LaH10',
      structure_families: [], element_count: 2, material_dimensionality: 'unknown',
    },
    {
      material: ' lah10 ',
      structure_families: [], element_count: 2, material_dimensionality: 'unknown',
    },
  ],
  structure_candidates: [], classification_evidence: [], field_evidence: {},
}

beforeEach(() => {
  mockedApi.get.mockResolvedValue({ ok: true, data: structuredClone(draft) })
  mockedApi.put.mockResolvedValue({ ok: true })
  mockedApi.post.mockResolvedValue({ ok: true, paper_id: 99, review_status: 'pending' })
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('论文级材料家族与材料状态多维分类编辑', () => {
  it('在论文级保存多个材料家族，状态级保留多选类型标签且不写主项标记', { timeout: 15000 }, async () => {
    render(<UploadTaskEditor taskId={'5'.repeat(32)} onSubmitted={vi.fn()} />)

    const elementCounts = await screen.findAllByLabelText('不同元素种类数')
    expect(elementCounts).toHaveLength(2)
    expect(elementCounts[0]).toHaveValue('2')
    expect(elementCounts[0]).not.toHaveAttribute('readonly')
    expect(screen.getAllByLabelText('材料家族')).toHaveLength(1)
    expect(screen.getByText('氢基超导体')).toBeVisible()

    const dimensionalities = screen.getAllByLabelText('材料维度')
    fireEvent.mouseDown(dimensionalities[0])
    fireEvent.click(await screen.findByRole('option', { name: '三维' }))

    expect(screen.queryByLabelText('主结构家族')).not.toBeInTheDocument()
    const structureInputs = screen.getAllByLabelText('更多类型标签（可以填写不止一个类型）')
    fireEvent.change(structureInputs[0], { target: { value: '笼状' } })
    fireEvent.click(await screen.findByText('笼状结构'))
    fireEvent.change(structureInputs[0], { target: { value: '层状' } })
    fireEvent.click(await screen.findByText('层状结构'))

    fireEvent.click(screen.getByRole('button', { name: '立即保存' }))

    await waitFor(() => expect(mockedApi.put).toHaveBeenCalledTimes(1))
    const saved = mockedApi.put.mock.calls[0][1] as typeof draft
    expect(saved.material_states).toEqual([
      expect.objectContaining({
        element_count: 2,
        material_dimensionality: 'three_dimensional',
        structure_families: [
          { id: 10, name: '笼状结构', status: 'confirmed', is_primary: false },
          { id: 11, name: '层状结构', status: 'confirmed', is_primary: false },
        ],
      }),
      expect.not.objectContaining({ material_family: expect.anything() }),
    ])
    expect(saved.paper.material_families).toEqual([
      { id: 1, name: '氢基超导体', status: 'confirmed' },
    ])
  })

  it('元素种类数可编辑，手动修改后保存带锁定标志与新值', async () => {
    render(<UploadTaskEditor taskId={'5'.repeat(32)} onSubmitted={vi.fn()} />)

    const elementCounts = await screen.findAllByLabelText('不同元素种类数')
    expect(elementCounts[0]).toHaveValue('2')
    expect(screen.getAllByText('自动计算，可手动修改')).toHaveLength(2)

    fireEvent.change(elementCounts[0], { target: { value: '5' } })
    fireEvent.click(screen.getByRole('button', { name: '立即保存' }))

    await waitFor(() => expect(mockedApi.put).toHaveBeenCalledTimes(1))
    const saved = mockedApi.put.mock.calls[0][1] as typeof draft
    expect(saved.material_states[0]).toEqual(expect.objectContaining({
      element_count: 5,
      element_count_locked: true,
    }))
    expect(saved.material_states[1]).toEqual(expect.objectContaining({ element_count: 2 }))
  })

  it('元素种类数输入非法值时即时提示且不写入草稿', async () => {
    render(<UploadTaskEditor taskId={'5'.repeat(32)} onSubmitted={vi.fn()} />)

    const elementCounts = await screen.findAllByLabelText('不同元素种类数')
    fireEvent.change(elementCounts[0], { target: { value: '0' } })
    expect(await screen.findByText('请输入 1–118 的整数')).toBeInTheDocument()

    fireEvent.change(elementCounts[0], { target: { value: '119' } })
    expect(screen.getByText('请输入 1–118 的整数')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '立即保存' }))
    await waitFor(() => expect(mockedApi.put).toHaveBeenCalledTimes(1))
    const saved = mockedApi.put.mock.calls[0][1] as typeof draft
    expect(saved.material_states[0]).toEqual(expect.objectContaining({ element_count: 2 }))
  })
})
