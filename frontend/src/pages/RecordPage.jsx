import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fileUrl, getRecord, updateRecord } from '../api'
import LanguageSuggestionBanner from '../components/LanguageSuggestionBanner'
import RecordForm, { STRUCTURED_FORM_ID } from '../components/RecordForm'
import { useLanguage, translateProcessingStep } from '../i18n/LanguageContext'
import { translateStatus } from '../lib/displayValues'

export default function RecordPage() {
  const { id } = useParams()
  const { t } = useLanguage()
  const [record, setRecord] = useState(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [showExtractedText, setShowExtractedText] = useState(false)
  const [editing, setEditing] = useState(false)
  const [formKey, setFormKey] = useState(0)
  const [dirty, setDirty] = useState(false)
  const [discardOpen, setDiscardOpen] = useState(false)
  const [saveNotice, setSaveNotice] = useState('')

  useEffect(() => {
    let cancelled = false
    let timer

    async function load(poll = false) {
      try {
        const data = await getRecord(id)
        if (cancelled) return
        setRecord(data)
        setError('')
        if (data.status === 'processing') {
          timer = setTimeout(() => load(true), poll ? 2000 : 1500)
        }
      } catch (err) {
        if (!cancelled) setError(err.message)
      }
    }

    load()
    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [id])

  useEffect(() => {
    setEditing(false)
    setShowExtractedText(false)
    setDirty(false)
    setDiscardOpen(false)
    setSaveNotice('')
  }, [id])

  useEffect(() => {
    if (!saveNotice) return undefined
    const timer = setTimeout(() => setSaveNotice(''), 4000)
    return () => clearTimeout(timer)
  }, [saveNotice])

  const onDirtyChange = useCallback((nextDirty) => {
    setDirty(nextDirty)
  }, [])

  function exitEditing() {
    setEditing(false)
    setDirty(false)
    setDiscardOpen(false)
    setFormKey((k) => k + 1)
  }

  async function onSave(structuredData) {
    setSaving(true)
    setError('')
    try {
      const updated = await updateRecord(id, structuredData)
      setRecord(updated)
      setEditing(false)
      setDirty(false)
      setFormKey((k) => k + 1)
      setSaveNotice(t('record.saveSuccess'))
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  function requestDone() {
    if (dirty) {
      setDiscardOpen(true)
      return
    }
    exitEditing()
  }

  function toggleEditing() {
    if (editing) {
      requestDone()
      return
    }
    setSaveNotice('')
    setEditing(true)
  }

  if (error && !record) {
    return (
      <section className="panel">
        <p className="error">{error}</p>
        <Link to="/">{t('record.back')}</Link>
      </section>
    )
  }

  if (!record) {
    return <p className="muted">{t('record.loading')}</p>
  }

  const isProcessing = record.status === 'processing'
  const processingStepMessage = record.processing
    ? translateProcessingStep(t, record.processing)
    : null
  const hasStructuredData = Boolean(record.structured_data)
  const sourceLanguage = record.structured_data?.meta?.source_language

  return (
    <section className="stack">
      <LanguageSuggestionBanner sourceLanguage={sourceLanguage} recordId={record.id} />

      <div className="panel heading-row">
        <div>
          <Link to="/" className="back-link">{t('record.allRecords')}</Link>
          <h1>{record.structured_data?.pet?.name || record.original_filename}</h1>
          <p className="muted">
            {t('record.status', { status: translateStatus(t, record.status) })}
            {isProcessing
              ? record.processing
                ? ` — ${t('record.statusProcessing', {
                    percent: record.processing.percent,
                    message: processingStepMessage,
                  })}`
                : ` — ${t('record.statusProcessingFallback')}`
              : ''}
            {record.error_message ? ` — ${record.error_message}` : ''}
          </p>
        </div>
        <div className="header-actions">
          <button
            type="button"
            className="ghost-button"
            onClick={() => setShowExtractedText((open) => !open)}
          >
            {showExtractedText ? t('record.hideExtractedText') : t('record.extractedText')}
          </button>
          <a className="ghost-button" href={fileUrl(record.id)} target="_blank" rel="noreferrer">
            {t('record.downloadFile')}
          </a>
        </div>
      </div>

      {isProcessing && !hasStructuredData && record.processing && (
        <div className="panel">
          <h2>{t('record.processingTitle')}</h2>
          <p className="muted">{t('record.processingHint')}</p>
          <div className="processing-progress" role="status" aria-live="polite">
            <div className="processing-progress-header">
              <span className="processing-progress-percent">{record.processing.percent}%</span>
              <span className="processing-progress-step">{processingStepMessage}</span>
            </div>
            <div className="processing-progress-bar" aria-hidden="true">
              <div
                className="processing-progress-fill"
                style={{ width: `${record.processing.percent}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {isProcessing && hasStructuredData && (
        <div className="panel processing-partial-notice" role="status">
          <p className="muted">
            {t('record.partialReady')}
            {processingStepMessage
              ? ` ${processingStepMessage}`
              : ` ${t('record.summaryInProgress')}`}
          </p>
        </div>
      )}

      {showExtractedText && (
        <div className="panel">
          <h2>{t('record.extractedTextTitle')}</h2>
          <pre className="text-preview">
            {record.raw_text ||
              (isProcessing ? t('record.waitingForText') : t('record.noTextExtracted'))}
          </pre>
        </div>
      )}

      <div className="panel">
        <div className="heading-row">
          <div className="heading-with-actions">
            <h2>{t('record.structuredRecord')}</h2>
            {record.structured_data && (
              <div className="heading-actions">
                {editing && (
                  <button
                    type="submit"
                    form={STRUCTURED_FORM_ID}
                    className="primary-button heading-action-button"
                    disabled={saving}
                  >
                    {saving ? t('record.saving') : t('record.saveCorrections')}
                  </button>
                )}
                <button
                  type="button"
                  className="ghost-button"
                  onClick={toggleEditing}
                  disabled={isProcessing}
                >
                  {editing ? t('record.cancel') : t('record.edit')}
                </button>
              </div>
            )}
          </div>
        </div>

        {saveNotice && (
          <div className="toast-success" role="status">{saveNotice}</div>
        )}

        {record.structured_data ? (
          <RecordForm
            key={`${record.id}-${record.updated_at}-${formKey}`}
            initial={record.structured_data}
            onSave={onSave}
            editing={editing}
            onDirtyChange={onDirtyChange}
            isProcessing={isProcessing}
            processing={record.processing}
          />
        ) : (
          <p className="muted">
            {isProcessing ? t('record.structuredSoon') : t('record.noStructuredData')}
          </p>
        )}
        {error && <p className="error">{error}</p>}
      </div>

      {discardOpen && (
        <div
          className="modal-backdrop"
          role="presentation"
          onClick={() => setDiscardOpen(false)}
        >
          <div
            className="modal-dialog"
            role="alertdialog"
            aria-labelledby="discard-title"
            aria-describedby="discard-desc"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 id="discard-title">{t('record.unsavedTitle')}</h3>
            <p id="discard-desc">{t('record.unsavedDesc')}</p>
            <div className="modal-actions">
              <button
                type="button"
                className="ghost-button"
                onClick={() => setDiscardOpen(false)}
              >
                {t('record.cancel')}
              </button>
              <button
                type="button"
                className="primary-button heading-action-button"
                onClick={exitEditing}
              >
                {t('record.continue')}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
