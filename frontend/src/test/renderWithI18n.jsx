import { render } from '@testing-library/react'
import { LanguageProvider } from '../i18n/LanguageContext'

export function renderWithI18n(ui, { locale = 'en', ...options } = {}) {
  return render(
    <LanguageProvider initialLocale={locale}>{ui}</LanguageProvider>,
    options,
  )
}
