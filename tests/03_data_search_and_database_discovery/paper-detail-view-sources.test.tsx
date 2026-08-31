/**
 * Feature: 探索页与社区页的物性与结构读取来源 (Issue #65)
 *
 * 条件化科学数据模型把 Tc、计算参数、普通物性、晶体结构拆到四张表。
 * 本测试固化「跨来源汇总」的读取契约，防止再次退回只读 key_properties。
 *
 * 载荷取自单质超导 Hg（papers id=9，1911 Onnes 原始报告）的真实 API 响应：
 * key_properties 为空数组，Tc 4.2 K 在 tc_results，816 字节 CIF 在 structures。
 */

import { describe, it, expect } from 'vitest'
import {
  collectPropertyRows, collectStructures, viewerFormat,
} from '../../frontend/src/lib/paperDetailView'

// Hg 论文的真实响应切片：只报告 Tc 的实验论文，没有任何普通物性
const HG_PAPER = {
  id: 9,
  title: 'Further experiments with liquid helium. V.',
  key_properties: [],
  material_states: [
    {
      id: 50,
      material: 'Hg',
      state_kind: 'experimental',
      pressure_value_gpa: null,
      pressure_raw: null,
      temperature_value_k: null,
      tc_results: [
        {
          id: 90, result_kind: 'experimental', tc_value_k: 4.2, tc_min_k: null, tc_max_k: null,
          tc_method: 'experimental', tc_method_custom: null, uncertainty_k: null,
          value_raw: '4.2', unit_raw: 'K',
        },
      ],
      calculation_contexts: [],
      structures: [
        {
          id: 1, structure_format: 'cif', space_group_symbol: 'I4/mmm',
          space_group_number: 139, structure_text: 'data_image0\n_chemical_formula_sum "Hg3"\n',
        },
      ],
    },
  ],
}

describe('关键物性跨来源汇总（Issue #65）', () => {
  it('key_properties 为空但存在 Tc 时，物性表不得为空', () => {
    const rows = collectPropertyRows(HG_PAPER)

    expect(rows.length).toBeGreaterThan(0)
    const tc = rows.find(row => row.label === 'Tc')
    expect(tc).toBeDefined()
    expect(tc!.material).toBe('Hg')
    expect(tc!.value).toBe('4.2 K')
  })

  it('Tc 的判定方法作为备注展示，枚举值翻译为中文', () => {
    const tc = collectPropertyRows(HG_PAPER).find(row => row.label === 'Tc')!
    expect(tc.note).toContain('实验测量')
  })

  it('计算上下文的 λ、ωlog、μ* 各自成行，NULL 项不产生空行', () => {
    const rows = collectPropertyRows({
      key_properties: [],
      material_states: [{
        id: 1, material: 'LaH10', pressure_value_gpa: 200,
        tc_results: [],
        calculation_contexts: [
          { id: 7, lambda_ep: 3.41, omega_log_k: 1120, mu_star: null, calculation_code: 'QE' },
        ],
        structures: [],
      }],
    })

    const labels = rows.map(row => row.label)
    expect(labels).toContain('λ (电声耦合)')
    expect(labels).toContain('ωlog')
    // mu_star 为 NULL，不得产生行
    expect(labels).not.toContain('μ*')

    const omega = rows.find(row => row.label === 'ωlog')!
    expect(omega.value).toBe('1120 K')
    expect(omega.condition).toBe('200 GPa')
    expect(omega.note).toBe('QE')
  })

  it('普通物性仍然纳入，且按 material_state_id 回查条件', () => {
    const rows = collectPropertyRows({
      key_properties: [
        { id: 3, material_state_id: 1, material: 'LaH10', name: '形成焓', value_raw: '0', value_number: 200, unit: 'meV/atom' },
      ],
      material_states: [{ id: 1, material: 'LaH10', pressure_raw: '200 GPa', tc_results: [], calculation_contexts: [], structures: [] }],
    })

    expect(rows).toHaveLength(1)
    expect(rows[0].label).toBe('形成焓')
    expect(rows[0].value).toBe('200 meV/atom')
    expect(rows[0].condition).toBe('200 GPa')
  })

  it('Tc 排在普通物性之前——Tc 是超导论文的核心结论', () => {
    const rows = collectPropertyRows({
      key_properties: [
        { id: 3, material_state_id: 1, material: 'LaH10', name: '形成焓', value_raw: '10', unit: 'meV' },
      ],
      material_states: [{
        id: 1, material: 'LaH10',
        tc_results: [{ id: 1, tc_value_k: 250 }],
        calculation_contexts: [], structures: [],
      }],
    })

    expect(rows.map(row => row.label)).toEqual(['Tc', '形成焓'])
  })

  it('Tc 单臂区间不补造缺失的一端', () => {
    const onlyMin = collectPropertyRows({
      material_states: [{ id: 1, material: 'X', tc_results: [{ id: 1, tc_min_k: 200, tc_max_k: null }] }],
    })
    expect(onlyMin[0].value).toBe('≥ 200 K')

    const bothEnds = collectPropertyRows({
      material_states: [{ id: 1, material: 'X', tc_results: [{ id: 1, tc_min_k: 250, tc_max_k: 260 }] }],
    })
    expect(bothEnds[0].value).toBe('250–260 K')
  })

  it('论文无任何来源数据时返回空数组，不抛错', () => {
    expect(collectPropertyRows({ key_properties: [], material_states: [] })).toEqual([])
    expect(collectPropertyRows(null)).toEqual([])
    expect(collectPropertyRows(undefined)).toEqual([])
  })
})

describe('结构预览读取来源（Issue #65）', () => {
  it('从 material_states[].structures[] 提取，而非 key_properties', () => {
    const structures = collectStructures(HG_PAPER)

    expect(structures).toHaveLength(1)
    expect(structures[0].material).toBe('Hg')
    expect(structures[0].structure_format).toBe('cif')
    expect(structures[0].name_note).toBe('I4/mmm')
    expect(structures[0].structure_text).toContain('Hg3')
  })

  it('key_properties[].structure_text 是废弃字段，不得作为来源', () => {
    // 该字段在 Go 侧标记 gorm:"-"，从不落库；若实现回退到读它，此处会误报有结构
    const structures = collectStructures({
      key_properties: [{ id: 1, material: 'Hg', structure_text: 'data_fake' }],
      material_states: [],
    })

    expect(structures).toEqual([])
  })

  it('结构文本为空的记录被过滤掉', () => {
    const structures = collectStructures({
      material_states: [{
        id: 1, material: 'Hg',
        structures: [
          { id: 1, structure_text: '', structure_format: 'cif' },
          { id: 2, structure_text: '   ', structure_format: 'cif' },
          { id: 3, structure_text: 'data_real', structure_format: 'poscar' },
        ],
      }],
    })

    expect(structures).toHaveLength(1)
    expect(structures[0].structure_text).toBe('data_real')
  })

  it('缺少 structures 键或论文为空时返回空数组，不抛错', () => {
    expect(collectStructures({ material_states: [{ id: 1, material: 'Hg' }] })).toEqual([])
    expect(collectStructures(null)).toEqual([])
  })
})

describe('3Dmol 格式映射', () => {
  it('poscar 与 vasp 都映射为 vasp，其余回退 cif', () => {
    expect(viewerFormat('poscar')).toBe('vasp')
    expect(viewerFormat('vasp')).toBe('vasp')
    expect(viewerFormat('cif')).toBe('cif')
    expect(viewerFormat(null)).toBe('cif')
    expect(viewerFormat(undefined)).toBe('cif')
  })
})
