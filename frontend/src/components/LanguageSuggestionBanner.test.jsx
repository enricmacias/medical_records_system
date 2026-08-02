import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import LanguageSuggestionBanner from './LanguageSuggestionBanner'
import { renderWithI18n } from '../test/renderWithI18n'

describe('LanguageSuggestionBanner', () => {
  it('shows when document language differs from site language', () => {
    renderWithI18n(
      <LanguageSuggestionBanner sourceLanguage="es" recordId="rec-1" />,
      { locale: 'en' },
    )
    expect(screen.getByText(/appears to be in Spanish/i)).toBeInTheDocument()
  })

  it('does not show when languages match', () => {
    renderWithI18n(
      <LanguageSuggestionBanner sourceLanguage="es" recordId="rec-1" />,
      { locale: 'es' },
    )
    expect(screen.queryByText(/appears to be in/i)).not.toBeInTheDocument()
  })

  it('does not show when source language is unknown', () => {
    renderWithI18n(
      <LanguageSuggestionBanner sourceLanguage="fr" recordId="rec-1" />,
      { locale: 'en' },
    )
    expect(screen.queryByText(/appears to be in/i)).not.toBeInTheDocument()
  })

  it('switches site language when user accepts the suggestion', async () => {
    const user = userEvent.setup()
    renderWithI18n(
      <LanguageSuggestionBanner sourceLanguage="en" recordId="rec-2" />,
      { locale: 'es' },
    )

    await user.click(screen.getByRole('button', { name: 'Cambiar a Inglés' }))
    expect(screen.queryByText(/parece estar en/i)).not.toBeInTheDocument()
  })

  it('hides after dismiss without changing locale', async () => {
    const user = userEvent.setup()
    renderWithI18n(
      <LanguageSuggestionBanner sourceLanguage="es" recordId="rec-dismiss" />,
      { locale: 'en' },
    )

    await user.click(screen.getByRole('button', { name: 'Keep English' }))
    expect(screen.queryByText(/appears to be in Spanish/i)).not.toBeInTheDocument()
  })
})
