import React, { useState } from 'react'
import { Card } from 'react-bootstrap'

interface Element {
  symbol: string
  name: string
  number: number
  category: string
  group: number
  period: number
  radioactive: boolean
  synthetic: boolean
}

const ELEMENTS: Element[] = [
  { symbol: 'H', name: '氢', number: 1, category: 'nonmetal', group: 1, period: 1, radioactive: false, synthetic: false },
  { symbol: 'He', name: '氦', number: 2, category: 'noble-gas', group: 18, period: 1, radioactive: false, synthetic: false },
  { symbol: 'Li', name: '锂', number: 3, category: 'alkali-metal', group: 1, period: 2, radioactive: false, synthetic: false },
  { symbol: 'Be', name: '铍', number: 4, category: 'alkaline-earth', group: 2, period: 2, radioactive: false, synthetic: false },
  { symbol: 'B', name: '硼', number: 5, category: 'metalloid', group: 13, period: 2, radioactive: false, synthetic: false },
  { symbol: 'C', name: '碳', number: 6, category: 'nonmetal', group: 14, period: 2, radioactive: false, synthetic: false },
  { symbol: 'N', name: '氮', number: 7, category: 'nonmetal', group: 15, period: 2, radioactive: false, synthetic: false },
  { symbol: 'O', name: '氧', number: 8, category: 'nonmetal', group: 16, period: 2, radioactive: false, synthetic: false },
  { symbol: 'F', name: '氟', number: 9, category: 'halogen', group: 17, period: 2, radioactive: false, synthetic: false },
  { symbol: 'Ne', name: '氖', number: 10, category: 'noble-gas', group: 18, period: 2, radioactive: false, synthetic: false },
  { symbol: 'Na', name: '钠', number: 11, category: 'alkali-metal', group: 1, period: 3, radioactive: false, synthetic: false },
  { symbol: 'Mg', name: '镁', number: 12, category: 'alkaline-earth', group: 2, period: 3, radioactive: false, synthetic: false },
  { symbol: 'Al', name: '铝', number: 13, category: 'post-transition', group: 13, period: 3, radioactive: false, synthetic: false },
  { symbol: 'Si', name: '硅', number: 14, category: 'metalloid', group: 14, period: 3, radioactive: false, synthetic: false },
  { symbol: 'P', name: '磷', number: 15, category: 'nonmetal', group: 15, period: 3, radioactive: false, synthetic: false },
  { symbol: 'S', name: '硫', number: 16, category: 'nonmetal', group: 16, period: 3, radioactive: false, synthetic: false },
  { symbol: 'Cl', name: '氯', number: 17, category: 'halogen', group: 17, period: 3, radioactive: false, synthetic: false },
  { symbol: 'Ar', name: '氩', number: 18, category: 'noble-gas', group: 18, period: 3, radioactive: false, synthetic: false },
  { symbol: 'K', name: '钾', number: 19, category: 'alkali-metal', group: 1, period: 4, radioactive: false, synthetic: false },
  { symbol: 'Ca', name: '钙', number: 20, category: 'alkaline-earth', group: 2, period: 4, radioactive: false, synthetic: false },
  { symbol: 'Sc', name: '钪', number: 21, category: 'transition-metal', group: 3, period: 4, radioactive: false, synthetic: false },
  { symbol: 'Ti', name: '钛', number: 22, category: 'transition-metal', group: 4, period: 4, radioactive: false, synthetic: false },
  { symbol: 'V', name: '钒', number: 23, category: 'transition-metal', group: 5, period: 4, radioactive: false, synthetic: false },
  { symbol: 'Cr', name: '铬', number: 24, category: 'transition-metal', group: 6, period: 4, radioactive: false, synthetic: false },
  { symbol: 'Mn', name: '锰', number: 25, category: 'transition-metal', group: 7, period: 4, radioactive: false, synthetic: false },
  { symbol: 'Fe', name: '铁', number: 26, category: 'transition-metal', group: 8, period: 4, radioactive: false, synthetic: false },
  { symbol: 'Co', name: '钴', number: 27, category: 'transition-metal', group: 9, period: 4, radioactive: false, synthetic: false },
  { symbol: 'Ni', name: '镍', number: 28, category: 'transition-metal', group: 10, period: 4, radioactive: false, synthetic: false },
  { symbol: 'Cu', name: '铜', number: 29, category: 'transition-metal', group: 11, period: 4, radioactive: false, synthetic: false },
  { symbol: 'Zn', name: '锌', number: 30, category: 'transition-metal', group: 12, period: 4, radioactive: false, synthetic: false },
  { symbol: 'Ga', name: '镓', number: 31, category: 'post-transition', group: 13, period: 4, radioactive: false, synthetic: false },
  { symbol: 'Ge', name: '锗', number: 32, category: 'metalloid', group: 14, period: 4, radioactive: false, synthetic: false },
  { symbol: 'As', name: '砷', number: 33, category: 'metalloid', group: 15, period: 4, radioactive: false, synthetic: false },
  { symbol: 'Se', name: '硒', number: 34, category: 'nonmetal', group: 16, period: 4, radioactive: false, synthetic: false },
  { symbol: 'Br', name: '溴', number: 35, category: 'halogen', group: 17, period: 4, radioactive: false, synthetic: false },
  { symbol: 'Kr', name: '氪', number: 36, category: 'noble-gas', group: 18, period: 4, radioactive: false, synthetic: false },
  { symbol: 'Rb', name: '铷', number: 37, category: 'alkali-metal', group: 1, period: 5, radioactive: false, synthetic: false },
  { symbol: 'Sr', name: '锶', number: 38, category: 'alkaline-earth', group: 2, period: 5, radioactive: false, synthetic: false },
  { symbol: 'Y', name: '钇', number: 39, category: 'transition-metal', group: 3, period: 5, radioactive: false, synthetic: false },
  { symbol: 'Zr', name: '锆', number: 40, category: 'transition-metal', group: 4, period: 5, radioactive: false, synthetic: false },
  { symbol: 'Nb', name: '铌', number: 41, category: 'transition-metal', group: 5, period: 5, radioactive: false, synthetic: false },
  { symbol: 'Mo', name: '钼', number: 42, category: 'transition-metal', group: 6, period: 5, radioactive: false, synthetic: false },
  { symbol: 'Tc', name: '锝', number: 43, category: 'transition-metal', group: 7, period: 5, radioactive: true, synthetic: true },
  { symbol: 'Ru', name: '钌', number: 44, category: 'transition-metal', group: 8, period: 5, radioactive: false, synthetic: false },
  { symbol: 'Rh', name: '铑', number: 45, category: 'transition-metal', group: 9, period: 5, radioactive: false, synthetic: false },
  { symbol: 'Pd', name: '钯', number: 46, category: 'transition-metal', group: 10, period: 5, radioactive: false, synthetic: false },
  { symbol: 'Ag', name: '银', number: 47, category: 'transition-metal', group: 11, period: 5, radioactive: false, synthetic: false },
  { symbol: 'Cd', name: '镉', number: 48, category: 'transition-metal', group: 12, period: 5, radioactive: false, synthetic: false },
  { symbol: 'In', name: '铟', number: 49, category: 'post-transition', group: 13, period: 5, radioactive: false, synthetic: false },
  { symbol: 'Sn', name: '锡', number: 50, category: 'post-transition', group: 14, period: 5, radioactive: false, synthetic: false },
  { symbol: 'Sb', name: '锑', number: 51, category: 'metalloid', group: 15, period: 5, radioactive: false, synthetic: false },
  { symbol: 'Te', name: '碲', number: 52, category: 'metalloid', group: 16, period: 5, radioactive: false, synthetic: false },
  { symbol: 'I', name: '碘', number: 53, category: 'halogen', group: 17, period: 5, radioactive: false, synthetic: false },
  { symbol: 'Xe', name: '氙', number: 54, category: 'noble-gas', group: 18, period: 5, radioactive: false, synthetic: false },
  { symbol: 'Cs', name: '铯', number: 55, category: 'alkali-metal', group: 1, period: 6, radioactive: false, synthetic: false },
  { symbol: 'Ba', name: '钡', number: 56, category: 'alkaline-earth', group: 2, period: 6, radioactive: false, synthetic: false },
  { symbol: 'La', name: '镧', number: 57, category: 'lanthanide', group: 3, period: 8, radioactive: false, synthetic: false },
  { symbol: 'Ce', name: '铈', number: 58, category: 'lanthanide', group: 3, period: 8, radioactive: false, synthetic: false },
  { symbol: 'Pr', name: '镨', number: 59, category: 'lanthanide', group: 3, period: 8, radioactive: false, synthetic: false },
  { symbol: 'Nd', name: '钕', number: 60, category: 'lanthanide', group: 3, period: 8, radioactive: false, synthetic: false },
  { symbol: 'Pm', name: '钷', number: 61, category: 'lanthanide', group: 3, period: 8, radioactive: true, synthetic: true },
  { symbol: 'Sm', name: '钐', number: 62, category: 'lanthanide', group: 3, period: 8, radioactive: false, synthetic: false },
  { symbol: 'Eu', name: '铕', number: 63, category: 'lanthanide', group: 3, period: 8, radioactive: false, synthetic: false },
  { symbol: 'Gd', name: '钆', number: 64, category: 'lanthanide', group: 3, period: 8, radioactive: false, synthetic: false },
  { symbol: 'Tb', name: '铽', number: 65, category: 'lanthanide', group: 3, period: 8, radioactive: false, synthetic: false },
  { symbol: 'Dy', name: '镝', number: 66, category: 'lanthanide', group: 3, period: 8, radioactive: false, synthetic: false },
  { symbol: 'Ho', name: '钬', number: 67, category: 'lanthanide', group: 3, period: 8, radioactive: false, synthetic: false },
  { symbol: 'Er', name: '铒', number: 68, category: 'lanthanide', group: 3, period: 8, radioactive: false, synthetic: false },
  { symbol: 'Tm', name: '铥', number: 69, category: 'lanthanide', group: 3, period: 8, radioactive: false, synthetic: false },
  { symbol: 'Yb', name: '镱', number: 70, category: 'lanthanide', group: 3, period: 8, radioactive: false, synthetic: false },
  { symbol: 'Lu', name: '镥', number: 71, category: 'lanthanide', group: 3, period: 8, radioactive: false, synthetic: false },
  { symbol: 'Hf', name: '铪', number: 72, category: 'transition-metal', group: 4, period: 6, radioactive: false, synthetic: false },
  { symbol: 'Ta', name: '钽', number: 73, category: 'transition-metal', group: 5, period: 6, radioactive: false, synthetic: false },
  { symbol: 'W', name: '钨', number: 74, category: 'transition-metal', group: 6, period: 6, radioactive: false, synthetic: false },
  { symbol: 'Re', name: '铼', number: 75, category: 'transition-metal', group: 7, period: 6, radioactive: false, synthetic: false },
  { symbol: 'Os', name: '锇', number: 76, category: 'transition-metal', group: 8, period: 6, radioactive: false, synthetic: false },
  { symbol: 'Ir', name: '铱', number: 77, category: 'transition-metal', group: 9, period: 6, radioactive: false, synthetic: false },
  { symbol: 'Pt', name: '铂', number: 78, category: 'transition-metal', group: 10, period: 6, radioactive: false, synthetic: false },
  { symbol: 'Au', name: '金', number: 79, category: 'transition-metal', group: 11, period: 6, radioactive: false, synthetic: false },
  { symbol: 'Hg', name: '汞', number: 80, category: 'transition-metal', group: 12, period: 6, radioactive: false, synthetic: false },
  { symbol: 'Tl', name: '铊', number: 81, category: 'post-transition', group: 13, period: 6, radioactive: false, synthetic: false },
  { symbol: 'Pb', name: '铅', number: 82, category: 'post-transition', group: 14, period: 6, radioactive: false, synthetic: false },
  { symbol: 'Bi', name: '铋', number: 83, category: 'post-transition', group: 15, period: 6, radioactive: true, synthetic: false },
  { symbol: 'Po', name: '钋', number: 84, category: 'post-transition', group: 16, period: 6, radioactive: true, synthetic: false },
  { symbol: 'At', name: '砹', number: 85, category: 'halogen', group: 17, period: 6, radioactive: true, synthetic: false },
  { symbol: 'Rn', name: '氡', number: 86, category: 'noble-gas', group: 18, period: 6, radioactive: true, synthetic: false },
  { symbol: 'Fr', name: '钫', number: 87, category: 'alkali-metal', group: 1, period: 7, radioactive: true, synthetic: false },
  { symbol: 'Ra', name: '镭', number: 88, category: 'alkaline-earth', group: 2, period: 7, radioactive: true, synthetic: false },
  { symbol: 'Ac', name: '锕', number: 89, category: 'actinide', group: 3, period: 9, radioactive: true, synthetic: false },
  { symbol: 'Th', name: '钍', number: 90, category: 'actinide', group: 3, period: 9, radioactive: true, synthetic: false },
  { symbol: 'Pa', name: '镤', number: 91, category: 'actinide', group: 3, period: 9, radioactive: true, synthetic: false },
  { symbol: 'U', name: '铀', number: 92, category: 'actinide', group: 3, period: 9, radioactive: true, synthetic: false },
  { symbol: 'Np', name: '镎', number: 93, category: 'actinide', group: 3, period: 9, radioactive: true, synthetic: true },
  { symbol: 'Pu', name: '钚', number: 94, category: 'actinide', group: 3, period: 9, radioactive: true, synthetic: true },
  { symbol: 'Am', name: '镅', number: 95, category: 'actinide', group: 3, period: 9, radioactive: true, synthetic: true },
  { symbol: 'Cm', name: '锔', number: 96, category: 'actinide', group: 3, period: 9, radioactive: true, synthetic: true },
  { symbol: 'Bk', name: '锫', number: 97, category: 'actinide', group: 3, period: 9, radioactive: true, synthetic: true },
  { symbol: 'Cf', name: '锎', number: 98, category: 'actinide', group: 3, period: 9, radioactive: true, synthetic: true },
  { symbol: 'Es', name: '锿', number: 99, category: 'actinide', group: 3, period: 9, radioactive: true, synthetic: true },
  { symbol: 'Fm', name: '镄', number: 100, category: 'actinide', group: 3, period: 9, radioactive: true, synthetic: true },
  { symbol: 'Md', name: '钔', number: 101, category: 'actinide', group: 3, period: 9, radioactive: true, synthetic: true },
  { symbol: 'No', name: '锘', number: 102, category: 'actinide', group: 3, period: 9, radioactive: true, synthetic: true },
  { symbol: 'Lr', name: '铹', number: 103, category: 'actinide', group: 3, period: 9, radioactive: true, synthetic: true },
  { symbol: 'Rf', name: '𬬻', number: 104, category: 'transition-metal', group: 4, period: 7, radioactive: true, synthetic: true },
  { symbol: 'Db', name: '𬭊', number: 105, category: 'transition-metal', group: 5, period: 7, radioactive: true, synthetic: true },
  { symbol: 'Sg', name: '𬭳', number: 106, category: 'transition-metal', group: 6, period: 7, radioactive: true, synthetic: true },
  { symbol: 'Bh', name: '𬭛', number: 107, category: 'transition-metal', group: 7, period: 7, radioactive: true, synthetic: true },
  { symbol: 'Hs', name: '𬭶', number: 108, category: 'transition-metal', group: 8, period: 7, radioactive: true, synthetic: true },
  { symbol: 'Mt', name: '鿏', number: 109, category: 'transition-metal', group: 9, period: 7, radioactive: true, synthetic: true },
  { symbol: 'Ds', name: '𫟼', number: 110, category: 'transition-metal', group: 10, period: 7, radioactive: true, synthetic: true },
  { symbol: 'Rg', name: '𬬭', number: 111, category: 'transition-metal', group: 11, period: 7, radioactive: true, synthetic: true },
  { symbol: 'Cn', name: '鿔', number: 112, category: 'transition-metal', group: 12, period: 7, radioactive: true, synthetic: true },
  { symbol: 'Nh', name: '鿭', number: 113, category: 'post-transition', group: 13, period: 7, radioactive: true, synthetic: true },
  { symbol: 'Fl', name: '𫓧', number: 114, category: 'post-transition', group: 14, period: 7, radioactive: true, synthetic: true },
  { symbol: 'Mc', name: '镆', number: 115, category: 'post-transition', group: 15, period: 7, radioactive: true, synthetic: true },
  { symbol: 'Lv', name: '𫟷', number: 116, category: 'post-transition', group: 16, period: 7, radioactive: true, synthetic: true },
  { symbol: 'Ts', name: '石田', number: 117, category: 'halogen', group: 17, period: 7, radioactive: true, synthetic: true },
  { symbol: 'Og', name: '奥气', number: 118, category: 'noble-gas', group: 18, period: 7, radioactive: true, synthetic: true },
]

