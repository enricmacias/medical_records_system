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
import {
  getFieldHighlight,
  isLowExtractionConfidence,
} from '../lib/fieldConfidence'
import { useLanguage, translateProcessingStep } from '../i18n/LanguageContext'

export const STRUCTURED_FORM_ID = 'structured-record-form'

function displayValue(value, t) {
  if (value == null || String(value).trim() === '') return t('form.empty')
  return value
}

function FieldLabel({ label, highlight, t }) {
  if (!highlight) return <span>{label}</span>
  const flagKey =
    highlight === 'missing' ? 'form.flagMissing' : 'form.flagLowConfidence'
  return (
    <span className="field-label">
      <span>{label}</span>
      <span className={`field-flag field-flag-${highlight}`}>{t(flagKey)}</span>
    </span>
  )
}

function fieldHighlightClass(highlight) {
  if (highlight === 'missing') return 'field-flagged-missing'
  if (highlight === 'low-confidence') return 'field-flagged-low-confidence'
  return ''
}

function Field({
  label,
  fieldPath,
  value,
  displayValue: formatted,
  onChange,
  editing,
  highlight,
}) {
  const { t } = useLanguage()
  const shown = formatted ?? value
  const flaggedClass = fieldHighlightClass(highlight)

  if (!editing) {
    return (
      <div className={`field field-readonly${flaggedClass ? ` ${flaggedClass}` : ''}`}>
        <FieldLabel label={label} highlight={highlight} t={t} />
        <p className="field-value">{displayValue(shown, t)}</p>
      </div>
    )
  }
  return (
    <label className={`field${flaggedClass ? ` ${flaggedClass}` : ''}`}>
      <FieldLabel label={label} highlight={highlight} t={t} />
      <input
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
        aria-invalid={highlight ? true : undefined}
      />
    </label>
  )
}

