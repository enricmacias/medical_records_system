import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import RecordForm, { STRUCTURED_FORM_ID } from './RecordForm'
import { renderWithI18n } from '../test/renderWithI18n'

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
    renderWithI18n(
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

  it('formats date of birth with month name in the site language', () => {
    renderWithI18n(
      <RecordForm
        initial={sampleRecord}
        onSave={vi.fn()}
        editing={false}
        onDirtyChange={vi.fn()}
      />,
      { locale: 'en' },
    )
    expect(screen.getByText('October 4, 2019')).toBeInTheDocument()
  })

  it('shows Spanish labels when site language is Spanish', () => {
    renderWithI18n(
      <RecordForm
        initial={sampleRecord}
        onSave={vi.fn()}
        editing={false}
        onDirtyChange={vi.fn()}
      />,
      { locale: 'es' },
    )
    expect(screen.getByText('Mascota')).toBeInTheDocument()
    expect(screen.getByText('Propietario')).toBeInTheDocument()
    expect(screen.getByText('4 de octubre de 2019')).toBeInTheDocument()
    expect(screen.getByText('Marley')).toBeInTheDocument()
    expect(screen.getByText('Beatriz Abarca')).toBeInTheDocument()
  })

  it('localizes sex display in read-only mode', () => {
    renderWithI18n(
      <RecordForm
        initial={sampleRecord}
        onSave={vi.fn()}
        editing={false}
        onDirtyChange={vi.fn()}
      />,
      { locale: 'es' },
    )
    expect(screen.getByText('Macho')).toBeInTheDocument()
  })

  it('keeps raw sex value when saving in edit mode', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn()

    renderWithI18n(
      <div>
        <button type="submit" form={STRUCTURED_FORM_ID}>Save</button>
        <RecordForm
          initial={sampleRecord}
          onSave={onSave}
          editing={true}
          onDirtyChange={vi.fn()}
        />
      </div>,
      { locale: 'es' },
    )

    await user.click(screen.getByRole('button', { name: 'Save' }))
    expect(onSave.mock.calls[0][0].pet.sex).toBe('M')
  })

  it('formats dates embedded in clinical summary for display', () => {
    renderWithI18n(
      <RecordForm
        initial={{
          ...sampleRecord,
          clinical: { history: 'Visit on 08/04/20.' },
        }}
        onSave={vi.fn()}
        editing={false}
        onDirtyChange={vi.fn()}
      />,
      { locale: 'en' },
    )
    expect(screen.getByText(/Visit on April 8, 2020/i)).toBeInTheDocument()
  })

  it('displays multi-paragraph clinical summary with preserved line breaks', () => {
    const multiParagraph = {
      ...sampleRecord,
      clinical: {
        history: 'First paragraph about giardiasis.\n\nSecond paragraph about visits.',
      },
    }
    renderWithI18n(
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

    renderWithI18n(
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

    renderWithI18n(
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

  it('shows progress while clinical summary is still generating', () => {
    renderWithI18n(
      <RecordForm
        initial={{
          ...sampleRecord,
          clinical: { history: null },
        }}
        onSave={vi.fn()}
        editing={false}
        onDirtyChange={vi.fn()}
        isProcessing={true}
        processing={{
          percent: 65,
          step: 'clinical_summary',
          message: 'Writing the clinical summary…',
        }}
      />,
    )

    expect(screen.getByText('65%')).toBeInTheDocument()
    expect(screen.getByText('Writing the clinical summary…')).toBeInTheDocument()
    expect(screen.queryByText('Stored clinical summary from extraction.')).not.toBeInTheDocument()
  })

  it('shows a fallback message when processing without progress details', () => {
    renderWithI18n(
      <RecordForm
        initial={{
          ...sampleRecord,
          clinical: { history: null },
        }}
        onSave={vi.fn()}
        editing={false}
        onDirtyChange={vi.fn()}
        isProcessing={true}
        processing={null}
      />,
    )

    expect(screen.getByText('Generating clinical summary…')).toBeInTheDocument()
    expect(screen.queryByText('65%')).not.toBeInTheDocument()
  })

  it('preserves clinical summary on save and only sends persisted fields', async () => {
    const user = userEvent.setup()
    const onSave = vi.fn()

    renderWithI18n(
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

  it('highlights fields listed in missing_fields', () => {
    renderWithI18n(
      <RecordForm
        initial={{
          ...sampleRecord,
          pet: { ...sampleRecord.pet, breed: null },
          meta: {
            ...sampleRecord.meta,
            missing_fields: ['pet.breed'],
          },
        }}
        onSave={vi.fn()}
        editing={false}
        onDirtyChange={vi.fn()}
      />,
    )

    expect(screen.getByText('Not extracted')).toBeInTheDocument()
    expect(document.querySelector('.field-flagged-missing')).toBeInTheDocument()
  })

  it('shows low-confidence notice and highlights empty fields', () => {
    renderWithI18n(
      <RecordForm
        initial={{
          ...sampleRecord,
          owner: { ...sampleRecord.owner, phone: null, email: null },
          meta: {
            extraction_confidence: 'low',
            source_language: 'es',
            missing_fields: [],
          },
        }}
        onSave={vi.fn()}
        editing={false}
        onDirtyChange={vi.fn()}
      />,
    )

    expect(
      screen.getByText(/Extraction confidence is low/i),
    ).toBeInTheDocument()
    expect(screen.getAllByText('Uncertain').length).toBeGreaterThan(0)
    expect(document.querySelector('.field-flagged-low-confidence')).toBeInTheDocument()
    expect(document.querySelector('.meta-confidence-low')).toHaveTextContent('low')
  })

  it('shows Spanish highlight labels when site language is Spanish', () => {
    renderWithI18n(
      <RecordForm
        initial={{
          ...sampleRecord,
          pet: { ...sampleRecord.pet, microchip: null },
          meta: {
            extraction_confidence: 'medium',
            source_language: 'es',
            missing_fields: ['pet.microchip'],
          },
        }}
        onSave={vi.fn()}
        editing={false}
        onDirtyChange={vi.fn()}
      />,
      { locale: 'es' },
    )

    expect(screen.getByText('No extraído')).toBeInTheDocument()
  })
})
