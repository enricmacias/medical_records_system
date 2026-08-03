import React from 'react'
import { renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { LanguageProvider, useLanguage } from '../i18n/LanguageContext'
import {
  displayRecordDate,
  displaySex,
  displaySpeciesLocalized,
  translateConfidence,
  translateFieldPath,
  translateStatus,
} from './displayValues'

function tFor(locale) {
  const { result } = renderHook(() => useLanguage(), {
    wrapper: ({ children }) => (
      <LanguageProvider initialLocale={locale}>{children}</LanguageProvider>
    ),
  })
  return result.current.t
}

describe('displayValues', () => {
  it('localizes species for display without changing stored values', () => {
    const tEn = tFor('en')
    const tEs = tFor('es')
    expect(displaySpeciesLocalized('Canino', 'en', tEn)).toBe('Dog')
    expect(displaySpeciesLocalized('Canino', 'es', tEs)).toBe('Perro')
  })

  it('localizes sex codes and canonical values for display', () => {
    const tEn = tFor('en')
    const tEs = tFor('es')
    expect(displaySex('M', 'en', tEn)).toBe('Male')
    expect(displaySex('Male', 'en', tEn)).toBe('Male')
    expect(displaySex('Female', 'en', tEn)).toBe('Female')
    expect(displaySex('Male', 'es', tEs)).toBe('Macho')
    expect(displaySex('Female', 'es', tEs)).toBe('Hembra')
    expect(displaySex('Hembra', 'es', tEs)).toBe('Hembra')
  })

  it('formats record dates with localized month names', () => {
    expect(displayRecordDate('04/10/19', 'en')).toBe('October 4, 2019')
    expect(displayRecordDate('04/10/19', 'es')).toBe('4 de octubre de 2019')
  })

  it('translates status and confidence labels', () => {
    const tEs = tFor('es')
    expect(translateStatus(tEs, 'completed')).toBe('completado')
    expect(translateConfidence(tEs, 'high')).toBe('alta')
  })

  it('translates missing field paths for meta display', () => {
    expect(translateFieldPath('clinical.history', 'es')).toBe('Resumen clínico')
    expect(translateFieldPath('pet.microchip', 'es')).toBe('Microchip')
  })
})
