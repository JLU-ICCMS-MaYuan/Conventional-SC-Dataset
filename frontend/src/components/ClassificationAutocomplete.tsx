import React from 'react'
import { Autocomplete, TextField } from '@mui/material'
import {
  ClassificationSelection,
  ClassificationTerm,
  pendingSelection,
  selectionForTerm,
} from '../lib/classifications'

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
  const selected = value?.id == null
    ? value?.name || null
    : options.find(option => option.id === value.id) || value.name

  return (
    <Autocomplete
      freeSolo
      options={options}
      value={selected}
      loading={loading}
      getOptionLabel={option => typeof option === 'string' ? option : option.name}
      isOptionEqualToValue={(option, candidate) => (
        typeof candidate !== 'string' && 'id' in candidate && option.id === candidate.id
      )}
      filterOptions={(catalogOptions, state) => {
        const needle = state.inputValue.trim().toLocaleLowerCase()
        if (!needle) return catalogOptions
        return catalogOptions.filter(option => (
          option.name.toLocaleLowerCase().includes(needle)
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
          helperText={error || (value?.status === 'pending' ? '新名称，提交后由管理员确认' : undefined)}
        />
      )}
      slotProps={{
        paper: { sx: { maxWidth: 'calc(100vw - 24px)' } },
      }}
    />
  )
}

export default ClassificationAutocomplete
