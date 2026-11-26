import {
  ArrowLeft,
  ArrowRight,
  Beaker,
  CheckCircle2,
  CircleAlert,
  ClipboardList,
  Download,
  FileCheck2,
  Search,
  ShieldCheck,
  X,
} from 'lucide-react'
import { useEffect, useState, type Dispatch, type FormEvent, type ReactNode, type SetStateAction } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { farmerApi } from '../api/farmer'
import { getApiErrorMessage } from '../api/client'
import { downloadBlob } from '../api/products'
import { labApi } from '../api/lab'
import type { LabMeasurement, LabTest } from '../api/types'
import { Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, Pagination, StatCard, StatusBadge } from '../components/UI'
import { useToast } from '../components/ToastProvider'

function PageContent({ children }: { children: ReactNode }) {
  return <div className="page-content">{children}</div>
}

function LabTestTable({ tests, onOpen }: { tests: LabTest[]; onOpen: (test: LabTest) => void }) {
  if (!tests.length) return <EmptyState title="No test requests found" message="Assigned requests will appear when a participant submits a batch for testing." />
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead><tr><th>Batch / herb</th><th>Test type</th><th>Request date</th><th>Status</th><th>Certificate</th><th>Action</th></tr></thead>
        <tbody>
          {tests.map((test) => (
            <tr key={test.test_id}>
              <td><span className="table-primary">{test.herb_name || `Batch ${test.batch}`}</span><span className="table-secondary">{test.batch_id || test.test_id}</span></td>
              <td>{test.test_type}</td>
              <td>{formatDate(test.test_date)}</td>
              <td><StatusBadge value={test.status} /></td>
              <td>{test.certificate_available ? <span className="status-badge status-approved">Available</span> : '—'}</td>
              <td><Button onClick={() => onOpen(test)} variant="secondary">Process <ArrowRight size={12} /></Button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function LabDashboardPage() {
  const dashboard = useQuery({ queryKey: ['lab', 'dashboard'], queryFn: labApi.dashboard })
  const requests = useQuery({ queryKey: ['lab', 'requests', 'dashboard'], queryFn: () => labApi.requests({ page: 1 }) })
  const navigate = useNavigate()
  const error = dashboard.error ?? requests.error
  if (dashboard.isLoading || requests.isLoading) return <PageContent><LoadingState /></PageContent>
  if (error) return <PageContent><ErrorState message={getApiErrorMessage(error)} onRetry={() => {
    void dashboard.refetch()
    void requests.refetch()
  }} /></PageContent>
  const counts = dashboard.data
  const tests = requests.data?.results ?? []
  return (
    <PageContent>
      <PageHeader eyebrow="Laboratory workspace" title="Quality testing dashboard" description="Review assigned samples, record assay measurements, and complete laboratory decisions." />
      <div className="stat-grid">
        <StatCard icon={<ClipboardList size={16} />} label="Pending tests" value={counts?.pending ?? 0} />
        <StatCard icon={<Beaker size={16} />} label="Under testing" value={counts?.under_testing ?? 0} />
        <StatCard icon={<CheckCircle2 size={16} />} label="Approved" value={counts?.approved ?? 0} />
        <StatCard icon={<CircleAlert size={16} />} label="Rejected" value={counts?.rejected ?? 0} />
      </div>
      <Card
        title="Assigned test requests"
        subtitle="Latest requests assigned to your laboratory"
        actions={<Link className="inline-link" to="/lab/requests">View all requests <ArrowRight size={12} /></Link>}
      >
        <LabTestTable tests={tests.slice(0, 6)} onOpen={(test) => navigate(`/lab/tests/${test.test_id}`)} />
      </Card>
    </PageContent>
  )
}

export function LabRequestsPage({ history = false }: { history?: boolean }) {
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState(params.get('search') ?? '')
  const page = Number(params.get('page') ?? '1')
  const query = useQuery({
    queryKey: ['lab', history ? 'history' : 'requests', params.toString()],
    queryFn: () => history
      ? labApi.history({ page })
      : labApi.requests({
        page,
        search: params.get('search') ?? undefined,
        ordering: params.get('ordering') ?? undefined,
      }),
  })
  const navigate = useNavigate()
  const submit = (event: FormEvent) => {
    event.preventDefault()
    setParams(search.trim() ? { search: search.trim(), page: '1' } : {})
  }
  if (query.isLoading) return <PageContent><LoadingState /></PageContent>
  if (query.error) return <PageContent><ErrorState message={getApiErrorMessage(query.error)} onRetry={() => void query.refetch()} /></PageContent>
  const tests = query.data?.results ?? []
  return (
    <PageContent>
      <PageHeader
        eyebrow={history ? 'Completed work' : 'Laboratory queue'}
        title={history ? 'Test history' : 'Assigned tests'}
        description={history ? 'Previously submitted test records for your laboratory.' : 'Search by batch identifier or herb name and open a request to process it.'}
      />
      <Card
        title={history ? 'Laboratory test history' : 'Assigned requests'}
        subtitle={`${query.data?.count ?? 0} records`}
        actions={!history ? (
          <form className="toolbar" onSubmit={submit}>
            <label className="search-control"><Search size={14} /><input aria-label="Search assigned tests" onChange={(event) => setSearch(event.target.value)} placeholder="Batch ID or herb…" value={search} /></label>
            <Button type="submit" variant="secondary">Search</Button>
          </form>
        ) : null}
      >
        <LabTestTable tests={tests} onOpen={(test) => navigate(`/lab/tests/${test.test_id}`)} />
        <Pagination
          count={query.data?.count ?? 0}
          disabled={query.isFetching}
          onChange={(nextPage) => setParams({
            ...(params.get('search') ? { search: params.get('search')! } : {}),
            page: String(nextPage),
          })}
          page={page}
        />
      </Card>
    </PageContent>
  )
}

interface MeasurementDraft {
  analyte: string
  method: string
  result_value: string
  numeric_value: string
  unit: string
  threshold: string
  verdict: LabMeasurement['verdict']
}

const emptyMeasurement: MeasurementDraft = {
  analyte: '',
  method: '',
  result_value: '',
  numeric_value: '',
  unit: '',
  threshold: '',
  verdict: 'INCONCLUSIVE',
}

export function LabTestDetailPage() {
  const { testId = '' } = useParams()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { notify } = useToast()
  const [measurements, setMeasurements] = useState<MeasurementDraft[]>([{ ...emptyMeasurement }])
  const [testResult, setTestResult] = useState('')
  const [summary, setSummary] = useState('')
  const [remarks, setRemarks] = useState('')
  const [certificate, setCertificate] = useState<File>()
  const [message, setMessage] = useState('')
  const testQuery = useQuery({
    queryKey: ['lab', 'test', testId],
    queryFn: () => labApi.test(testId),
    enabled: Boolean(testId),
  })
  const test = testQuery.data
  useEffect(() => {
    if (!test) return
    setTestResult(test.test_result)
    setSummary(test.result_summary)
    setRemarks(test.remarks)
    setMeasurements(test.measurements.length
      ? test.measurements.map((measurement) => ({
        analyte: measurement.analyte,
        method: measurement.method,
        result_value: measurement.result_value,
        numeric_value: measurement.numeric_value ?? '',
        unit: measurement.unit,
        threshold: measurement.threshold,
        verdict: measurement.verdict,
      }))
      : [{ ...emptyMeasurement }])
  }, [test])
  const batchHistory = useQuery({
    queryKey: ['lab', 'batch-history', test?.batch_id],
    queryFn: () => farmerApi.history(test?.batch_id ?? ''),
    enabled: Boolean(test?.batch_id),
  })
  const decision = useMutation({
    mutationFn: async (accepted: boolean) => {
      if (!test) throw new Error('Test request not found.')
      return accepted
        ? labApi.approve(test.test_id, remarks)
        : labApi.reject(test.test_id, remarks)
    },
    onSuccess: async (_result, accepted) => {
      await queryClient.invalidateQueries({ queryKey: ['lab'] })
      notify(accepted ? 'Lab test approved and batch status updated.' : 'Lab test rejected and batch status updated.')
      navigate('/lab/requests')
    },
    onError: (error) => setMessage(getApiErrorMessage(error)),
  })
  const saveResult = useMutation({
    mutationFn: () => {
      if (!test) throw new Error('Test request not found.')
      const cleanMeasurements: LabMeasurement[] = measurements
        .filter((item) => item.analyte.trim() && item.result_value.trim())
        .map((item) => ({
          analyte: item.analyte.trim(),
          method: item.method.trim(),
          result_value: item.result_value.trim(),
          numeric_value: item.numeric_value.trim() || null,
          unit: item.unit.trim(),
          threshold: item.threshold.trim(),
          verdict: item.verdict,
        }))
      if (!testResult.trim() && cleanMeasurements.length === 0) {
        throw new Error('Enter a test result or at least one complete assay measurement.')
      }
      return labApi.submitResult({
        test_id: test.test_id,
        test_result: testResult.trim(),
        result_summary: summary.trim(),
        remarks: remarks.trim(),
        measurements: cleanMeasurements,
        certificate_file: certificate,
      })
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['lab'] })
      await testQuery.refetch()
      notify('Test results saved.')
      setMessage('')
    },
    onError: (error) => setMessage(getApiErrorMessage(error)),
  })

  if (testQuery.isLoading) return <PageContent><LoadingState /></PageContent>
  if (testQuery.error || !test) return <PageContent><ErrorState message={getApiErrorMessage(testQuery.error ?? new Error('Test was not found.'))} onRetry={() => void testQuery.refetch()} /></PageContent>
  const batch = batchHistory.data?.batch
  const canProcess = ['PENDING', 'UNDER_TESTING'].includes(test.status)
  const hasSavedResults = Boolean(test.test_result?.trim() || test.measurements.length)

  return (
    <PageContent>
      <PageHeader
        eyebrow="Test processing & submission"
        title={test.herb_name ?? 'Laboratory test'}
        description={`${test.batch_id ?? `Batch ${test.batch}`} · ${test.test_type}`}
        actions={<><StatusBadge value={test.status} /><Link className="button button-secondary" to="/lab/requests"><ArrowLeft size={14} /> Assigned tests</Link></>}
      />
      <div className="content-grid">
        <div style={{ display: 'grid', alignContent: 'start', gap: 16 }}>
          <Card title="Batch information & provenance" subtitle="Source data from the associated batch history">
            {batchHistory.isLoading ? <LoadingState /> : batchHistory.error ? (
              <div className="card-body"><ErrorState message={getApiErrorMessage(batchHistory.error)} onRetry={() => void batchHistory.refetch()} /></div>
            ) : batch ? (
              <div className="card-body key-value-list">
                <KeyValue label="Batch identifier" value={batch.batch_id} />
                <KeyValue label="Herb" value={batch.herb_name} />
                <KeyValue label="Botanical name" value={batch.botanical_name} />
                <KeyValue label="Plant part" value={batch.plant_part || '—'} />
                <KeyValue label="Harvested" value={batch.collection_date} />
                <KeyValue label="Origin" value={[batch.village, batch.district, batch.state].filter(Boolean).join(', ')} />
                <KeyValue label="Current batch status" value={batch.status.replaceAll('_', ' ')} />
              </div>
            ) : (
              <div className="card-body"><KeyValue label="Batch identifier" value={test.batch_id ?? String(test.batch)} /><KeyValue label="Herb" value={test.herb_name ?? '—'} /></div>
            )}
          </Card>
          <Card title="Recorded measurements" subtitle="Measurements already stored for this test">
            {test.measurements.length === 0 ? <EmptyState title="No assay measurements" message="Record validated assay rows in the result form." /> : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead><tr><th>Analyte</th><th>Result</th><th>Threshold</th><th>Verdict</th></tr></thead>
                  <tbody>
                    {test.measurements.map((measurement) => (
                      <tr key={measurement.measurement_id ?? measurement.analyte}>
                        <td>{measurement.analyte}<span className="table-secondary">{measurement.method || 'Method not specified'}</span></td>
                        <td>{measurement.result_value} {measurement.unit}</td>
                        <td>{measurement.threshold || '—'}</td>
                        <td><StatusBadge value={measurement.verdict} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
        <Card title="Test result" subtitle="Submit real observations and optional structured measurements.">
          <div className="card-body">
            {test.certificate_available && (
              <Button
                onClick={async () => {
                  try {
                    downloadBlob(await labApi.downloadCertificate(test.test_id), `lab-certificate-${test.test_id}.pdf`)
                  } catch (error) {
                    setMessage(getApiErrorMessage(error))
                  }
                }}
                variant="secondary"
              >
                <Download size={14} /> Download private certificate
              </Button>
            )}
            {canProcess && (
              <form className="auth-form" onSubmit={(event) => {
                event.preventDefault()
                setMessage('')
                saveResult.mutate()
              }}>
                <div className="field">
                  <label htmlFor="test-result-text">Observed result / notes</label>
                  <textarea id="test-result-text" onChange={(event) => setTestResult(event.target.value)} placeholder="Optional when structured measurements are recorded…" value={testResult} />
                </div>
                <div className="field">
                  <label htmlFor="test-summary">Result summary</label>
                  <input id="test-summary" onChange={(event) => setSummary(event.target.value)} value={summary} />
                </div>
                <div className="field">
                  <label htmlFor="test-remarks">Remarks</label>
                  <textarea id="test-remarks" onChange={(event) => setRemarks(event.target.value)} value={remarks} />
                </div>
                <div className="card" style={{ boxShadow: 'none' }}>
                  <div className="card-header">
                    <div><h2>Assay measurements</h2><p>Enter only observed values; verdict is recorded explicitly.</p></div>
                    <Button onClick={() => setMeasurements((current) => [...current, { ...emptyMeasurement }])} variant="secondary">Add row</Button>
                  </div>
                  <div className="card-body" style={{ display: 'grid', gap: 12 }}>
                    {measurements.map((measurement, index) => (
                      <div className="form-grid" key={index}>
                        <div className="field">
                          <label htmlFor={`analyte-${index}`}>Analyte</label>
                          <input id={`analyte-${index}`} onChange={(event) => updateMeasurement(index, 'analyte', event.target.value, setMeasurements)} value={measurement.analyte} />
                        </div>
                        <div className="field">
                          <label htmlFor={`method-${index}`}>Method</label>
                          <input id={`method-${index}`} onChange={(event) => updateMeasurement(index, 'method', event.target.value, setMeasurements)} value={measurement.method} />
                        </div>
                        <div className="field">
                          <label htmlFor={`value-${index}`}>Observed result</label>
                          <input id={`value-${index}`} onChange={(event) => updateMeasurement(index, 'result_value', event.target.value, setMeasurements)} value={measurement.result_value} />
                        </div>
                        <div className="field">
                          <label htmlFor={`numeric-${index}`}>Numeric value (optional)</label>
                          <input id={`numeric-${index}`} onChange={(event) => updateMeasurement(index, 'numeric_value', event.target.value, setMeasurements)} type="number" step="any" value={measurement.numeric_value} />
                        </div>
                        <div className="field">
                          <label htmlFor={`unit-${index}`}>Unit</label>
                          <input id={`unit-${index}`} onChange={(event) => updateMeasurement(index, 'unit', event.target.value, setMeasurements)} value={measurement.unit} />
                        </div>
                        <div className="field">
                          <label htmlFor={`threshold-${index}`}>Threshold</label>
                          <input id={`threshold-${index}`} onChange={(event) => updateMeasurement(index, 'threshold', event.target.value, setMeasurements)} value={measurement.threshold} />
                        </div>
                        <div className="field">
                          <label htmlFor={`verdict-${index}`}>Verdict</label>
                          <select id={`verdict-${index}`} onChange={(event) => updateMeasurement(index, 'verdict', event.target.value as LabMeasurement['verdict'], setMeasurements)} value={measurement.verdict}>
                            <option value="PASS">Pass</option>
                            <option value="FAIL">Fail</option>
                            <option value="INCONCLUSIVE">Inconclusive</option>
                          </select>
                        </div>
                        {measurements.length > 1 && <div className="form-actions"><Button onClick={() => setMeasurements((current) => current.filter((_row, rowIndex) => rowIndex !== index))} variant="quiet"><X size={14} /> Remove row</Button></div>}
                      </div>
                    ))}
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="test-certificate">Certificate PDF <span className="field-hint">(optional, private)</span></label>
                  <label className="file-drop" htmlFor="test-certificate">
                    <FileCheck2 size={18} />
                    <strong>{certificate?.name ?? 'Choose certificate document'}</strong>
                    <span>Only upload an issued laboratory document.</span>
                  </label>
                  <input accept=".pdf,.jpg,.jpeg,.png" id="test-certificate" onChange={(event) => setCertificate(event.target.files?.[0])} style={{ display: 'none' }} type="file" />
                </div>
                {message && <ErrorState message={message} />}
                {saveResult.error && <ErrorState message={getApiErrorMessage(saveResult.error)} />}
                <Button className="button-full" disabled={saveResult.isPending} type="submit">
                  {saveResult.isPending ? 'Saving results…' : 'Save test results'} <ArrowRight size={14} />
                </Button>
              </form>
            )}
            {hasSavedResults && test.status === 'UNDER_TESTING' && (
              <div className="divider" />
            )}
            {['PENDING', 'UNDER_TESTING'].includes(test.status) && (
              <div className="form-actions" style={{ justifyContent: 'space-between' }}>
                <Button disabled={decision.isPending} onClick={() => decision.mutate(false)} variant="danger"><X size={14} /> Reject batch</Button>
                {test.status === 'UNDER_TESTING' && (
                  <Button disabled={decision.isPending || !hasSavedResults} onClick={() => decision.mutate(true)}>
                    {decision.isPending ? 'Submitting…' : 'Approve test results'} <ShieldCheck size={14} />
                  </Button>
                )}
              </div>
            )}
            {test.status === 'APPROVED' && <div className="alert alert-success"><ShieldCheck size={16} />This test is approved. Measurements are visible in public verification; the certificate file remains private.</div>}
            {message && <div style={{ marginTop: 12 }}><ErrorState message={message} /></div>}
            {decision.error && <div style={{ marginTop: 12 }}><ErrorState message={getApiErrorMessage(decision.error)} /></div>}
          </div>
        </Card>
      </div>
    </PageContent>
  )
}

function updateMeasurement<K extends keyof MeasurementDraft>(
  index: number,
  key: K,
  value: MeasurementDraft[K],
  setRows: Dispatch<SetStateAction<MeasurementDraft[]>>,
) {
  setRows((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, [key]: value } : row))
}

function KeyValue({ label, value }: { label: string; value: string }) {
  return <div className="key-value-row"><span>{label}</span><strong>{value || '—'}</strong></div>
}

function formatDate(value: string) {
  if (!value) return '—'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(`${value.slice(0, 10)}T00:00:00`))
}
