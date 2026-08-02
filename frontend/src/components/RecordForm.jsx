import { useEffect, useMemo, useState } from 'react'
import {
  buildClinicalResume,
  buildStructuredPetPayload,
  displaySpecies,
  isStructuredRecordDirty,
  normalizeSpeciesForStorage,
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

function TextArea({ label, value, onChange, rows = 3, hint, editing }) {
  if (!editing) {
    return (
      <div className="field field-readonly">
        <span>{label}</span>
        <p className="field-value field-value-block">{displayValue(value)}</p>
      </div>
    )
  }
  return (
    <label className="field">
      <span>{label}</span>
      <textarea rows={rows} value={value ?? ''} onChange={(e) => onChange(e.target.value || null)} />
      {hint ? <span className="field-hint">{hint}</span> : null}
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
    clone.clinical = clone.clinical || {}
    clone.meta = clone.meta || {}
    return clone
  }, [initial])

  const clinicalSummary = useMemo(() => buildClinicalResume(seed.clinical), [seed])

  const [data, setData] = useState(seed)

  const dirty = useMemo(
    () => isStructuredRecordDirty({ data, seed }),
    [data, seed],
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
    onSave({
      pet: buildStructuredPetPayload(data.pet),
      owner: {
        name: data.owner?.name?.trim() || null,
        phone: data.owner?.phone?.trim() || null,
        email: data.owner?.email?.trim() || null,
        address: data.owner?.address?.trim() || null,
      },
      clinical: { history: seed.clinical?.history ?? null },
      meta: seed.meta || {},
    })
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
