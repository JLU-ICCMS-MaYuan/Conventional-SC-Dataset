import '@testing-library/jest-dom/vitest'
import React from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'

import LlmProviderSwitcher from '../../frontend/src/components/LlmProviderSwitcher'
import { LanguageProvider } from '../../frontend/src/context/LanguageContext'
import { api } from '../../frontend/src/lib/api'

vi.mock('../../frontend/src/lib/api', () => ({ api: { get: vi.fn(), post: vi.fn() } }))

const mockedApi = vi.mocked(api)

beforeEach(() => {
  localStorage.clear()
  mockedApi.get.mockResolvedValue({
    ok: true,
    data: { provider: 'server-default', provider_name: 'DeepSeek', model: 'deepseek-chat', source: 'server' },
  })
})

afterEach(() => {
  cleanup()
  localStorage.clear()
  vi.clearAllMocks()
})

describe('Issue #73 FR-024：默认模型可见性', () => {
  it('未保存个人配置时显示服务端供应商和模型，不显示任何凭据', async () => {
    render(<LanguageProvider><LlmProviderSwitcher /></LanguageProvider>)

    expect(await screen.findByRole('button', { name: '配置 AI 供应商' })).toHaveTextContent('DeepSeek · deepseek-chat')
    expect(mockedApi.get).toHaveBeenCalledWith('/api/rag/llm/current')
    expect(document.body.textContent).not.toContain('secret-key')
  })

  it('已保存个人配置时显示本地选择且不查询服务端默认值', async () => {
    localStorage.setItem('sc-wiki.llm-provider', JSON.stringify({
      provider: 'kimi', baseUrl: 'https://api.moonshot.cn/v1', model: 'moonshot-v1-8k', apiKey: 'secret-key',
    }))
    render(<LanguageProvider><LlmProviderSwitcher /></LanguageProvider>)

    await waitFor(() => expect(screen.getByRole('button', { name: '配置 AI 供应商' })).toHaveTextContent('Kimi · moonshot-v1-8k'))
    expect(mockedApi.get).not.toHaveBeenCalled()
    expect(document.body.textContent).not.toContain('secret-key')
  })
})