const CATEGORY_COLORS: Record<string, string> = {
  'alkali-metal': '#f4bcc2',
  'alkaline-earth': '#e3bd91',
  'transition-metal': '#edcda9',
  'post-transition': '#ededab',
  'metalloid': '#9cd5a8',
  'nonmetal': '#a3d7dc',
  'halogen': '#b7a0db',
  'noble-gas': '#cfb5d6',
  'lanthanide': '#cea1ce',
  'actinide': '#c782ab',
}

interface PeriodicTableProps {
  onElementClick: (symbols: string[]) => void
}

const PeriodicTable: React.FC<PeriodicTableProps> = ({ onElementClick }) => {
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const toggle = (symbol: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(symbol)) next.delete(symbol)
      else next.add(symbol)
      onElementClick(Array.from(next))
      return next
    })
  }

  const mainElements = ELEMENTS.filter((e) => e.period < 8 && (e.group < 3 || e.group > 3 || e.number > 71))
  const lanthanides = ELEMENTS.filter((e) => e.period === 8 && e.category === 'lanthanide')
  const actinides = ELEMENTS.filter((e) => e.period === 9 && e.category === 'actinide')

  const maxGroup = 18
  const maxPeriod = 7

  const grid = new Map<string, Element>()
  mainElements.forEach((e) => {
    // Map period 8/9 back to period 6/7 for lanthanides/actinides placeholder
    const displayPeriod = e.period > 7 ? (e.category === 'lanthanide' ? 6 : 7) : e.period
    grid.set(`${displayPeriod}-${e.group}`, e)
  })

  return (
    <div style={{ overflowX: 'auto' }}>
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${maxGroup}, 48px)`, gap: 2, justifyContent: 'center', marginBottom: 8 }}>
        {/* Headers */}
        {Array.from({ length: maxGroup }, (_, i) => (
          <div key={i} style={{ textAlign: 'center', fontSize: 10, color: '#999', padding: 2 }}>{i + 1}</div>
        ))}
        {/* Main table */}
        {Array.from({ length: maxPeriod }, (_, p) => (
          <React.Fragment key={p}>
            {Array.from({ length: maxGroup }, (_, g) => {
              const key = `${p + 1}-${g + 1}`
              const el = grid.get(key)
              if (!el) return <div key={g} />
              const sel = selected.has(el.symbol)
              const isRadioactive = el.radioactive || el.synthetic
              return (
                <button
                  key={key}
                  onClick={() => !isRadioactive && toggle(el.symbol)}
                  disabled={isRadioactive}
                  style={{
                    width: 48, height: 48, border: '1px solid #ddd', borderRadius: 4,
                    backgroundColor: sel ? '#4d6bfe' : CATEGORY_COLORS[el.category] || '#eee',
                    color: sel ? '#fff' : '#333', cursor: isRadioactive ? 'not-allowed' : 'pointer',
                    opacity: isRadioactive ? 0.5 : 1, padding: 2, display: 'flex', flexDirection: 'column',
                    alignItems: 'center', justifyContent: 'center', transition: 'all 0.15s',
                    fontSize: 10,
                  }}
                >
                  <span style={{ fontSize: 7, lineHeight: 1 }}>{el.number}</span>
                  <span style={{ fontWeight: 'bold', fontSize: 16, lineHeight: 1.2 }}>{el.symbol}</span>
                </button>
              )
            })}
          </React.Fragment>
        ))}
      </div>

      {/* Lanthanides */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: 2, marginBottom: 4 }}>
        {lanthanides.map((el) => {
          const sel = selected.has(el.symbol)
          return (
            <button
              key={el.symbol}
              onClick={() => !el.radioactive && toggle(el.symbol)}
              disabled={el.synthetic}
              style={{
                width: 48, height: 36, border: '1px solid #ddd', borderRadius: 4,
                backgroundColor: sel ? '#4d6bfe' : CATEGORY_COLORS.lanthanide,
                color: sel ? '#fff' : '#333', cursor: el.synthetic ? 'not-allowed' : 'pointer',
                opacity: el.synthetic ? 0.5 : 1, fontSize: 11, fontWeight: 'bold',
                transition: 'all 0.15s',
              }}
            >
              {el.symbol}
            </button>
          )
        })}
      </div>

      {/* Actinides */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: 2 }}>
        {actinides.map((el) => {
          const sel = selected.has(el.symbol)
          return (
            <button
              key={el.symbol}
              onClick={() => !el.radioactive && toggle(el.symbol)}
              disabled={el.synthetic}
              style={{
                width: 48, height: 36, border: '1px solid #ddd', borderRadius: 4,
                backgroundColor: sel ? '#4d6bfe' : CATEGORY_COLORS.actinide,
                color: sel ? '#fff' : '#333', cursor: el.synthetic ? 'not-allowed' : 'pointer',
                opacity: el.synthetic ? 0.5 : 1, fontSize: 11, fontWeight: 'bold',
                transition: 'all 0.15s',
              }}
            >
              {el.symbol}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default PeriodicTable
