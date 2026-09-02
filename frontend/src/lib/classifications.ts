import { api } from './api'

export type ClassificationStatus = 'confirmed' | 'pending'

export interface ClassificationTerm {
  id: number
  name: string
  /** 规范中文名。目录接口在 `name` 之外增量返回，旧响应可能缺失。 */
  name_zh?: string
  /** 规范英文名。用户自建家族只写中文名，此项为空字符串。 */
  name_en?: string
  aliases: string[]
}

export interface ClassificationSelection {
  id: number | null
  name: string
  status: ClassificationStatus
}

/**
 * 带双语名的家族选择。Issue #76（FR-024）：管理端详情接口回传 name_zh/name_en，
 * 供 familyName 在英文界面显示规范英文名；上传链路的普通选择（无双语名）仍满足该形态。
 */
export interface FamilySelection extends ClassificationSelection {
  name_zh?: string
  name_en?: string
}

export interface StructureFamilySelection extends ClassificationSelection {
  is_primary: boolean
}

export type MaterialDimensionality =
  | 'zero_dimensional'
  | 'one_dimensional'
  | 'two_dimensional'
  | 'three_dimensional'
  | 'quasi_one_dimensional'
  | 'quasi_two_dimensional'
  | 'unknown'

export interface ClassificationCatalogs {
  material_families: ClassificationTerm[]
  structure_families: ClassificationTerm[]
  material_dimensionalities: Array<{ value: MaterialDimensionality; name: string }>
}

export const DEFAULT_MATERIAL_DIMENSIONALITIES: ClassificationCatalogs['material_dimensionalities'] = [
  { value: 'zero_dimensional', name: '零维' },
  { value: 'one_dimensional', name: '一维' },
  { value: 'two_dimensional', name: '二维' },
  { value: 'three_dimensional', name: '三维' },
  { value: 'quasi_one_dimensional', name: '准一维' },
  { value: 'quasi_two_dimensional', name: '准二维' },
  { value: 'unknown', name: '未知' },
]

let catalogPromise: Promise<ClassificationCatalogs> | null = null

export function loadClassificationCatalogs(): Promise<ClassificationCatalogs> {
  if (!catalogPromise) {
    catalogPromise = api.get<ClassificationCatalogs>('/api/classification-catalogs')
      .catch(error => {
        catalogPromise = null
        throw error
      })
  }
  return catalogPromise
}

export function refreshClassificationCatalogs(): Promise<ClassificationCatalogs> {
  catalogPromise = null
  return loadClassificationCatalogs()
}

export function selectionForTerm(term: ClassificationTerm): ClassificationSelection {
  return { id: term.id, name: term.name, status: 'confirmed' }
}

/**
 * 按语言取分类家族名。
 *
 * 英文缺失时回退中文名而非留空：用户自建家族只有中文名（后端 resolveMaterialFamily
 * 创建时不写 name_en），留空会使下拉项不可辨认。
 *
 * 论文叙述字段只有统一英文内容，不参与这里的双语取值与回退。
 */
export function familyName(
  term: { name_zh?: string; name_en?: string; name?: string } | null | undefined,
  lang: 'zh' | 'en',
): string {
  if (!term) return ''
  const zh = term.name_zh?.trim() || term.name?.trim() || ''
  if (lang === 'zh') return zh
  return term.name_en?.trim() || zh
}

export function pendingSelection(name: string): ClassificationSelection | null {
  const normalized = name.trim()
  return normalized ? { id: null, name: normalized, status: 'pending' } : null
}
