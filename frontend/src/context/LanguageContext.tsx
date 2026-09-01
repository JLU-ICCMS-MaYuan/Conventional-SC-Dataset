import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { DEFAULT_LANG, Dictionary, Lang, dictionaries, isLang } from '../i18n'

export interface LanguageState {
  lang: Lang
  setLang: (lang: Lang) => void
  /** 按点分键取文案；`vars` 用于替换 `{name}` 形式的占位符。 */
  t: (key: string, vars?: Record<string, string | number>) => string
  /** 直接取字典分支，用于枚举等需要整表查询的场景。 */
  dict: Dictionary
}

const STORAGE_KEY = 'sc-wiki.language'

/**
 * 读取语言偏好。
 *
 * localStorage 在隐私模式或配额耗尽时会抛异常，未捕获会导致整个 Provider 初始化失败
 * 并白屏；存储值也可能被手工篡改成未知语言。两种情况都回退默认中文。
 */
function readStoredLang(): Lang {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return isLang(stored) ? stored : DEFAULT_LANG
  } catch {
    return DEFAULT_LANG
  }
}

/** 写入偏好。失败不阻断切换——当前会话已通过组件状态生效，只是跨会话不保持。 */
function writeStoredLang(lang: Lang): void {
  try {
    localStorage.setItem(STORAGE_KEY, lang)
  } catch {
    // 存储不可用，忽略
  }
}

/** 按点分路径在字典中取值，取不到返回 undefined。 */
function lookup(dict: Dictionary, key: string): unknown {
  return key.split('.').reduce<unknown>(
    (node, segment) => (
      node && typeof node === 'object' ? (node as Record<string, unknown>)[segment] : undefined
    ),
    dict,
  )
}

function interpolate(text: string, vars?: Record<string, string | number>): string {
  if (!vars) return text
  return text.replace(/\{(\w+)\}/g, (match, name: string) => (
    name in vars ? String(vars[name]) : match
  ))
}

/**
 * 默认 context 用真实的默认语言字典解析文案，而非返回键名。
 *
 * 组件可能在没有 Provider 的情况下被渲染（例如只挂载单个组件的单元测试）。
 * 若此时 `t` 返回裸键，界面与测试都会看到 `nav.mainNav` 这类字符串——既不可读，
 * 也让「缺 Provider」这个真正的问题伪装成文案缺失。
 */
function resolveWith(lang: Lang, key: string, vars?: Record<string, string | number>): string {
  const found = lookup(dictionaries[lang], key)
  if (typeof found === 'string') return interpolate(found, vars)
  const fallback = lang === DEFAULT_LANG ? undefined : lookup(dictionaries[DEFAULT_LANG], key)
  if (typeof fallback === 'string') return interpolate(fallback, vars)
  // 键在两侧字典都不存在时返回键名；静态字典缺键由类型检查拦截。
  return key
}

const LanguageContext = createContext<LanguageState>({
  lang: DEFAULT_LANG,
  setLang: () => {},
  t: (key, vars) => resolveWith(DEFAULT_LANG, key, vars),
  dict: dictionaries[DEFAULT_LANG],
})

export const useLanguage = () => useContext(LanguageContext)

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [lang, setLangState] = useState<Lang>(readStoredLang)

  const setLang = useCallback((next: Lang) => {
    setLangState(next)
    writeStoredLang(next)
  }, [])

  // 同步 <html lang>：读屏软件据此选择发音，搜索引擎据此判定页面语言。
  useEffect(() => {
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en'
  }, [lang])

  const value = useMemo<LanguageState>(() => {
    return {
      lang,
      setLang,
      dict: dictionaries[lang],
      t: (key, vars) => resolveWith(lang, key, vars),
    }
  }, [lang, setLang])

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}
