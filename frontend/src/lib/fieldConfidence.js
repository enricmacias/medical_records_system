/** Which structured field paths can be highlighted for low-confidence empty values. */
export const HIGHLIGHTABLE_FIELD_PATHS = [
  'pet.name',
  'pet.species',
  'pet.breed',
  'pet.sex',
  'pet.date_of_birth',
  'pet.microchip',
  'owner.name',
  'owner.phone',
  'owner.email',
  'owner.address',
  'clinical.history',
]

export function isValueEmpty(value) {
  return value == null || String(value).trim() === ''
}

export function isMissingFieldPath(path, missingFields = []) {
  return missingFields.includes(path)
}

/**
 * Returns highlight reason for a field, or null if no highlight.
 * - `missing` — listed in meta.missing_fields
 * - `low-confidence` — overall confidence is low and value is still empty
 */
export function getFieldHighlight(path, { meta = {}, value, isProcessing = false } = {}) {
  const missingFields = meta.missing_fields || []

  if (isMissingFieldPath(path, missingFields)) {
    if (path === 'clinical.history' && isProcessing) return null
    return 'missing'
  }

  if (meta.extraction_confidence === 'low') {
    if (HIGHLIGHTABLE_FIELD_PATHS.includes(path) && isValueEmpty(value)) {
      if (path === 'clinical.history' && isProcessing) return null
      return 'low-confidence'
    }
  }

  return null
}

export function isLowExtractionConfidence(meta) {
  return meta?.extraction_confidence === 'low'
}
