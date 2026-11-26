import { zodResolver } from '@hookform/resolvers/zod'
import {
  ArrowLeft,
  ArrowRight,
  Beaker,
  Boxes,
  CheckCircle2,
  Clock3,
  FileImage,
  Leaf,
  Plus,
  Search,
  Truck,
  UploadCloud,
} from 'lucide-react'
import { useState, type FormEvent, type InputHTMLAttributes, type ReactNode } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { collectorApi } from '../api/collector'
import { getApiErrorMessage } from '../api/client'
import { farmerApi, type BatchInput } from '../api/farmer'
import { labApi } from '../api/lab'
import { participantsApi } from '../api/participants'
import type { HerbBatch } from '../api/types'
import { Button, Card, EmptyState, ErrorState, FieldError, LoadingState, Modal, PageHeader, Pagination, StatCard, StatusBadge } from '../components/UI'
import { useToast } from '../components/ToastProvider'
import { useAuth } from '../auth/AuthProvider'

const batchSchema = z.object({
  herb_name: z.string().trim().min(2, 'Enter the herb name.'),
  botanical_name: z.string().trim().min(2, 'Enter the botanical name.'),
  plant_part: z.string(),
  cultivar: z.string(),
  quality_grade: z.string(),
  description: z.string(),
  packaging_details: z.string(),
  drying_notes: z.string(),
  gacp_attested: z.boolean(),
  quantity: z.string().refine((value) => Number(value) > 0, 'Quantity must be greater than zero.'),
  unit: z.string().min(1, 'Enter a unit.'),
  source_type: z.enum(['CULTIVATED', 'WILD_COLLECTED']),
  collection_date: z.string().min(1, 'Choose a harvest date.'),
  collection_time: z.string().min(1, 'Choose a harvest time.'),
  latitude: z.string(),
  longitude: z.string(),
  collection_address: z.string().min(2, 'Enter the origin address.'),
  village: z.string().min(1, 'Enter the village.'),
  district: z.string().min(1, 'Enter the district.'),
  state: z.string().min(1, 'Enter the state.'),
  remarks: z.string(),
})
type BatchFormValues = z.infer<typeof batchSchema>

function PageContent({ children }: { children: ReactNode }) {
  return <div className="page-content">{children}</div>
}

function DataQueryError({
  error,
  retry,
}: {
  error: unknown
  retry: () => void
}) {
  return <ErrorState message={getApiErrorMessage(error)} onRetry={retry} />
}

