import { ArrowLeft, ArrowRight, Camera, Leaf, Search, ShieldCheck, X } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import type { Html5Qrcode } from 'html5-qrcode'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { productApi } from '../api/products'
import { getApiErrorMessage } from '../api/client'
import type { ProductVerification } from '../api/types'
import { Button, Card, EmptyState, ErrorState, LoadingState, StatusBadge } from '../components/UI'

function PublicShell({ children }: { children: ReactNode }) {
  return (
    <main className="public-page">
      <header className="public-header">
        <Link className="auth-brand" to="/">
          <span className="brand-mark"><Leaf size={19} /></span>
          <span><strong>Product Chain</strong><span>Botanical Traceability</span></span>
        </Link>
        <Link className="inline-link" to="/login">Participant sign in <ArrowRight size={13} /></Link>
      </header>
      {children}
    </main>
  )
}

function verificationReference(value: string): string {
  const scanned = value.trim()
  if (!scanned) return ''
  try {
    const url = new URL(scanned)
    const path = url.pathname.split('/').filter(Boolean)
    const verifyIndex = path.lastIndexOf('verify')
    if (verifyIndex >= 0 && path[verifyIndex + 1]) return decodeURIComponent(path[verifyIndex + 1])
    return decodeURIComponent(path[path.length - 1] ?? scanned)
  } catch {
    return scanned.replace(/^\/+|\/+$/g, '').split('/').pop() ?? scanned
  }
}

export function QrScannerPage() {
  const navigate = useNavigate()
  const scanner = useRef<Html5Qrcode | null>(null)
  const [manualCode, setManualCode] = useState('')
  const [running, setRunning] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => () => {
    const activeScanner = scanner.current
    if (activeScanner?.isScanning) void activeScanner.stop().catch(() => undefined)
  }, [])

  const startScanner = async () => {
    setMessage('')
    try {
      const { Html5Qrcode: QrScanner } = await import('html5-qrcode')
      const instance = new QrScanner('product-chain-qr-reader')
      scanner.current = instance
      await instance.start(
        { facingMode: 'environment' },
        { fps: 10, qrbox: { width: 240, height: 240 } },
        (decoded) => {
          const reference = verificationReference(decoded)
          if (!reference) {
            setMessage('The QR code did not contain a product reference.')
            return
          }
          void instance.stop().then(() => setRunning(false)).catch((error: unknown) => setMessage(getApiErrorMessage(error)))
          navigate(`/verify/${encodeURIComponent(reference)}`)
        },
        () => undefined,
      )
      setRunning(true)
    } catch (error) {
      setMessage(getApiErrorMessage(error))
      scanner.current = null
    }
  }

  const stopScanner = async () => {
    if (!scanner.current?.isScanning) return
    try {
      await scanner.current.stop()
      setRunning(false)
      scanner.current = null
    } catch (error) {
      setMessage(getApiErrorMessage(error))
    }
  }

  return (
    <PublicShell>
      <section className="scanner-panel">
        <div className="eyebrow">Consumer verification</div>
        <h1>Scan a product QR code</h1>
        <p>Verify the product’s source batches, manufacturing record, and laboratory status from backend records.</p>
        <div className="scanner-frame">
          <div id="product-chain-qr-reader" />
          {!running && (
            <div className="scanner-placeholder">
              <span className="scanner-icon"><Camera size={24} /></span>
              <strong>Camera scan</strong>
              <span>Allow camera access to scan the product label.</span>
              <Button onClick={() => void startScanner()}><Camera size={14} /> Start camera</Button>
            </div>
          )}
        </div>
        {running && <Button onClick={() => void stopScanner()} variant="secondary"><X size={14} /> Stop camera</Button>}
        {message && <div style={{ marginTop: 14 }}><ErrorState message={message} /></div>}
        <div className="scanner-divider"><span>or enter a reference</span></div>
        <form className="toolbar scanner-manual" onSubmit={(event) => {
          event.preventDefault()
          const reference = verificationReference(manualCode)
          if (reference) navigate(`/verify/${encodeURIComponent(reference)}`)
        }}>
          <label className="search-control">
            <Search size={14} />
            <input aria-label="Product QR reference" onChange={(event) => setManualCode(event.target.value)} placeholder="Enter QR reference" value={manualCode} />
          </label>
          <Button disabled={!manualCode.trim()} type="submit">Verify <ArrowRight size={14} /></Button>
        </form>
        <Link className="inline-link" to="/"><ArrowLeft size={13} /> Back</Link>
      </section>
    </PublicShell>
  )
}

