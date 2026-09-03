export interface LlmProviderConfig {
  provider: string
  baseUrl: string
  model: string
  apiKey: string
}

export interface ProviderPreset {
  id: string
  label: string
  baseUrl: string
  model: string
}

export const LLM_PROVIDER_STORAGE_KEY = 'sc-wiki.llm-provider'

export const PROVIDER_PRESETS: readonly ProviderPreset[] = [
  { id: 'server-default', label: '服务端默认', baseUrl: '', model: '' },
  { id: 'deepseek', label: 'DeepSeek', baseUrl: 'https://api.deepseek.com', model: 'deepseek-chat' },
  { id: 'kimi', label: 'Kimi', baseUrl: 'https://api.moonshot.cn/v1', model: 'moonshot-v1-8k' },
  { id: 'glm', label: '智谱 GLM', baseUrl: 'https://open.bigmodel.cn/api/paas/v4', model: 'glm-4-plus' },
  { id: 'qwen', label: '通义千问', baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus' },
  { id: 'openai', label: 'OpenAI', baseUrl: 'https://api.openai.com/v1', model: 'gpt-4o-mini' },
  { id: 'claude', label: 'Claude', baseUrl: 'https://api.anthropic.com/v1', model: 'claude-3-5-sonnet-latest' },
  { id: 'custom', label: '自定义', baseUrl: '', model: '' },
]

export function readStoredLlmConfig(): LlmProviderConfig | null {
  try {
    const raw = localStorage.getItem(LLM_PROVIDER_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<LlmProviderConfig>
    if (!parsed.provider || !parsed.baseUrl || !parsed.model || !parsed.apiKey) return null
    return { provider: parsed.provider, baseUrl: parsed.baseUrl, model: parsed.model, apiKey: parsed.apiKey }
  } catch {
    return null
  }
}

export function saveLlmConfig(config: LlmProviderConfig): void {
  localStorage.setItem(LLM_PROVIDER_STORAGE_KEY, JSON.stringify(config))
}

export function clearLlmConfig(): void {
  localStorage.removeItem(LLM_PROVIDER_STORAGE_KEY)
}

export function maskApiKey(value: string): string {
  if (!value) return ''
  if (value.length <= 8) return '****'
  return `${value.slice(0, 3)}****${value.slice(-4)}`
}

export function buildLlmHeaders(): Record<string, string> {
  const config = readStoredLlmConfig()
  if (!config) return {}
  return {
    'X-LLM-Provider': config.provider,
    'X-LLM-Base-URL': config.baseUrl,
    'X-LLM-Model': config.model,
    'X-LLM-Api-Key': config.apiKey,
  }
}

export function validateLlmBaseUrl(value: string): string | null {
  try {
    const url = new URL(value.trim())
    const host = url.hostname.toLowerCase()
    const local = host === 'localhost' || host === '127.0.0.1'
    if (!['http:', 'https:'].includes(url.protocol)) return 'Base URL 必须是有效的 http(s) 地址'
    if (url.protocol !== 'https:' && !local) return '非本机 Base URL 必须使用 https'
    if (/^(10\.|192\.168\.|169\.254\.)/.test(host) || /^172\.(1[6-9]|2\d|3[01])\./.test(host)) {
      return 'Base URL 不允许访问内网地址'
    }
    return null
  } catch {
    return 'Base URL 必须是有效的 http(s) 地址'
  }
}
