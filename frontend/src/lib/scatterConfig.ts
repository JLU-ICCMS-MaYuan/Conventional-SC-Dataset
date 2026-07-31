// 7 种超导类型的形状 + 中文标签
export const SC_TYPE_CONFIG: Record<string, {
  label: string
  shape: 'triangle' | 'square' | 'diamond' | 'circle' | 'wye' | 'cross'
}> = {
  hydride:       { label: '氢化物', shape: 'triangle' },
  cuprate:       { label: '铜基',   shape: 'square' },
  iron_based:    { label: '铁基',   shape: 'diamond' },
  nickel_based:  { label: '镍基',   shape: 'circle' },
  carbon:        { label: '碳基',   shape: 'wye' },
  organic:       { label: '有机',   shape: 'cross' },
  others:        { label: '其他',   shape: 'diamond' },
}

// 实验 / 理论颜色
export const EXP_COLOR = '#dc2626'       // 红色
export const THEORY_COLOR = '#3b82f6'    // 蓝色

export function getPointColor(articleType: string | null): string {
  return articleType === 'e' ? EXP_COLOR : THEORY_COLOR
}

// 背景点半透明度
export const BACKGROUND_OPACITY = 0.3
