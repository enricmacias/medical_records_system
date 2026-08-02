import React from 'react'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import RecordPage from './RecordPage'

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

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/records/rec-1']}>
      <Routes>
        <Route path="/records/:id" element={<RecordPage />} />
      </Routes>
    </MemoryRouter>,
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
})
