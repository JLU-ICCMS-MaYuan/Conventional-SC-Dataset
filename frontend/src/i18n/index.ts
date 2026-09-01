/**
 * 文案字典聚合入口。
 *
 * 类型策略：字典形状由中文侧推导（`Dictionary = typeof zh`），英文字典声明为同一类型。
 * 英文缺键或多键会在 `tsc -b` 阶段报错，不会等到运行时才发现——这是不引入
 * react-i18next 的关键收益之一（后者的运行时 key 查找只会静默回退）。
 *
 * 按功能域分文件而非单文件：全站约 2400 条文案集中在一处会使冲突与检索都困难，
 * 分域也与 frontend/src/pages/ 的模块边界对齐。
 */
import zhCommon from './zh/common'
import zhEnums from './zh/enums'
import zhNav from './zh/nav'
import zhSearch from './zh/search'
import zhTcPredict from './zh/tcPredict'
import zhKg from './zh/kg'
import zhShare from './zh/share'
import zhNews from './zh/news'
import zhPaperDetail from './zh/paperDetail'
import zhUpload from './zh/upload'
import zhAdmin from './zh/admin'
import zhAccount from './zh/account'
import zhRag from './zh/rag'
import enCommon from './en/common'
import enEnums from './en/enums'
import enNav from './en/nav'
import enSearch from './en/search'
import enTcPredict from './en/tcPredict'
import enKg from './en/kg'
import enShare from './en/share'
import enNews from './en/news'
import enPaperDetail from './en/paperDetail'
import enUpload from './en/upload'
import enAdmin from './en/admin'
import enAccount from './en/account'
import enRag from './en/rag'

export type Lang = 'zh' | 'en'

export const LANGS: readonly Lang[] = ['zh', 'en'] as const
export const DEFAULT_LANG: Lang = 'zh'

const zh = {
  common: zhCommon,
  enums: zhEnums,
  nav: zhNav,
  search: zhSearch,
  tcPredict: zhTcPredict,
  kg: zhKg,
  share: zhShare,
  news: zhNews,
  paperDetail: zhPaperDetail,
  upload: zhUpload,
  admin: zhAdmin,
  account: zhAccount,
  rag: zhRag,
}

/**
 * 把字面量类型放宽为 string，只保留键结构。
 *
 * 各域文件用 `as const` 是为了让键名可被 IDE 补全，但副作用是值被窄化成字面量
 * （`'确认'` 而非 `string`），英文字典的 `'Confirm'` 会因此不匹配。此处逐层放宽值类型，
 * 键集仍严格校验——英文缺键或多键依然是编译错误。
 */
type Widen<T> = T extends string ? string
  : T extends readonly (infer U)[] ? readonly Widen<U>[]
  : { -readonly [K in keyof T]: Widen<T[K]> }

/** 字典形状以中文侧为准；英文字典必须逐键对齐。 */
export type Dictionary = Widen<typeof zh>

const en: Dictionary = {
  common: enCommon,
  enums: enEnums,
  nav: enNav,
  search: enSearch,
  tcPredict: enTcPredict,
  kg: enKg,
  share: enShare,
  news: enNews,
  paperDetail: enPaperDetail,
  upload: enUpload,
  admin: enAdmin,
  account: enAccount,
  rag: enRag,
}

export const dictionaries: Record<Lang, Dictionary> = { zh, en }

/** 运行时校验语言值：localStorage 可能被手工篡改为未知值。 */
export function isLang(value: unknown): value is Lang {
  return value === 'zh' || value === 'en'
}
