import { useEffect, useMemo, useState } from 'react'
import {
  CLINICAL_RESUME_MAX,
  buildClinicalResume,
  formatMedicationsList,
  isStructuredRecordDirty,
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

export default function RecordForm({ initial, onSave, editing, onDirtyChange }) {
  const seed = useMemo(() => {
    const clone = structuredClone(initial)
    clone.pet = clone.pet || {}
    clone.owner = clone.owner || {}
    clone.visit = clone.visit || {}
    clone.clinical = clone.clinical || {}
    clone.clinical.medications = clone.clinical.medications || []
    clone.clinical.history_entries = clone.clinical.history_entries || []
    clone.meta = clone.meta || {}
    return clone
  }, [initial])

  const baselineResume = useMemo(() => buildClinicalResume(seed.clinical), [seed])
  const baselineMedications = useMemo(
    () => formatMedicationsList(seed.clinical.medications),
    [seed],
  )

  const [data, setData] = useState(seed)
  const [clinicalResume, setClinicalResume] = useState(baselineResume)
  const [medicationsText, setMedicationsText] = useState(baselineMedications)

  const dirty = useMemo(
    () =>
      isStructuredRecordDirty({
        data,
        seed,
        clinicalResume,
        baselineResume,
        medicationsText,
        baselineMedications,
      }),
    [data, clinicalResume, medicationsText, seed, baselineResume, baselineMedications],
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
    const resume = (clinicalResume || '').slice(0, CLINICAL_RESUME_MAX)
    const payload = {
      ...data,
      clinical: {
        ...data.clinical,
        history: resume || null,
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
          <Field
            label="Species"
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
          <Field
            label="Weight"
            value={data.pet?.weight}
            onChange={(v) => setPet('weight', v)}
            editing={editing}
          />
          <Field
            label="Coat / color"
            value={data.pet?.coat_color}
            onChange={(v) => setPet('coat_color', v)}
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

      <fieldset disabled={!editing}>
        <legend>Clinical record</legend>
        <TextArea
          label="Resume of clinic visits"
          value={clinicalResume}
          onChange={(v) => setClinicalResume(v ?? '')}
          rows={8}
          maxLength={CLINICAL_RESUME_MAX}
          hint="Summary across visits · "
          editing={editing}
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
