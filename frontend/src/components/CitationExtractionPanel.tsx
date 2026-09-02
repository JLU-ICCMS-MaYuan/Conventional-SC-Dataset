import React, { useState } from 'react'
import {
  Accordion, AccordionDetails, AccordionSummary, Alert, Box, Button, Chip, Typography,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { useLanguage } from '../context/LanguageContext'
import { CitationExtraction, CitationExtractionStatus } from '../lib/paperProcessing'

interface Props {
  extraction: CitationExtraction
}

const statusColors: Record<CitationExtractionStatus, 'success' | 'warning' | 'error' | 'info'> = {
  succeeded: 'success',
  partial: 'warning',
  failed: 'error',
  unavailable: 'info',
}

const CitationExtractionPanel: React.FC<Props> = ({ extraction }) => {
  const { t } = useLanguage()
  const [showAll, setShowAll] = useState(false)
  const previewLimit = 5
  const references = showAll ? extraction.references : extraction.references.slice(0, previewLimit)
  const remaining = Math.max(0, extraction.references.length - previewLimit)

  return (
    <Accordion disableGutters elevation={0} sx={{ mb: 2, border: 1, borderColor: 'divider', '&:before': { display: 'none' } }}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', minWidth: 0 }}>
          <Typography variant="subtitle2" fontWeight={700}>{t('upload.citationExtractionTitle')}</Typography>
          <Chip size="small" color={statusColors[extraction.status]} label={t(`upload.citationStatus.${extraction.status}`)} />
          <Typography variant="caption" color="text.secondary">
            {t('upload.citationReferenceCount', { count: extraction.references.length })}
          </Typography>
        </Box>
      </AccordionSummary>
      <AccordionDetails>
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
          {extraction.parser_name}{extraction.parser_version ? ` · ${extraction.parser_version}` : ''}
        </Typography>
        {extraction.error_message && <Alert severity={extraction.status === 'unavailable' ? 'info' : 'warning'} sx={{ mb: 1.5 }}>{extraction.error_message}</Alert>}
        {references.length === 0 ? (
          <Typography variant="body2" color="text.secondary">{t('upload.citationNoReferences')}</Typography>
        ) : (
          <Box sx={{ display: 'grid', gap: 1 }}>
            {references.map((reference, index) => (
              <Box key={`${reference.reference_index}-${index}`} sx={{ borderBottom: 1, borderColor: 'divider', pb: 1 }}>
                <Typography variant="caption" color="text.secondary" display="block">
                  #{reference.reference_index + 1}
                </Typography>
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
                  {reference.raw_citation}
                </Typography>
                {(reference.title || reference.doi || reference.year) && (
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5, overflowWrap: 'anywhere' }}>
                    {[reference.title, reference.doi, reference.year].filter(Boolean).join(' · ')}
                  </Typography>
                )}
              </Box>
            ))}
          </Box>
        )}
        {extraction.references.length > previewLimit && (
          <Button size="small" sx={{ mt: 1 }} onClick={() => setShowAll(value => !value)}>
            {showAll ? t('upload.citationShowLess') : t('upload.citationShowMore', { count: remaining })}
          </Button>
        )}
      </AccordionDetails>
    </Accordion>
  )
}

export default CitationExtractionPanel
