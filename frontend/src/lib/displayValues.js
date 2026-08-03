import { formatDisplayDate } from './formatDate'
import { translations } from '../i18n/translations'
import { normalizeSexForStorage, normalizeSpeciesForStorage } from './recordDisplay'

export function displaySex(value, locale, t) {
  const normalized = normalizeSexForStorage(value)
  if (normalized === 'Male') return t('sex.male')
  if (normalized === 'Female') return t('sex.female')
  if (value == null || String(value).trim() === '') return null
  return value
}

export function displaySpeciesLocalized(value, locale, t) {
  const normalized = normalizeSpeciesForStorage(value)
  if (normalized === 'Dog') return t('species.dog')
  if (normalized === 'Cat') return t('species.cat')
  if (value == null || String(value).trim() === '') return null
  return value
}

export function displayRecordDate(value, locale) {
  if (value == null || String(value).trim() === '') return null
  return formatDisplayDate(value, locale)
}

export function translateFieldPath(path, locale = 'en') {
  const fields = translations[locale]?.fields ?? translations.en.fields
  return fields[path] ?? path
}

export function translateStatus(t, status) {
  if (!status) return status
  const key = `status.${status}`
  const translated = t(key)
  return translated === key ? status : translated
}

export function translateConfidence(t, value) {
  if (!value) return value
  const key = `confidence.${value}`
  const translated = t(key)
  return translated === key ? value : translated
}

export function translateOllamaStatus(t, value) {
  if (!value) return value
  const key = `ollama.${value}`
  const translated = t(key)
  return translated === key ? value : translated
}
