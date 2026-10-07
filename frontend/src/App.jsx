import { useMemo, useState } from 'react'
import './App.css'
import { createAssessment, updateAssessment, uploadDocument } from './api'

const initialForm = {
  country: '',
  university: '',
  course: '',
  tuition: '',
  living_costs: '',
  scholarships: '',
  savings: '',
  fees_paid: '',
  family_contribution: '',
  income: '',
  assets: '',
  liabilities: '',
  collateral_value: '',
  cibil_score: '',
  route: 'non_collateral',
  co_applicant_type: 'salaried',
  property_state: 'Other',
}

const formatMoney = (value) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(Number(value || 0))

const numericFields = new Set([
  'tuition',
  'living_costs',
  'scholarships',
  'savings',
  'fees_paid',
  'family_contribution',
  'income',
  'assets',
  'liabilities',
  'collateral_value',
  'cibil_score',
])

function App() {
  const [form, setForm] = useState(initialForm)
  const [assessment, setAssessment] = useState(null)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [documentType, setDocumentType] = useState('pan_card')
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploadedDocuments, setUploadedDocuments] = useState([])
  const [documentError, setDocumentError] = useState('')
  const [isUploadingDocument, setIsUploadingDocument] = useState(false)

  const fundingGap = useMemo(() => {
    if (!assessment) return null
    return Number(assessment.calculation.funding_gap)
  }, [assessment])

  const routeOptions = useMemo(() => {
    if (!assessment) return []
    return assessment.lenders.map((lender) => ({
      ...lender,
      label: `${lender.name} · ${lender.conditions || 'Reference rate'}`,
    }))
  }, [assessment])

  const requiredDocuments = assessment?.document_checklist || []
  const documentReadiness = assessment?.document_readiness
  const uploadedDocumentTypes = assessment?.uploaded_document_types || []
  const selectedDocumentTypeAlreadyUploaded = uploadedDocumentTypes.includes(documentType)
  const documentTypeOptions = requiredDocuments.map((document) => ({
    value: document.key,
    label: document.label,
  }))

  function updateField(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
  }

  function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    setUploadedDocuments([])

    const payload = Object.fromEntries(
      Object.entries(form).map(([key, value]) => {
        if (numericFields.has(key)) {
          return [key, value === '' ? 0 : Number(value)]
        }

        return [key, value]
      }),
    )

    createAssessment(payload)
      .then((result) => {
        setAssessment(result)
        setUploadedDocuments([])
      })
      .catch((requestError) => setError(requestError.message))
      .finally(() => setIsSubmitting(false))
  }

  function handleDocumentUpload(event) {
    event.preventDefault()
    setDocumentError('')

    if (!assessment || !assessment.assessment || !assessment.assessment.id) {
      setDocumentError('Create an assessment before uploading documents.')
      return
    }

    if (!selectedFile) {
      setDocumentError('Choose a file to upload.')
      return
    }
    if (uploadedDocumentTypes.includes(documentType)) {
      setDocumentError('This document type is already uploaded. Choose another type.')
      return
    }

    const formData = new FormData()
    formData.append('assessment', assessment.assessment.id)
    formData.append('document_type', documentType)
    formData.append('file', selectedFile)

    setIsUploadingDocument(true)
    uploadDocument(formData)
      .then((document) => {
        setAssessment((current) => ({
          ...current,
          document_readiness: document.document_readiness,
          uploaded_document_types: document.uploaded_document_types,
        }))
        const nextDocumentType = documentTypeOptions.find(
          (option) => !document.uploaded_document_types.includes(option.value),
        )
        if (nextDocumentType) setDocumentType(nextDocumentType.value)
        setUploadedDocuments((current) => [
          {
            id: document.id,
            name: selectedFile.name,
            type: document.document_type,
            status: document.status,
          },
          ...current,
        ])
        setSelectedFile(null)
        event.target.reset()
      })
      .catch((requestError) => setDocumentError(requestError.message))
      .finally(() => setIsUploadingDocument(false))
  }

  function handleScenarioChange(event) {
    const value = Number(event.target.value)
    const scenarioForm = { ...form, scholarships: String(value) }
    setForm(scenarioForm)

    if (assessment) {
      updateAssessment(assessment.assessment.id, scenarioForm)
        .then((result) => setAssessment(result))
        .catch((requestError) => setError(requestError.message))
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <span className="eyebrow">GradGuide</span>
          <h1>Education Loan Assessment</h1>
        </div>
        <div className="status-pill">
          <span className="status-dot" aria-hidden="true" />
          Assignment reference data
        </div>
      </header>

      <section className="hero-card">
        <div>
          <p className="hero-kicker">Financial planning for study abroad</p>
          <h2>Understand the funding gap before you apply.</h2>
          <p className="hero-copy">
            Estimate study costs, map your financial profile, compare routes, and review
            relevant lender requirements without treating the result as a guarantee.
          </p>
        </div>
        <div className="hero-summary">
          <span>Assessment</span>
          <strong>{assessment ? 'Ready' : 'Not started'}</strong>
          <small>Decision support only</small>
        </div>
      </section>

      <div className="layout-grid">
        <section className="panel form-panel">
          <div className="section-heading">
            <div>
              <span className="step">Step 1</span>
              <h3>Study and funding details</h3>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="assessment-form">
            <div className="field-grid two-columns">
              <label>
                Country
                <input name="country" value={form.country} onChange={updateField} placeholder="United States" />
              </label>
              <label>
                University
                <input name="university" value={form.university} onChange={updateField} placeholder="University name" />
              </label>
              <label className="full-width">
                Course
                <input name="course" value={form.course} onChange={updateField} placeholder="Course name" />
              </label>
            </div>

            <div className="field-grid two-columns">
              <label>
                Tuition fees
                <input name="tuition" type="number" min="0" value={form.tuition} onChange={updateField} />
              </label>
              <label>
                Living costs
                <input name="living_costs" type="number" min="0" value={form.living_costs} onChange={updateField} />
              </label>
            </div>

            <div className="field-grid three-columns">
              <label>
                Scholarship
                <input name="scholarships" type="number" min="0" value={form.scholarships} onChange={updateField} />
              </label>
              <label>
                Savings
                <input name="savings" type="number" min="0" value={form.savings} onChange={updateField} />
              </label>
              <label>
                Fees paid
                <input name="fees_paid" type="number" min="0" value={form.fees_paid} onChange={updateField} />
              </label>
              <label>
                Family contribution
                <input name="family_contribution" type="number" min="0" value={form.family_contribution} onChange={updateField} />
              </label>
              <label>
                Annual income
                <input name="income" type="number" min="0" value={form.income} onChange={updateField} />
              </label>
              <label>
                CIBIL score
                <input name="cibil_score" type="number" min="0" max="900" value={form.cibil_score} onChange={updateField} />
              </label>
            </div>

            <div className="field-grid three-columns">
              <label>
                Assets
                <input name="assets" type="number" min="0" value={form.assets} onChange={updateField} />
              </label>
              <label>
                Liabilities
                <input name="liabilities" type="number" min="0" value={form.liabilities} onChange={updateField} />
              </label>
              <label>
                Collateral value
                <input name="collateral_value" type="number" min="0" value={form.collateral_value} onChange={updateField} />
              </label>
            </div>

            <div className="selector-row">
              <label>
                Preferred route
                <select name="route" value={form.route} onChange={updateField}>
                  <option value="non_collateral">Non-collateral</option>
                  <option value="collateral">Collateral</option>
                </select>
              </label>
              <label>
                Co-applicant employment type
                <select name="co_applicant_type" value={form.co_applicant_type} onChange={updateField}>
                  <option value="salaried">Salaried</option>
                  <option value="self_employed">Self-employed</option>
                </select>
              </label>
              {form.route === 'collateral' && (
                <label>
                  Property state
                  <select name="property_state" value={form.property_state} onChange={updateField}>
                    <option value="Delhi">Delhi</option>
                    <option value="Maharashtra">Maharashtra</option>
                    <option value="Other">Other</option>
                  </select>
                </label>
              )}
            </div>

            {error && <p className="error-message" role="alert">{error}</p>}
            <button className="primary-button" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Assessing…' : 'Generate assessment'}
            </button>
          </form>
        </section>

        <aside className="panel results-panel">
          <div className="section-heading">
            <div>
              <span className="step">Live summary</span>
              <h3>Financial position</h3>
            </div>
          </div>

          {assessment ? (
            <>
              <div className="metric-grid">
                <article>
                  <span>Total study cost</span>
                  <strong>{formatMoney(assessment.calculation.total_study_cost)}</strong>
                </article>
                <article>
                  <span>Funding gap</span>
                  <strong>{formatMoney(fundingGap)}</strong>
                </article>
                <article>
                  <span>Net worth</span>
                  <strong>{formatMoney(assessment.calculation.net_worth)}</strong>
                </article>
                <article>
                  <span>Collateral</span>
                  <strong>{formatMoney(assessment.calculation.collateral_value)}</strong>
                </article>
              </div>

              <div className="warning-box">
                <strong>Assessment confidence</strong>
                <p>
                  {assessment.calculation.warnings.length
                    ? 'More information is needed before a lender decision can be made.'
                    : 'The available data is sufficient to produce a preliminary assessment.'}
                </p>
              </div>

              <div className="scenario-box">
                <label htmlFor="scenario-scholarship">
                  Original feature: scenario planner
                </label>
                <input
                  id="scenario-scholarship"
                  type="range"
                  min="0"
                  max={Number(form.tuition || 0) + Number(form.living_costs || 0)}
                  value={Number(form.scholarships || 0)}
                  onChange={handleScenarioChange}
                />
                <small>Scholarship scenario: {formatMoney(form.scholarships)}</small>
              </div>

              <div className="lender-list">
                <h4>Relevant lenders</h4>
                {routeOptions.length ? (
                  routeOptions.map((lender) => (
                    <div key={`${lender.name}-${lender.loan_type}`} className="lender-item">
                      <div>
                        <strong>{lender.name}</strong>
                        <span>{lender.loan_type.replace('_', ' ')}</span>
                      </div>
                      <div className="lender-details">
                        <span>{lender.interest_rate || 'Rate unavailable'}</span>
                        <small>
                          Minimum CIBIL: {lender.minimum_cibil || 'Not supplied'}
                        </small>
                      </div>
                    </div>
                  ))
                ) : (
                  <p>No lenders match the current route and CIBIL profile.</p>
                )}
              </div>

              {assessment.calculation.warnings.length > 0 && (
                <ul className="warning-list">
                  {assessment.calculation.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <div className="empty-state">
              <span aria-hidden="true">₹</span>
              <p>Complete the form to generate a preliminary assessment.</p>
            </div>
          )}
        </aside>
      </div>
      {assessment && (
        <section className="document-box document-full-width">
          <h4>Document readiness</h4>
          <p className="document-note">
            Upload supporting files for the lender checklist. This is preparation support only and not a loan guarantee.
          </p>

          <div className="document-checklist">
            {requiredDocuments.length ? (
              requiredDocuments.map((document) => (
                <span key={document.key} className="document-pill">
                  {document.label}
                </span>
              ))
            ) : (
              <span className="document-pill muted">No specific lender categories yet</span>
            )}
          </div>

          <div className="requirement-status">
            <strong>Readiness: {documentReadiness?.readiness_score ?? 0}%</strong>
            <p>
              {documentReadiness?.total_uploaded ?? 0} of {documentReadiness?.total_required ?? requiredDocuments.length} required documents uploaded
            </p>
            {documentReadiness?.missing_documents?.length ? (
              <ul>
                {documentReadiness.missing_documents.map((document) => (
                  <li key={document.key}>{document.label}</li>
                ))}
              </ul>
            ) : (
              <p>All required documents are uploaded for this profile.</p>
            )}
          </div>

          <form onSubmit={handleDocumentUpload} className="document-upload-form">
            <label>
              Document type
              <select value={documentType} onChange={(event) => setDocumentType(event.target.value)}>
                {documentTypeOptions.map((option) => (
                  <option
                    key={option.value}
                    value={option.value}
                    disabled={uploadedDocumentTypes.includes(option.value)}
                  >
                    {option.label}{uploadedDocumentTypes.includes(option.value) ? ' · uploaded' : ''}
                  </option>
                ))}
              </select>
            </label>

            <label>
              File
              <input type="file" onChange={(event) => setSelectedFile(event.target.files?.[0] || null)} />
            </label>

            {documentError && <p className="error-message" role="alert">{documentError}</p>}

            <button
              className="secondary-button"
              type="submit"
              disabled={isUploadingDocument || !assessment || selectedDocumentTypeAlreadyUploaded}
            >
              {isUploadingDocument ? 'Uploading…' : 'Upload document'}
            </button>
          </form>

          {uploadedDocuments.length > 0 && (
            <ul className="uploaded-documents">
              {uploadedDocuments.map((document) => (
                <li key={document.id}>
                  <span>{document.name}</span>
                  <small>{document.type} · {document.status}</small>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </main>
  )
}

export default App
