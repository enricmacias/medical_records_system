import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fileUrl, getRecord, updateRecord } from '../api'
import RecordForm from '../components/RecordForm'

export default function RecordPage() {
  const { id } = useParams()
  const [record, setRecord] = useState(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [savedAt, setSavedAt] = useState('')

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

  async function onSave(structuredData) {
    setSaving(true)
    setError('')
    try {
      const updated = await updateRecord(id, structuredData)
      setRecord(updated)
      setSavedAt(new Date().toLocaleTimeString())
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
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
        <a className="ghost-button" href={fileUrl(record.id)} target="_blank" rel="noreferrer">
          Download PDF
        </a>
      </div>

      {isProcessing && (
        <div className="panel">
          <p className="muted">
            Processing can take up to a couple of minutes on a local 7B model. This page
            refreshes automatically.
          </p>
        </div>
      )}

      <div className="split">
        <div className="panel">
          <h2>Extracted text</h2>
          <pre className="text-preview">
            {record.raw_text || (isProcessing ? 'Waiting for text extraction…' : 'No text extracted.')}
          </pre>
        </div>
        <div className="panel">
          <div className="heading-row">
            <h2>Structured record</h2>
            {savedAt && <span className="muted">Saved at {savedAt}</span>}
          </div>
          {record.structured_data ? (
            <RecordForm
              key={`${record.id}-${record.updated_at}`}
              initial={record.structured_data}
              onSave={onSave}
              saving={saving}
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
      </div>
    </section>
  )
}
