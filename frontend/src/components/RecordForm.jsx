import { useEffect, useMemo, useState } from 'react'
import {
  buildClinicalResume,
  buildStructuredPetPayload,
  displaySpecies,
  formatMedicationsList,
  isStructuredRecordDirty,
  normalizeSpeciesForStorage,
  parseMedicationsList,
} from '../lib/recordDisplay'

export const STRUCTURED_FORM_ID = 'structured-record-form'

function displayValue(value) {
  if (value == null || String(value).trim() === '') return '—'
  return value
}

function Field({ label, value, onChange, editing }) {
  if (!editing) {
    return (
      <div className="field field-readonly">
        <span>{label}</span>
        <p className="field-value">{displayValue(value)}</p>
      </div>
    )
  }
  return (
    <label className="field">
      <span>{label}</span>
      <input value={value ?? ''} onChange={(e) => onChange(e.target.value || null)} />
    </label>
  )
}

function TextArea({ label, value, onChange, rows = 3, maxLength, hint, editing }) {
  if (!editing) {
    return (
      <div className="field field-readonly">
        <span>{label}</span>
        <p className="field-value field-value-block">{displayValue(value)}</p>
      </div>
    )
  }
  const length = (value ?? '').length
  return (
    <label className="field">
      <span>{label}</span>
      <textarea
        rows={rows}
        maxLength={maxLength}
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
      />
      {hint || maxLength ? (
        <span className="field-hint">
          {hint}
          {maxLength ? `${length}/${maxLength}` : ''}
        </span>
      ) : null}
    </label>
  )
}

function SpeciesField({ value, onChange, editing }) {
  if (!editing) {
    return (
      <div className="field field-readonly">
        <span>Species</span>
        <p className="field-value">{displaySpecies(value)}</p>
      </div>
    )
  }
  const selectValue = normalizeSpeciesForStorage(value) ?? ''
  return (
    <label className="field">
      <span>Species</span>
      <select value={selectValue} onChange={(e) => onChange(e.target.value || null)}>
        <option value="">—</option>
        <option value="Dog">Dog</option>
        <option value="Cat">Cat</option>
      </select>
    </label>
  )
}

function normalizePetForForm(pet) {
  if (!pet) return {}
  return {
    ...pet,
    species: normalizeSpeciesForStorage(pet.species) ?? pet.species ?? null,
  }
}

export default function RecordForm({ initial, onSave, editing, onDirtyChange }) {
  const seed = useMemo(() => {
    const clone = structuredClone(initial)
    clone.pet = normalizePetForForm(clone.pet || {})
    clone.owner = clone.owner || {}
    clone.visit = clone.visit || {}
    clone.clinical = clone.clinical || {}
    clone.clinical.medications = clone.clinical.medications || []
    clone.clinical.history_entries = clone.clinical.history_entries || []
    clone.meta = clone.meta || {}
    return clone
  }, [initial])

  const clinicalSummary = useMemo(() => buildClinicalResume(seed.clinical), [seed])
  const baselineMedications = useMemo(
    () => formatMedicationsList(seed.clinical.medications),
    [seed],
  )

  const [data, setData] = useState(seed)
  const [medicationsText, setMedicationsText] = useState(baselineMedications)

  const dirty = useMemo(
    () =>
      isStructuredRecordDirty({
        data,
        seed,
        medicationsText,
        baselineMedications,
      }),
    [data, medicationsText, seed, baselineMedications],
  )

  useEffect(() => {
    onDirtyChange?.(dirty)
  }, [dirty, onDirtyChange])

  function setPet(key, value) {
    setData((prev) => ({ ...prev, pet: { ...prev.pet, [key]: value } }))
  }

  function setOwner(key, value) {
    setData((prev) => ({ ...prev, owner: { ...prev.owner, [key]: value } }))
  }

  function handleSave(event) {
    event.preventDefault()
    if (!editing) return
    const payload = {
      ...data,
      pet: buildStructuredPetPayload(data.pet),
      clinical: {
        ...data.clinical,
        history: seed.clinical?.history ?? null,
        medications: parseMedicationsList(medicationsText),
      },
    }
    onSave(payload)
  }

  return (
    <form
      id={STRUCTURED_FORM_ID}
      className={`record-form${editing ? '' : ' record-form-readonly'}`}
      onSubmit={handleSave}
    >
      <fieldset disabled={!editing}>
        <legend>Pet</legend>
        <div className="grid">
          <Field
            label="Name"
            value={data.pet?.name}
            onChange={(v) => setPet('name', v)}
            editing={editing}
          />
          <SpeciesField
            value={data.pet?.species}
            onChange={(v) => setPet('species', v)}
            editing={editing}
          />
          <Field
            label="Breed"
            value={data.pet?.breed}
            onChange={(v) => setPet('breed', v)}
            editing={editing}
          />
          <Field
            label="Sex"
            value={data.pet?.sex}
            onChange={(v) => setPet('sex', v)}
            editing={editing}
          />
          <Field
            label="Date of birth"
            value={data.pet?.date_of_birth}
            onChange={(v) => setPet('date_of_birth', v)}
            editing={editing}
          />
          <Field
            label="Microchip"
            value={data.pet?.microchip}
            onChange={(v) => setPet('microchip', v)}
            editing={editing}
          />
        </div>
      </fieldset>

      <fieldset disabled={!editing}>
        <legend>Owner</legend>
        <div className="grid">
          <Field
            label="Name"
            value={data.owner?.name}
            onChange={(v) => setOwner('name', v)}
            editing={editing}
          />
          <Field
            label="Phone"
            value={data.owner?.phone}
            onChange={(v) => setOwner('phone', v)}
            editing={editing}
          />
          <Field
            label="Email"
            value={data.owner?.email}
            onChange={(v) => setOwner('email', v)}
            editing={editing}
          />
        </div>
        <TextArea
          label="Address"
          value={data.owner?.address}
          onChange={(v) => setOwner('address', v)}
          rows={2}
          editing={editing}
        />
      </fieldset>

      <fieldset>
        <legend>Clinical summary</legend>
        <TextArea
          label="Clinical summary"
          value={clinicalSummary}
          onChange={() => {}}
          rows={8}
          hint="Auto-generated on upload; not editable."
          editing={false}
        />
      </fieldset>

      <fieldset disabled={!editing}>
        <legend>Medications</legend>
        <TextArea
          label="All medications"
          value={medicationsText}
          onChange={(v) => setMedicationsText(v ?? '')}
          rows={6}
          hint="One medication per line (optional dosage/frequency in parentheses)."
          editing={editing}
        />
      </fieldset>

      <fieldset>
        <legend>Meta</legend>
        <p className="muted">
          Confidence: {data.meta?.extraction_confidence || 'n/a'} · Language:{' '}
          {data.meta?.source_language || 'n/a'}
        </p>
        {(data.meta?.missing_fields || []).length > 0 && (
          <p className="muted">Missing: {data.meta.missing_fields.join(', ')}</p>
        )}
      </fieldset>
    </form>
  )
}
