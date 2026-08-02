import { useState } from 'react'
import { useLanguage } from '../i18n/LanguageContext'
import { documentLocaleFromSource } from '../i18n/translations'

export default function LanguageSuggestionBanner({ sourceLanguage, recordId }) {
  const { locale, setLocale, t } = useLanguage()
  const docLocale = documentLocaleFromSource(sourceLanguage)
  const dismissKey = recordId ? `lang-hint-dismissed-${recordId}` : null

  const [dismissed, setDismissed] = useState(() => {
    if (!dismissKey) return false
    try {
      return localStorage.getItem(dismissKey) === '1'
    } catch {
      return false
    }
  })

  if (!docLocale || docLocale === locale || dismissed) return null

  const suggestedLocale = docLocale
  const suggestedLangName = t(`language.${suggestedLocale}`)
  const currentLangName = t(`language.${locale}`)

  function dismiss() {
    setDismissed(true)
    if (dismissKey) {
      try {
        localStorage.setItem(dismissKey, '1')
      } catch {
        /* ignore */
      }
    }
  }

  function accept() {
    setLocale(suggestedLocale)
    dismiss()
  }

  return (
    <div className="panel language-suggestion" role="status">
      <p className="muted">
        {t('language.suggestion', {
          docLang: suggestedLangName,
          siteLang: suggestedLangName,
        })}
      </p>
      <div className="language-suggestion-actions">
        <button type="button" className="primary-button heading-action-button" onClick={accept}>
          {t('language.switchTo', { lang: suggestedLangName })}
        </button>
        <button type="button" className="ghost-button" onClick={dismiss}>
          {t('language.dismiss', { lang: currentLangName })}
        </button>
      </div>
    </div>
  )
}