function BatchTable({
  batches,
  emptyTitle = 'No batches yet',
  emptyMessage = 'Batches you register will appear here.',
}: {
  batches: HerbBatch[]
  emptyTitle?: string
  emptyMessage?: string
}) {
  if (batches.length === 0) {
    return <EmptyState title={emptyTitle} message={emptyMessage} />
  }
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Batch & herb</th>
            <th>Origin</th>
            <th>Harvested</th>
            <th>Quantity</th>
            <th>Status</th>
            <th aria-label="Action" />
          </tr>
        </thead>
        <tbody>
          {batches.map((batch) => (
            <tr key={batch.batch_id}>
              <td>
                <span className="table-primary">{batch.herb_name}</span>
                <span className="table-secondary">{batch.batch_id} · {batch.botanical_name}</span>
              </td>
              <td>{[batch.village, batch.district, batch.state].filter(Boolean).join(', ') || '—'}</td>
              <td>{formatDate(batch.collection_date)}</td>
              <td>{formatQuantity(batch.available_quantity)} {batch.unit}</td>
              <td><StatusBadge value={batch.status} /></td>
              <td><Link className="inline-link" to={`/farmer/batches/${encodeURIComponent(batch.batch_id)}`}>Details</Link></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function FarmerDashboardPage() {
  const countsQuery = useQuery({ queryKey: ['farmer', 'dashboard'], queryFn: farmerApi.dashboard })
  const batchesQuery = useQuery({ queryKey: ['farmer', 'batches', 'recent'], queryFn: () => farmerApi.batches({ page: 1 }) })
  const counts = countsQuery.data
  const retry = () => {
    void countsQuery.refetch()
    void batchesQuery.refetch()
  }
  if (countsQuery.isLoading || batchesQuery.isLoading) return <PageContent><LoadingState /></PageContent>
  if (countsQuery.error || batchesQuery.error) {
    return <PageContent><DataQueryError error={countsQuery.error ?? batchesQuery.error} retry={retry} /></PageContent>
  }

  return (
    <PageContent>
      <PageHeader
        description="Track harvest records and the latest custody status of your batches."
        eyebrow="Farmer workspace"
        title="Good day, farmer"
        actions={<Link className="button button-primary" to="/farmer/batches/new"><Plus size={15} /> Register new batch</Link>}
      />
      <div className="stat-grid">
        <StatCard icon={<Boxes size={16} />} label="Total registered batches" value={counts?.total_batches ?? 0} />
        <StatCard icon={<Clock3 size={16} />} label="Registered" value={counts?.registered ?? 0} caption="Awaiting the next workflow step" />
        <StatCard icon={<CheckCircle2 size={16} />} label="Approved" value={counts?.approved ?? 0} />
        <StatCard icon={<Leaf size={16} />} label="Rejected" value={counts?.rejected ?? 0} />
      </div>
      <Card
        title="Recent batches"
        subtitle="Your latest registered harvest records"
        actions={<Link className="inline-link" to="/farmer/batches">View all batches <ArrowRight size={12} /></Link>}
      >
        <BatchTable batches={batchesQuery.data?.results ?? []} />
      </Card>
    </PageContent>
  )
}

export function FarmerBatchesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [search, setSearch] = useState(searchParams.get('search') ?? '')
  const page = Number(searchParams.get('page') ?? '1')
  const query = useQuery({
    queryKey: ['farmer', 'batches', searchParams.toString()],
    queryFn: () => farmerApi.batches({
      search: searchParams.get('search') ?? undefined,
      page,
    }),
  })

  const submitSearch = (event: FormEvent) => {
    event.preventDefault()
    setSearchParams(search.trim() ? { search: search.trim(), page: '1' } : {})
  }

  return (
    <PageContent>
      <PageHeader
        description="Search and open your registered herb batches."
        eyebrow="Harvest records"
        title="My batches"
        actions={<Link className="button button-primary" to="/farmer/batches/new"><Plus size={15} /> Register batch</Link>}
      />
      <Card
        title="Batch register"
        subtitle={query.data ? `${query.data.count} records` : 'Live records from your account'}
        actions={
          <form className="toolbar" onSubmit={submitSearch}>
            <label className="search-control">
              <Search size={14} />
              <input aria-label="Search batches" onChange={(event) => setSearch(event.target.value)} placeholder="Search ID, herb, district…" value={search} />
            </label>
            <Button type="submit" variant="secondary">Search</Button>
          </form>
        }
      >
        {query.isLoading ? <LoadingState /> : query.error ? (
          <div className="card-body"><DataQueryError error={query.error} retry={() => void query.refetch()} /></div>
        ) : <BatchTable batches={query.data?.results ?? []} emptyTitle="No matching batches" emptyMessage="Try another search or register a new batch." />}
        {query.data && (
          <Pagination
            count={query.data.count}
            disabled={query.isFetching}
            onChange={(nextPage) => setSearchParams({
              ...(searchParams.get('search') ? { search: searchParams.get('search')! } : {}),
              page: String(nextPage),
            })}
            page={page}
          />
        )}
      </Card>
    </PageContent>
  )
}

const emptyBatchForm: BatchFormValues = {
  herb_name: '',
  botanical_name: '',
  plant_part: '',
  cultivar: '',
  quality_grade: '',
  description: '',
  packaging_details: '',
  drying_notes: '',
  gacp_attested: false,
  quantity: '',
  unit: '',
  source_type: 'CULTIVATED',
  collection_date: new Date().toISOString().slice(0, 10),
  collection_time: '',
  latitude: '',
  longitude: '',
  collection_address: '',
  village: '',
  district: '',
  state: '',
  remarks: '',
}

export function RegisterBatchPage() {
  const navigate = useNavigate()
  const { notify } = useToast()
  const queryClient = useQueryClient()
  const [photos, setPhotos] = useState<File[]>([])
  const [message, setMessage] = useState('')
  const form = useForm<BatchFormValues>({
    resolver: zodResolver(batchSchema),
    defaultValues: emptyBatchForm,
  })
  const mutation = useMutation({
    mutationFn: (input: BatchInput) => farmerApi.createBatch(input),
    onSuccess: async (batch) => {
      try {
        for (const photo of photos.slice(0, 8)) {
          await farmerApi.uploadEvidence(batch.batch_id, photo, 'PHOTO', photo.name)
        }
      } catch (error) {
        await queryClient.invalidateQueries({ queryKey: ['farmer'] })
        setMessage(`Batch ${batch.batch_id} was registered, but evidence upload failed: ${getApiErrorMessage(error)}`)
        notify('The batch was saved, but at least one evidence file could not be uploaded. Open the batch to retry.', 'error')
        return
      }
      await queryClient.invalidateQueries({ queryKey: ['farmer'] })
      notify('Harvest batch registered successfully.')
      navigate(`/farmer/batches/${encodeURIComponent(batch.batch_id)}`)
    },
    onError: (error) => setMessage(getApiErrorMessage(error)),
  })

  const submit = (values: BatchFormValues) => {
    setMessage('')
    if (photos.length > 8) {
      setMessage('A batch can have at most 8 evidence files.')
      return
    }
    const numberOrNull = (value: string) => value.trim() ? value.trim() : null
    mutation.mutate({
      ...values,
      latitude: numberOrNull(values.latitude),
      longitude: numberOrNull(values.longitude),
    })
  }

  return (
    <PageContent>
      <PageHeader
        description="Record the harvest details and attach field evidence for this batch."
        eyebrow="Harvest records"
        title="Register a new batch"
        actions={<Link className="button button-secondary" to="/farmer/batches"><ArrowLeft size={14} /> Back to batches</Link>}
      />
      {message && <div style={{ marginBottom: 16 }}><ErrorState message={message} /></div>}
      <Card title="Batch and origin details" subtitle="Fields are saved to the batch record. Evidence files upload after the batch is created.">
        <div className="card-body">
          <form onSubmit={form.handleSubmit(submit)}>
            <div className="form-grid">
              <TextField form={form} name="herb_name" label="Herb name" placeholder="e.g. Ashwagandha" />
              <TextField form={form} name="botanical_name" label="Botanical name" placeholder="e.g. Withania somnifera" />
              <TextField form={form} name="plant_part" label="Plant part" placeholder="Root, leaf, flower…" />
              <TextField form={form} name="cultivar" label="Cultivar / variety" />
              <TextField form={form} name="quality_grade" label="Quality grade" />
              <div className="field">
                <label htmlFor="batch-source">Source type</label>
                <select id="batch-source" {...form.register('source_type')}>
                  <option value="CULTIVATED">Cultivated</option>
                  <option value="WILD_COLLECTED">Wild collected</option>
                </select>
              </div>
              <TextField form={form} name="quantity" label="Harvest quantity" type="number" step="0.001" min="0.001" />
              <TextField form={form} name="unit" label="Unit" placeholder="kg" />
              <TextField form={form} name="collection_date" label="Harvest date" type="date" />
              <TextField form={form} name="collection_time" label="Harvest time" type="time" />
              <TextField form={form} name="collection_address" label="Farm / collection address" />
              <TextField form={form} name="village" label="Village" />
              <TextField form={form} name="district" label="District" />
              <TextField form={form} name="state" label="State" />
              <TextField form={form} name="latitude" label="Latitude (optional)" type="number" step="0.000001" min="-90" max="90" />
              <TextField form={form} name="longitude" label="Longitude (optional)" type="number" step="0.000001" min="-180" max="180" />
              <TextField form={form} name="packaging_details" label="Packaging details" />
              <TextField form={form} name="description" label="Cultivation / field notes" />
              <div className="field span-2">
                <label htmlFor="batch-drying-notes">Drying notes</label>
                <textarea id="batch-drying-notes" {...form.register('drying_notes')} />
              </div>
              <div className="field span-2">
                <label className="toolbar" htmlFor="gacp-attested">
                  <input id="gacp-attested" type="checkbox" {...form.register('gacp_attested')} />
                  GACP practices attested by the farmer
                </label>
              </div>
              <div className="field span-2">
                <label htmlFor="batch-remarks">Additional remarks</label>
                <textarea id="batch-remarks" {...form.register('remarks')} />
              </div>
              <div className="field span-2">
                <label htmlFor="batch-photos">Field evidence photos <span className="field-hint">(optional, up to 8 images)</span></label>
                <label className="file-drop" htmlFor="batch-photos">
                  <UploadCloud size={19} />
                  <strong>Choose harvest photos</strong>
                  <span>{photos.length ? `${photos.length} file${photos.length === 1 ? '' : 's'} selected` : 'Images are uploaded to the configured private storage.'}</span>
                </label>
                <input
                  accept="image/*"
                  id="batch-photos"
                  multiple
                  onChange={(event) => setPhotos(Array.from(event.target.files ?? []))}
                  style={{ display: 'none' }}
                  type="file"
                />
              </div>
            </div>
            {mutation.isError && <div style={{ marginTop: 16 }}><ErrorState message={getApiErrorMessage(mutation.error)} /></div>}
            <div className="form-actions">
              <Button onClick={() => navigate('/farmer/batches')} variant="secondary">Cancel</Button>
              <Button disabled={mutation.isPending} type="submit">
                {mutation.isPending ? 'Registering…' : 'Register batch'} <ArrowRight size={14} />
              </Button>
            </div>
          </form>
        </div>
      </Card>
    </PageContent>
  )
}

function TextField({
  form,
  name,
  label,
  ...inputProps
}: {
  form: ReturnType<typeof useForm<BatchFormValues>>
  name: keyof BatchFormValues
  label: string
} & Omit<InputHTMLAttributes<HTMLInputElement>, 'name' | 'form'>) {
  const id = `batch-${String(name)}`
  const registration = form.register(name)
  const error = form.formState.errors[name]
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input id={id} {...inputProps} {...registration} />
      <FieldError>{error?.message}</FieldError>
    </div>
  )
}

function formatDate(value: string) {
  if (!value) return '—'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(`${value}T00:00:00`))
}

function formatQuantity(value: string | number) {
  const number = Number(value)
  return Number.isFinite(number)
    ? new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 }).format(number)
    : String(value)
}

