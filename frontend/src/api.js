const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'

async function request(path, options = {}) {
  const isFormData = options.body instanceof FormData
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: isFormData ? (options.headers || {}) : { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}))
    throw new Error(errorBody.detail || errorBody.message || 'The request could not be completed.')
  }

  return response.json()
}

export function createAssessment(data) {
  return request('/assessments/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function uploadDocument(formData) {
  return request('/documents/', {
    method: 'POST',
    body: formData,
  })
}

export function updateAssessment(id, data) {
  return request(`/assessments/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function getLenders(loanType) {
  const query = loanType ? `?loan_type=${encodeURIComponent(loanType)}` : ''
  return request(`/lenders/available/${query}`)
}
