import { describe, expect, it } from 'vitest'
import {
  CLINICAL_RESUME_MAX,
  CLINICAL_SUMMARY_MAX,
  buildClinicalResume,
  buildStructuredPetPayload,
  displaySpecies,
  formatMedicationsList,
  isStructuredRecordDirty,
  normalizeSpeciesForStorage,
  parseMedicationsList,
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
      sex: 'F',
      date_of_birth: '05/07/2018',
      microchip: '123',
    })
  })
})

describe('buildClinicalResume', () => {
  it('prefers clinical.history when present', () => {
    const resume = buildClinicalResume({
      history: 'Overall case summary',
      history_entries: [{ date: '01/01/20', summary: 'Visit note' }],
    })
    expect(resume).toBe('Overall case summary')
  })

  it('builds a resume from visit history entries', () => {
    const resume = buildClinicalResume({
      history_entries: [
        { date: '08/12/19', summary: 'Emergency visit' },
        { date: '08/04/20', summary: 'Giardia positive' },
      ],
    })
    expect(resume).toContain('08/12/19 — Emergency visit')
    expect(resume).toContain('08/04/20 — Giardia positive')
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

  it('falls back to diagnosis fields when there are no entries', () => {
    const resume = buildClinicalResume({
      diagnosis: 'Otitis',
      chief_complaint: 'Ear scratching',
      treatment: 'Drops',
    })
    expect(resume).toBe('Otitis. Ear scratching. Drops')
  })
})

describe('medications list helpers', () => {
  it('formats medications as one line each', () => {
    const text = formatMedicationsList([
      { name: 'Fortiflora', dosage: '1 sachet', frequency: 'daily' },
      { name: 'Tobradex', dosage: null, frequency: null },
    ])
    expect(text).toBe('Fortiflora (1 sachet, daily)\nTobradex')
  })

  it('parses medication lines back into objects', () => {
    const meds = parseMedicationsList('Fortiflora (1 sachet, daily)\nTobradex\n')
    expect(meds).toEqual([
      { name: 'Fortiflora', dosage: '1 sachet', frequency: 'daily' },
      { name: 'Tobradex', dosage: null, frequency: null },
    ])
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
    expect(
      isStructuredRecordDirty({
        data: structuredClone(seed),
        seed,
        medicationsText: 'Fortiflora',
        baselineMedications: 'Fortiflora',
      }),
    ).toBe(false)
  })

  it('is true when a pet field changes', () => {
    expect(
      isStructuredRecordDirty({
        data: { ...seed, pet: { ...seed.pet, name: 'Buddy' } },
        seed,
        medicationsText: '',
        baselineMedications: '',
      }),
    ).toBe(true)
  })

  it('is false when only clinical.history changes (summary is not editable)', () => {
    const data = structuredClone(seed)
    data.clinical = { history: 'A different summary from extraction.' }
    expect(
      isStructuredRecordDirty({
        data,
        seed,
        medicationsText: '',
        baselineMedications: '',
      }),
    ).toBe(false)
  })
})
