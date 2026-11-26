import {
  ArrowLeft,
  ArrowRight,
  Boxes,
  Check,
  ClipboardCheck,
  PackageCheck,
  Search,
  Truck,
  X,
} from 'lucide-react'
import { useState, type FormEvent, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { collectorApi } from '../api/collector'
import { getApiErrorMessage } from '../api/client'
import { participantsApi } from '../api/participants'
import type { TransferEvent } from '../api/types'
import { Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, StatCard, StatusBadge } from '../components/UI'
import { useToast } from '../components/ToastProvider'

function PageContent({ children }: { children: ReactNode }) {
  return <div className="page-content">{children}</div>
}

function TransferRows({
  events,
  onReview,
}: {
  events: TransferEvent[]
  onReview?: (event: TransferEvent) => void
}) {
  if (!events.length) return <EmptyState title="No transfers to show" message="Transfer activity will appear here when recorded by the backend." />
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr><th>Batch</th><th>From</th><th>To</th><th>Quantity</th><th>Location</th><th>Status</th>{onReview && <th>Action</th>}</tr>
        </thead>
        <tbody>
          {events.map((event) => (
            <tr key={event.event_id}>
              <td><span className="table-primary">{event.herb_name}</span><span className="table-secondary">{event.batch_identifier}</span></td>
              <td>{event.from_party_name}</td>
              <td>{event.to_party_name}</td>
              <td>{formatQuantity(event.quantity)} {event.unit}</td>
              <td>{event.transfer_location || '—'}</td>
              <td><StatusBadge value={event.status} /></td>
              {onReview && <td><Button onClick={() => onReview(event)} variant="secondary">Review <ArrowRight size={12} /></Button></td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function CollectorDashboardPage() {
  const navigate = useNavigate()
  const dashboard = useQuery({ queryKey: ['collector', 'dashboard'], queryFn: collectorApi.dashboard })
  const incoming = useQuery({ queryKey: ['collector', 'incoming'], queryFn: collectorApi.pendingTransfers })
  const available = useQuery({ queryKey: ['collector', 'available'], queryFn: collectorApi.availableBatches })
  const history = useQuery({ queryKey: ['collector', 'history'], queryFn: collectorApi.history })
  const retry = () => {
    void dashboard.refetch()
    void incoming.refetch()
    void available.refetch()
    void history.refetch()
  }
  const error = dashboard.error ?? incoming.error ?? available.error ?? history.error
  if (dashboard.isLoading || incoming.isLoading || available.isLoading || history.isLoading) {
    return <PageContent><LoadingState /></PageContent>
  }
  if (error) return <PageContent><ErrorState message={getApiErrorMessage(error)} onRetry={retry} /></PageContent>

  const counts = dashboard.data
  const availableBatches = available.data?.results ?? []
  return (
    <PageContent>
      <PageHeader
        description="Review incoming custody requests and prepare approved batches for the next handover."
        eyebrow="Collector workspace"
        title="Collector dashboard"
        actions={<Link className="button button-primary" to="/collector/factory-transfers"><Truck size={15} /> Transfer to factory</Link>}
      />
      <div className="stat-grid">
        <StatCard icon={<Boxes size={16} />} label="Available batches" value={availableBatches.length} />
        <StatCard icon={<ClipboardCheck size={16} />} label="Incoming requests" value={counts?.pending_transfers ?? 0} />
        <StatCard icon={<PackageCheck size={16} />} label="Accepted receipts" value={counts?.accepted_transfers ?? 0} />
        <StatCard icon={<Truck size={16} />} label="Transfer events" value={history.data?.count ?? 0} />
      </div>
      <div style={{ display: 'grid', gap: 17 }}>
        <Card
          title="Pending incoming transfers"
          subtitle="Accept or reject only after checking the batch and sender details."
          actions={<Link className="inline-link" to="/collector/incoming">View requests <ArrowRight size={12} /></Link>}
        >
          <TransferRows
            events={(incoming.data?.results ?? []).slice(0, 5)}
            onReview={(event) => navigate(`/collector/incoming/${event.event_id}`)}
          />
        </Card>
        <Card
          title="Available inventory"
          subtitle="Batches currently owned by your Collector account"
          actions={<Link className="inline-link" to="/collector/batches">View inventory</Link>}
        >
          {availableBatches.length === 0 ? (
            <EmptyState title="No available batches" message="Inventory appears after you accept an incoming transfer." />
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead><tr><th>Batch</th><th>Origin</th><th>Available quantity</th><th>Status</th></tr></thead>
                <tbody>
                  {availableBatches.slice(0, 5).map((batch) => (
                    <tr key={batch.batch_id}>
                      <td><span className="table-primary">{batch.herb_name}</span><span className="table-secondary">{batch.batch_id}</span></td>
                      <td>{[batch.village, batch.district].filter(Boolean).join(', ') || '—'}</td>
                      <td>{formatQuantity(batch.available_quantity)} {batch.unit}</td>
                      <td><StatusBadge value={batch.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </PageContent>
  )
}

export function CollectorIncomingPage() {
  const navigate = useNavigate()
  const query = useQuery({ queryKey: ['collector', 'incoming'], queryFn: collectorApi.pendingTransfers })
  if (query.isLoading) return <PageContent><LoadingState /></PageContent>
  if (query.error) return <PageContent><ErrorState message={getApiErrorMessage(query.error)} onRetry={() => void query.refetch()} /></PageContent>
  return (
    <PageContent>
      <PageHeader eyebrow="Custody requests" title="Incoming transfers" description="Review sender, batch provenance, laboratory status, and dispatch notes before accepting." />
      <Card title="Pending transfer requests" subtitle={`${query.data?.count ?? 0} requests`}>
        <TransferRows events={query.data?.results ?? []} onReview={(event) => navigate(`/collector/incoming/${event.event_id}`)} />
      </Card>
    </PageContent>
  )
}

export function CollectorIncomingDetailPage() {
  const { eventId = '' } = useParams()
  const navigate = useNavigate()
  const { notify } = useToast()
  const queryClient = useQueryClient()
  const [remarks, setRemarks] = useState('')
  const [message, setMessage] = useState('')
  const pending = useQuery({ queryKey: ['collector', 'incoming'], queryFn: collectorApi.pendingTransfers })
  const event = pending.data?.results.find((item) => item.event_id === eventId)
  const action = useMutation({
    mutationFn: async (accepted: boolean) => {
      if (accepted) return collectorApi.accept(eventId, remarks)
      return collectorApi.reject(eventId, remarks)
    },
    onSuccess: async (_result, accepted) => {
      await queryClient.invalidateQueries({ queryKey: ['collector'] })
      notify(accepted ? 'Transfer accepted and custody updated.' : 'Transfer request rejected.')
      navigate('/collector/incoming', { replace: true })
    },
    onError: (error) => setMessage(getApiErrorMessage(error)),
  })

  if (pending.isLoading) return <PageContent><LoadingState /></PageContent>
  if (pending.error) return <PageContent><ErrorState message={getApiErrorMessage(pending.error)} onRetry={() => void pending.refetch()} /></PageContent>
  if (!event) return (
    <PageContent>
      <PageHeader eyebrow="Custody request" title="Transfer not found" actions={<Link className="button button-secondary" to="/collector/incoming"><ArrowLeft size={14} /> Incoming requests</Link>} />
      <EmptyState title="This request is no longer pending" message="It may have already been accepted, rejected, or removed from your pending list." />
    </PageContent>
  )

  return (
    <PageContent>
      <PageHeader
        eyebrow="Incoming transfer details"
        title={event.herb_name}
        description={`${event.batch_identifier} · ${formatQuantity(event.quantity)} ${event.unit}`}
        actions={<Link className="button button-secondary" to="/collector/incoming"><ArrowLeft size={14} /> Back to requests</Link>}
      />
      <div className="content-grid">
        <Card title="Batch and sender" subtitle="Review the transfer details before taking action">
          <div className="card-body key-value-list">
            <KeyValue label="Sender" value={event.from_party_name} />
            <KeyValue label="Sender" value={event.from_party_name} />
            <KeyValue label="Batch identifier" value={event.batch_identifier} />
            <KeyValue label="Botanical name" value={event.botanical_name} />
            <KeyValue label="Quantity" value={`${formatQuantity(event.quantity)} ${event.unit}`} />
            <KeyValue label="Transfer location" value={event.transfer_location} />
            <KeyValue label="Transfer date" value={event.transfer_date} />
            <KeyValue label="Status" value={event.status.replaceAll('_', ' ')} />
            <KeyValue label="Transfer notes" value={event.remarks || 'No notes provided'} />
          </div>
        </Card>
        <Card title="Review decision" subtitle="A rejection reason is added to the transfer record.">
          <div className="card-body">
            <div className="field">
              <label htmlFor="transfer-review-notes">Review notes / rejection reason</label>
              <textarea id="transfer-review-notes" onChange={(input) => setRemarks(input.target.value)} placeholder="Add a note for the custody record…" value={remarks} />
            </div>
            {message && <div style={{ marginTop: 12 }}><ErrorState message={message} /></div>}
            <div className="form-actions" style={{ justifyContent: 'space-between' }}>
              <Button disabled={action.isPending} onClick={() => action.mutate(false)} variant="danger"><X size={14} /> Reject</Button>
              <Button disabled={action.isPending} onClick={() => action.mutate(true)}>
                {action.isPending ? 'Saving…' : 'Accept transfer'} <Check size={14} />
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </PageContent>
  )
}

export function CollectorBatchesPage() {
  const query = useQuery({ queryKey: ['collector', 'available'], queryFn: collectorApi.availableBatches })
  if (query.isLoading) return <PageContent><LoadingState /></PageContent>
  if (query.error) return <PageContent><ErrorState message={getApiErrorMessage(query.error)} onRetry={() => void query.refetch()} /></PageContent>
  const batches = query.data?.results ?? []
  return (
    <PageContent>
      <PageHeader eyebrow="Owned inventory" title="Available batches" description="Only batches currently owned by your Collector account are listed." />
      <Card title="Available inventory" subtitle={`${query.data?.count ?? 0} batches`}>
        {batches.length === 0 ? <EmptyState title="No inventory available" message="Accept an incoming transfer to add a batch to your inventory." /> : (
          <div className="table-wrap">
            <table className="data-table">
              <thead><tr><th>Batch</th><th>Botanical name</th><th>Origin</th><th>Available</th><th>Status</th></tr></thead>
              <tbody>
                {batches.map((batch) => (
                  <tr key={batch.batch_id}>
                    <td><span className="table-primary">{batch.herb_name}</span><span className="table-secondary">{batch.batch_id}</span></td>
                    <td>{batch.botanical_name}</td>
                    <td>{[batch.village, batch.district, batch.state].filter(Boolean).join(', ')}</td>
                    <td>{formatQuantity(batch.available_quantity)} {batch.unit}</td>
                    <td><StatusBadge value={batch.status} /></td>
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

export function CollectorFactoryTransferPage() {
  const { notify } = useToast()
  const queryClient = useQueryClient()
  const [batchId, setBatchId] = useState('')
  const [factoryId, setFactoryId] = useState('')
  const [location, setLocation] = useState('')
  const [remarks, setRemarks] = useState('')
  const [search, setSearch] = useState('')
  const [message, setMessage] = useState('')
  const batches = useQuery({ queryKey: ['collector', 'available'], queryFn: collectorApi.availableBatches })
  const factories = useQuery({
    queryKey: ['participants', 'FACTORY', search],
    queryFn: () => participantsApi.list('FACTORY', search),
  })
  const history = useQuery({ queryKey: ['collector', 'history'], queryFn: collectorApi.history })
  const selectedBatch = batches.data?.results.find((batch) => batch.batch_id === batchId)
  const mutation = useMutation({
    mutationFn: () => {
      if (!selectedBatch) throw new Error('Choose a batch from your current inventory.')
      if (!factoryId) throw new Error('Choose a verified Factory.')
      if (!location.trim()) throw new Error('Enter a transfer location.')
      return collectorApi.initiate({
        batch_id: selectedBatch.batch_id,
        to_party: Number(factoryId),
        quantity: selectedBatch.available_quantity,
        transfer_location: location.trim(),
        remarks,
      })
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['collector'] })
      setBatchId('')
      setFactoryId('')
      setLocation('')
      setRemarks('')
      setMessage('')
      notify('Factory transfer initiated. The Factory must acknowledge receipt.')
    },
    onError: (error) => setMessage(getApiErrorMessage(error)),
  })

  if (batches.isLoading || factories.isLoading || history.isLoading) return <PageContent><LoadingState /></PageContent>
  const error = batches.error ?? factories.error ?? history.error
  if (error) return <PageContent><ErrorState message={getApiErrorMessage(error)} onRetry={() => {
    void batches.refetch()
    void factories.refetch()
    void history.refetch()
  }} /></PageContent>

  return (
    <PageContent>
      <PageHeader eyebrow="Factory dispatch" title="Transfer to factory" description="Select a batch and an approved Factory. The full available quantity moves after acceptance." />
      <div className="content-grid">
        <Card title="Initiate a transfer" subtitle="Custody changes only after the recipient accepts the request.">
          <div className="card-body">
            <form className="auth-form" onSubmit={(event: FormEvent) => {
              event.preventDefault()
              mutation.mutate()
            }}>
              <div className="field">
                <label htmlFor="collector-batch-select">Available batch</label>
                <select id="collector-batch-select" onChange={(event) => setBatchId(event.target.value)} required value={batchId}>
                  <option value="">Select an owned batch</option>
                  {(batches.data?.results ?? []).map((batch) => (
                    <option key={batch.batch_id} value={batch.batch_id}>
                      {batch.batch_id} · {batch.herb_name} · {formatQuantity(batch.available_quantity)} {batch.unit}
                    </option>
                  ))}
                </select>
                {batches.data?.results.length === 0 && <span className="field-hint">No eligible inventory is available.</span>}
              </div>
              {selectedBatch && (
                <div className="alert">
                  <Boxes size={15} />Full batch: {formatQuantity(selectedBatch.available_quantity)} {selectedBatch.unit}
                </div>
              )}
              <div className="field">
                <label htmlFor="factory-directory-search">Search verified factories</label>
                <label className="search-control">
                  <Search size={14} />
                  <input id="factory-directory-search" onChange={(event) => setSearch(event.target.value)} placeholder="Factory or contact name" value={search} />
                </label>
              </div>
              <div className="field">
                <label htmlFor="factory-select">Factory recipient</label>
                <select id="factory-select" onChange={(event) => setFactoryId(event.target.value)} required value={factoryId}>
                  <option value="">Choose an approved Factory</option>
                  {(factories.data?.results ?? []).map((factory) => (
                    <option key={factory.user_id} value={factory.id}>
                      {factory.profile_name}{factory.profile_registration_number ? ` · ${factory.profile_registration_number}` : ''}
                    </option>
                  ))}
                </select>
                {factories.data?.results.length === 0 && <span className="field-hint">No verified Factory accounts matched.</span>}
              </div>
              <div className="field">
                <label htmlFor="factory-transfer-location">Transfer location</label>
                <input id="factory-transfer-location" onChange={(event) => setLocation(event.target.value)} required value={location} />
              </div>
              <div className="field">
                <label htmlFor="factory-transfer-notes">Dispatch details</label>
                <textarea id="factory-transfer-notes" onChange={(event) => setRemarks(event.target.value)} value={remarks} />
              </div>
              {message && <ErrorState message={message} />}
              <Button className="button-full" disabled={mutation.isPending || !batches.data?.results.length || !factories.data?.results.length} type="submit">
                {mutation.isPending ? 'Initiating…' : 'Initiate factory transfer'} <ArrowRight size={14} />
              </Button>
            </form>
          </div>
        </Card>
        <Card title="Transfer status & history" subtitle="Transfer events returned by your account">
          <TransferRows events={history.data?.results ?? []} />
        </Card>
      </div>
    </PageContent>
  )
}

function KeyValue({ label, value }: { label: string; value: string }) {
  return <div className="key-value-row"><span>{label}</span><strong>{value || '—'}</strong></div>
}

function formatQuantity(value: string) {
  const number = Number(value)
  return Number.isFinite(number) ? new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 }).format(number) : value
}
