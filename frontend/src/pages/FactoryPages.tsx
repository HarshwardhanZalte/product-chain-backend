import { zodResolver } from '@hookform/resolvers/zod'
import {
  ArrowDownToLine,
  ArrowRight,
  Boxes,
  Check,
  ClipboardCheck,
  Copy,
  Factory,
  Package,
  PackageCheck,
  Plus,
  Printer,
  QrCode,
  Search,
  Truck,
} from 'lucide-react'
import { useEffect, useMemo, useState, type InputHTMLAttributes, type ReactNode } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router-dom'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { factoryApi, type ManufacturingInput } from '../api/factory'
import { getApiErrorMessage } from '../api/client'
import { downloadBlob, productApi } from '../api/products'
import type { HerbBatch, ManufacturingRecord, Product, TransferEvent } from '../api/types'
import { Button, Card, EmptyState, ErrorState, FieldError, LoadingState, Modal, PageHeader, StatCard, StatusBadge } from '../components/UI'
import { useToast } from '../components/ToastProvider'

function PageContent({ children }: { children: ReactNode }) {
  return <div className="page-content">{children}</div>
}

function IncomingTransferTable({
  events,
  onReceive,
  workingId,
}: {
  events: TransferEvent[]
  onReceive: (event: TransferEvent) => void
  workingId?: string
}) {
  if (!events.length) return <EmptyState title="No incoming batches" message="A batch appears here after a Collector initiates a transfer to your account." />
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead><tr><th>Batch & origin</th><th>Collector</th><th>Quantity</th><th>Transfer location</th><th>Status</th><th>Action</th></tr></thead>
        <tbody>
          {events.map((event) => (
            <tr key={event.event_id}>
              <td><span className="table-primary">{event.herb_name}</span><span className="table-secondary">{event.batch_identifier}</span></td>
              <td>{event.from_party_name}</td>
              <td>{formatQuantity(event.quantity)} {event.unit}</td>
              <td>{event.transfer_location || '—'}</td>
              <td><StatusBadge value={event.status} /></td>
              <td>
                <Button disabled={workingId === event.event_id} onClick={() => onReceive(event)}>
                  {workingId === event.event_id ? 'Receiving…' : 'Receive batch'} <Check size={12} />
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function FactoryDashboardPage() {
  const { notify } = useToast()
  const queryClient = useQueryClient()
  const dashboard = useQuery({ queryKey: ['factory', 'dashboard'], queryFn: factoryApi.dashboard })
  const incoming = useQuery({ queryKey: ['factory', 'incoming'], queryFn: factoryApi.pendingTransfers })
  const inventory = useQuery({ queryKey: ['factory', 'inventory'], queryFn: factoryApi.availableBatches })
  const records = useQuery({ queryKey: ['factory', 'manufacturing'], queryFn: factoryApi.manufacturingRecords })
  const products = useQuery({ queryKey: ['factory', 'products'], queryFn: factoryApi.products })
  const queryList = [dashboard, incoming, inventory, records, products]
  const receiveMutation = useMutation({
    mutationFn: (eventId: string) => factoryApi.receiveTransfer(eventId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['factory'] })
      await queryClient.invalidateQueries({ queryKey: ['collector'] })
      notify('Batch received. Custody has been updated.')
    },
    onError: (error) => notify(getApiErrorMessage(error), 'error'),
  })
  const error = queryList.find((query) => query.error)?.error
  const retry = () => queryList.forEach((query) => void query.refetch())
  if (queryList.some((query) => query.isLoading)) return <PageContent><LoadingState /></PageContent>
  if (error) return <PageContent><ErrorState message={getApiErrorMessage(error)} onRetry={retry} /></PageContent>

  return (
    <PageContent>
      <PageHeader eyebrow="Factory workspace" title="Factory operations" description="Receive approved herb batches, manage manufacturing runs, and serialize finished products." />
      <div className="stat-grid">
        <StatCard icon={<Truck size={16} />} label="Incoming transfers" value={incoming.data?.count ?? 0} />
        <StatCard icon={<Boxes size={16} />} label="Available input batches" value={inventory.data?.count ?? 0} />
        <StatCard icon={<Factory size={16} />} label="Manufacturing records" value={dashboard.data?.manufacturing_records ?? 0} />
        <StatCard icon={<PackageCheck size={16} />} label="Products" value={products.data?.count ?? 0} />
      </div>
      <div style={{ display: 'grid', gap: 17 }}>
        <Card title="Pending incoming batches" subtitle="Receive only transfers addressed to your Factory account." actions={<Link className="inline-link" to="/factory/incoming">View incoming <ArrowRight size={12} /></Link>}>
          <IncomingTransferTable
            events={(incoming.data?.results ?? []).slice(0, 5)}
            onReceive={(event) => receiveMutation.mutate(event.event_id)}
            workingId={receiveMutation.isPending ? receiveMutation.variables : undefined}
          />
        </Card>
        <Card title="Recent manufacturing activity" subtitle="Records created by your Factory">
          <ManufacturingTable records={(records.data?.results ?? []).slice(0, 5)} />
        </Card>
      </div>
    </PageContent>
  )
}

export function FactoryIncomingPage() {
  const { notify } = useToast()
  const queryClient = useQueryClient()
  const incoming = useQuery({ queryKey: ['factory', 'incoming'], queryFn: factoryApi.pendingTransfers })
  const mutation = useMutation({
    mutationFn: (eventId: string) => factoryApi.receiveTransfer(eventId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['factory'] })
      await queryClient.invalidateQueries({ queryKey: ['collector'] })
      notify('Batch received. Custody has been updated.')
    },
  })
  if (incoming.isLoading) return <PageContent><LoadingState /></PageContent>
  if (incoming.error) return <PageContent><ErrorState message={getApiErrorMessage(incoming.error)} onRetry={() => void incoming.refetch()} /></PageContent>
  return (
    <PageContent>
      <PageHeader eyebrow="Raw material intake" title="Incoming batches" description="Review the transfer details and acknowledge receipt to update custody." />
      {mutation.error && <div style={{ marginBottom: 15 }}><ErrorState message={getApiErrorMessage(mutation.error)} /></div>}
      <Card title="Pending receiving queue" subtitle={`${incoming.data?.count ?? 0} transfers`}>
        <IncomingTransferTable
          events={incoming.data?.results ?? []}
          onReceive={(event) => mutation.mutate(event.event_id)}
          workingId={mutation.isPending ? mutation.variables : undefined}
        />
      </Card>
    </PageContent>
  )
}

