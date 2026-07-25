const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

async function parseError(response) {
  try {
    const data = await response.json()
    if (typeof data.detail === 'string') return data.detail
    return JSON.stringify(data.detail || data)
  } catch {
    return response.statusText || 'Request failed'
  }
}

export async function getHealth() {
  const response = await fetch(`${API_BASE}/api/health`)
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function listRecords() {
  const response = await fetch(`${API_BASE}/api/records`)
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function getRecord(id) {
  const response = await fetch(`${API_BASE}/api/records/${id}`)
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function uploadRecord(file) {
  const form = new FormData()
  form.append('file', file)
  const response = await fetch(`${API_BASE}/api/records`, {
    method: 'POST',
    body: form,
  })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export async function updateRecord(id, structuredData) {
  const response = await fetch(`${API_BASE}/api/records/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ structured_data: structuredData }),
  })
  if (!response.ok) throw new Error(await parseError(response))
  return response.json()
}

export function fileUrl(id) {
  return `${API_BASE}/api/records/${id}/file`
}
