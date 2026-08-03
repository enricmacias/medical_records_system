import { describe, expect, it } from 'vitest'
import {
  CLINICAL_SUMMARY_MAX,
  buildClinicalResume,
  buildStructuredPetPayload,
  displaySpecies,
  isStructuredRecordDirty,
  normalizeSexForStorage,
  normalizeSpeciesForStorage,
} from './recordDisplay'

describe('species normalization', () => {
  it('maps Spanish and English labels to Dog or Cat', () => {
    expect(normalizeSpeciesForStorage('Canino')).toBe('Dog')
    expect(normalizeSpeciesForStorage('CANINA')).toBe('Dog')
    expect(normalizeSpeciesForStorage('Felino')).toBe('Cat')
    expect(normalizeSpeciesForStorage('Felina')).toBe('Cat')
    expect(normalizeSpeciesForStorage('dog')).toBe('Dog')
    expect(normalizeSpeciesForStorage('Gato')).toBe('Cat')
    expect(normalizeSpeciesForStorage('unknown')).toBeNull()
  })

  it('displays normalized species labels', () => {
    expect(displaySpecies('Canino')).toBe('Dog')
    expect(displaySpecies(null)).toBe('—')
  })
})

describe('sex normalization', () => {
  it('maps Spanish and English labels to Male or Female', () => {
    expect(normalizeSexForStorage('M')).toBe('Male')
    expect(normalizeSexForStorage('Macho')).toBe('Male')
    expect(normalizeSexForStorage('H')).toBe('Female')
    expect(normalizeSexForStorage('Hembra')).toBe('Female')
    expect(normalizeSexForStorage('Female (Spayed)')).toBe('Female')
    expect(normalizeSexForStorage('unknown')).toBeNull()
  })
})

describe('buildStructuredPetPayload', () => {
  it('returns only the six structured pet fields', () => {
    expect(
      buildStructuredPetPayload({
        name: 'ALYA',
        species: 'Canino',
        breed: 'Labrador',
        sex: 'F',
        date_of_birth: '05/07/2018',
        microchip: '123',
      }),
    ).toEqual({
      name: 'ALYA',
      species: 'Dog',
      breed: 'Labrador',
      sex: 'Female',
      date_of_birth: '05/07/2018',
      microchip: '123',
    })
  })

  it('normalizes legacy sex codes and leaves breed as trimmed text', () => {
    expect(
      buildStructuredPetPayload({
        name: 'Marley',
        species: 'Dog',
        breed: '  Golden Retriever  ',
        sex: 'Macho',
        date_of_birth: null,
        microchip: null,
      }),
    ).toEqual({
      name: 'Marley',
      species: 'Dog',
      breed: 'Golden Retriever',
      sex: 'Male',
      date_of_birth: null,
      microchip: null,
    })
  })
})

describe('buildClinicalResume', () => {
  it('returns clinical.history when present', () => {
    const resume = buildClinicalResume({
      history: 'Overall case summary',
    })
    expect(resume).toBe('Overall case summary')
  })

  it('preserves paragraph breaks from stored clinical.history', () => {
    const resume = buildClinicalResume({
      history: 'First paragraph.\n\nSecond paragraph.',
    })
    expect(resume).toBe('First paragraph.\n\nSecond paragraph.')
  })

  it('caps resume length at 2000 characters', () => {
    const longSummary = 'x'.repeat(CLINICAL_SUMMARY_MAX + 50)
    const resume = buildClinicalResume({ history: longSummary })
    expect(resume).toHaveLength(CLINICAL_SUMMARY_MAX)
  })

  it('returns empty string when history is absent', () => {
    expect(buildClinicalResume({})).toBe('')
  })
})

describe('isStructuredRecordDirty', () => {
  const seed = {
    pet: {
      name: 'Marley',
      species: 'Dog',
      breed: 'Labrador',
      sex: 'M',
      date_of_birth: '04/10/19',
      microchip: '941000024967769',
    },
    owner: { name: 'Beatriz', phone: null, email: null, address: null },
  }

  it('is false when all tracked fields match the baseline', () => {
    expect(isStructuredRecordDirty({ data: structuredClone(seed), seed })).toBe(false)
  })

  it('is true when a pet field changes', () => {
    expect(
      isStructuredRecordDirty({
        data: { ...seed, pet: { ...seed.pet, name: 'Buddy' } },
        seed,
      }),
    ).toBe(true)
  })

  it('is false when only clinical.history changes (summary is not editable)', () => {
    const data = structuredClone(seed)
    data.clinical = { history: 'A different summary from extraction.' }
    expect(isStructuredRecordDirty({ data, seed })).toBe(false)
  })
})
