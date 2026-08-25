import { api } from './api'

export type ClassificationStatus = 'confirmed' | 'pending'

export interface ClassificationTerm {
  id: number
  name: string
  aliases: string[]
}

export interface ClassificationSelection {
  id: number | null
  name: string
  status: ClassificationStatus
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

export function pendingSelection(name: string): ClassificationSelection | null {
  const normalized = name.trim()
  return normalized ? { id: null, name: normalized, status: 'pending' } : null
}
