import { useLanguage } from '../i18n/LanguageContext'

export default function LanguageToggle() {
  const { locale, setLocale, t, locales } = useLanguage()

  return (
    <div className="language-toggle" role="group" aria-label={t('language.toggleLabel')}>
      {locales.map((code) => (
        <button
          key={code}
          type="button"
          className={`language-toggle-button${locale === code ? ' is-active' : ''}`}
          onClick={() => setLocale(code)}
          aria-pressed={locale === code}
        >
          {t(`language.${code}`)}
        </button>
      ))}
    </div>
  )
}
