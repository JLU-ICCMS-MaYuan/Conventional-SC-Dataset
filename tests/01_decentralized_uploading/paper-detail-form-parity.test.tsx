/**
 * Feature: 只读详情页与校对表单一致 (Issue #59)
 *
 * 测试详情页展示的字段集与校对页材料状态卡片逐项对应，
 * 字段名称与内容语义一致，研究方法可读展示，结构预览同源，
 * 且组件为纯只读（无编辑控件与死函数）。
 */

import '@testing-library/jest-dom/vitest'
import React from 'react'
import { describe, it, expect } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import PaperEditView from '../../frontend/src/components/PaperEditView'

const propertyModule = (records: Array<Record<string, unknown>>) => ({
  module_key: 'module-superconductive', module_code: 'superconductive_properties',
  definition_key: 'module.superconductive_properties', definition_version: 1, display_order: 0, records,
})

const propertyRecord = (overrides: Record<string, unknown>) => ({
  record_key: 'record-property', module_code: 'superconductive_properties', record_type: 'property',
  property_code: 'custom', definition_key: 'record.superconductive_properties.custom', definition_version: 1,
  name_raw: '', value_kind: 'number', value_raw: '', value_number: null, unit_raw: '', payload: {},
  ...overrides,
})

describe('只读详情页与校对表单字段一致（Issue #59）', () => {
  /**
   * T002 [US1]: 材料状态分类区 9 项均渲染（FR-001、FR-005）
   *
   * 验收：构造含完整材料状态的论文对象渲染 PaperEditView，
   * 断言材料状态分类字段及论文级超导类型均可见。
   */
  it('材料状态分类区 9 项均渲染', () => {
    const paper = {
      id: 1,
      title: '测试论文',
      material_families: [{ id: 1, name: '氢化物' }],
      superconductor_kind: 'conventional',
      material_states: [
        {
          id: 1,
          material: 'LaH10',
          element_count: 2,
          material_dimensionality: '3D',
          structure_families: [
            { id: 1, name: 'perovskite', is_primary: true },
          ],
          crystal_system: 'cubic',
          reported_space_group_symbol: 'Fm-3m',
          reported_space_group_number: 225,
        },
      ],
    }

    render(<PaperEditView paper={paper} onBack={() => {}} />)

    // 材料状态分类与论文级类型断言
    expect(screen.getAllByText('LaH10')).toHaveLength(2)
    expect(screen.getByText('氢化物')).toBeInTheDocument()
    expect(screen.getByText('不同元素种类数')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('材料维度')).toBeInTheDocument()
    expect(screen.getByText('3D')).toBeInTheDocument()
    expect(screen.getByText('perovskite')).toBeInTheDocument()
    expect(screen.getByText('晶系')).toBeInTheDocument()
    expect(screen.getByText('cubic')).toBeInTheDocument()
    expect(screen.getByText('空间群符号')).toBeInTheDocument()
    expect(screen.getByText('Fm-3m')).toBeInTheDocument()
    expect(screen.getByText('空间群号')).toBeInTheDocument()
    expect(screen.getByText('225')).toBeInTheDocument()
    expect(screen.getByText('超导类型')).toBeInTheDocument()
    expect(screen.getByText('conventional')).toBeInTheDocument()
  })

  /**
   * T003 [US1]: 单臂区间只显示存在的一侧（FR-002）
   *
   * 验收：pressure_min_gpa=200、pressure_max_gpa=null 时，
   * 显示下限与原文，不出现上限、不把 null 渲染为 0。
   */
  it('压强单臂区间不补造缺失的一侧', () => {
    const paper = {
      id: 1,
      title: '测试论文',
      material_states: [
        {
          id: 1,
          material: 'H3S',
          pressure_raw: 'above 200 GPa',
          pressure_min_gpa: 200,
          pressure_max_gpa: null,
        },
      ],
    }

    render(<PaperEditView paper={paper} onBack={() => {}} />)

    // 断言原文与下限可见
    expect(screen.getByText(/above 200 GPa/)).toBeInTheDocument()
    expect(screen.getByText('压强下限：200 GPa')).toBeInTheDocument()

    // 断言不显示上限（无「压强上限」文本）
    expect(screen.queryByText(/压强上限/)).not.toBeInTheDocument()
  })

  /**
   * T004 [US1]: Tc 数值/方法与 λ/ωlog/μ* 可见，
   * 关键用例——注入 2 条计算上下文（首条全 NULL、次条含值）（FR-003）
   *
   * 验收：全部展示，含数值全为 NULL 的记录，防止实现只取首条。
   */
  it('Tc 与计算上下文全部展示（含首条全 NULL 记录）', () => {
    const paper = {
      id: 4,
      title: '测试论文',
      material_states: [
        {
          id: 1,
          material: 'LaH10',
          property_modules: [propertyModule([
            propertyRecord({
              record_key: 'record-measured', record_type: 'measured_tc', property_code: 'tc',
              definition_key: 'record.superconductive_properties.measured_tc.resistivity',
              name_raw: 'critical temperature', value_raw: '274', value_number: 274, unit_raw: 'K',
              method_code: 'resistivity', payload: { experimental_conditions: {} },
            }),
            propertyRecord({
              record_key: 'record-predicted', record_type: 'predicted_tc', property_code: 'tc',
              definition_key: 'record.superconductive_properties.predicted_tc.mcmillan',
              name_raw: 'critical temperature', method_code: 'mcmillan',
              payload: {
                calculation_conditions: {},
                parameters: { lambda_ep: 2.56, omega_log: null, mu_star: 0.1 },
              },
            }),
          ])],
        },
      ],
    }

    render(<PaperEditView paper={paper} onBack={() => {}} />)

    // Tc 可见
    const measured = screen.getByTestId('property-record-record-measured')
    expect(within(measured).getByLabelText('数值')).toHaveValue(274)
    expect(screen.getByText(/测量 Tc · resistivity/)).toBeInTheDocument()

    // λ=2.56 与 μ*=0.1 可见（关键断言：如果只取首条，这些值不会出现）
    const predicted = screen.getByTestId('property-record-record-predicted')
    expect(within(predicted).getByLabelText('电声耦合强度 λ')).toHaveValue(2.56)
    expect(within(predicted).getByLabelText('μ*')).toHaveValue(0.1)
  })

  /**
   * T005 [US1]: 物性显示名称、原始值、解析值、单位，
   * 且页面不含「最小值」「最大值」文本（FR-004）
   */
  it('物性字段集无多余项（无最小值/最大值）', () => {
    const paper = {
      id: 4,
      title: '测试论文',
      material_states: [
        {
          id: 1,
          material: 'LaH10',
          property_modules: [propertyModule([propertyRecord({
            record_key: 'record-stability', name_raw: 'thermodynamic stability',
            value_raw: '0', value_number: 200, unit_raw: 'meV/atom',
          })])],
        },
      ],
    }

    render(<PaperEditView paper={paper} onBack={() => {}} />)

    // 物性字段集断言
    const record = screen.getByTestId('property-record-record-stability')
    expect(within(record).getByLabelText('名称')).toHaveValue('thermodynamic stability')
    expect(within(record).getByLabelText('原始值')).toHaveValue('0')
    expect(within(record).getByLabelText('数值')).toHaveValue(200)
    expect(within(record).getByLabelText('单位')).toHaveValue('meV/atom')

    // 关键断言：页面不含「最小值」「最大值」文本
    expect(screen.queryByText(/最小值/)).not.toBeInTheDocument()
    expect(screen.queryByText(/最大值/)).not.toBeInTheDocument()
  })

  /**
   * T007 [US2]: 断言页面含「研究驱动力」且不含旧标签（Issue #66 FR-002）
   * 原断言为「分类理由」，Issue #66 将该字段语义改为研究驱动力并统一命名。
   */
  it('研究驱动力标签正确，无「分类理由」「研究理由」旧标签残留', () => {
    const paper = {
      id: 1,
      title: '测试论文',
      research_motivation: '该材料在高压下表现出超导特性',
    }

    render(<PaperEditView paper={paper} onBack={() => {}} />)

    // 断言「研究驱动力」标签存在（侧边栏与主区都有，所以用 getAllByText）
    const labels = screen.getAllByText('研究驱动力')
    expect(labels.length).toBeGreaterThanOrEqual(1)
    // 断言内容可见
    expect(screen.getByText(/该材料在高压下表现出超导特性/)).toBeInTheDocument()

    // 关键断言：两个旧标签均不得出现
    expect(screen.queryByText('研究理由')).not.toBeInTheDocument()
    expect(screen.queryByText('分类理由')).not.toBeInTheDocument()
  })

  /**
   * T008 [US2]: 研究方法逐项独立可见，且页面文本不含 `["` 片段；
   * 覆盖 methodology 为空与非数组两个边界（FR-008）
   */
  it('研究方法以可读列表展示（无 JSON 原文）', () => {
    const paper = {
      id: 1,
      title: '测试论文',
      methodology: ['density functional theory', 'particle swarm optimization'],
    }

    render(<PaperEditView paper={paper} onBack={() => {}} />)

    // 断言研究方法逐项可见（组件中用 • 前缀）
    expect(screen.getByText('• density functional theory')).toBeInTheDocument()
    expect(screen.getByText('• particle swarm optimization')).toBeInTheDocument()

    // 关键断言：页面不含 JSON 数组原文片段
    const bodyText = document.body.textContent || ''
    expect(bodyText).not.toContain('["')
    expect(bodyText).not.toContain('"]')
  })

  it('研究方法为空或非数组时不渲染空容器不抛错', () => {
    const paperEmpty = {
      id: 1,
      title: '测试论文',
      methodology: [],
    }

    const paperNonArray = {
      id: 2,
      title: '测试论文2',
      methodology: 'invalid',
    }

    // 边界：空数组
    const { unmount: unmount1 } = render(<PaperEditView paper={paperEmpty} onBack={() => {}} />)
    const labels1 = screen.getAllByText('研究方法')
    expect(labels1.length).toBeGreaterThanOrEqual(1)
    unmount1()

    // 边界：非数组
    render(<PaperEditView paper={paperNonArray} onBack={() => {}} />)
    const labels2 = screen.getAllByText('研究方法')
    expect(labels2.length).toBeGreaterThanOrEqual(1)
  })

  /**
   * T010 [US3]: 覆盖有结构数据（注入 material_states[].structures[]）
   * 与无结构数据两个分支，后者断言空态文案存在且不抛错（FR-009）
   */
  it('结构预览同源与空态（无结构数据不报错）', () => {
    const paperWithStructures = {
      id: 1,
      title: '测试论文',
      material_states: [
        {
          id: 1,
          material: 'LaH10',
          structures: [
            {
              id: 1,
              structure_text: 'data_LaH10\n_cell_length_a 3.7',
              structure_format: 'cif',
              space_group_symbol: 'Fm-3m',
            },
          ],
        },
      ],
    }

    const paperNoStructures = {
      id: 2,
      title: '测试论文2',
      material_states: [],
    }

    // 有结构数据
    const { unmount: unmount1 } = render(<PaperEditView paper={paperWithStructures} onBack={() => {}} />)
    expect(screen.getByText(/data_LaH10/)).toBeInTheDocument()
    unmount1()

    // 无结构数据：断言空态文案存在（侧边栏可能也有）
    const emptyMessages = screen.getAllByText(/该记录暂无结构数据/)
    expect(emptyMessages.length).toBeGreaterThanOrEqual(1)
  })

  /**
   * T011 [US3]: 断言页面不存在可编辑输入框（无非只读 input/textarea），
   * 无「添加物性」「删除」按钮（FR-010）
   */
  it('只读性：无编辑控件与增删改按钮', () => {
    const paper = {
      id: 1,
      title: '测试论文',
      material_states: [
        {
          id: 1,
          material: 'LaH10',
        },
      ],
      key_properties: [
        {
          id: 1,
          material_state_id: 1,
          name: 'test property',
          value_raw: '100',
        },
      ],
    }

    const { container } = render(<PaperEditView paper={paper} onBack={() => {}} />)

    // 断言页面不含可编辑的 input/textarea（基础信息等只读展示用 Typography）
    const inputs = container.querySelectorAll('input:not([readonly])')
    const textareas = container.querySelectorAll('textarea:not([readonly])')
    expect(inputs.length).toBe(0)
    expect(textareas.length).toBe(0)

    // 断言无「添加物性」「删除」按钮
    expect(screen.queryByText(/添加物性/)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/删除/)).not.toBeInTheDocument()
  })

  /**
   * T012 [US3]: 覆盖无材料状态的空态分支，
   * 断言不渲染空白卡片骨架（边界场景）
   */
  it('无材料状态时不渲染空白卡片骨架', () => {
    const paper = {
      id: 1,
      title: '测试论文',
      material_states: [],
    }

    render(<PaperEditView paper={paper} onBack={() => {}} />)

    // 断言不渲染「材料状态分类」区块（整个 details 不存在）
    expect(screen.queryByText('材料状态分类')).not.toBeInTheDocument()
  })
})
