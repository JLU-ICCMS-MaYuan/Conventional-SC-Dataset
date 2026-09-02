/**
 * Feature #75-1：材料状态「材料」字段改名为「化学式」
 * Spec: docs/specs/75-chemical-formula-label/spec.md（FR-001、FR-003、FR-004、FR-008）
 *
 * - T004：上传校对页首个输入框标签在中文下为「化学式」、英文下为 Chemical formula。
 * - T005：填入化学式提交后请求体字段名仍为 material（接口契约不变）。
 * - T015：语义正确的标签（材料家族、材料维度、图表组合「材料名」）不被误改。
 */

import '@testing-library/jest-dom/vitest'
import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import UploadTaskEditor from '../../frontend/src/components/UploadTaskEditor'
import { LanguageProvider } from '../../frontend/src/context/LanguageContext'
import { api } from '../../frontend/src/lib/api'
import type { UploadDraft } from '../../frontend/src/lib/paperProcessing'

vi.mock('../../frontend/src/lib/api', () => ({
  api: { get: vi.fn(), put: vi.fn(), post: vi.fn() },
}))

vi.mock('../../frontend/src/lib/classifications', async importOriginal => {
  const actual = await importOriginal<typeof import('../../frontend/src/lib/classifications')>()
  return {
    ...actual,
    loadClassificationCatalogs: vi.fn(async () => ({
      material_families: [{ id: 1, name: '氢基超导体', aliases: ['hydride'] }],
      structure_families: [],
      material_dimensionalities: [{ value: 'unknown', name: '未知' }],
    })),
  }
})

vi.mock('../../frontend/src/components/StructureCandidatePanel', () => ({
  default: () => <div data-testid="structure-candidate-panel" />,
}))

const mockedApi = vi.mocked(api)

const draft: UploadDraft = {
  paper: {
    title: 'Hydrogen study', authors: [], paper_type: 'experimental',
    research_materials: ['LaH10'],
    material_families: [{ id: 1, name: '氢基超导体', status: 'confirmed' }],
  },
  material_states: [
    {
      material: 'LaH10',
      structure_families: [],
      element_count: 2,
      material_dimensionality: 'unknown',
      tc_results: [],
      properties: [],
    },
  ],
  structure_candidates: [], classification_evidence: [], field_evidence: {},
}

beforeEach(() => {
  localStorage.clear()
  mockedApi.get.mockResolvedValue({ ok: true, data: structuredClone(draft) })
  mockedApi.put.mockResolvedValue({ ok: true })
  mockedApi.post.mockResolvedValue({ ok: true, paper_id: 99, review_status: 'pending' })
})

afterEach(() => {
  cleanup()
  localStorage.clear()
  vi.clearAllMocks()
})

describe('T004/T005：上传校对页化学式标签（FR-001、FR-004）', () => {
  it('中文界面首个输入框标签为「化学式」', async () => {
    render(<UploadTaskEditor taskId={'a'.repeat(32)} onSubmitted={vi.fn()} />)
    expect(await screen.findByLabelText('化学式')).toBeVisible()
    expect(screen.queryByLabelText('材料')).not.toBeInTheDocument()
  })

  it('英文界面首个输入框标签为 Chemical formula', async () => {
    localStorage.setItem('sc-wiki.language', 'en')
    render(
      <LanguageProvider>
        <UploadTaskEditor taskId={'a'.repeat(32)} onSubmitted={vi.fn()} />
      </LanguageProvider>,
    )
    expect(await screen.findByLabelText('Chemical formula')).toBeVisible()
    expect(screen.queryByLabelText('Material')).not.toBeInTheDocument()
  })

  it('填入化学式保存后请求体字段名仍为 material', async () => {
    render(<UploadTaskEditor taskId={'b'.repeat(32)} onSubmitted={vi.fn()} />)

    const input = await screen.findByLabelText('化学式')
    fireEvent.change(input, { target: { value: 'H3S' } })
    fireEvent.click(screen.getByRole('button', { name: '立即保存' }))

    await waitFor(() => expect(mockedApi.put).toHaveBeenCalledTimes(1))
    const saved = mockedApi.put.mock.calls[0][1] as UploadDraft
    // 请求体契约不变：字段名仍是 material，值即化学式
    expect(saved.material_states[0].material).toBe('H3S')
  })
})

describe('T015：语义正确的标签不被误改（FR-008）', () => {
  it('「材料家族」「材料维度」字典值未变', async () => {
    const zhUpload = (await import('../../frontend/src/i18n/zh/upload')).default
    expect(zhUpload.materialFamilyField).toBe('材料家族')
    expect(zhUpload.materialDimensionalityField).toBe('材料维度')
  })

  it('图表组合编辑器的「材料名」标签未变', async () => {
    const zhShare = (await import('../../frontend/src/i18n/zh/share')).default
    expect(zhShare.materialNameLabel).toBe('材料名')
  })
})
