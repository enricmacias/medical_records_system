import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getHealth, listRecords, uploadRecord } from '../api'

export default function HomePage() {
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [health, setHealth] = useState(null)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)

  async function refresh() {
    const [records, healthStatus] = await Promise.all([listRecords(), getHealth()])
    setItems(records.items || [])
    setHealth(healthStatus)
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message))
  }, [])

  async function onFileChange(event) {
    const file = event.target.files?.[0]
    if (!file) return
    setError('')
    setUploading(true)
    try {
      const record = await uploadRecord(file)
      await refresh()
      navigate(`/records/${record.id}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
      event.target.value = ''
    }
  }

  return (
    <section className="stack">
      <div className="panel">
        <h1>Upload a veterinary PDF</h1>
        <p className="muted">
          Text is extracted with pdfplumber, then structured locally with Ollama
          into an editable medical record.
        </p>
        <label className="upload-button">
          <input
            type="file"
            accept="application/pdf,.pdf"
            onChange={onFileChange}
            disabled={uploading}
          />
          {uploading ? 'Processing…' : 'Choose PDF'}
        </label>
        {health && (
          <p className="health">
            API: {health.status} · LLM: {health.ollama} · model: {health.model}
          </p>
        )}
        {error && <p className="error">{error}</p>}
      </div>

      <div className="panel">
        <h2>Recent records</h2>
        {items.length === 0 ? (
          <p className="muted">No records yet. Upload a PDF to get started.</p>
        ) : (
          <ul className="record-list">
            {items.map((item) => (
              <li key={item.id}>
                <Link to={`/records/${item.id}`}>
                  <strong>{item.pet_name || item.original_filename}</strong>
                  <span>
                    {item.status} · {new Date(item.created_at).toLocaleString()}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
