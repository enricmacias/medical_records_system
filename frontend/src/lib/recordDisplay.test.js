import { describe, expect, it } from 'vitest'
import {
  CLINICAL_RESUME_MAX,
  buildClinicalResume,
  formatMedicationsList,
  isStructuredRecordDirty,
  parseMedicationsList,
} from './recordDisplay'

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

  it('caps resume length at 1000 characters', () => {
    const longSummary = 'x'.repeat(1200)
    const resume = buildClinicalResume({ history: longSummary })
    expect(resume).toHaveLength(CLINICAL_RESUME_MAX)
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
    pet: { name: 'Marley', species: 'Canino' },
    owner: { name: 'Beatriz', phone: null, email: null, address: null },
  }

  it('is false when values match the baseline', () => {
    expect(
      isStructuredRecordDirty({
        data: structuredClone(seed),
        seed,
        clinicalResume: 'same',
        baselineResume: 'same',
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
        clinicalResume: 'same',
        baselineResume: 'same',
        medicationsText: '',
        baselineMedications: '',
      }),
    ).toBe(true)
  })
})
