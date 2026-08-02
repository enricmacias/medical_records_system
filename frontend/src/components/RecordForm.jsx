import { useEffect, useMemo, useState } from 'react'
import {
  buildClinicalResume,
  buildStructuredPetPayload,
  isStructuredRecordDirty,
  normalizeSpeciesForStorage,
} from '../lib/recordDisplay'
import {
  displayRecordDate,
  displaySex,
  displaySpeciesLocalized,
  translateConfidence,
  translateFieldPath,
} from '../lib/displayValues'
import { formatDatesInText } from '../lib/formatDate'
import { useLanguage, translateProcessingStep } from '../i18n/LanguageContext'

export const STRUCTURED_FORM_ID = 'structured-record-form'

function displayValue(value, t) {
  if (value == null || String(value).trim() === '') return t('form.empty')
  return value
}

function Field({ label, value, displayValue: formatted, onChange, editing }) {
  const { t } = useLanguage()
  const shown = formatted ?? value
  if (!editing) {
    return (
      <div className="field field-readonly">
        <span>{label}</span>
        <p className="field-value">{displayValue(shown, t)}</p>
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
  const { t } = useLanguage()
  if (!editing) {
    return (
      <div className="field field-readonly">
        <span>{label}</span>
        <p className="field-value field-value-block">{displayValue(value, t)}</p>
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

function ProcessingIndicator({ processing }) {
  const { t } = useLanguage()
  if (!processing) return null
  const message = translateProcessingStep(t, processing)
  return (
    <div className="processing-progress" role="status" aria-live="polite">
      <div className="processing-progress-header">
        <span className="processing-progress-percent">{processing.percent}%</span>
        <span className="processing-progress-step">{message}</span>
      </div>
      <div className="processing-progress-bar" aria-hidden="true">
        <div
          className="processing-progress-fill"
          style={{ width: `${processing.percent}%` }}
        />
      </div>
    </div>
  )
}

function SpeciesField({ value, onChange, editing }) {
  const { t } = useLanguage()
  if (!editing) {
    return (
      <div className="field field-readonly">
        <span>{t('form.species')}</span>
        <p className="field-value">{displayValue(displaySpeciesLocalized(value, null, t), t)}</p>
      </div>
    )
  }
  const selectValue = normalizeSpeciesForStorage(value) ?? ''
  return (
    <label className="field">
      <span>{t('form.species')}</span>
      <select value={selectValue} onChange={(e) => onChange(e.target.value || null)}>
        <option value="">{t('form.empty')}</option>
        <option value="Dog">{t('species.dog')}</option>
        <option value="Cat">{t('species.cat')}</option>
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

export default function RecordForm({
  initial,
  onSave,
  editing,
  onDirtyChange,
  isProcessing = false,
  processing = null,
}) {
  const { locale, t } = useLanguage()

  const seed = useMemo(() => {
    const clone = structuredClone(initial)
    clone.pet = normalizePetForForm(clone.pet || {})
    clone.owner = clone.owner || {}
    clone.clinical = clone.clinical || {}
    clone.meta = clone.meta || {}
    return clone
  }, [initial])

  const clinicalSummary = useMemo(() => {
    const raw = buildClinicalResume(seed.clinical)
    return raw ? formatDatesInText(raw, locale) : ''
  }, [seed, locale])

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

  const missingFields = (data.meta?.missing_fields || [])
    .map((path) => translateFieldPath(path, locale))
    .join(', ')

  return (
    <form
      id={STRUCTURED_FORM_ID}
      className={`record-form${editing ? '' : ' record-form-readonly'}`}
      onSubmit={handleSave}
    >
      <fieldset disabled={!editing}>
        <legend>{t('form.pet')}</legend>
        <div className="grid">
          <Field
            label={t('form.name')}
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
            label={t('form.breed')}
            value={data.pet?.breed}
            onChange={(v) => setPet('breed', v)}
            editing={editing}
          />
          <Field
            label={t('form.sex')}
            value={data.pet?.sex}
            displayValue={displaySex(data.pet?.sex, locale, t)}
            onChange={(v) => setPet('sex', v)}
            editing={editing}
          />
          <Field
            label={t('form.dateOfBirth')}
            value={data.pet?.date_of_birth}
            displayValue={displayRecordDate(data.pet?.date_of_birth, locale)}
            onChange={(v) => setPet('date_of_birth', v)}
            editing={editing}
          />
          <Field
            label={t('form.microchip')}
            value={data.pet?.microchip}
            onChange={(v) => setPet('microchip', v)}
            editing={editing}
          />
        </div>
      </fieldset>

      <fieldset disabled={!editing}>
        <legend>{t('form.owner')}</legend>
        <div className="grid">
          <Field
            label={t('form.name')}
            value={data.owner?.name}
            onChange={(v) => setOwner('name', v)}
            editing={editing}
          />
          <Field
            label={t('form.phone')}
            value={data.owner?.phone}
            onChange={(v) => setOwner('phone', v)}
            editing={editing}
          />
          <Field
            label={t('form.email')}
            value={data.owner?.email}
            onChange={(v) => setOwner('email', v)}
            editing={editing}
          />
        </div>
        <TextArea
          label={t('form.address')}
          value={data.owner?.address}
          onChange={(v) => setOwner('address', v)}
          rows={2}
          editing={editing}
        />
      </fieldset>

      <fieldset>
        <legend>{t('form.clinicalSummary')}</legend>
        {isProcessing && !clinicalSummary ? (
          processing ? (
            <ProcessingIndicator processing={processing} />
          ) : (
            <p className="muted">{t('form.generatingSummary')}</p>
          )
        ) : (
          <TextArea
            label={t('form.clinicalSummary')}
            value={clinicalSummary}
            onChange={() => {}}
            rows={8}
            hint={t('form.summaryHint')}
            editing={false}
          />
        )}
      </fieldset>

      <fieldset>
        <legend>{t('form.meta')}</legend>
        <p className="muted">
          {t('form.confidence', {
            value: translateConfidence(t, data.meta?.extraction_confidence) || t('form.n_a'),
          })}
          {' · '}
          {t('form.language', {
            value: data.meta?.source_language || t('form.n_a'),
          })}
        </p>
        {(data.meta?.missing_fields || []).length > 0 && (
          <p className="muted">{t('form.missing', { fields: missingFields })}</p>
        )}
      </fieldset>
    </form>
  )
}
