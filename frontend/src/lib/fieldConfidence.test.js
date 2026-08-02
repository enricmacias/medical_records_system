import { describe, expect, it } from 'vitest'
import {
  getFieldHighlight,
  isLowExtractionConfidence,
  isMissingFieldPath,
  isValueEmpty,
} from './fieldConfidence'

describe('fieldConfidence', () => {
  it('detects empty values', () => {
    expect(isValueEmpty(null)).toBe(true)
    expect(isValueEmpty('')).toBe(true)
    expect(isValueEmpty('  ')).toBe(true)
    expect(isValueEmpty('Buddy')).toBe(false)
  })

  it('flags paths listed in missing_fields', () => {
    expect(
      getFieldHighlight('pet.name', {
        meta: { missing_fields: ['pet.name'] },
        value: 'Buddy',
      }),
    ).toBe('missing')
  })

  it('flags empty fields when extraction confidence is low', () => {
    expect(
      getFieldHighlight('owner.phone', {
        meta: { extraction_confidence: 'low', missing_fields: [] },
        value: null,
      }),
    ).toBe('low-confidence')
  })

  it('does not flag filled fields when confidence is low', () => {
    expect(
      getFieldHighlight('owner.phone', {
        meta: { extraction_confidence: 'low', missing_fields: [] },
        value: '+34 600',
      }),
    ).toBeNull()
  })

  it('does not flag clinical.history while processing', () => {
    expect(
      getFieldHighlight('clinical.history', {
        meta: { missing_fields: ['clinical.history'] },
        value: null,
        isProcessing: true,
      }),
    ).toBeNull()
  })

  it('detects low extraction confidence on meta', () => {
    expect(isLowExtractionConfidence({ extraction_confidence: 'low' })).toBe(true)
    expect(isLowExtractionConfidence({ extraction_confidence: 'high' })).toBe(false)
    expect(isMissingFieldPath('pet.breed', ['pet.breed'])).toBe(true)
  })
})
