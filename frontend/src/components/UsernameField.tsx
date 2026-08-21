import React, { useState } from 'react'
import { TextField } from '@mui/material'
import { checkUsernameAvailability, usernameValidationError } from '../lib/username'

interface Props {
  value: string
  onChange: (value: string) => void
  label?: string
  autoFocus?: boolean
  disabled?: boolean
}

const UsernameField: React.FC<Props> = ({
  value, onChange, label = '用户名', autoFocus = false, disabled = false,
}) => {
  const [feedback, setFeedback] = useState('')
  const [available, setAvailable] = useState<boolean | null>(null)

  const handleBlur = async () => {
    const localError = usernameValidationError(value)
    if (localError) {
      setAvailable(false)
      setFeedback(localError)
      return
    }
    try {
      const result = await checkUsernameAvailability(value)
      setAvailable(result.available)
      setFeedback(result.available ? '用户名可用' : (result.reason || '用户名不可用'))
    } catch {
      setAvailable(null)
      setFeedback('暂时无法检查，提交时会再次验证')
    }
  }

  return (
    <TextField
      label={label}
      value={value}
      onChange={event => {
        onChange(event.target.value)
        setAvailable(null)
        setFeedback('')
      }}
      onBlur={() => { void handleBlur() }}
      error={available === false}
      color={available ? 'success' : undefined}
      helperText={feedback || '3–32 位，以字母开头，可使用字母、数字和下划线'}
      inputProps={{ maxLength: 32 }}
      fullWidth
      size="small"
      autoFocus={autoFocus}
      disabled={disabled}
    />
  )
}

export default UsernameField
