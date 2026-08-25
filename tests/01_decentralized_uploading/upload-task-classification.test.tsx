import '@testing-library/jest-dom/vitest'
import React from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ClassificationAutocomplete from '../../frontend/src/components/ClassificationAutocomplete'


const options = [
  { id: 1, name: '氢基超导体', aliases: ['hydride', '氢化物', '高压氢化物'] },
  { id: 2, name: '重费米子超导体', aliases: ['heavy fermion'] },
]

afterEach(cleanup)


describe('材料分类数据库候选', () => {
  it('展开数据库中文候选，并可用审核别名筛选', () => {
    render(
      <ClassificationAutocomplete
        label="材料家族"
        options={options}
        value={null}
        onChange={vi.fn()}
      />,
    )

    const input = screen.getByLabelText('材料家族')
    fireEvent.mouseDown(input)
    expect(screen.getByText('氢基超导体')).toBeInTheDocument()
    expect(screen.getByText('重费米子超导体')).toBeInTheDocument()

    fireEvent.change(input, { target: { value: 'hydride' } })
    expect(screen.getByText('氢基超导体')).toBeInTheDocument()
    expect(document.querySelector('datalist')).not.toBeInTheDocument()
  })

  it('未知名称以 pending 结构返回', () => {
    const onChange = vi.fn()
    render(
      <ClassificationAutocomplete
        label="材料家族"
        options={options}
        value={null}
        onChange={onChange}
      />,
    )
    fireEvent.change(screen.getByLabelText('材料家族'), { target: { value: '新材料家族' } })
    expect(onChange).toHaveBeenLastCalledWith({ id: null, name: '新材料家族', status: 'pending' })
  })
})
