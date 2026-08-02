import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getHealth, listRecords, uploadRecord } from '../api'
import { useLanguage } from '../i18n/LanguageContext'
import { translateOllamaStatus } from '../lib/displayValues'

export default function HomePage() {
  const navigate = useNavigate()
  const { locale, t } = useLanguage()
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
        <h1>{t('home.uploadTitle')}</h1>
        <p className="muted">{t('home.uploadHint')}</p>
        <label className="upload-button">
          <input
            type="file"
            accept="application/pdf,.pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx"
            onChange={onFileChange}
            disabled={uploading}
          />
          {uploading ? t('home.uploading') : t('home.chooseFile')}
        </label>
        {health && (
          <p className="health">
            {t('home.health', {
              status: health.status,
              ollama: translateOllamaStatus(t, health.ollama),
              model: health.model,
            })}
          </p>
        )}
        {error && <p className="error">{error}</p>}
      </div>

      <div className="panel">
        <h2>{t('home.recentRecords')}</h2>
        {items.length === 0 ? (
          <p className="muted">{t('home.noRecords')}</p>
        ) : (
          <ul className="record-list">
            {items.map((item) => (
              <li key={item.id}>
                <Link to={`/records/${item.id}`}>
                  <strong>{item.pet_name || item.original_filename}</strong>
                  <span>
                    {item.status} ·{' '}
                    {new Date(item.created_at).toLocaleString(locale === 'es' ? 'es-ES' : 'en-US')}
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
