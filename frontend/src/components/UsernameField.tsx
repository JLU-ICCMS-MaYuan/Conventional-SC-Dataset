import React, { useState } from 'react'
import { TextField } from '@mui/material'
import { checkUsernameAvailability, usernameValidationError } from '../lib/username'
import { useLanguage } from '../context/LanguageContext'

interface Props {
  value: string
  onChange: (value: string) => void
  label?: string
  autoFocus?: boolean
  disabled?: boolean
}

// username.ts 返回的本地校验机器键；服务器返回的 reason 为后端文案，
// 一律回退到 taken 展示（本地校验已先行拦截 format/sc_prefix/reserved）。
const MACHINE_ERROR_KEYS = ['format', 'sc_prefix', 'reserved'] as const
type MachineErrorKey = typeof MACHINE_ERROR_KEYS[number]
const isMachineErrorKey = (key: string): key is MachineErrorKey =>
  (MACHINE_ERROR_KEYS as readonly string[]).includes(key)

const UsernameField: React.FC<Props> = ({
  value, onChange, label, autoFocus = false, disabled = false,
}) => {
  const { t } = useLanguage()
  const [feedback, setFeedback] = useState('')
  const [available, setAvailable] = useState<boolean | null>(null)

  const handleBlur = async () => {
    const localError = usernameValidationError(value)
    if (localError) {
      setAvailable(false)
      setFeedback(t(`admin.usernameError.${localError}`))
      return
    }
    try {
      const result = await checkUsernameAvailability(value)
      setAvailable(result.available)
      setFeedback(result.available
        ? t('admin.usernameAvailable')
        : result.reason && isMachineErrorKey(result.reason)
          ? t(`admin.usernameError.${result.reason}`)
          : t('admin.usernameError.taken'))
    } catch {
      setAvailable(null)
      setFeedback(t('admin.usernameError.checkUnavailable'))
    }
  }

  return (
    <TextField
      label={label ?? t('admin.usernameLabel')}
      value={value}
      onChange={event => {
        onChange(event.target.value)
        setAvailable(null)
        setFeedback('')
      }}
      onBlur={() => { void handleBlur() }}
      error={available === false}
      color={available ? 'success' : undefined}
      helperText={feedback || t('admin.usernameHint')}
      inputProps={{ maxLength: 32 }}
      fullWidth
      size="small"
      autoFocus={autoFocus}
      disabled={disabled}
    />
  )
}

export default UsernameField
