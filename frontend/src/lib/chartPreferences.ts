export const TC_FIELDS = [
  'experimental_tc',
  'anisotropic_eliashberg_tc',
  'isotropic_eliashberg_tc',
  'allen_dynes_tc',
  'mcmillan_tc',
] as const

export type TcField = typeof TC_FIELDS[number]

export const DEFAULT_TC_FIELD: TcField = 'experimental_tc'

export const TC_FIELD_LABELS: Record<TcField, string> = {
  experimental_tc: '实验 Tc',
  anisotropic_eliashberg_tc: '各向异性 Eliashberg Tc',
  isotropic_eliashberg_tc: '各向同性 Eliashberg Tc',
  allen_dynes_tc: 'Allen–Dynes Tc',
  mcmillan_tc: 'McMillan Tc',
}

export interface ChartPreferences {
  version: 1
  pressureTcField: TcField
  yearTcField: TcField
}

export const DEFAULT_CHART_PREFERENCES: ChartPreferences = {
  version: 1,
  pressureTcField: DEFAULT_TC_FIELD,
  yearTcField: DEFAULT_TC_FIELD,
}

export const chartPreferencesKey = (userId: number) =>
  `scwiki_chart_preferences:v1:${userId}`

export const isTcField = (value: unknown): value is TcField =>
  typeof value === 'string' && TC_FIELDS.includes(value as TcField)

export function readChartPreferences(userId: number): ChartPreferences {
  try {
    const raw = localStorage.getItem(chartPreferencesKey(userId))
    if (!raw) return DEFAULT_CHART_PREFERENCES
    const value = JSON.parse(raw) as Partial<ChartPreferences>
    if (value.version !== 1 || !isTcField(value.pressureTcField) || !isTcField(value.yearTcField)) {
      return DEFAULT_CHART_PREFERENCES
    }
    return { version: 1, pressureTcField: value.pressureTcField, yearTcField: value.yearTcField }
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
