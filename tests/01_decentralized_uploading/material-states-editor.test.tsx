/**
 * Feature #76-4：材料状态编辑区抽成共享受控组件（FR-023）
 * Spec: docs/specs/76-review-scientific-data-editing/（R5、T017）
 *
 * - T017-1：readOnly 模式下组件不可编辑（编辑不触发 onChange、卡片恒展开、无折叠交互）。
 * - T017-2：传入 issues 时对应字段显示错误态（data-issue-field 锚点 + helperText 错误文案）。
 * - T017-3：交互后 onChange 回调传出**完整**状态数组（改化学式后数组含更新后的 material）。
 */

import '@testing-library/jest-dom/vitest'
import React from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import MaterialStatesEditor from '../../frontend/src/components/MaterialStatesEditor'
import type { DraftMaterialState } from '../../frontend/src/lib/paperProcessing'
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
      structure_families: [{ id: 10, name: '笼状结构', aliases: ['clathrate'] }],
      material_dimensionalities: [{ value: 'unknown', name: '未知' }],
    })),
  }
})

vi.mock('../../frontend/src/components/StructureCandidatePanel', () => ({
  default: () => <div data-testid="structure-candidate-panel" />,
}))

const makeState = (overrides: Partial<DraftMaterialState> = {}): DraftMaterialState => ({
  material: 'LaH10',
  material_family: null,
  structure_families: [],
  element_count: 2,
  material_dimensionality: 'unknown',
  tc_results: [],
  properties: [],
  ...overrides,
})

const renderEditor = (overrides: Partial<React.ComponentProps<typeof MaterialStatesEditor>> = {}) => {
  const onChange = vi.fn()
  const utils = render(
    <MaterialStatesEditor
      states={[makeState()]}
      onChange={onChange}
      catalogs={null}
      taskId={'5'.repeat(32)}
      {...overrides}
    />,
  )
  return { onChange, ...utils }
}

describe('MaterialStatesEditor 共享组件（T017）', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('readOnly 模式下不可编辑：编辑输入不触发 onChange，卡片恒展开且无折叠交互', () => {
    const { onChange } = renderEditor({
      readOnly: true,
      states: [makeState(), makeState({ material: 'H3S' }), makeState({ material: 'MgB2' })],
    })

    // 卡片数 >2 时默认折叠规则失效：readOnly 下恒展开
    expect(document.getElementById('material-state-0-content')).toHaveClass('MuiCollapse-entered')
    expect(document.getElementById('material-state-1-content')).toHaveClass('MuiCollapse-entered')
    expect(document.getElementById('material-state-2-content')).toHaveClass('MuiCollapse-entered')

    // 点击卡片头部不改变展开状态（不可折叠交互）
    const header = screen.getByRole('button', { name: /材料状态 #1/ })
    expect(header).toHaveAttribute('aria-expanded', 'true')
    fireEvent.click(header)
    expect(header).toHaveAttribute('aria-expanded', 'true')

    // 编辑输入不触达父级 onChange
    fireEvent.change(screen.getAllByLabelText('化学式')[0], { target: { value: 'H3S' } })
    expect(onChange).not.toHaveBeenCalled()
  })

  it('传入 issues 时对应字段显示错误态（data-issue-field 锚点与错误文案）', async () => {
    renderEditor({
      issues: [{ stateIndex: 0, field: 'material_states[0].material', message: '第 1 个材料状态缺少化学式' }],
    })

    const anchor = document.querySelector('[data-issue-field="material_states[0].material"]')
    expect(anchor).not.toBeNull()
    expect(anchor).toHaveTextContent('第 1 个材料状态缺少化学式')

    const input = await screen.findByLabelText('化学式')
    expect(input).toHaveAttribute('aria-invalid', 'true')
  })

  it('交互后 onChange 回调传出完整状态数组', () => {
    const { onChange } = renderEditor({ states: [makeState({ material: 'H3S' }), makeState()] })

    fireEvent.change(screen.getAllByLabelText('化学式')[1], { target: { value: 'MgB2' } })

    expect(onChange).toHaveBeenCalledTimes(1)
    const nextStates = onChange.mock.calls[0][0] as DraftMaterialState[]
    // 完整数组：长度不变，更新项含新化学式，未编辑项原样保留
    expect(nextStates).toHaveLength(2)
    expect(nextStates[0]).toEqual(expect.objectContaining({ material: 'H3S' }))
    expect(nextStates[1]).toEqual(expect.objectContaining({ material: 'MgB2', element_count: 2 }))
    expect(nextStates[0]).not.toBe(nextStates[1])
  })
})
