import { renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { LanguageProvider, translateProcessingStep, useLanguage } from './LanguageContext'
import { documentLocaleFromSource, resolveLocale } from './translations'

function renderLanguage(locale) {
  return renderHook(() => useLanguage(), {
    wrapper: ({ children }) => (
      <LanguageProvider initialLocale={locale}>{children}</LanguageProvider>
    ),
  })
}

describe('translations helpers', () => {
  it('resolveLocale normalizes to en or es', () => {
    expect(resolveLocale('es')).toBe('es')
    expect(resolveLocale('en')).toBe('en')
    expect(resolveLocale('fr')).toBe('en')
  })

  it('documentLocaleFromSource maps ISO codes', () => {
    expect(documentLocaleFromSource('es')).toBe('es')
    expect(documentLocaleFromSource('en-US')).toBe('en')
    expect(documentLocaleFromSource('fr')).toBeNull()
    expect(documentLocaleFromSource(null)).toBeNull()
  })
})

describe('translateProcessingStep', () => {
  it('translates step ids in English', () => {
    const { result } = renderLanguage('en')
    const { t } = result.current
    expect(translateProcessingStep(t, 'clinical_summary')).toBe('Writing the clinical summary…')
  })

  it('translates step ids in Spanish', () => {
    const { result } = renderLanguage('es')
    const { t } = result.current
    expect(translateProcessingStep(t, 'clinical_summary')).toBe('Escribiendo el resumen clínico…')
  })

  it('uses demographics_ready message when percent is at least 35', () => {
    const { result } = renderLanguage('en')
    const { t } = result.current
    expect(
      translateProcessingStep(t, { step: 'demographics', percent: 35, message: 'ignored' }),
    ).toBe('Pet and owner details are ready. Clinical summary in progress…')
  })

  it('uses demographics extract message below 35 percent', () => {
    const { result } = renderLanguage('en')
    const { t } = result.current
    expect(
      translateProcessingStep(t, { step: 'demographics', percent: 20, message: 'ignored' }),
    ).toBe('Extracting pet and owner details from the document…')
  })
})

describe('useLanguage', () => {
  it('interpolates translation parameters', () => {
    const { result } = renderLanguage('en')
    expect(result.current.t('record.status', { status: 'completed' })).toBe('Status: completed')
  })

  it('falls back to English for missing keys', () => {
    const { result } = renderLanguage('es')
    expect(result.current.t('nonexistent.key')).toBe('nonexistent.key')
  })
})
