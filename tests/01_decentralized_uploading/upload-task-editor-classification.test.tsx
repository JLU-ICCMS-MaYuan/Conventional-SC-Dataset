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
  },
  material_states: [
    {
      material: 'LaH10',
      material_family: { id: 1, name: '氢基超导体', status: 'confirmed' },
      structure_families: [], element_count: 2, material_dimensionality: 'unknown',
    },
    {
      material: ' lah10 ',
      material_family: null,
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

describe('材料状态多维分类编辑', () => {
  it('保存维度、结构多选和唯一主项，并把分类应用到同一材料', async () => {
    render(<UploadTaskEditor taskId={'5'.repeat(32)} onSubmitted={vi.fn()} />)

    const elementCounts = await screen.findAllByLabelText('不同元素种类数')
    expect(elementCounts).toHaveLength(2)
    expect(elementCounts[0]).toHaveValue('2')
    expect(elementCounts[0]).toHaveAttribute('readonly')

    const dimensionalities = screen.getAllByLabelText('材料维度')
    fireEvent.mouseDown(dimensionalities[0])
    fireEvent.click(await screen.findByRole('option', { name: '三维' }))

    const structureInputs = screen.getAllByLabelText('结构家族（可多选）')
    fireEvent.change(structureInputs[0], { target: { value: '笼状' } })
    fireEvent.click(await screen.findByText('笼状结构'))
    fireEvent.change(structureInputs[0], { target: { value: '层状' } })
    fireEvent.click(await screen.findByText('层状结构'))

    const primarySelectors = screen.getAllByLabelText('主结构家族')
    fireEvent.mouseDown(primarySelectors[0])
    fireEvent.click(await screen.findByRole('option', { name: '层状结构' }))

    fireEvent.click(screen.getAllByRole('button', { name: '应用到同材料' })[0])
    fireEvent.click(screen.getByRole('button', { name: '立即保存' }))

    await waitFor(() => expect(mockedApi.put).toHaveBeenCalledTimes(1))
    const saved = mockedApi.put.mock.calls[0][1] as typeof draft
    expect(saved.material_states).toEqual([
      expect.objectContaining({
        element_count: 2,
        material_dimensionality: 'three_dimensional',
        structure_families: [
          { id: 10, name: '笼状结构', status: 'confirmed', is_primary: false },
          { id: 11, name: '层状结构', status: 'confirmed', is_primary: true },
        ],
      }),
      expect.objectContaining({
        material_family: { id: 1, name: '氢基超导体', status: 'confirmed' },
        material_dimensionality: 'three_dimensional',
        structure_families: [
          { id: 10, name: '笼状结构', status: 'confirmed', is_primary: false },
          { id: 11, name: '层状结构', status: 'confirmed', is_primary: true },
        ],
      }),
    ])
  })
})
