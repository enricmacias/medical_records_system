import { useState } from 'react'

function Field({ label, value, onChange }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input value={value ?? ''} onChange={(e) => onChange(e.target.value || null)} />
    </label>
  )
}

function TextArea({ label, value, onChange, rows = 3 }) {
  return (
    <label className="field">
      <span>{label}</span>
      <textarea
        rows={rows}
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
      />
    </label>
  )
}

export default function RecordForm({ initial, onSave, saving }) {
  const [data, setData] = useState(() => {
    const clone = structuredClone(initial)
    clone.pet = clone.pet || {}
    clone.owner = clone.owner || {}
    clone.visit = clone.visit || {}
    clone.clinical = clone.clinical || {}
    clone.clinical.medications = clone.clinical.medications || []
    clone.clinical.history_entries = clone.clinical.history_entries || []
    clone.meta = clone.meta || {}
    return clone
  })

  function setPet(key, value) {
    setData((prev) => ({ ...prev, pet: { ...prev.pet, [key]: value } }))
  }
  function setOwner(key, value) {
    setData((prev) => ({ ...prev, owner: { ...prev.owner, [key]: value } }))
  }
  function setVisit(key, value) {
    setData((prev) => ({ ...prev, visit: { ...prev.visit, [key]: value } }))
  }
  function setClinical(key, value) {
    setData((prev) => ({
      ...prev,
      clinical: { ...prev.clinical, [key]: value },
    }))
  }
  function setMedication(index, key, value) {
    setData((prev) => {
      const medications = [...(prev.clinical.medications || [])]
      medications[index] = { ...medications[index], [key]: value }
      return {
        ...prev,
        clinical: { ...prev.clinical, medications },
      }
    })
  }
  function addMedication() {
    setData((prev) => ({
      ...prev,
      clinical: {
        ...prev.clinical,
        medications: [
          ...(prev.clinical.medications || []),
          { name: null, dosage: null, frequency: null },
        ],
      },
    }))
  }
  function setHistoryEntry(index, key, value) {
    setData((prev) => {
      const history_entries = [...(prev.clinical.history_entries || [])]
      history_entries[index] = { ...history_entries[index], [key]: value }
      return {
        ...prev,
        clinical: { ...prev.clinical, history_entries },
      }
    })
  }
  function addHistoryEntry() {
    setData((prev) => ({
      ...prev,
      clinical: {
        ...prev.clinical,
        history_entries: [
          ...(prev.clinical.history_entries || []),
          { date: null, summary: null },
        ],
      },
    }))
  }

  return (
    <form
      className="record-form"
      onSubmit={(e) => {
        e.preventDefault()
        onSave(data)
      }}
    >
      <fieldset>
        <legend>Pet</legend>
        <div className="grid">
          <Field label="Name" value={data.pet?.name} onChange={(v) => setPet('name', v)} />
          <Field label="Species" value={data.pet?.species} onChange={(v) => setPet('species', v)} />
          <Field label="Breed" value={data.pet?.breed} onChange={(v) => setPet('breed', v)} />
          <Field label="Sex" value={data.pet?.sex} onChange={(v) => setPet('sex', v)} />
          <Field
            label="Date of birth"
            value={data.pet?.date_of_birth}
            onChange={(v) => setPet('date_of_birth', v)}
          />
          <Field
            label="Microchip"
            value={data.pet?.microchip}
            onChange={(v) => setPet('microchip', v)}
          />
          <Field label="Weight" value={data.pet?.weight} onChange={(v) => setPet('weight', v)} />
          <Field
            label="Coat / color"
            value={data.pet?.coat_color}
            onChange={(v) => setPet('coat_color', v)}
          />
        </div>
      </fieldset>

      <fieldset>
        <legend>Owner</legend>
        <div className="grid">
          <Field label="Name" value={data.owner?.name} onChange={(v) => setOwner('name', v)} />
          <Field label="Phone" value={data.owner?.phone} onChange={(v) => setOwner('phone', v)} />
          <Field label="Email" value={data.owner?.email} onChange={(v) => setOwner('email', v)} />
        </div>
        <TextArea
          label="Address"
          value={data.owner?.address}
          onChange={(v) => setOwner('address', v)}
          rows={2}
        />
      </fieldset>

      <fieldset>
        <legend>Visit</legend>
        <div className="grid">
          <Field label="Date" value={data.visit?.date} onChange={(v) => setVisit('date', v)} />
          <Field
            label="Clinic"
            value={data.visit?.clinic_name}
            onChange={(v) => setVisit('clinic_name', v)}
          />
          <Field
            label="Veterinarian"
            value={data.visit?.veterinarian}
            onChange={(v) => setVisit('veterinarian', v)}
          />
        </div>
      </fieldset>

      <fieldset>
        <legend>Clinical</legend>
        <TextArea
          label="Chief complaint"
          value={data.clinical?.chief_complaint}
          onChange={(v) => setClinical('chief_complaint', v)}
        />
        <TextArea
          label="History"
          value={data.clinical?.history}
          onChange={(v) => setClinical('history', v)}
          rows={4}
        />
        <TextArea
          label="Examination"
          value={data.clinical?.examination}
          onChange={(v) => setClinical('examination', v)}
        />
        <TextArea
          label="Diagnosis"
          value={data.clinical?.diagnosis}
          onChange={(v) => setClinical('diagnosis', v)}
        />
        <TextArea
          label="Treatment"
          value={data.clinical?.treatment}
          onChange={(v) => setClinical('treatment', v)}
        />
        <TextArea
          label="Notes"
          value={data.clinical?.notes}
          onChange={(v) => setClinical('notes', v)}
        />

        <div className="medications">
          <div className="heading-row">
            <h3>Visit highlights</h3>
            <button type="button" className="ghost-button" onClick={addHistoryEntry}>
              Add
            </button>
          </div>
          {(data.clinical?.history_entries || []).map((entry, index) => (
            <div className="grid" key={`hist-${index}`}>
              <Field
                label="Date"
                value={entry.date}
                onChange={(v) => setHistoryEntry(index, 'date', v)}
              />
              <TextArea
                label="Summary"
                value={entry.summary}
                onChange={(v) => setHistoryEntry(index, 'summary', v)}
                rows={2}
              />
            </div>
          ))}
        </div>

        <div className="medications">
          <div className="heading-row">
            <h3>Medications</h3>
            <button type="button" className="ghost-button" onClick={addMedication}>
              Add
            </button>
          </div>
          {(data.clinical?.medications || []).map((med, index) => (
            <div className="grid" key={`med-${index}`}>
              <Field
                label="Name"
                value={med.name}
                onChange={(v) => setMedication(index, 'name', v)}
              />
              <Field
                label="Dosage"
                value={med.dosage}
                onChange={(v) => setMedication(index, 'dosage', v)}
              />
              <Field
                label="Frequency"
                value={med.frequency}
                onChange={(v) => setMedication(index, 'frequency', v)}
              />
            </div>
          ))}
        </div>
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

      <button type="submit" className="primary-button" disabled={saving}>
        {saving ? 'Saving…' : 'Save corrections'}
      </button>
    </form>
  )
}
