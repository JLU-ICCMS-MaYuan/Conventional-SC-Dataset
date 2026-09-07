/**
 * Feature: 探索页与社区页的物性与结构读取来源 (Issue #65)
 *
 * 统一物性模型把 Tc、计算参数和普通物性收敛为模块记录，晶体结构独立存储。
 * 本测试固化目标读取契约，防止再次退回读取旧物性字段。
 *
 * 载荷取自单质超导 Hg（papers id=9，1911 Onnes 原始报告）的真实 API 响应：
 * Tc 4.2 K 在 property_modules，816 字节 CIF 在 structures。
 */

import { describe, it, expect } from 'vitest'
import {
  collectPropertyRows, collectStructures, viewerFormat,
} from '../../frontend/src/lib/paperDetailView'

const moduleWith = (records: Array<Record<string, unknown>>) => ({
  module_key: 'module-superconductive',
  module_code: 'superconductive_properties',
  definition_key: 'module.superconductive_properties',
  definition_version: 1,
  display_order: 0,
  records,
})

const tcRecord = (overrides: Record<string, unknown> = {}) => ({
  record_key: 'record-tc',
  module_code: 'superconductive_properties',
  record_type: 'measured_tc',
  property_code: 'tc',
  definition_key: 'record.superconductive_properties.measured_tc.resistivity',
  definition_version: 1,
  name_raw: 'critical temperature',
  value_kind: 'number',
  value_raw: '4.2',
  value_number: 4.2,
  unit_raw: 'K',
  method_code: 'resistivity',
  payload: { experimental_conditions: {} },
  ...overrides,
})

const propertyRecord = (overrides: Record<string, unknown> = {}) => ({
  record_key: 'record-property',
  module_code: 'superconductive_properties',
  record_type: 'property',
  property_code: 'custom',
  definition_key: 'record.superconductive_properties.custom',
  definition_version: 1,
  name_raw: '形成焓',
  value_kind: 'number',
  value_raw: '0',
  value_number: 200,
  unit_raw: 'meV/atom',
  payload: {},
  ...overrides,
})

// Hg 论文的目标响应切片：只报告 Tc 的实验论文，没有任何普通物性
const HG_PAPER = {
  id: 9,
  title: 'Further experiments with liquid helium. V.',
  material_states: [
    {
      id: 50,
      material: 'Hg',
      state_kind: 'experimental',
      pressure_value_gpa: null,
      pressure_raw: null,
      temperature_value_k: null,
      property_modules: [moduleWith([tcRecord()])],
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
  it('普通物性为空但存在 Tc 时，物性表不得为空', () => {
    const rows = collectPropertyRows(HG_PAPER)

    expect(rows.length).toBeGreaterThan(0)
    const tc = rows.find(row => row.label === 'Tc')
    expect(tc).toBeDefined()
    expect(tc!.material).toBe('Hg')
    expect(tc!.value).toBe('4.2 K')
  })

  it('Tc 的判定方法作为备注展示，枚举值翻译为中文', () => {
    const tc = collectPropertyRows(HG_PAPER).find(row => row.label === 'Tc')!
    expect(tc.note).toContain('电阻法')
  })

  it('计算上下文的 λ、ωlog、μ* 各自成行，NULL 项不产生空行', () => {
    const rows = collectPropertyRows({
      key_properties: [],
      material_states: [{
        id: 1, material: 'LaH10', pressure_value_gpa: 200,
        property_modules: [moduleWith([tcRecord({
          record_key: 'record-predicted', record_type: 'predicted_tc', method_code: 'allen_dynes',
          definition_key: 'record.superconductive_properties.predicted_tc.allen_dynes',
          payload: {
            calculation_conditions: { calculation_code: 'QE' },
            parameters: { lambda_ep: 3.41, omega_log: 1120, mu_star: null },
          },
        })])],
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
      material_states: [{
        id: 1, material: 'LaH10', pressure_raw: '200 GPa',
        property_modules: [moduleWith([propertyRecord()])], structures: [],
      }],
    })

    expect(rows).toHaveLength(1)
    expect(rows[0].label).toBe('形成焓')
    expect(rows[0].value).toBe('200 meV/atom')
    expect(rows[0].condition).toBe('200 GPa')
  })

  it('Tc 排在普通物性之前——Tc 是超导论文的核心结论', () => {
    const rows = collectPropertyRows({
      material_states: [{
        id: 1, material: 'LaH10',
        property_modules: [moduleWith([
          propertyRecord({ value_raw: '10', value_number: null, unit_raw: 'meV' }),
          tcRecord({ value_raw: '250', value_number: 250 }),
        ])],
        structures: [],
      }],
    })

    expect(rows.map(row => row.label)).toEqual(['Tc', '形成焓'])
  })

  it('Tc 单臂区间不补造缺失的一端', () => {
    const onlyMin = collectPropertyRows({
      material_states: [{ id: 1, material: 'X', property_modules: [moduleWith([tcRecord({ value_kind: 'range', value_number: null, value_min: 200, value_max: null })])] }],
    })
    expect(onlyMin[0].value).toBe('≥ 200 K')

    const bothEnds = collectPropertyRows({
      material_states: [{ id: 1, material: 'X', property_modules: [moduleWith([tcRecord({ value_kind: 'range', value_number: null, value_min: 250, value_max: 260 })])] }],
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
