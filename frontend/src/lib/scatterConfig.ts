// 图表的视觉编码。
//
// 分类维度是「材料家族」（material_families 目录），而非早先硬编码的 7 类超导类型：
// 该目录由 /api/classification-catalogs 动态提供，并允许用户自建家族，硬编码覆盖不到。
//
// 双通道编码，避免撞色导致不可辨：
//   家族      → 形状 + 描边色
//   实验/计算  → 实心 / 空心
// 因此任意两个家族即使配色循环撞上，形状仍能区分；实验与计算不依赖颜色单一通道。

export type ScatterSymbol = 'circle' | 'cross' | 'diamond' | 'square' | 'star' | 'triangle' | 'wye'

// recharts 支持的 7 种符号。与调色板长度（8）互质，两者循环组合出 56 个可区分外观。
export const FAMILY_SYMBOLS: readonly ScatterSymbol[] = [
  'triangle', 'square', 'diamond', 'circle', 'wye', 'cross', 'star',
]

export const FAMILY_COLORS: readonly string[] = [
  '#2563eb', '#dc2626', '#059669', '#d97706',
  '#7c3aed', '#0891b2', '#be185d', '#4d7c0f',
]

// 图例里用字符近似表示形状，供纯文本环境与屏幕阅读器辅助识别。
const SYMBOL_ICONS: Record<ScatterSymbol, string> = {
  triangle: '▲', square: '■', diamond: '◆', circle: '●',
  wye: '▼', cross: '✚', star: '★',
}

// 未分类家族的固定档位：family_id = 0，恒为「其他」，不参与循环分配。
export const UNCLASSIFIED_FAMILY_ID = 0
export const UNCLASSIFIED_FAMILY_NAME = '其他'

export interface FamilyStyle {
  id: number
  name: string
  symbol: ScatterSymbol
  color: string
  icon: string
}

/**
 * 按目录顺序确定性分配形状与颜色。
 *
 * 输入顺序即 /api/classification-catalogs 的 id 升序，故内置家族的样式稳定；
 * 用户新建家族追加在末尾，不会改变既有家族的外观。
 */
export function buildFamilyStyles(
  families: Array<{ id: number; name: string }>,
): Map<number, FamilyStyle> {
  const styles = new Map<number, FamilyStyle>()
  families.forEach((family, index) => {
    const symbol = FAMILY_SYMBOLS[index % FAMILY_SYMBOLS.length]
    styles.set(family.id, {
      id: family.id,
      name: family.name,
      symbol,
      color: FAMILY_COLORS[index % FAMILY_COLORS.length],
      icon: SYMBOL_ICONS[symbol],
    })
  })
  styles.set(UNCLASSIFIED_FAMILY_ID, {
    id: UNCLASSIFIED_FAMILY_ID,
    name: UNCLASSIFIED_FAMILY_NAME,
    symbol: 'circle',
    color: '#64748b',
    icon: SYMBOL_ICONS.circle,
  })
  return styles
}

export function familyStyleOf(
  styles: Map<number, FamilyStyle>,
  familyId: number,
): FamilyStyle {
  return styles.get(familyId) ?? {
    id: familyId,
    name: UNCLASSIFIED_FAMILY_NAME,
    symbol: 'circle',
    color: '#64748b',
    icon: SYMBOL_ICONS.circle,
  }
}

// ── 品质因子分区 ───────────────────────────────────────
// Pickard 品质因子 S = Tc / sqrt(39² + P²)，39 K 是常压 MgB2 基准。
// 等值线 Tc = S × sqrt(39² + P²) 在相邻档位之间围出色带，即背景分区。
export const QUALITY_FACTOR_REFERENCE_TC = 39
export const QUALITY_FACTOR_LEVELS: readonly number[] = [0.2, 0.5, 1, 2, 3]

// 由低到高 6 个区间（<0.2、0.2–0.5、0.5–1、1–2、2–3、>3）的填充色，越高越暖。
//
// 与年份图的温度渐变同为「暖 = 高、冷 = 低」，两图并排不会同色异义。
export const QUALITY_FACTOR_BAND_COLORS: readonly string[] = [
  '#eef2f6', '#dcece4', '#c8e6c9', '#ffe8a3', '#ffc9a3', '#ffb0a3',
]

export const QUALITY_FACTOR_BAND_OPACITY = 0.55

// ── Tc-Year 温度渐变 ───────────────────────────────────
// 年份图按纵轴温度着色：低温蓝、高温红。分区边界只依赖 Tc（水平线），
// 故用单个矩形配 linearGradient 沿 Y 轴渐变，无需像品质因子那样逐段采样曲线。
export const TEMPERATURE_LOW_COLOR = '#2f6fb3'   // 低温端（纵轴底部）
export const TEMPERATURE_MID_COLOR = '#f2eff2'   // 中段过渡，避免蓝红直接对撞
export const TEMPERATURE_HIGH_COLOR = '#c0392b'  // 高温端（纵轴顶部）

// 背景须让散点保持可读，故整体不透明度低于品质因子色带。
export const TEMPERATURE_BAND_OPACITY = 0.28

export function qualityFactorTc(s: number, pressureGPa: number): number {
  return s * Math.sqrt(QUALITY_FACTOR_REFERENCE_TC ** 2 + pressureGPa ** 2)
}

// 固定坐标域：没有数据点也要画出坐标系与背景分区。
export const EMPTY_PRESSURE_DOMAIN: [number, number] = [0, 400]
export const EMPTY_YEAR_DOMAIN: [number, number] = [1900, new Date().getFullYear() + 1]

// 纵轴由两张图共用，保证并排时可直接比对 Tc 高度（不共用的话「对齐」只剩几何意义）。
// 代价：压力图的低档位等值线（S=0.2）被压缩到图的下部，分辨率下降。
export const EMPTY_TC_DOMAIN: [number, number] = [0, 500]
