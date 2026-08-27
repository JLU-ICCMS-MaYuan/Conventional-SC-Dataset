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
import { render, screen } from '@testing-library/react'
import PaperEditView from '../../frontend/src/components/PaperEditView'

describe('只读详情页与校对表单字段一致（Issue #59）', () => {
  /**
   * T002 [US1]: 材料状态分类区 9 项均渲染（FR-001、FR-005）
   *
   * 验收：构造含完整材料状态的论文对象渲染 PaperEditView，
   * 断言分类区 9 项均可见：材料、材料家族、元素种类数、材料维度、
   * 结构家族标签、晶系、空间群符号、空间群号、超导类型。
   */
  it('材料状态分类区 9 项均渲染', () => {
    const paper = {
      id: 1,
      title: '测试论文',
      material_states: [
        {
          id: 1,
          material: 'LaH10',
          material_family: { id: 1, name: '氢化物' },
          element_count: 2,
          material_dimensionality: '3D',
          structure_families: [
            { id: 1, name: 'perovskite', is_primary: true },
          ],
          crystal_system: 'cubic',
          reported_space_group_symbol: 'Fm-3m',
          reported_space_group_number: 225,
          superconductor_kind: 'conventional',
        },
      ],
    }

    render(<PaperEditView paper={paper} onBack={() => {}} />)

    // 分类区 9 项断言
    expect(screen.getByText('LaH10')).toBeInTheDocument()
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
          tc_results: [
            {
              id: 1,
              tc_value_k: 274,
              tc_method: 'resistivity',
            },
          ],
          calculation_contexts: [
            // 首条全 NULL——关键边界，防止只取首条
            {
              id: 1,
              lambda_ep: null,
              omega_log_k: null,
              mu_star: null,
            },
            // 次条含值
            {
              id: 2,
              lambda_ep: 2.56,
              omega_log_k: null,
              mu_star: 0.1,
            },
          ],
        },
      ],
    }

    render(<PaperEditView paper={paper} onBack={() => {}} />)

    // Tc 可见
    expect(screen.getByText(/274 K/)).toBeInTheDocument()
    expect(screen.getByText(/resistivity/)).toBeInTheDocument()

    // λ=2.56 与 μ*=0.1 可见（关键断言：如果只取首条，这些值不会出现）
    expect(screen.getByText(/2\.56/)).toBeInTheDocument()
    expect(screen.getByText(/0\.1/)).toBeInTheDocument()
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
        },
      ],
      key_properties: [
        {
          id: 1,
          material_state_id: 1,
          name: 'thermodynamic stability',
          name_raw: 'thermodynamic stability',
          value_raw: '0',
          value_number: 200,
          unit: 'meV/atom',
        },
      ],
    }

    render(<PaperEditView paper={paper} onBack={() => {}} />)

    // 物性字段集断言
    expect(screen.getByText(/thermodynamic stability/)).toBeInTheDocument()
    expect(screen.getByText(/原始值.*0/)).toBeInTheDocument()
    expect(screen.getByText(/解析值.*200/)).toBeInTheDocument()
    expect(screen.getByText(/meV\/atom/)).toBeInTheDocument()

    // 关键断言：页面不含「最小值」「最大值」文本
    expect(screen.queryByText(/最小值/)).not.toBeInTheDocument()
    expect(screen.queryByText(/最大值/)).not.toBeInTheDocument()
  })

  /**
   * T007 [US2]: 断言页面含「分类理由」且不含「研究理由」（FR-006、FR-007）
   */
  it('分类理由标签正确，无「研究理由」错配', () => {
    const paper = {
      id: 1,
      title: '测试论文',
      rationale: '该材料在高压下表现出超导特性',
    }

    render(<PaperEditView paper={paper} onBack={() => {}} />)

    // 断言「分类理由」标签存在（侧边栏与主区都有，所以用 getAllByText）
    const labels = screen.getAllByText('分类理由')
    expect(labels.length).toBeGreaterThanOrEqual(1)
    // 断言内容可见
    expect(screen.getByText(/该材料在高压下表现出超导特性/)).toBeInTheDocument()

    // 关键断言：页面不含「研究理由」标签
    expect(screen.queryByText('研究理由')).not.toBeInTheDocument()
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