export function FactoryInventoryPage() {
  const query = useQuery({ queryKey: ['factory', 'inventory'], queryFn: factoryApi.availableBatches })
  if (query.isLoading) return <PageContent><LoadingState /></PageContent>
  if (query.error) return <PageContent><ErrorState message={getApiErrorMessage(query.error)} onRetry={() => void query.refetch()} /></PageContent>
  const batches = query.data?.results ?? []
  return (
    <PageContent>
      <PageHeader eyebrow="Input inventory" title="Available herb batches" description="Inventory currently owned by this Factory and eligible for manufacturing." />
      <Card title="Available raw material" subtitle={`${query.data?.count ?? 0} batches`}>
        {batches.length === 0 ? <EmptyState title="No available inputs" message="Received, approved batches with remaining quantity will appear here." /> : (
          <BatchTable batches={batches} />
        )}
      </Card>
    </PageContent>
  )
}

const manufacturingSchema = z.object({
  product_name: z.string().min(2, 'Enter the planned product name.'),
  process_date: z.string().min(1, 'Choose the process date.'),
  process_description: z.string().min(2, 'Describe the process.'),
  output_quantity: z.string().refine((value) => Number(value) > 0, 'Output quantity must be greater than zero.'),
  remarks: z.string(),
  facility_line: z.string(),
  shift: z.string(),
  standard_operating_procedure: z.string(),
  solvent_method: z.string(),
  target_yield_ratio: z.string(),
  process_parameters: z.string(),
  quality_control_lead: z.string(),
})
type ManufacturingFormValues = z.infer<typeof manufacturingSchema>

const manufacturingDefaults: ManufacturingFormValues = {
  product_name: '',
  process_date: new Date().toISOString().slice(0, 10),
  process_description: '',
  output_quantity: '',
  remarks: '',
  facility_line: '',
  shift: '',
  standard_operating_procedure: '',
  solvent_method: '',
  target_yield_ratio: '',
  process_parameters: '',
  quality_control_lead: '',
}

