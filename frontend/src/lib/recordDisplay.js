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

export function isStructuredRecordDirty({ data, seed }) {
  const petChanged = STRUCTURED_PET_FIELDS.some(
    (key) =>
      normalizeComparable(data.pet?.[key]) !== normalizeComparable(seed.pet?.[key]),
  )
  const ownerKeys = ['name', 'phone', 'email', 'address']
  const ownerChanged = ownerKeys.some(
    (key) => normalizeComparable(data.owner?.[key]) !== normalizeComparable(seed.owner?.[key]),
  )
  return petChanged || ownerChanged
}

export const CLINICAL_SUMMARY_MAX = 2000
export const CLINICAL_RESUME_MAX = CLINICAL_SUMMARY_MAX

export function buildClinicalResume(clinical) {
  if (clinical?.history?.trim()) {
    return clinical.history.trim().slice(0, CLINICAL_SUMMARY_MAX)
  }
  return ''
}
