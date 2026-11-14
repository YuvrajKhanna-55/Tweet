const jsonHeaders = { 'Content-Type': 'application/json' }

async function csrfToken() {
  const response = await fetch('/api/auth/csrf/', { credentials: 'include' })
  const data = await response.json()
  return data.csrfToken
}

export async function api(path, options = {}) {
  const method = options.method || 'GET'
  const headers = { ...(options.body instanceof FormData ? {} : jsonHeaders), ...(options.headers || {}) }
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    headers['X-CSRFToken'] = await csrfToken()
  }
  const response = await fetch(`/api${path}`, {
    ...options,
    method,
    headers,
    credentials: 'include',
  })
  if (response.status === 204) return null
  const raw = await response.text()
  let data
  try {
    data = raw ? JSON.parse(raw) : {}
  } catch {
    data = {}
  }
  if (!response.ok) {
    const validationMessage = Object.values(data).flat().join(' ')
    throw new Error(data.detail || validationMessage || `Request failed (${response.status})`)
  }
  return data
}