export function FactoryManufacturingPage() {
  const { notify } = useToast()
  const queryClient = useQueryClient()
  const batchesQuery = useQuery({ queryKey: ['factory', 'inventory'], queryFn: factoryApi.availableBatches })
  const recordsQuery = useQuery({ queryKey: ['factory', 'manufacturing'], queryFn: factoryApi.manufacturingRecords })
  const [selected, setSelected] = useState<Record<string, string>>({})
  const [message, setMessage] = useState('')
  const form = useForm<ManufacturingFormValues>({
    resolver: zodResolver(manufacturingSchema),
    defaultValues: manufacturingDefaults,
  })
  const records = recordsQuery.data?.results ?? []
  const batches = batchesQuery.data?.results ?? []
  const selectedBatches = batches.filter((batch) => selected[batch.batch_id])
  const units = [...new Set(selectedBatches.map((batch) => batch.unit))]
  const inputMismatch = units.length > 1
  const create = useMutation({
    mutationFn: async ({ values, draft }: { values: ManufacturingFormValues; draft: boolean }) => {
      if (selectedBatches.length === 0) throw new Error('Select at least one approved input batch.')
      if (inputMismatch) throw new Error('Selected batches must use the same unit.')
      let parameters: Record<string, unknown> = {}
      if (values.process_parameters.trim()) {
        const parsed: unknown = JSON.parse(values.process_parameters)
        if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
          throw new Error('Process parameters must be a JSON object.')
        }
        parameters = parsed as Record<string, unknown>
      }
      const input: ManufacturingInput = {
        product_name: values.product_name,
        process_date: values.process_date,
        process_description: values.process_description,
        output_quantity: values.output_quantity,
        unit: units[0],
        remarks: values.remarks,
        facility_line: values.facility_line,
        shift: values.shift,
        standard_operating_procedure: values.standard_operating_procedure,
        solvent_method: values.solvent_method,
        target_yield_ratio: values.target_yield_ratio,
        process_parameters: parameters,
        quality_control_lead: values.quality_control_lead,
        save_as_draft: draft,
        input_batches: selectedBatches.map((batch) => ({
          batch_id: batch.batch_id,
          quantity_used: selected[batch.batch_id],
        })),
      }
      return factoryApi.createManufacturing(input)
    },
    onSuccess: async (record, variables) => {
      await queryClient.invalidateQueries({ queryKey: ['factory'] })
      setSelected({})
      form.reset(manufacturingDefaults)
      setMessage('')
      notify(variables.draft ? 'Manufacturing draft saved. Stock is not reserved.' : `Manufacturing record ${record.manufacturing_id} completed.`)
    },
    onError: (error) => setMessage(getApiErrorMessage(error)),
  })
  const lifecycle = useMutation({
    mutationFn: ({ id, complete }: { id: string; complete: boolean }) => (
      complete ? factoryApi.completeManufacturing(id) : factoryApi.cancelManufacturing(id)
    ),
    onSuccess: async (_record, variables) => {
      await queryClient.invalidateQueries({ queryKey: ['factory'] })
      notify(variables.complete ? 'Draft completed and input inventory consumed.' : 'Manufacturing draft cancelled.')
    },
    onError: (error) => setMessage(getApiErrorMessage(error)),
  })

  if (batchesQuery.isLoading || recordsQuery.isLoading) return <PageContent><LoadingState /></PageContent>
  const error = batchesQuery.error ?? recordsQuery.error
  if (error) return <PageContent><ErrorState message={getApiErrorMessage(error)} onRetry={() => {
    void batchesQuery.refetch()
    void recordsQuery.refetch()
  }} /></PageContent>

  return (
    <PageContent>
      <PageHeader eyebrow="Production records" title="Manufacturing" description="Select received, lab-approved inputs and record a planned draft or complete production run." />
      <div style={{ display: 'grid', gap: 17 }}>
        <Card title="Create manufacturing record" subtitle="Drafts do not reserve inventory; completing a run rechecks and consumes the selected input quantities.">
          <div className="card-body">
            {message && <div style={{ marginBottom: 14 }}><ErrorState message={message} /></div>}
            <form onSubmit={form.handleSubmit((values) => create.mutate({ values, draft: false }))}>
              <div className="form-grid">
                <FormInput form={form} name="product_name" label="Product / formulation name" />
                <FormInput form={form} name="process_date" label="Manufacturing date" type="date" />
                <FormInput form={form} name="facility_line" label="Facility line" />
                <FormInput form={form} name="shift" label="Shift" />
                <FormInput form={form} name="standard_operating_procedure" label="SOP reference" />
                <FormInput form={form} name="solvent_method" label="Solvent / method" />
                <FormInput form={form} name="target_yield_ratio" label="Target yield ratio" />
                <FormInput form={form} name="quality_control_lead" label="Quality-control lead" />
                <div className="field span-2">
                  <label htmlFor="manufacturing-description">Process description</label>
                  <textarea id="manufacturing-description" {...form.register('process_description')} />
                  <FieldError>{form.formState.errors.process_description?.message}</FieldError>
                </div>
                <FormInput form={form} name="output_quantity" label={`Output quantity${units[0] ? ` (${units[0]})` : ''}`} type="number" step="0.001" min="0.001" />
                <div className="field">
                  <label htmlFor="manufacturing-parameters">Process parameters (JSON object, optional)</label>
                  <textarea id="manufacturing-parameters" placeholder='{"temperature_c": 0}' {...form.register('process_parameters')} />
                  <FieldError>{form.formState.errors.process_parameters?.message}</FieldError>
                  <span className="field-hint">Enter real measured process values only. Leave blank when none are recorded.</span>
                </div>
                <div className="field span-2">
                  <label htmlFor="manufacturing-remarks">Remarks</label>
                  <textarea id="manufacturing-remarks" {...form.register('remarks')} />
                </div>
              </div>
              <div style={{ margin: '18px 0 10px' }}>
                <strong style={{ color: 'var(--forest)', fontSize: 12 }}>Select input batches</strong>
                <p className="field-hint" style={{ marginTop: 4 }}>Choose the actual quantities used. The batch units must match.</p>
              </div>
              {inputMismatch && <div className="alert alert-error" style={{ marginBottom: 12 }}>Selected batches have different units. Select inputs with matching units to continue.</div>}
              <InputBatchSelector batches={batches} selected={selected} setSelected={setSelected} />
              <div className="form-actions">
                <Button
                  disabled={create.isPending || selectedBatches.length === 0 || inputMismatch}
                  onClick={form.handleSubmit((values) => create.mutate({ values, draft: true }))}
                  variant="secondary"
                >
                  Save draft
                </Button>
                <Button disabled={create.isPending || selectedBatches.length === 0 || inputMismatch} type="submit">
                  {create.isPending ? 'Saving…' : 'Complete manufacturing'} <Check size={14} />
                </Button>
              </div>
            </form>
          </div>
        </Card>
        <Card title="Manufacturing records" subtitle={`${recordsQuery.data?.count ?? 0} records`}>
          <ManufacturingTable
            records={records}
            onAction={(record, complete) => lifecycle.mutate({ id: record.manufacturing_id, complete })}
            working={lifecycle.isPending ? lifecycle.variables?.id : undefined}
          />
        </Card>
      </div>
    </PageContent>
  )
}