export function ProductVerificationPage({ reference }: { reference: string }) {
  const query = useQuery({
    queryKey: ['public-verification', reference],
    queryFn: () => productApi.verify(reference),
    enabled: Boolean(reference),
    retry: false,
  })

  return (
    <PublicShell>
      <section className="verification-page">
        <div className="verification-title">
          <div>
            <div className="eyebrow">Public product record</div>
            <h1>Product verification</h1>
            <p>Reference: <strong>{reference}</strong></p>
          </div>
          <Link className="button button-secondary" to="/scan"><Camera size={14} /> Scan another</Link>
        </div>
        {!reference && <EmptyState title="Missing product reference" message="Scan a QR code or enter its reference to view the record." />}
        {query.isLoading && <LoadingState label="Loading verified product records…" />}
        {query.error && <ErrorState message={getApiErrorMessage(query.error)} onRetry={() => void query.refetch()} />}
        {query.data && <VerificationRecord verification={query.data} />}
        <p className="verification-disclaimer">
          This page shows the current records supplied by the traceability service. It does not represent a blockchain or independent certification claim.
        </p>
      </section>
    </PublicShell>
  )
}

function VerificationRecord({ verification }: { verification: ProductVerification }) {
  const product = verification.product
  const manufacturing = verification.manufacturing
  return (
    <div className="verification-content">
      <div className="verification-hero">
        {product.product_image_url && <img alt={product.product_name} src={product.product_image_url} />}
        <div className="verification-product">
          <StatusBadge value={verification.verification_status} />
          <h2>{product.product_name}</h2>
          <p>{product.product_type} · Batch {product.batch_number}</p>
          <div className="verification-manufacturer"><ShieldCheck size={15} /> Manufactured by {product.manufacturer_name}</div>
          <div className="verification-meta">
            <span>Manufactured {formatDate(product.manufacture_date)}</span>
            <span>Product status: {product.status.replaceAll('_', ' ')}</span>
          </div>
        </div>
      </div>
      <Card title="Manufacturing record" subtitle="Current backend production data">
        <div className="card-body key-value-list">
          <KeyValue label="Process date" value={formatDate(manufacturing.process_date)} />
          <KeyValue label="Process description" value={manufacturing.process_description} />
          <KeyValue label="Recorded output" value={`${manufacturing.output_quantity} ${manufacturing.unit}`} />
        </div>
      </Card>
      <section className="lineage-section">
        <div className="eyebrow">Product lineage</div>
        <h2>Input batches & quality records</h2>
        {verification.input_herb_batches.length === 0 ? (
          <EmptyState title="No source batches listed" message="The public verification response contains no input-batch records." />
        ) : verification.input_herb_batches.map((batch) => (
          <Card className="lineage-card" key={batch.batch_id} title={`${batch.herb_name} · ${batch.batch_id}`} subtitle={batch.botanical_name}>
            <div className="card-body">
              <div className="key-value-list">
                <KeyValue label="Input amount" value={`${batch.quantity_used} ${batch.unit}`} />
                <KeyValue label="Harvest origin" value={[batch.origin.village, batch.origin.district, batch.origin.state].filter(Boolean).join(', ') || 'Not recorded'} />
                <KeyValue label="Harvest date" value={formatDate(batch.origin.collection_date)} />
                <KeyValue label="Latest laboratory status" value={batch.laboratory_test_status ?? 'No approved test recorded'} />
                <KeyValue label="Laboratory" value={batch.laboratory_name ?? 'Not available'} />
                <KeyValue label="Certificate" value={batch.certificate_available ? 'Available to authorized users' : 'Not available'} />
              </div>
              {batch.lab_measurements.length > 0 && (
                <div className="table-wrap" style={{ marginTop: 16 }}>
                  <table className="data-table">
                    <thead><tr><th>Analyte</th><th>Method</th><th>Result</th><th>Threshold</th><th>Verdict</th></tr></thead>
                    <tbody>{batch.lab_measurements.map((measurement, index) => (
                      <tr key={`${measurement.analyte}-${index}`}>
                        <td>{measurement.analyte}</td><td>{measurement.method}</td>
                        <td>{measurement.result_value} {measurement.unit}</td><td>{measurement.threshold || '—'}</td>
                        <td><StatusBadge value={measurement.verdict} /></td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
              )}
              <div className="lineage-transfers">
                <strong>Custody transfers</strong>
                {batch.transfer_history.length === 0 ? <p>No transfer events in the public record.</p> : batch.transfer_history.map((transfer) => (
                  <div className="transfer-history-item" key={transfer.event_id}>
                    <span><StatusBadge value={transfer.status} /></span>
                    <span>{formatDate(transfer.transfer_date)}</span>
                    <span>{transfer.transfer_location || 'Location not recorded'}</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        ))}
      </section>
    </div>
  )
}

function KeyValue({ label, value }: { label: string; value: string }) {
  return <div className="key-value-row"><span>{label}</span><strong>{value || '—'}</strong></div>
}

function formatDate(value: string) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(date)
}
