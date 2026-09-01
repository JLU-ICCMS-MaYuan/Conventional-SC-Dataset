/**
 * Feature #74：固定枚举与分类家族名的双语展示（US2）
 * Spec: docs/specs/74-site-wide-i18n/spec.md（FR-008、FR-009、FR-010）
 *
 * - T027：七类枚举标签随语言切换，选中后提交值不变。
 * - T028：seed 家族显示英文名；自建家族（name_en 空）英文界面回退中文名，
 *         且不影响选择与提交。
 */

import '@testing-library/jest-dom/vitest'
import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import UploadTaskEditor from '../../frontend/src/components/UploadTaskEditor'
import ClassificationAutocomplete from '../../frontend/src/components/ClassificationAutocomplete'
import { LanguageProvider, useLanguage } from '../../frontend/src/context/LanguageContext'
import { familyName } from '../../frontend/src/lib/classifications'
import { api } from '../../frontend/src/lib/api'

vi.mock('../../frontend/src/lib/api', () => ({
  api: { get: vi.fn(), put: vi.fn(), post: vi.fn() },
}))

vi.mock('../../frontend/src/lib/classifications', async importOriginal => {
  const actual = await importOriginal<typeof import('../../frontend/src/lib/classifications')>()
  return {
    ...actual,
    loadClassificationCatalogs: vi.fn(async () => ({
      material_families: [
        { id: 1, name: '氢基超导体', name_zh: '氢基超导体', name_en: 'Hydrogen-based superconductor', aliases: ['hydride'] },
        { id: 2, name: '单质超导体', name_zh: '单质超导体', name_en: '', aliases: [] },
      ],
      structure_families: [],
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
    title: 'Hydrogen study', authors: [], paper_type: 'experimental',
    research_materials: ['LaH10'],
  },
  material_states: [
    {
      material: 'LaH10',
      material_family: { id: 1, name: '氢基超导体', status: 'confirmed' },
      structure_families: [], element_count: 2, material_dimensionality: 'unknown',
    },
  ],
  structure_candidates: [], classification_evidence: [], field_evidence: {},
}

/** 测试内切换语言的探针：与 LanguageProvider 同层渲染。 */
const LangToggle: React.FC = () => {
  const { lang, setLang } = useLanguage()
  return <button onClick={() => setLang(lang === 'zh' ? 'en' : 'zh')} data-testid="lang-toggle">{lang}</button>
}

const STORAGE_KEY = 'sc-wiki.language'

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

describe('T027：枚举标签随语言切换，提交值不变（FR-008）', () => {
  it('材料维度下拉：中文界面显示中文，切换英文后显示英文', async () => {
    render(
      <LanguageProvider>
        <LangToggle />
        <UploadTaskEditor taskId={'5'.repeat(32)} onSubmitted={vi.fn()} />
      </LanguageProvider>,
    )

    // 默认中文：标签与选项均为中文
    const zhDropdown = await screen.findByLabelText('材料维度')
    fireEvent.mouseDown(zhDropdown)
    expect(await screen.findByRole('option', { name: '三维' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: '未知' })).toBeInTheDocument()
    fireEvent.keyDown(document.body, { key: 'Escape' })

    // 切换英文：标签与选项立即变英文
    fireEvent.click(screen.getByTestId('lang-toggle'))
    const enDropdowns = await screen.findAllByLabelText('Material dimensionality')
    fireEvent.mouseDown(enDropdowns[0])
    expect(await screen.findByRole('option', { name: 'Three-dimensional' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Unknown' })).toBeInTheDocument()
  })

  it('英文界面选中枚举后提交的 value 与中文界面一致', async () => {
    localStorage.setItem(STORAGE_KEY, 'en')
    render(
      <LanguageProvider>
        <UploadTaskEditor taskId={'5'.repeat(32)} onSubmitted={vi.fn()} />
      </LanguageProvider>,
    )

    const dropdowns = await screen.findAllByLabelText('Material dimensionality')
    fireEvent.mouseDown(dropdowns[0])
    fireEvent.click(await screen.findByRole('option', { name: 'Three-dimensional' }))

    fireEvent.click(screen.getByRole('button', { name: 'Save now' }))
    await waitFor(() => expect(mockedApi.put).toHaveBeenCalledTimes(1))
    const saved = mockedApi.put.mock.calls[0][1] as typeof draft
    // 提交值必须是后端契约 value，而非英文标签
    expect(saved.material_states[0].material_dimensionality).toBe('three_dimensional')
  })
})

describe('T028：分类家族名按语言展示，缺英文名回退中文（FR-009、FR-010）', () => {
  it('familyName：中文取中文名，英文取英文名，英文缺失回退中文', () => {
    const seed = { name: '氢基超导体', name_zh: '氢基超导体', name_en: 'Hydrogen-based superconductor' }
    const selfBuilt = { name: '单质超导体', name_zh: '单质超导体', name_en: '' }
    expect(familyName(seed, 'zh')).toBe('氢基超导体')
    expect(familyName(seed, 'en')).toBe('Hydrogen-based superconductor')
    expect(familyName(selfBuilt, 'zh')).toBe('单质超导体')
    // 英文缺失回退中文名而非空白（FR-010）
    expect(familyName(selfBuilt, 'en')).toBe('单质超导体')
    expect(familyName(null, 'en')).toBe('')
  })

  it('英文界面下拉：seed 家族显示英文名，自建家族回退中文名且可选', async () => {
    localStorage.setItem(STORAGE_KEY, 'en')
    render(
      <LanguageProvider>
        <ClassificationAutocomplete
          label="Material family"
          options={[
            { id: 1, name: '氢基超导体', name_zh: '氢基超导体', name_en: 'Hydrogen-based superconductor', aliases: [] },
            { id: 2, name: '单质超导体', name_zh: '单质超导体', name_en: '', aliases: [] },
          ]}
          value={null}
          onChange={vi.fn()}
        />
      </LanguageProvider>,
    )

    fireEvent.mouseDown(screen.getByRole('combobox'))
    expect(await screen.findByText('Hydrogen-based superconductor')).toBeInTheDocument()
    // 自建家族无英文名：回退中文名，可辨认、可选
    expect(screen.getByText('单质超导体')).toBeInTheDocument()
  })
})