function BatchActionModal({
  batch,
  mode,
  onClose,
}: {
  batch: HerbBatch
  mode: 'lab' | 'transfer'
  onClose: () => void
}) {
  const { notify } = useToast()
  const queryClient = useQueryClient()
  const [message, setMessage] = useState('')
  const [working, setWorking] = useState(false)
  const [selectedParticipant, setSelectedParticipant] = useState('')
  const [testType, setTestType] = useState('')
  const [location, setLocation] = useState('')
  const [remarks, setRemarks] = useState('')
  const participantsQuery = useQuery({
    queryKey: ['participants', mode === 'lab' ? 'LAB' : 'COLLECTOR'],
    queryFn: () => participantsApi.list(mode === 'lab' ? 'LAB' : 'COLLECTOR'),
  })

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setWorking(true)
    setMessage('')
    try {
      if (!selectedParticipant) throw new Error(mode === 'lab' ? 'Select an approved laboratory.' : 'Select an approved Collector.')
      if (mode === 'lab') {
        if (!testType.trim()) throw new Error('Enter the requested test type.')
        await labApi.submitBatch({
          batch_id: batch.batch_id,
          laboratory_id: selectedParticipant,
          test_type: testType.trim(),
          test_date: new Date().toISOString().slice(0, 10),
          test_parameters: {},
        })
        notify('Laboratory test request submitted.')
      } else {
        if (!location.trim()) throw new Error('Enter the transfer location.')
        await collectorApi.initiate({
          batch_id: batch.batch_id,
          to_party: Number(selectedParticipant),
          quantity: batch.available_quantity,
          transfer_location: location.trim(),
          remarks,
        })
        notify('Transfer request created. The recipient must accept it before custody changes.')
      }
      await queryClient.invalidateQueries({ queryKey: ['farmer'] })
      onClose()
    } catch (error) {
      setMessage(getApiErrorMessage(error))
    } finally {
      setWorking(false)
    }
  }

  const roleName = mode === 'lab' ? 'Laboratory' : 'Collector'
  return (
    <Modal
      description={mode === 'lab' ? `Choose a verified Lab for batch ${batch.batch_id}.` : `This backend transfers the full available batch quantity.`}
      onClose={onClose}
      title={mode === 'lab' ? 'Submit for laboratory testing' : 'Transfer batch to Collector'}
    >
      {participantsQuery.isLoading ? <LoadingState label={`Loading approved ${roleName.toLowerCase()}s…`} /> : participantsQuery.error ? (
        <ErrorState message={getApiErrorMessage(participantsQuery.error)} onRetry={() => void participantsQuery.refetch()} />
      ) : (
        <form className="auth-form" onSubmit={submit}>
          <div className="field">
            <label htmlFor="action-participant">Verified {roleName}</label>
            <select id="action-participant" onChange={(event) => setSelectedParticipant(event.target.value)} required value={selectedParticipant}>
              <option value="">Choose {roleName.toLowerCase()}</option>
              {(participantsQuery.data?.results ?? []).map((participant) => (
                <option key={participant.user_id} value={mode === 'lab' ? participant.profile_id : participant.id}>
                  {participant.profile_name}{participant.profile_registration_number ? ` · ${participant.profile_registration_number}` : ''}
                </option>
              ))}
            </select>
            {participantsQuery.data?.results.length === 0 && <span className="field-hint">No verified {roleName.toLowerCase()}s are available yet.</span>}
          </div>
          {mode === 'lab' ? (
            <div className="field">
              <label htmlFor="test-type">Test type</label>
              <input id="test-type" onChange={(event) => setTestType(event.target.value)} placeholder="Purity and safety screening" required value={testType} />
            </div>
          ) : (
            <>
              <div className="field">
                <label htmlFor="transfer-quantity">Whole-batch quantity</label>
                <input id="transfer-quantity" readOnly value={`${batch.available_quantity} ${batch.unit}`} />
                <span className="field-hint">Partial-batch transfers are not supported.</span>
              </div>
              <div className="field">
                <label htmlFor="transfer-location">Transfer location</label>
                <input id="transfer-location" onChange={(event) => setLocation(event.target.value)} required value={location} />
              </div>
              <div className="field">
                <label htmlFor="transfer-remarks">Dispatch notes</label>
                <textarea id="transfer-remarks" onChange={(event) => setRemarks(event.target.value)} value={remarks} />
              </div>
            </>
          )}
          {message && <ErrorState message={message} />}
          <div className="form-actions">
            <Button onClick={onClose} variant="secondary">Cancel</Button>
            <Button disabled={working || participantsQuery.data?.results.length === 0} type="submit">
              {working ? 'Submitting…' : mode === 'lab' ? 'Submit test request' : 'Initiate transfer'} <ArrowRight size={14} />
            </Button>
          </div>
        </form>
      )}
    </Modal>
  )
}

