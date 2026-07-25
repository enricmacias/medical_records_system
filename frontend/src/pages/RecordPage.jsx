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
    getRecord(id)
      .then(setRecord)
      .catch((err) => setError(err.message))
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
            {record.error_message ? ` — ${record.error_message}` : ''}
          </p>
        </div>
        <a className="ghost-button" href={fileUrl(record.id)} target="_blank" rel="noreferrer">
          Download PDF
        </a>
      </div>

      <div className="split">
        <div className="panel">
          <h2>Extracted text</h2>
          <pre className="text-preview">{record.raw_text || 'No text extracted.'}</pre>
        </div>
        <div className="panel">
          <div className="heading-row">
            <h2>Structured record</h2>
            {savedAt && <span className="muted">Saved at {savedAt}</span>}
          </div>
          {record.structured_data ? (
            <RecordForm
              initial={record.structured_data}
              onSave={onSave}
              saving={saving}
            />
          ) : (
            <p className="muted">No structured data available.</p>
          )}
          {error && <p className="error">{error}</p>}
        </div>
      </div>
    </section>
  )
}