function InputBatchSelector({
  batches,
  selected,
  setSelected,
}: {
  batches: HerbBatch[]
  selected: Record<string, string>
  setSelected: (value: Record<string, string>) => void
}) {
  if (!batches.length) return <EmptyState title="No eligible input batches" message="Receive a transfer and ensure the batch has approved laboratory results before manufacturing." />
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead><tr><th>Select</th><th>Batch / herb</th><th>Available quantity</th><th>Quantity used</th></tr></thead>
        <tbody>
          {batches.map((batch) => {
            const checked = Boolean(selected[batch.batch_id])
            return (
              <tr key={batch.batch_id}>
                <td><input aria-label={`Select ${batch.batch_id}`} checked={checked} onChange={(event) => {
                  const next = { ...selected }
                  if (event.target.checked) next[batch.batch_id] = batch.available_quantity
                  else delete next[batch.batch_id]
                  setSelected(next)
                }} type="checkbox" /></td>
                <td><span className="table-primary">{batch.herb_name}</span><span className="table-secondary">{batch.batch_id} · <StatusBadge value={batch.status} /></span></td>
                <td>{formatQuantity(batch.available_quantity)} {batch.unit}</td>
                <td>
                  {checked ? (
                    <input
                      aria-label={`Quantity used from ${batch.batch_id}`}
                      className="form-control"
                      max={batch.available_quantity}
                      min="0.001"
                      onChange={(event) => setSelected({ ...selected, [batch.batch_id]: event.target.value })}
                      step="0.001"
                      type="number"
                      value={selected[batch.batch_id]}
                    />
                  ) : '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function ManufacturingTable({
  records,
  onAction,
  working,
}: {
  records: ManufacturingRecord[]
  onAction?: (record: ManufacturingRecord, complete: boolean) => void
  working?: string
}) {
  if (!records.length) return <EmptyState title="No manufacturing records" message="Create a manufacturing record after receiving eligible raw-material batches." />
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead><tr><th>Product / run</th><th>Inputs</th><th>Output</th><th>Process date</th><th>Status</th>{onAction && <th>Actions</th>}</tr></thead>
        <tbody>
          {records.map((record) => (
            <tr key={record.manufacturing_id}>
              <td><span className="table-primary">{record.product_name}</span><span className="table-secondary">{record.manufacturing_id}</span></td>
              <td>{record.input_batches.length} batches<span className="table-secondary">{record.input_batches.map((item) => item.batch_id).join(', ')}</span></td>
              <td>{formatQuantity(record.output_quantity)} {record.unit}</td>
              <td>{formatDate(record.process_date)}</td>
              <td><StatusBadge value={record.status} /></td>
              {onAction && <td>
                {record.status === 'PLANNED' ? (
                  <div className="toolbar">
                    <Button disabled={working === record.manufacturing_id} onClick={() => onAction(record, true)}>
                      Complete
                    </Button>
                    <Button disabled={working === record.manufacturing_id} onClick={() => onAction(record, false)} variant="danger">
                      Cancel
                    </Button>
                  </div>
                ) : <span className="field-hint">—</span>}
              </td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function FormInput({
  form,
  name,
  label,
  ...props
}: {
  form: ReturnType<typeof useForm<ManufacturingFormValues>>
  name: keyof ManufacturingFormValues
  label: string
} & Omit<InputHTMLAttributes<HTMLInputElement>, 'name' | 'form'>) {
  const id = `manufacturing-${String(name)}`
  const error = form.formState.errors[name]
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input id={id} {...props} {...form.register(name)} />
      <FieldError>{error?.message}</FieldError>
    </div>
  )
}

const productSchema = z.object({
  manufacturing_id: z.string().min(1, 'Select a completed manufacturing record.'),
  product_name: z.string().min(2, 'Enter the retail product name.'),
  description: z.string(),
  product_type: z.string().min(1, 'Enter a product type.'),
  manufacture_date: z.string().min(1, 'Choose the manufacturing date.'),
  expiry_date: z.string(),
  batch_number: z.string().min(1, 'Enter the retail batch number.'),
  total_quantity: z.string().refine((value) => Number(value) > 0, 'Quantity must be greater than zero.'),
  product_image: z.custom<FileList>().optional(),
})
type ProductFormValues = z.infer<typeof productSchema>

export function FactoryProductsPage() {
  const { notify } = useToast()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [message, setMessage] = useState('')
  const [printing, setPrinting] = useState(false)
  const productQuery = useQuery({ queryKey: ['factory', 'products'], queryFn: factoryApi.products })
  const manufacturingQuery = useQuery({ queryKey: ['factory', 'manufacturing'], queryFn: factoryApi.manufacturingRecords })
  const form = useForm<ProductFormValues>({
    resolver: zodResolver(productSchema),
    defaultValues: { manufacturing_id: '', product_name: '', description: '', product_type: '', manufacture_date: new Date().toISOString().slice(0, 10), expiry_date: '', batch_number: '', total_quantity: '' },
  })
  const completedRecords = (manufacturingQuery.data?.results ?? []).filter((record) => record.status === 'COMPLETED')
  const selectedRecord = completedRecords.find((record) => record.manufacturing_id === form.watch('manufacturing_id'))
  const products = useMemo(() => (productQuery.data?.results ?? []).filter((product) => (
    `${product.product_name} ${product.batch_number} ${product.qr_reference}`.toLowerCase().includes(search.toLowerCase())
  )), [productQuery.data?.results, search])

  const create = useMutation({
    mutationFn: (values: ProductFormValues) => {
      if (!selectedRecord) throw new Error('Select a completed manufacturing record.')
      return factoryApi.createProduct({
        manufacturing_id: values.manufacturing_id,
        product_name: values.product_name,
        description: values.description,
        product_type: values.product_type,
        manufacture_date: values.manufacture_date,
        expiry_date: values.expiry_date,
        batch_number: values.batch_number,
        total_quantity: values.total_quantity,
        unit: selectedRecord.unit,
        product_image: values.product_image?.[0],
      })
    },
    onSuccess: async (product) => {
      await queryClient.invalidateQueries({ queryKey: ['factory', 'products'] })
      form.reset()
      setShowCreate(false)
      setSelectedProduct(product)
      notify('Product serialized and QR code generated.')
    },
    onError: (error) => setMessage(getApiErrorMessage(error)),
  })
  useEffect(() => {
    const resetPrintMode = () => setPrinting(false)
    window.addEventListener('afterprint', resetPrintMode)
    return () => window.removeEventListener('afterprint', resetPrintMode)
  }, [])

  if (productQuery.isLoading || manufacturingQuery.isLoading) return <PageContent><LoadingState /></PageContent>
  const error = productQuery.error ?? manufacturingQuery.error
  if (error) return <PageContent><ErrorState message={getApiErrorMessage(error)} onRetry={() => {
    void productQuery.refetch()
    void manufacturingQuery.refetch()
  }} /></PageContent>

  const printLabels = () => {
    setPrinting(true)
    window.setTimeout(() => window.print(), 100)
  }

  return (
    <PageContent>
      <PageHeader
        eyebrow="Finished catalog"
        title="Products & QR codes"
        description="Manage finished-product records, view generated QR codes, and share the public verification route."
        actions={
          <>
            <Button disabled={!products.some((product) => product.qr_code_image)} onClick={printLabels} variant="secondary"><Printer size={14} /> Print QR labels</Button>
            <Button onClick={() => setShowCreate((current) => !current)}><Plus size={14} /> Create new product</Button>
          </>
        }
      />
      <div className="stat-grid">
        <StatCard icon={<Package size={16} />} label="Serialized products" value={productQuery.data?.count ?? 0} />
        <StatCard icon={<QrCode size={16} />} label="Generated QR codes" value={(productQuery.data?.results ?? []).filter((product) => Boolean(product.qr_code_image)).length} />
        <StatCard icon={<Factory size={16} />} label="Completed runs" value={completedRecords.length} />
        <StatCard icon={<ClipboardCheck size={16} />} label="Source batches linked" value={(productQuery.data?.results ?? []).reduce((total, product) => total + product.source_batches.length, 0)} />
      </div>
      {showCreate && (
        <div style={{ marginBottom: 18 }}>
          <Card title="Create product record" subtitle="Product quantity must fit within the selected completed manufacturing output.">
            <div className="card-body">
              {message && <div style={{ marginBottom: 14 }}><ErrorState message={message} /></div>}
              {completedRecords.length === 0 ? (
                <EmptyState title="No completed manufacturing runs" message="Complete a manufacturing record before creating a product." />
              ) : (
                <form onSubmit={form.handleSubmit((values) => create.mutate(values))}>
                  <div className="form-grid">
                    <div className="field span-2">
                      <label htmlFor="product-manufacturing">Completed manufacturing record</label>
                      <select id="product-manufacturing" {...form.register('manufacturing_id')}>
                        <option value="">Select a completed run</option>
                        {completedRecords.map((record) => (
                          <option key={record.manufacturing_id} value={record.manufacturing_id}>
                            {record.product_name} · {record.manufacturing_id} · {formatQuantity(record.output_quantity)} {record.unit}
                          </option>
                        ))}
                      </select>
                      <FieldError>{form.formState.errors.manufacturing_id?.message}</FieldError>
                    </div>
                    <ProductInput form={form} name="product_name" label="Retail product name" />
                    <ProductInput form={form} name="product_type" label="Product type" />
                    <ProductInput form={form} name="batch_number" label="Retail batch number" />
                    <ProductInput form={form} name="total_quantity" label={`Total quantity${selectedRecord ? ` (${selectedRecord.unit})` : ''}`} type="number" min="0.001" step="0.001" />
                    <ProductInput form={form} name="manufacture_date" label="Manufacture date" type="date" />
                    <ProductInput form={form} name="expiry_date" label="Expiry date (optional)" type="date" />
                    <div className="field span-2">
                      <label htmlFor="product-description">Description</label>
                      <textarea id="product-description" {...form.register('description')} />
                    </div>
                    <div className="field span-2">
                      <label htmlFor="product-image">Product image (optional)</label>
                      <input accept="image/*" id="product-image" type="file" {...form.register('product_image')} />
                    </div>
                  </div>
                  {create.error && <div style={{ marginTop: 13 }}><ErrorState message={getApiErrorMessage(create.error)} /></div>}
                  <div className="form-actions">
                    <Button onClick={() => setShowCreate(false)} variant="secondary">Cancel</Button>
                    <Button disabled={create.isPending} type="submit">{create.isPending ? 'Creating…' : 'Create & generate QR'} <QrCode size={14} /></Button>
                  </div>
                </form>
              )}
            </div>
          </Card>
        </div>
      )}
      <Card
        title="Product catalog"
        subtitle={`${productQuery.data?.count ?? 0} records from your Factory`}
        actions={<label className="search-control"><Search size={14} /><input aria-label="Search products" onChange={(event) => setSearch(event.target.value)} placeholder="Search product, batch or QR reference…" value={search} /></label>}
      >
        {products.length === 0 ? <EmptyState title="No products found" message={search ? 'Try another search.' : 'Create a product from a completed manufacturing run.'} /> : (
          <div className="table-wrap">
            <table className="data-table">
              <thead><tr><th>Product & batch</th><th>Manufacturing run</th><th>Quantity</th><th>Manufactured</th><th>Status</th><th>QR</th><th>Action</th></tr></thead>
              <tbody>
                {products.map((product) => (
                  <tr key={product.product_id}>
                    <td><span className="table-primary">{product.product_name}</span><span className="table-secondary">{product.batch_number}</span></td>
                    <td>{product.manufacturing?.product_name || product.manufacturing_record}<span className="table-secondary">{product.manufacturing?.manufacturing_id}</span></td>
                    <td>{formatQuantity(product.total_quantity)} {product.unit}</td>
                    <td>{formatDate(product.manufacture_date)}</td>
                    <td><StatusBadge value={product.status} /></td>
                    <td>{product.qr_code_image ? <span className="status-badge status-approved">Generated</span> : <span className="status-badge status-neutral">Unavailable</span>}</td>
                    <td><Button onClick={() => setSelectedProduct(product)} variant="secondary">View QR <ArrowRight size={12} /></Button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      {selectedProduct && (
        <ProductQrModal
          onClose={() => setSelectedProduct(null)}
          onRegenerate={async () => {
            const refreshed = await factoryApi.regenerateQr(selectedProduct.product_id)
            await queryClient.invalidateQueries({ queryKey: ['factory', 'products'] })
            setSelectedProduct(refreshed)
            notify('Product QR code regenerated.')
          }}
          product={selectedProduct}
        />
      )}
      {printing && (
        <div className="print-sheet">
          {products.filter((product) => product.qr_code_image).map((product) => (
            <article className="print-label" key={product.product_id}>
              <img alt={`QR code for ${product.product_name}`} src={product.qr_code_image ?? ''} />
              <strong>{product.product_name}</strong>
              <span>{product.batch_number}</span>
              <span>{product.qr_reference}</span>
            </article>
          ))}
        </div>
      )}
    </PageContent>
  )
}

function ProductQrModal({
  product,
  onClose,
  onRegenerate,
}: {
  product: Product
  onClose: () => void
  onRegenerate: () => Promise<void>
}) {
  const { notify } = useToast()
  const [message, setMessage] = useState('')
  const [regenerating, setRegenerating] = useState(false)
  const verificationUrl = `${window.location.origin}/verify/${encodeURIComponent(product.qr_reference)}`
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(verificationUrl)
      notify('Verification URL copied.')
    } catch (error) {
      setMessage(getApiErrorMessage(error))
    }
  }
  const download = async () => {
    try {
      downloadBlob(await productApi.downloadAsset(product.product_id, 'qr'), `${product.batch_number}-qr.png`)
    } catch (error) {
      setMessage(getApiErrorMessage(error))
    }
  }
  const regenerate = async () => {
    setRegenerating(true)
    setMessage('')
    try {
      await onRegenerate()
    } catch (error) {
      setMessage(getApiErrorMessage(error))
    } finally {
      setRegenerating(false)
    }
  }
  return (
    <Modal description={product.product_name} onClose={onClose} title="Product QR code">
      <div style={{ display: 'grid', justifyItems: 'center', gap: 12 }}>
        {product.qr_code_image ? <img alt={`QR code for ${product.product_name}`} className="qr-preview" src={product.qr_code_image} /> : <EmptyState title="QR unavailable" message="The backend has not returned a QR image for this product." />}
        <StatusBadge value={product.status} />
      </div>
      <div className="divider" />
      <div className="key-value-list">
        <KeyValue label="Product" value={product.product_name} />
        <KeyValue label="Batch number" value={product.batch_number} />
        <KeyValue label="Manufacturing run" value={product.manufacturing?.manufacturing_id ?? product.manufacturing_record} />
        <KeyValue label="QR reference" value={product.qr_reference} />
      </div>
      <div className="field" style={{ marginTop: 16 }}>
        <label htmlFor="public-url">Public verification URL</label>
        <div className="toolbar">
          <input className="form-control" id="public-url" readOnly value={verificationUrl} />
          <Button onClick={() => void copy()} variant="secondary"><Copy size={14} /> Copy</Button>
        </div>
      </div>
      {message && <div style={{ marginTop: 12 }}><ErrorState message={message} /></div>}
      <div className="form-actions">
        <Button disabled={regenerating} onClick={() => void regenerate()} variant="secondary"><QrCode size={14} /> {regenerating ? 'Regenerating…' : 'Regenerate QR'}</Button>
        <Button disabled={!product.qr_code_image} onClick={() => void download()}><ArrowDownToLine size={14} /> Download PNG</Button>
      </div>
      <div className="field-hint" style={{ marginTop: 9 }}>
        Public verification displays the backend’s approved product and source-batch data. Certificate documents remain private.
      </div>
    </Modal>
  )
}

function ProductInput({
  form,
  name,
  label,
  ...props
}: {
  form: ReturnType<typeof useForm<ProductFormValues>>
  name: keyof Omit<ProductFormValues, 'product_image' | 'manufacturing_id'>
  label: string
} & Omit<InputHTMLAttributes<HTMLInputElement>, 'name' | 'form'>) {
  const id = `product-${String(name)}`
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input id={id} {...props} {...form.register(name)} />
      <FieldError>{form.formState.errors[name]?.message}</FieldError>
    </div>
  )
}

function BatchTable({ batches }: { batches: HerbBatch[] }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead><tr><th>Batch & herb</th><th>Origin</th><th>Quantity available</th><th>Batch status</th></tr></thead>
        <tbody>
          {batches.map((batch) => (
            <tr key={batch.batch_id}>
              <td><span className="table-primary">{batch.herb_name}</span><span className="table-secondary">{batch.batch_id} · {batch.botanical_name}</span></td>
              <td>{[batch.village, batch.district, batch.state].filter(Boolean).join(', ')}</td>
              <td>{formatQuantity(batch.available_quantity)} {batch.unit}</td>
              <td><StatusBadge value={batch.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function KeyValue({ label, value }: { label: string; value: string }) {
  return <div className="key-value-row"><span>{label}</span><strong>{value}</strong></div>
}

function formatQuantity(value: string) {
  const number = Number(value)
  return Number.isFinite(number) ? new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 }).format(number) : value
}

function formatDate(value: string) {
  if (!value) return '—'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(`${value.slice(0, 10)}T00:00:00`))
}
