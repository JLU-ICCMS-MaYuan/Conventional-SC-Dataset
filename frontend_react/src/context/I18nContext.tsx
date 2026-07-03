import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

type Lang = 'zh' | 'en'
type Dict = Record<string, { zh: string; en: string }>

const dict: Dict = {
  'nav.title': { zh: 'SC-Wiki', en: 'SC-Wiki' },
  'nav.subtitle': { zh: '超导工作台', en: 'Superconductor workspace' },
  'nav.hotspot': { zh: '超导热点', en: 'SC Hotspot' },
  'nav.explore': { zh: '超导探索', en: 'SC Explore' },
  'nav.share': { zh: '超导分享', en: 'SC Share' },
  'nav.chat': { zh: '超导对话', en: 'SC Chat' },
  'nav.predict': { zh: '超导预测', en: 'SC Predict' },
  'nav.admin': { zh: '管理工具', en: 'Admin tools' },
  'nav.admin_dashboard': { zh: '审核面板', en: 'Review dashboard' },
  'nav.admin_papers': { zh: '文献管理', en: 'Paper admin' },
  'nav.admin_users': { zh: '用户管理', en: 'User admin' },
  'common.language': { zh: '中/EN', en: '中/EN' },
  'common.login': { zh: '登录 / 注册', en: 'Login / Register' },
  'common.logout': { zh: '退出', en: 'Logout' },
  'explore.kicker': { zh: 'Explore', en: 'Explore' },
  'explore.title': { zh: '超导探索', en: 'SC Explore' },
  'explore.subtitle': { zh: '输入化学式，或用元素周期表选择体系，进入对应文献与数据。', en: 'Enter a formula or choose elements to open the matching literature and data.' },
  'explore.formula_title': { zh: '化学式检索', en: 'Formula Search' },
  'explore.formula_desc': { zh: '支持模糊搜索，找到目标体系后进入文献与数据页面。', en: 'Use fuzzy search to find a target system, then open its literature and data.' },
  'explore.formula_label': { zh: '化学式', en: 'Formula' },
  'explore.formula_placeholder': { zh: 'LaH10、FeSe1-xTex、YBa2Cu3O7', en: 'LaH10, FeSe1-xTex, YBa2Cu3O7' },
  'explore.formula_search': { zh: '搜索', en: 'Search' },
  'explore.elements_title': { zh: '元素周期表检索', en: 'Periodic Table Search' },
  'explore.selected': { zh: '已选元素', en: 'Selected' },
  'explore.none_selected': { zh: '未选择', en: 'None' },
  'explore.mode_combination': { zh: '选择元素的组合', en: 'Combinations of Selected' },
  'explore.mode_exact': { zh: '仅包含选择元素', en: 'Selected Elements Only' },
  'explore.mode_contains': { zh: '包含所选元素', en: 'Contains Selected Elements' },
  'explore.enter': { zh: '进入页面', en: 'View' },
  'explore.clear': { zh: '清除选择', en: 'Clear Selection' },
  'explore.hint': { zh: '点击元素进行选择，选中后再次点击可取消。选择完成后点击进入页面或按 Enter。', en: 'Click elements to select, click again to remove. Press View or Enter when ready.' },
}

interface I18nState {
  lang: Lang
  setLang: (lang: Lang) => void
  toggleLang: () => void
  t: (key: string) => string
}

const I18nContext = createContext<I18nState>({
  lang: 'zh',
  setLang: () => {},
  toggleLang: () => {},
  t: (key) => key,
})

export const useI18n = () => useContext(I18nContext)

export const I18nProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [lang, setLangState] = useState<Lang>(() => (localStorage.getItem('lang') === 'en' ? 'en' : 'zh'))

  const setLang = useCallback((nextLang: Lang) => {
    localStorage.setItem('lang', nextLang)
    setLangState(nextLang)
  }, [])

  const toggleLang = useCallback(() => {
    setLang(lang === 'zh' ? 'en' : 'zh')
  }, [lang, setLang])

  const t = useCallback((key: string) => dict[key]?.[lang] || key, [lang])

  useEffect(() => {
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en'
  }, [lang])

  const value = useMemo(() => ({ lang, setLang, toggleLang, t }), [lang, setLang, toggleLang, t])

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}
