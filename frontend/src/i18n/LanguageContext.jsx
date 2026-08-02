import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import {
  LOCALES,
  resolveLocale,
  translations,
} from './translations'

const STORAGE_KEY = 'vetrecords-ui-locale'

const LanguageContext = createContext(null)

function readStoredLocale() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored && LOCALES.includes(stored)) return stored
  } catch {
    /* ignore */
  }
  if (typeof navigator !== 'undefined' && navigator.language?.toLowerCase().startsWith('es')) {
    return 'es'
  }
  return 'en'
}

function interpolate(template, params = {}) {
  return template.replace(/\{\{(\w+)\}\}/g, (_, key) => params[key] ?? '')
}

function getNested(obj, path) {
  return path.split('.').reduce((acc, part) => acc?.[part], obj)
}

export function LanguageProvider({ children, initialLocale }) {
  const [locale, setLocaleState] = useState(() =>
    initialLocale ? resolveLocale(initialLocale) : readStoredLocale(),
  )

  const setLocale = useCallback((next) => {
    const resolved = resolveLocale(next)
    setLocaleState(resolved)
    try {
      localStorage.setItem(STORAGE_KEY, resolved)
    } catch {
      /* ignore */
    }
  }, [])

  const t = useCallback(
    (key, params) => {
      const value = getNested(translations[locale], key) ?? getNested(translations.en, key)
      if (typeof value !== 'string') return key
      return interpolate(value, params)
    },
    [locale],
  )

  const value = useMemo(
    () => ({ locale, setLocale, t, locales: LOCALES }),
    [locale, setLocale, t],
  )

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage() {
  const ctx = useContext(LanguageContext)
  if (!ctx) {
    throw new Error('useLanguage must be used within LanguageProvider')
  }
  return ctx
}

export function translateProcessingStep(t, processingOrStep) {
  if (typeof processingOrStep === 'string') {
    const key = `processing.${processingOrStep || 'processing'}`
    const translated = t(key)
    return translated === key ? t('processing.processing') : translated
  }

  const processing = processingOrStep
  if (!processing) return t('processing.processing')

  const { step, percent } = processing
  if (step === 'demographics' && percent >= 35) {
    return t('processing.demographics_ready')
  }

  const key = `processing.${step || 'processing'}`
  const translated = t(key)
  return translated === key ? t('processing.processing') : translated
}
