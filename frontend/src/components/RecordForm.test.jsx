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
  clinical: {
    history: 'Stored clinical summary from extraction.',
  },
  meta: {
    extraction_confidence: 'medium',
    source_language: 'es',
    missing_fields: [],
  },
}

describe('RecordForm', () => {
  it('renders only pet, owner, clinical summary, and meta sections', () => {
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
    expect(screen.getByText('Owner')).toBeInTheDocument()
    expect(screen.getAllByText('Clinical summary').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Stored clinical summary from extraction.')).toBeInTheDocument()
    expect(screen.getByText('Meta')).toBeInTheDocument()
    expect(screen.queryByText('Medications')).not.toBeInTheDocument()
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
  })

  it('displays multi-paragraph clinical summary with preserved line breaks', () => {
    const multiParagraph = {
      ...sampleRecord,
      clinical: {
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

  it('preserves clinical summary on save and only sends persisted fields', async () => {
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

    const phone = screen.getByLabelText('Phone')
    await user.type(phone, '+34 600 000 000')

    await user.click(screen.getByRole('button', { name: 'Save corrections' }))

    expect(onSave).toHaveBeenCalledTimes(1)
    const payload = onSave.mock.calls[0][0]
    expect(payload.clinical.history).toBe('Stored clinical summary from extraction.')
    expect(payload.owner.phone).toBe('+34 600 000 000')
    expect(payload.pet.breed).toBe('Labrador')
    expect(payload.meta).toEqual(sampleRecord.meta)
    expect(Object.keys(payload)).toEqual(['pet', 'owner', 'clinical', 'meta'])
  })
})
