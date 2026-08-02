import React from 'react'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import RecordPage from './RecordPage'
import { renderWithI18n } from '../test/renderWithI18n'

vi.mock('../api', () => ({
  getRecord: vi.fn(),
  updateRecord: vi.fn(),
  fileUrl: (id) => `/api/records/${id}/file`,
}))

import { getRecord, updateRecord } from '../api'

const structuredData = {
  pet: {
    name: 'Marley',
    species: 'Canino',
    breed: 'Labrador',
    sex: 'M',
    date_of_birth: '04/10/19',
    microchip: '941000024967769',
  },
  owner: { name: 'Beatriz', phone: null, email: null, address: null },
  clinical: { history: 'Visit summary' },
  meta: {
    extraction_confidence: 'medium',
    source_language: 'es',
    missing_fields: [],
  },
}

function renderPage(locale = 'en') {
  return renderWithI18n(
    <MemoryRouter initialEntries={['/records/rec-1']}>
      <Routes>
        <Route path="/records/:id" element={<RecordPage />} />
      </Routes>
    </MemoryRouter>,
    { locale },
  )
}

async function structuredPanel() {
  const heading = await screen.findByRole('heading', { name: 'Structured record' })
  return heading.closest('.panel')
}

describe('RecordPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getRecord.mockResolvedValue({
      id: 'rec-1',
      original_filename: 'marley.pdf',
      status: 'completed',
      error_message: null,
      raw_text: 'RAW PDF TEXT CONTENT',
      structured_data: structuredData,
      updated_at: '2026-08-01T10:00:00Z',
    })
    updateRecord.mockImplementation(async (_id, data) => ({
      id: 'rec-1',
      original_filename: 'marley.pdf',
      status: 'completed',
      error_message: null,
      raw_text: 'RAW PDF TEXT CONTENT',
      structured_data: data,
      updated_at: '2026-08-01T10:05:00Z',
    }))
  })

  it('hides extracted text until the Extracted text button is clicked', async () => {
    const user = userEvent.setup()
    renderPage()

    await screen.findByRole('heading', { name: 'Marley' })
    expect(screen.queryByText('RAW PDF TEXT CONTENT')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Extracted text' }))
    expect(screen.getByText('RAW PDF TEXT CONTENT')).toBeInTheDocument()
  })

  it('keeps structured fields read-only until Edit is clicked', async () => {
    const user = userEvent.setup()
    renderPage()

    const panel = await structuredPanel()
    expect(within(panel).getByText('Marley')).toBeInTheDocument()
    expect(within(panel).getByText('Dog')).toBeInTheDocument()
    expect(within(panel).getByText('Visit summary')).toBeInTheDocument()
    expect(within(panel).queryByRole('button', { name: 'Save corrections' })).not.toBeInTheDocument()
    expect(within(panel).queryByRole('textbox')).not.toBeInTheDocument()

    await user.click(within(panel).getByRole('button', { name: 'Edit' }))
    expect(within(panel).getByRole('button', { name: 'Save corrections' })).toBeInTheDocument()
    expect(within(panel).getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
    expect(within(panel).getAllByRole('textbox').length).toBeGreaterThan(0)
  })

  it('warns before discarding unsaved edits', async () => {
    const user = userEvent.setup()
    renderPage()

    const panel = await structuredPanel()
    await user.click(within(panel).getByRole('button', { name: 'Edit' }))

    const nameInputs = within(panel).getAllByLabelText('Name')
    await user.clear(nameInputs[0])
    await user.type(nameInputs[0], 'Buddy')

    await user.click(within(panel).getByRole('button', { name: 'Cancel' }))
    expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    expect(screen.getByText(/Modified fields will not be saved/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Continue' }))
    await waitFor(() => {
      expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    })
    expect(within(panel).getByRole('button', { name: 'Edit' })).toBeInTheDocument()
    expect(within(panel).getByText('Marley')).toBeInTheDocument()
  })

  it('shows partial structured data and progress while processing', async () => {
    getRecord.mockResolvedValue({
      id: 'rec-1',
      original_filename: 'marley.pdf',
      status: 'processing',
      error_message: null,
      raw_text: 'RAW PDF TEXT CONTENT',
      structured_data: {
        pet: { name: 'Marley', species: 'Dog' },
        owner: { name: 'Beatriz' },
        clinical: { history: null },
        meta: { extraction_confidence: 'high', source_language: 'es', missing_fields: [] },
      },
      processing: {
        percent: 65,
        step: 'clinical_summary',
        message: 'Writing the clinical summary…',
      },
      updated_at: '2026-08-01T10:00:00Z',
    })

    renderPage()

    await screen.findByRole('heading', { name: 'Marley' })
    const panel = await structuredPanel()
    expect(within(panel).getByText('Marley')).toBeInTheDocument()
    expect(within(panel).getByText('65%')).toBeInTheDocument()
    expect(within(panel).getByText('Writing the clinical summary…')).toBeInTheDocument()
    expect(within(panel).getByRole('button', { name: 'Edit' })).toBeDisabled()
  })

  it('shows processing panel before structured data is available', async () => {
    getRecord.mockResolvedValue({
      id: 'rec-1',
      original_filename: 'marley.pdf',
      status: 'processing',
      error_message: null,
      raw_text: null,
      structured_data: null,
      processing: {
        percent: 15,
        step: 'extracting_text',
        message: 'Reading text from your PDF…',
      },
      updated_at: '2026-08-01T10:00:00Z',
    })

    renderPage()

    await screen.findByRole('heading', { name: 'Processing your document' })
    expect(screen.getByText('15%')).toBeInTheDocument()
    expect(screen.getByText('Reading text from your PDF…')).toBeInTheDocument()
    expect(
      screen.getByText(/Structured fields will appear shortly as each section is ready/i),
    ).toBeInTheDocument()
  })

  it('shows a success notice after saving corrections', async () => {
    const user = userEvent.setup()
    renderPage()

    const panel = await structuredPanel()
    await user.click(within(panel).getByRole('button', { name: 'Edit' }))

    const nameInputs = within(panel).getAllByLabelText('Name')
    await user.clear(nameInputs[0])
    await user.type(nameInputs[0], 'Buddy')

    await user.click(within(panel).getByRole('button', { name: 'Save corrections' }))

    await screen.findByText('Changes saved successfully.')
    expect(updateRecord).toHaveBeenCalledTimes(1)
    expect(within(await structuredPanel()).getByRole('button', { name: 'Edit' })).toBeInTheDocument()
  })

  it('suggests switching site language when PDF language differs', async () => {
    renderPage('en')

    await screen.findByRole('heading', { name: 'Marley' })
    expect(screen.getByText(/appears to be in Spanish/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Switch to Spanish' })).toBeInTheDocument()
  })

  it('shows Spanish record page chrome when site language is Spanish', async () => {
    renderPage('es')

    await screen.findByRole('heading', { name: 'Marley' })
    expect(screen.getByRole('heading', { name: 'Registro estructurado' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Texto extraído' })).toBeInTheDocument()
    expect(screen.queryByText(/appears to be in/i)).not.toBeInTheDocument()
  })

  it('translates processing status line in Spanish', async () => {
    getRecord.mockResolvedValue({
      id: 'rec-1',
      original_filename: 'marley.pdf',
      status: 'processing',
      error_message: null,
      raw_text: null,
      structured_data: null,
      processing: {
        percent: 15,
        step: 'extracting_text',
        message: 'Reading text from your PDF…',
      },
      updated_at: '2026-08-01T10:00:00Z',
    })

    renderPage('es')

    await screen.findByRole('heading', { name: 'marley.pdf' })
    expect(screen.getAllByText(/Leyendo el texto del PDF/i).length).toBeGreaterThan(0)
  })
})