function TextArea({
  label,
  fieldPath,
  value,
  onChange,
  rows = 3,
  hint,
  editing,
  highlight,
}) {
  const { t } = useLanguage()
  const flaggedClass = fieldHighlightClass(highlight)

  if (!editing) {
    return (
      <div className={`field field-readonly${flaggedClass ? ` ${flaggedClass}` : ''}`}>
        <FieldLabel label={label} highlight={highlight} t={t} />
        <p className="field-value field-value-block">{displayValue(value, t)}</p>
      </div>
    )
  }
  return (
    <label className={`field${flaggedClass ? ` ${flaggedClass}` : ''}`}>
      <FieldLabel label={label} highlight={highlight} t={t} />
      <textarea
        rows={rows}
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
        aria-invalid={highlight ? true : undefined}
      />
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

function SpeciesField({ value, onChange, editing, highlight }) {
  const { t } = useLanguage()
  const flaggedClass = fieldHighlightClass(highlight)

  if (!editing) {
    return (
      <div className={`field field-readonly${flaggedClass ? ` ${flaggedClass}` : ''}`}>
        <FieldLabel label={t('form.species')} highlight={highlight} t={t} />
        <p className="field-value">{displayValue(displaySpeciesLocalized(value, null, t), t)}</p>
      </div>
    )
  }
  const selectValue = normalizeSpeciesForStorage(value) ?? ''
  return (
    <label className={`field${flaggedClass ? ` ${flaggedClass}` : ''}`}>
      <FieldLabel label={t('form.species')} highlight={highlight} t={t} />
      <select
        value={selectValue}
        onChange={(e) => onChange(e.target.value || null)}
        aria-invalid={highlight ? true : undefined}
      >
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

  const highlightContext = useMemo(
    () => ({
      meta: data.meta,
      isProcessing,
    }),
    [data.meta, isProcessing],
  )

  function fieldHighlight(path, value) {
    return getFieldHighlight(path, { ...highlightContext, value })
  }

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

  const confidenceLabel = translateConfidence(t, data.meta?.extraction_confidence) || t('form.n_a')
  const lowConfidence = isLowExtractionConfidence(data.meta)

  const clinicalHighlight = fieldHighlight('clinical.history', seed.clinical?.history)

  return (
    <form
      id={STRUCTURED_FORM_ID}
      className={`record-form${editing ? '' : ' record-form-readonly'}`}
      onSubmit={handleSave}
    >
      {lowConfidence && (
        <p className="form-confidence-notice" role="status">
          {t('form.lowConfidenceNotice')}
        </p>
      )}

      <fieldset disabled={!editing}>
        <legend>{t('form.pet')}</legend>
        <div className="grid">
          <Field
            label={t('form.name')}
            fieldPath="pet.name"
            value={data.pet?.name}
            highlight={fieldHighlight('pet.name', data.pet?.name)}
            onChange={(v) => setPet('name', v)}
            editing={editing}
          />
          <SpeciesField
            value={data.pet?.species}
            highlight={fieldHighlight('pet.species', data.pet?.species)}
            onChange={(v) => setPet('species', v)}
            editing={editing}
          />
          <Field
            label={t('form.breed')}
            fieldPath="pet.breed"
            value={data.pet?.breed}
            highlight={fieldHighlight('pet.breed', data.pet?.breed)}
            onChange={(v) => setPet('breed', v)}
            editing={editing}
          />
          <Field
            label={t('form.sex')}
            fieldPath="pet.sex"
            value={data.pet?.sex}
            displayValue={displaySex(data.pet?.sex, locale, t)}
            highlight={fieldHighlight('pet.sex', data.pet?.sex)}
            onChange={(v) => setPet('sex', v)}
            editing={editing}
          />
          <Field
            label={t('form.dateOfBirth')}
            fieldPath="pet.date_of_birth"
            value={data.pet?.date_of_birth}
            displayValue={displayRecordDate(data.pet?.date_of_birth, locale)}
            highlight={fieldHighlight('pet.date_of_birth', data.pet?.date_of_birth)}
            onChange={(v) => setPet('date_of_birth', v)}
            editing={editing}
          />
          <Field
            label={t('form.microchip')}
            fieldPath="pet.microchip"
            value={data.pet?.microchip}
            highlight={fieldHighlight('pet.microchip', data.pet?.microchip)}
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
            fieldPath="owner.name"
            value={data.owner?.name}
            highlight={fieldHighlight('owner.name', data.owner?.name)}
            onChange={(v) => setOwner('name', v)}
            editing={editing}
          />
          <Field
            label={t('form.phone')}
            fieldPath="owner.phone"
            value={data.owner?.phone}
            highlight={fieldHighlight('owner.phone', data.owner?.phone)}
            onChange={(v) => setOwner('phone', v)}
            editing={editing}
          />
          <Field
            label={t('form.email')}
            fieldPath="owner.email"
            value={data.owner?.email}
            highlight={fieldHighlight('owner.email', data.owner?.email)}
            onChange={(v) => setOwner('email', v)}
            editing={editing}
          />
        </div>
        <TextArea
          label={t('form.address')}
          fieldPath="owner.address"
          value={data.owner?.address}
          highlight={fieldHighlight('owner.address', data.owner?.address)}
          onChange={(v) => setOwner('address', v)}
          rows={2}
          editing={editing}
        />
      </fieldset>

      <fieldset className={clinicalHighlight ? 'fieldset-flagged-missing' : undefined}>
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
            fieldPath="clinical.history"
            value={clinicalSummary}
            highlight={clinicalHighlight}
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
          {t('form.confidenceLabel')}:{' '}
          <span className={lowConfidence ? 'meta-confidence-low' : undefined}>
            {confidenceLabel}
          </span>
          {' · '}
          {t('form.languageLabel')}: {data.meta?.source_language || t('form.n_a')}
        </p>
        {(data.meta?.missing_fields || []).length > 0 && (
          <p className="muted">{t('form.missing', { fields: missingFields })}</p>
        )}
      </fieldset>
    </form>
  )
}
