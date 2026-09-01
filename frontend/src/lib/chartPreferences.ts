export const TC_FIELDS = [
  'experimental_tc',
  'anisotropic_eliashberg_tc',
  'isotropic_eliashberg_tc',
  'allen_dynes_tc',
  'mcmillan_tc',
] as const

export type TcField = typeof TC_FIELDS[number]

export const DEFAULT_TC_FIELD: TcField = 'experimental_tc'

// 标签用英文：与图表坐标轴、Eliashberg/Allen-Dynes/McMillan 等术语的英文语境一致。
// 键名是 tc_field 查询参数的一部分（API 契约 + 已存偏好），不随标签改动。
export const TC_FIELD_LABELS: Record<TcField, string> = {
  experimental_tc: 'Experimental Tc',
  anisotropic_eliashberg_tc: 'Anisotropic Eliashberg Tc',
  isotropic_eliashberg_tc: 'Isotropic Eliashberg Tc',
  allen_dynes_tc: 'Allen-Dynes Tc',
  mcmillan_tc: 'McMillan Tc',
}

// 材料家族多选：null 表示「全部」，即跟随目录，新增家族自动可见。
// 存具体 id 数组则表示用户显式选择过某个子集。
export type FamilySelection = number[] | null

export interface ChartPreferences {
  version: 2
  pressureTcField: TcField
  yearTcField: TcField
  pressureFamilies: FamilySelection
  yearFamilies: FamilySelection
}

export const DEFAULT_CHART_PREFERENCES: ChartPreferences = {
  version: 2,
  pressureTcField: DEFAULT_TC_FIELD,
  yearTcField: DEFAULT_TC_FIELD,
  pressureFamilies: null,
  yearFamilies: null,
}

// v2 加入家族多选。键名带版本号，v1 的旧值不会被读到，自然回落默认，无需迁移代码。
export const chartPreferencesKey = (userId: number) =>
  `scwiki_chart_preferences:v2:${userId}`

export const isTcField = (value: unknown): value is TcField =>
  typeof value === 'string' && TC_FIELDS.includes(value as TcField)

const isFamilySelection = (value: unknown): value is FamilySelection =>
  value === null
  || (Array.isArray(value) && value.every(item => typeof item === 'number' && Number.isFinite(item)))

export function readChartPreferences(userId: number): ChartPreferences {
  try {
    const raw = localStorage.getItem(chartPreferencesKey(userId))
    if (!raw) return DEFAULT_CHART_PREFERENCES
    const value = JSON.parse(raw) as Partial<ChartPreferences>
    if (
      value.version !== 2
      || !isTcField(value.pressureTcField) || !isTcField(value.yearTcField)
      || !isFamilySelection(value.pressureFamilies) || !isFamilySelection(value.yearFamilies)
    ) {
      return DEFAULT_CHART_PREFERENCES
    }
    return {
      version: 2,
      pressureTcField: value.pressureTcField,
      yearTcField: value.yearTcField,
      pressureFamilies: value.pressureFamilies,
      yearFamilies: value.yearFamilies,
    }
  } catch {
    return DEFAULT_CHART_PREFERENCES
  }
}

export function writeChartPreferences(userId: number, preferences: ChartPreferences) {
  localStorage.setItem(chartPreferencesKey(userId), JSON.stringify(preferences))
}

export function clearChartPreferences(userId: number) {
  localStorage.removeItem(chartPreferencesKey(userId))
}
