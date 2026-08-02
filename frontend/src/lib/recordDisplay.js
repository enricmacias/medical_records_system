export const STRUCTURED_PET_FIELDS = [
  'name',
  'species',
  'breed',
  'sex',
  'date_of_birth',
  'microchip',
]

export function normalizeSpeciesForStorage(value) {
  if (value == null || String(value).trim() === '') return null
  const text = String(value).trim()
  const lower = text.toLowerCase()
  if (lower === 'dog' || /canino|canina|canine|perro/.test(lower)) return 'Dog'
  if (lower === 'cat' || /felino|felina|feline|gato|gata/.test(lower)) return 'Cat'
  if (text === 'Dog' || text === 'Cat') return text
  return null
}

export function displaySpecies(value) {
  const normalized = normalizeSpeciesForStorage(value)
  if (normalized) return normalized
  if (value == null || String(value).trim() === '') return '—'
  return value
}

export function buildStructuredPetPayload(pet) {
  return {
    name: pet?.name?.trim() || null,
    species: normalizeSpeciesForStorage(pet?.species),
    breed: pet?.breed?.trim() || null,
    sex: pet?.sex?.trim() || null,
    date_of_birth: pet?.date_of_birth?.trim() || null,
    microchip: pet?.microchip?.trim() || null,
  }
}

export function normalizeComparable(value) {
  if (value == null) return ''
  return String(value).trim()
}

export function isStructuredRecordDirty({
  data,
  seed,
  medicationsText,
  baselineMedications,
}) {
  const petChanged = STRUCTURED_PET_FIELDS.some(
    (key) =>
      normalizeComparable(data.pet?.[key]) !== normalizeComparable(seed.pet?.[key]),
  )
  const ownerKeys = ['name', 'phone', 'email', 'address']
  const ownerChanged = ownerKeys.some(
    (key) => normalizeComparable(data.owner?.[key]) !== normalizeComparable(seed.owner?.[key]),
  )
  const medsChanged =
    normalizeComparable(medicationsText) !== normalizeComparable(baselineMedications)
  return petChanged || ownerChanged || medsChanged
}

// Clinical summary helpers (stored in clinical.history).
export const CLINICAL_SUMMARY_MAX = 2000
export const CLINICAL_RESUME_MAX = CLINICAL_SUMMARY_MAX

export function buildClinicalResume(clinical) {
  if (clinical?.history?.trim()) {
    return clinical.history.trim().slice(0, CLINICAL_SUMMARY_MAX)
  }
  const entries = clinical?.history_entries || []
  if (!entries.length) {
    const parts = [clinical?.diagnosis, clinical?.chief_complaint, clinical?.treatment].filter(
      Boolean,
    )
    return parts.join('. ').slice(0, CLINICAL_SUMMARY_MAX)
  }
  const lines = entries
    .filter((e) => e?.date || e?.summary)
    .map((e) => `${e.date || '—'} — ${e.summary || ''}`.trim())
  let resume = ''
  for (const line of lines) {
    const next = resume ? `${resume}\n${line}` : line
    if (next.length > CLINICAL_SUMMARY_MAX) {
      const remaining = CLINICAL_SUMMARY_MAX - resume.length - 1
      if (remaining > 20) {
        resume = `${resume}\n${line.slice(0, remaining - 1)}…`
      }
      break
    }
    resume = next
  }
  return resume
}

export function formatMedicationsList(medications) {
  return (medications || [])
    .filter((m) => m?.name)
    .map((m) => {
      const extras = [m.dosage, m.frequency].filter(Boolean).join(', ')
      return extras ? `${m.name} (${extras})` : m.name
    })
    .join('\n')
}

export function parseMedicationsList(text) {
  if (!text?.trim()) return []
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const match = line.match(/^(.+?)\s*\((.+)\)\s*$/)
      if (!match) {
        return { name: line, dosage: null, frequency: null }
      }
      const name = match[1].trim()
      const parts = match[2].split(',').map((p) => p.trim()).filter(Boolean)
      return {
        name,
        dosage: parts[0] || null,
        frequency: parts.slice(1).join(', ') || null,
      }
    })
}
