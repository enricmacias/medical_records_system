import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import RecordForm, { STRUCTURED_FORM_ID } from './RecordForm'

const sampleRecord = {
  pet: {
    name: 'Marley',
    species: 'Canino',
    breed: 'Labrador',
    sex: 'M',
    date_of_birth: '04/10/19',
    microchip: '941000024967769',
  },
  owner: {
    name: 'Beatriz Abarca',
    phone: null,
    email: null,
    address: 'Madrid',
  },
  visit: {},
  clinical: {
    history: 'Stored clinical summary from extraction.',
    history_entries: [
      { date: '08/12/19', summary: 'Emergency visit' },
      { date: '03/10/20', summary: 'Conjunctivitis' },
    ],
    medications: [{ name: 'Tobradex', dosage: null, frequency: null }],
  },
  meta: {
    extraction_confidence: 'medium',
    source_language: 'es',
    missing_fields: [],
  },
}

describe('RecordForm', () => {
  it('renders pet identity fields and other structured sections read-only by default', () => {
    render(
      <RecordForm
        initial={sampleRecord}
        onSave={vi.fn()}
        editing={false}
        onDirtyChange={vi.fn()}
      />,
    )

    expect(screen.getByText('Pet')).toBeInTheDocument()
    expect(screen.getByText('Marley')).toBeInTheDocument()
    expect(screen.getByText('Dog')).toBeInTheDocument()
    expect(screen.getAllByText('Clinical summary').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Stored clinical summary from extraction.')).toBeInTheDocument()
    expect(screen.getByText('Tobradex')).toBeInTheDocument()
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
  })

  it('displays multi-paragraph clinical summary with preserved line breaks', () => {
    const multiParagraph = {
      ...sampleRecord,
      clinical: {
        ...sampleRecord.clinical,
        history: 'First paragraph about giardiasis.\n\nSecond paragraph about visits.',
      },
    }
    render(
      <RecordForm
        initial={multiParagraph}
        onSave={vi.fn()}
        editing={false}
        onDirtyChange={vi.fn()}
      />,
    )
    const summaryEl = screen.getByText((_, el) =>
      el?.classList?.contains('field-value-block') &&
      el.textContent?.includes('First paragraph about giardiasis.'),
    )
    expect(summaryEl.textContent).toContain('Second paragraph about visits.')
  })

  it('exposes editable fields and reports dirty changes while editing', async () => {
    const user = userEvent.setup()
    const onDirtyChange = vi.fn()

    render(
      <RecordForm
        initial={sampleRecord}
        onSave={vi.fn()}
        editing={true}
        onDirtyChange={onDirtyChange}
      />,
    )

    const nameInputs = screen.getAllByLabelText('Name')
    await user.clear(nameInputs[0])
    await user.type(nameInputs[0], 'Buddy')
    expect(onDirtyChange).toHaveBeenCalledWith(true)
  })

  it('saves the six structured pet fields on save', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn()

    render(
      <div>
        <button type="submit" form={STRUCTURED_FORM_ID}>
          Save corrections
        </button>
        <RecordForm
          initial={sampleRecord}
          onSave={onSave}
          editing={true}
          onDirtyChange={vi.fn()}
        />
      </div>,
    )

    const breed = screen.getByLabelText('Breed')
    await user.clear(breed)
    await user.type(breed, 'Golden Retriever')

    await user.click(screen.getByRole('button', { name: 'Save corrections' }))

    expect(onSave).toHaveBeenCalledTimes(1)
    const payload = onSave.mock.calls[0][0]
    expect(payload.pet).toEqual({
      name: 'Marley',
      species: 'Dog',
      breed: 'Golden Retriever',
      sex: 'M',
      date_of_birth: '04/10/19',
      microchip: '941000024967769',
    })
  })

  it('preserves clinical summary on save and updates medications', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn()

    render(
      <div>
        <button type="submit" form={STRUCTURED_FORM_ID}>
          Save corrections
        </button>
        <RecordForm
          initial={sampleRecord}
          onSave={onSave}
          editing={true}
          onDirtyChange={vi.fn()}
        />
      </div>,
    )

    expect(screen.queryByLabelText(/Clinical summary/)).not.toBeInTheDocument()

    const meds = screen.getByLabelText(/All medications/)
    await user.clear(meds)
    await user.type(meds, 'Fortiflora (1 sachet, daily)')

    await user.click(screen.getByRole('button', { name: 'Save corrections' }))

    expect(onSave).toHaveBeenCalledTimes(1)
    const payload = onSave.mock.calls[0][0]
    expect(payload.clinical.history).toBe('Stored clinical summary from extraction.')
    expect(payload.clinical.medications).toEqual([
      { name: 'Fortiflora', dosage: '1 sachet', frequency: 'daily' },
    ])
  })
})
