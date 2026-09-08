// 论文详情的列表字段为 JSON 文本列；上传等调用方也可能提供数组。
// 仅解码一层，普通文本保留为一项，不按标点猜测分隔。
export const toTextList = (value: unknown): string[] => {
  if (Array.isArray(value)) {
    return value.map(item => String(item ?? '').trim()).filter(Boolean)
  }
  if (typeof value !== 'string' || !value.trim()) return []
  try {
    const parsed: unknown = JSON.parse(value)
    if (Array.isArray(parsed)) return parsed.map(item => String(item ?? '').trim()).filter(Boolean)
  } catch {
    // 旧普通文本按原文显示，避免解析失败丢失内容。
  }
  return [value.trim()]
}

// 编辑时保留原始换行，提交时才过滤空行；逗号属于条目内容。
export const textLinesToList = (value: string): string[] =>
  value.split(/\r?\n/).map(item => item.trim()).filter(Boolean)
