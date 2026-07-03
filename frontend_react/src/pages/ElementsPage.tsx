import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Button, Card, CardContent, CardHeader, Chip, Separator, Input } from '@heroui/react'
import { useNavigate } from 'react-router-dom'
import { useI18n } from '../context/I18nContext'
import { periodicElements, type PeriodicElement } from '../lib/periodicElements'

const modeStorageKey = 'element_selection_mode'
const defaultMode = 'elements_combination_search'

const ElementsPage: React.FC = () => {
  const navigate = useNavigate()
  const { t } = useI18n()
  const [selected, setSelected] = useState<string[]>([])
  const [formula, setFormula] = useState('')
  const [mode, setMode] = useState(() => localStorage.getItem(modeStorageKey) || defaultMode)

  const selectedLabel = useMemo(() => selected.slice().sort().join(', ') || t('explore.none_selected'), [selected, t])
  const cells = useMemo(() => buildPeriodicCells(), [])

  const goElements = useCallback(() => {
    if (!selected.length) return
    const sorted = [...selected].sort()
    navigate(`/compound/${sorted.join('-')}?mode=${mode}`)
  }, [mode, navigate, selected])

  useEffect(() => {
    localStorage.setItem(modeStorageKey, mode)
  }, [mode])

  useEffect(() => {
    function handleEnter(event: KeyboardEvent) {
      if (event.key !== 'Enter') return
      if ((event.target as HTMLElement | null)?.id === 'formula-search-input') return
      if (selected.length > 0) goElements()
    }

    document.addEventListener('keypress', handleEnter)
    return () => document.removeEventListener('keypress', handleEnter)
  }, [goElements, selected.length])

  function toggle(symbol: string) {
    if (symbol.includes('-')) return
    setSelected((prev) => (prev.includes(symbol) ? prev.filter((item) => item !== symbol) : [...prev, symbol]))
  }

  function goFormula() {
    const value = formula.trim()
    if (!value) return
    navigate(`/compound/${encodeURIComponent(value)}?mode=formula_search&formula=${encodeURIComponent(value)}`)
  }

  return (
    <section className="page explore-page">
      <header className="page-header">
        <div>
          <p className="page-kicker">{t('explore.kicker')}</p>
          <h1 className="page-title">{t('explore.title')}</h1>
        </div>
        <p className="muted">{t('explore.subtitle')}</p>
      </header>

      <Card   aria-labelledby="formula-search-title">
        <CardContent>
          <section className="formula-panel">
            <div>
              <h2 className="section-title" id="formula-search-title">{t('explore.formula_title')}</h2>
              <p className="section-subtitle">{t('explore.formula_desc')}</p>
            </div>
            <div className="formula-row">
              <label className="stack min-w-[280px] flex-1 gap-2 text-sm font-semibold text-[var(--sc-muted)]">
                {t('explore.formula_label')}
                <Input
                  id="formula-search-input"
                  value={formula}
                  onChange={(event) => setFormula(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      event.preventDefault()
                      goFormula()
                    }
                  }}
                  placeholder={t('explore.formula_placeholder')}
                />
              </label>
              <Button variant="primary"  onPress={goFormula}>{t('explore.formula_search')}</Button>
            </div>
          </section>
        </CardContent>
      </Card>

      <Card   aria-labelledby="elements-search-title">
        <CardHeader className="elements-toolbar">
          <div>
            <h2 className="section-title" id="elements-search-title">{t('explore.elements_title')}</h2>
            <div className="selected-summary">
              <span>{t('explore.selected')}</span>
              <Chip color={selected.length ? 'accent' : 'default'} variant="soft" >{selectedLabel}</Chip>
            </div>
          </div>

          <div className="elements-controls">
            <div className="toolbar" role="group" aria-label={t('explore.elements_title')}>
              {[
                ['elements_combination_search', t('explore.mode_combination')],
                ['elements_exact_search', t('explore.mode_exact')],
                ['elements_contained_search', t('explore.mode_contains')],
              ].map(([key, label]) => (
                <Button
                  key={key}
                  variant={mode === key ? 'secondary' : 'outline'}
                  onPress={() => setMode(key)}
                >
                  {label}
                </Button>
              ))}
            </div>
            <div className="toolbar">
              <Button variant="outline"  onPress={() => setSelected([])}>{t('explore.clear')}</Button>
              <Button variant="primary"  isDisabled={!selected.length} onPress={goElements}>{t('explore.enter')}</Button>
            </div>
          </div>
        </CardHeader>
        <Separator />
        <CardContent>

        <div className="periodic-table-container">
          <div className="periodic-table">
            {cells.map((element, index) => (
              element ? (
                <button
                  key={`${element.symbol}-${index}`}
                  className={[
                    'element',
                    element.category,
                    element.exist === 'synthetic' ? 'synthetic' : '',
                    element.radioactive ? 'radioactive' : '',
                    selected.includes(element.symbol) ? 'selected' : '',
                  ].filter(Boolean).join(' ')}
                  style={{ ['--i' as string]: index }}
                  disabled={element.radioactive || element.rangeLabel}
                  onClick={() => toggle(element.symbol)}
                  title={element.symbol}
                >
                  <span className="atomic-number">{element.number}</span>
                  <span className="symbol">{element.symbol}</span>
                </button>
              ) : (
                <span key={`empty-${index}`} className="element empty" aria-hidden="true" />
              )
            ))}
          </div>
        </div>
        <p className="muted explore-hint">{t('explore.hint')}</p>
        </CardContent>
      </Card>
    </section>
  )
}

function buildPeriodicCells(): Array<PeriodicElement | null> {
  const cells: Array<PeriodicElement | null> = []
  for (let row = 1; row <= 10; row += 1) {
    for (let col = 1; col <= 18; col += 1) {
      cells.push(periodicElements.find((element) => element.row === row && element.col === col) || null)
    }
  }
  return cells
}

export default ElementsPage