export function FarmerBatchDetailPage() {
  const { batchId = '' } = useParams()
  const { user } = useAuth()
  const { notify } = useToast()
  const [action, setAction] = useState<'lab' | 'transfer' | null>(null)
  const batchQuery = useQuery({ queryKey: ['farmer', 'batch', batchId], queryFn: () => farmerApi.batch(batchId), enabled: Boolean(batchId) })
  const historyQuery = useQuery({ queryKey: ['farmer', 'history', batchId], queryFn: () => farmerApi.history(batchId), enabled: Boolean(batchId) })
  const evidenceQuery = useQuery({ queryKey: ['farmer', 'evidence', batchId], queryFn: () => farmerApi.evidence(batchId), enabled: Boolean(batchId) })

  if (batchQuery.isLoading) return <PageContent><LoadingState /></PageContent>
  if (batchQuery.error || !batchQuery.data) return <PageContent><ErrorState message={batchQuery.error ? getApiErrorMessage(batchQuery.error) : 'Batch not found.'} onRetry={() => void batchQuery.refetch()} /></PageContent>
  const batch = batchQuery.data
  const canEditEvidence = user?.role === 'FARMER' && ['REGISTERED', 'COLLECTED'].includes(batch.status)

  return (
    <PageContent>
      <PageHeader
        description={`${batch.botanical_name} · ${batch.batch_id}`}
        eyebrow="Batch traceability"
        title={batch.herb_name}
        actions={
          <>
            <StatusBadge value={batch.status} />
            <Link className="button button-secondary" to="/farmer/batches"><ArrowLeft size={14} /> Batches</Link>
            <Button onClick={() => setAction('lab')} variant="secondary"><Beaker size={14} /> Request lab test</Button>
            <Button onClick={() => setAction('transfer')}><Truck size={14} /> Transfer to Collector</Button>
          </>
        }
      />
      <div className="content-grid">
        <div style={{ display: 'grid', alignContent: 'start', gap: 16 }}>
          <Card title="Harvest and origin" subtitle="Persisted details for this batch">
            <div className="card-body key-value-list">
              <KeyValue label="Batch ID" value={batch.batch_id} />
              <KeyValue label="Plant part" value={batch.plant_part || '—'} />
              <KeyValue label="Cultivar" value={batch.cultivar || '—'} />
              <KeyValue label="Quality grade" value={batch.quality_grade || '—'} />
              <KeyValue label="Quantity available" value={`${formatQuantity(batch.available_quantity)} ${batch.unit}`} />
              <KeyValue label="Harvest date" value={formatDate(batch.collection_date)} />
              <KeyValue label="Origin" value={[batch.village, batch.district, batch.state].filter(Boolean).join(', ')} />
              <KeyValue label="GACP attested" value={batch.gacp_attested ? 'Yes' : 'No'} />
            </div>
          </Card>
          <Card
            title="Field evidence"
            subtitle="Photos and documents submitted for this batch"
            actions={canEditEvidence ? (
              <label className="button button-secondary" htmlFor="evidence-upload">
                <UploadCloud size={14} /> Add evidence
                <input
                  accept="image/*,.pdf"
                  id="evidence-upload"
                  onChange={async (event) => {
                    const file = event.target.files?.[0]
                    if (!file) return
                    try {
                      await farmerApi.uploadEvidence(
                        batch.batch_id,
                        file,
                        file.type.startsWith('image/') ? 'PHOTO' : 'DOCUMENT',
                        file.name,
                      )
                      await evidenceQuery.refetch()
                      notify('Field evidence uploaded.')
                    } catch (error) {
                      notify(getApiErrorMessage(error), 'error')
                    } finally {
                      event.target.value = ''
                    }
                  }}
                  style={{ display: 'none' }}
                  type="file"
                />
              </label>
            ) : null}
          >
            {evidenceQuery.isLoading ? <LoadingState /> : evidenceQuery.error ? (
              <div className="card-body"><DataQueryError error={evidenceQuery.error} retry={() => void evidenceQuery.refetch()} /></div>
            ) : (evidenceQuery.data?.length ?? 0) === 0 ? (
              <EmptyState title="No field evidence" message="Evidence will appear here after it is uploaded." />
            ) : (
              <div className="card-body" style={{ display: 'grid', gap: 10 }}>
                {evidenceQuery.data?.map((evidence) => (
                  <a className="key-value-row" href={evidence.file} key={evidence.evidence_id} rel="noreferrer" target="_blank">
                    <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}><FileImage size={14} />{evidence.label || evidence.kind}</span>
                    <span>{formatDate(evidence.created_at.slice(0, 10))} <ArrowRight size={12} /></span>
                  </a>
                ))}
              </div>
            )}
          </Card>
          {historyQuery.error && <ErrorState message={getApiErrorMessage(historyQuery.error)} onRetry={() => void historyQuery.refetch()} />}
        </div>
        <Card title="Traceability history" subtitle="Custody, testing and production events">
          <div className="card-body">
            {historyQuery.isLoading ? <LoadingState /> : historyQuery.data?.history.length ? (
              <div className="timeline">
                {historyQuery.data.history.map((event, index) => (
                  <div className="timeline-item" key={`${event.event_type}-${event.event_id}-${index}`}>
                    <span className="timeline-dot"><Clock3 size={11} /></span>
                    <div className="timeline-copy">
                      <strong>{eventTitle(event.event_type)}</strong>
                      <span>
                        {event.status?.replaceAll('_', ' ')}
                        {event.from && event.to ? ` · ${event.from} → ${event.to}` : ''}
                        {event.laboratory ? ` · ${event.laboratory}` : ''}
                        {event.product_name ? ` · ${event.product_name}` : ''}
                      </span>
                      <span>{event.occurred_at ? new Date(event.occurred_at).toLocaleString() : ''}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : <EmptyState title="History not available" message="No workflow events are currently recorded." />}
          </div>
        </Card>
      </div>
      {action && <BatchActionModal batch={batch} mode={action} onClose={() => setAction(null)} />}
    </PageContent>
  )
}

function KeyValue({ label, value }: { label: string; value: string }) {
  return <div className="key-value-row"><span>{label}</span><strong>{value}</strong></div>
}

function eventTitle(type?: string) {
  const titles: Record<string, string> = {
    BATCH_REGISTERED: 'Batch registered',
    TRANSFER: 'Custody transfer',
    LAB_TEST: 'Laboratory test',
    MANUFACTURING: 'Manufacturing run',
    PRODUCT: 'Finished product',
  }
  return type ? titles[type] ?? type.replaceAll('_', ' ') : 'Traceability event'
}

export function FarmerTransfersPage() {
  const query = useQuery({ queryKey: ['farmer', 'transfers'], queryFn: collectorApi.history })
  if (query.isLoading) return <PageContent><LoadingState /></PageContent>
  if (query.error) return <PageContent><DataQueryError error={query.error} retry={() => void query.refetch()} /></PageContent>
  const events = query.data?.results ?? []
  return (
    <PageContent>
      <PageHeader eyebrow="Custody handovers" title="Batch transfers" description="Review transfer requests and custody history associated with your account." />
      <Card title="Transfer history" subtitle={`${events.length} records on this page`}>
        {events.length === 0 ? <EmptyState title="No transfers yet" message="Transfers initiated for your batches will appear here." /> : (
          <div className="table-wrap">
            <table className="data-table">
              <thead><tr><th>Batch</th><th>Direction</th><th>Counterparty</th><th>Quantity</th><th>Location</th><th>Status</th><th>Date</th></tr></thead>
              <tbody>
                {events.map((event) => (
                  <tr key={event.event_id}>
                    <td><span className="table-primary">{event.herb_name}</span><span className="table-secondary">{event.batch_identifier}</span></td>
                    <td>{event.from_party_name} → {event.to_party_name}</td>
                    <td>{event.from_party_name} → {event.to_party_name}</td>
                    <td>{formatQuantity(event.quantity)} {event.unit}</td>
                    <td>{event.transfer_location}</td>
                    <td><StatusBadge value={event.status} /></td>
                    <td>{formatDate(event.transfer_date)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </PageContent>
  )
}
