import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fileUrl, getRecord, updateRecord } from '../api'
import RecordForm, { STRUCTURED_FORM_ID } from '../components/RecordForm'

export default function RecordPage() {
  const { id } = useParams()
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
      setSaveNotice('Changes saved successfully.')
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
        <Link to="/">Back</Link>
      </section>
    )
  }

  if (!record) {
    return <p className="muted">Loading record…</p>
  }

  const isProcessing = record.status === 'processing'

  return (
    <section className="stack">
      <div className="panel heading-row">
        <div>
          <Link to="/" className="back-link">
            ← All records
          </Link>
          <h1>{record.structured_data?.pet?.name || record.original_filename}</h1>
          <p className="muted">
            Status: {record.status}
            {isProcessing ? ' — extracting and structuring with the local LLM…' : ''}
            {record.error_message ? ` — ${record.error_message}` : ''}
          </p>
        </div>
        <div className="header-actions">
          <button
            type="button"
            className="ghost-button"
            onClick={() => setShowExtractedText((open) => !open)}
          >
            {showExtractedText ? 'Hide extracted text' : 'Extracted text'}
          </button>
          <a className="ghost-button" href={fileUrl(record.id)} target="_blank" rel="noreferrer">
            Download PDF
          </a>
        </div>
      </div>

      {isProcessing && (
        <div className="panel">
          <p className="muted">
            Processing can take up to a couple of minutes on a local 7B model. This page
            refreshes automatically.
          </p>
        </div>
      )}

      {showExtractedText && (
        <div className="panel">
          <h2>Extracted text</h2>
          <pre className="text-preview">
            {record.raw_text ||
              (isProcessing ? 'Waiting for text extraction…' : 'No text extracted.')}
          </pre>
        </div>
      )}

      <div className="panel">
        <div className="heading-row">
          <div className="heading-with-actions">
            <h2>Structured record</h2>
            {record.structured_data && (
              <div className="heading-actions">
                {editing && (
                  <button
                    type="submit"
                    form={STRUCTURED_FORM_ID}
                    className="primary-button heading-action-button"
                    disabled={saving}
                  >
                    {saving ? 'Saving…' : 'Save corrections'}
                  </button>
                )}
                <button type="button" className="ghost-button" onClick={toggleEditing}>
                  {editing ? 'Cancel' : 'Edit'}
                </button>
              </div>
            )}
          </div>
        </div>

        {saveNotice && (
          <div className="toast-success" role="status">
            {saveNotice}
          </div>
        )}

        {record.structured_data ? (
          <RecordForm
            key={`${record.id}-${record.updated_at}-${formKey}`}
            initial={record.structured_data}
            onSave={onSave}
            editing={editing}
            onDirtyChange={onDirtyChange}
          />
        ) : (
          <p className="muted">
            {isProcessing
              ? 'Structured fields will appear when processing finishes.'
              : 'No structured data available.'}
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
            <h3 id="discard-title">Unsaved changes</h3>
            <p id="discard-desc">
              Modified fields will not be saved. Do you want to continue without saving?
            </p>
            <div className="modal-actions">
              <button
                type="button"
                className="ghost-button"
                onClick={() => setDiscardOpen(false)}
              >
                Cancel
              </button>
              <button type="button" className="primary-button heading-action-button" onClick={exitEditing}>
                Continue
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
