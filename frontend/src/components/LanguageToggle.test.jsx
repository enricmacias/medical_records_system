import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import LanguageToggle from './LanguageToggle'
import { useLanguage } from '../i18n/LanguageContext'
import { renderWithI18n } from '../test/renderWithI18n'

function LocaleReader() {
  const { locale } = useLanguage()
  return <span data-testid="locale">{locale}</span>
}

describe('LanguageToggle', () => {
  it('renders English and Spanish options', () => {
    renderWithI18n(
      <>
        <LanguageToggle />
        <LocaleReader />
      </>,
      { locale: 'en' },
    )
    expect(screen.getByRole('button', { name: 'English' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'Spanish' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('switches locale when Spanish is selected', async () => {
    const user = userEvent.setup()
    renderWithI18n(
      <>
        <LanguageToggle />
        <LocaleReader />
      </>,
      { locale: 'en' },
    )

    await user.click(screen.getByRole('button', { name: 'Spanish' }))
    expect(screen.getByTestId('locale')).toHaveTextContent('es')
    expect(screen.getByRole('button', { name: 'Español' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('shows Spanish button labels when site is Spanish', () => {
    renderWithI18n(<LanguageToggle />, { locale: 'es' })
    expect(screen.getByRole('button', { name: 'Inglés' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Español' })).toBeInTheDocument()
  })
})
