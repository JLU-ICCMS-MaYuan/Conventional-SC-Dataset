import React from 'react'
import { Autocomplete, TextField } from '@mui/material'
import {
  ClassificationSelection,
  ClassificationTerm,
  pendingSelection,
  selectionForTerm,
  familyName,
} from '../lib/classifications'
import { useLanguage } from '../context/LanguageContext'

interface ClassificationAutocompleteProps {
  label: string
  options: ClassificationTerm[]
  value: ClassificationSelection | null | undefined
  loading?: boolean
  error?: string
  onChange: (value: ClassificationSelection | null) => void
}

const ClassificationAutocomplete: React.FC<ClassificationAutocompleteProps> = ({
  label,
  options,
  value,
  loading = false,
  error,
  onChange,
}) => {
  const { lang, t } = useLanguage()
  // 目录内找不到时回退到 familyName 标签（而非裸 name）：管理端详情带入的 name_en
  // 使英文界面显示规范英文名（如 Elemental superconductor，FR-024）。
  const selected = value?.id == null
    ? value?.name || null
    : options.find(option => option.id === value.id) || (value ? familyName(value, lang) : null)

  return (
    <Autocomplete
      freeSolo
      options={options}
      value={selected}
      loading={loading}
      getOptionLabel={option => typeof option === 'string' ? option : familyName(option, lang)}
      isOptionEqualToValue={(option, candidate) => (
        typeof candidate !== 'string' && 'id' in candidate && option.id === candidate.id
      )}
      filterOptions={(catalogOptions, state) => {
        const needle = state.inputValue.trim().toLocaleLowerCase()
        if (!needle) return catalogOptions
        return catalogOptions.filter(option => (
          familyName(option, lang).toLocaleLowerCase().includes(needle)
          || option.name.toLocaleLowerCase().includes(needle)
          || (option.name_zh || '').toLocaleLowerCase().includes(needle)
          || (option.name_en || '').toLocaleLowerCase().includes(needle)
          || option.aliases.some(alias => alias.toLocaleLowerCase().includes(needle))
        ))
      }}
      onChange={(_, nextValue) => {
        if (typeof nextValue === 'string') onChange(pendingSelection(nextValue))
        else onChange(nextValue ? selectionForTerm(nextValue) : null)
      }}
      onInputChange={(_, inputValue, reason) => {
        if (reason === 'input') onChange(pendingSelection(inputValue))
      }}
      renderInput={params => (
        <TextField
          {...params}
          label={label}
          error={Boolean(error)}
          helperText={error || (value?.status === 'pending' ? t('common.pendingClassification') : undefined)}
        />
      )}
      slotProps={{
        paper: { sx: { maxWidth: 'calc(100vw - 24px)' } },
      }}
    />
  )
}

export default ClassificationAutocomplete
