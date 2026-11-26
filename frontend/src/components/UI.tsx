import { useEffect, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { AlertCircle, CheckCircle2, Info, LoaderCircle } from 'lucide-react'
import { X } from 'lucide-react'

export function Button({
  children,
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'danger' | 'danger-solid' | 'quiet'
}) {
  return (
    <button className={`button button-${variant} ${className}`} type="button" {...props}>
      {children}
    </button>
  )
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string
  title: string
  description?: string
  actions?: ReactNode
}) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {actions && <div className="toolbar">{actions}</div>}
    </div>
  )
}

export function Card({
  title,
  subtitle,
  actions,
  children,
  className = '',
}: {
  title?: string
  subtitle?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <div className="card-header">
          <div>
            {title && <h2>{title}</h2>}
            {subtitle && <p>{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  )
}

export function StatusBadge({ value }: { value?: string | null }) {
  const normalized = value?.toLowerCase().replaceAll('_', '-').replaceAll(' ', '-') ?? ''
  const known = [
    'approved',
    'completed',
    'active',
    'verified',
    'accepted',
    'pending',
    'registered',
    'planned',
    'under-testing',
    'rejected',
    'cancelled',
    'suspended',
    'in-transit',
    'initiated',
    'sent-to-lab',
    'with-collector',
    'sent-to-factory',
  ]
  const tone = known.includes(normalized) ? `status-${normalized}` : 'status-neutral'
  return <span className={`status-badge ${tone}`}>{value?.replaceAll('_', ' ') ?? 'Unknown'}</span>
}

export function StatCard({
  label,
  value,
  icon,
  caption,
}: {
  label: string
  value: string | number
  icon: ReactNode
  caption?: string
}) {
  return (
    <article className="stat-card">
      <div className="stat-top">
        <span>{label}</span>
        <span className="stat-icon">{icon}</span>
      </div>
      <div className="stat-value">{value}</div>
      {caption && <div className="stat-caption">{caption}</div>}
    </article>
  )
}

export function LoadingState({ label = 'Loading live data…' }: { label?: string }) {
  return (
    <div className="loading-state" role="status">
      <LoaderCircle className="spinner" size={18} />
      <span>{label}</span>
    </div>
  )
}

export function EmptyState({
  title,
  message,
  action,
}: {
  title: string
  message: string
  action?: ReactNode
}) {
  return (
    <div className="empty-state">
      <Info size={19} style={{ margin: '0 auto', color: 'var(--sage)' }} />
      <strong>{title}</strong>
      <p>{message}</p>
      {action}
    </div>
  )
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string
  onRetry?: () => void
}) {
  return (
    <div className="alert alert-error" role="alert">
      <AlertCircle size={16} />
      <div style={{ flex: 1 }}>{message}</div>
      {onRetry && <Button onClick={onRetry} variant="secondary">Try again</Button>}
    </div>
  )
}

export function InlineSuccess({ children }: { children: ReactNode }) {
  return (
    <div className="alert alert-success">
      <CheckCircle2 size={16} />
      <span>{children}</span>
    </div>
  )
}

export function FieldError({ children }: { children?: ReactNode }) {
  if (!children) return null
  return <span className="field-error">{children}</span>
}

export function Modal({
  title,
  description,
  onClose,
  children,
}: {
  title: string
  description?: string
  onClose: () => void
  children: ReactNode
}) {
  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [onClose])

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.currentTarget === event.target) onClose()
      }}
    >
      <section aria-labelledby="modal-title" aria-modal="true" className="modal" role="dialog">
        <div className="modal-header">
          <div>
            <h2 id="modal-title">{title}</h2>
            {description && <p>{description}</p>}
          </div>
          <button aria-label="Close dialog" className="button-icon" onClick={onClose} type="button">
            <X size={15} />
          </button>
        </div>
        <div className="modal-content">{children}</div>
      </section>
    </div>
  )
}

export function Pagination({
  count,
  page,
  pageSize = 20,
  onChange,
  disabled,
}: {
  count: number
  page: number
  pageSize?: number
  onChange: (page: number) => void
  disabled?: boolean
}) {
  const totalPages = Math.max(1, Math.ceil(count / pageSize))
  if (totalPages <= 1) return null
  return (
    <div className="pagination">
      <span>Page {page} of {totalPages} · {count} records</span>
      <div className="toolbar">
        <Button disabled={disabled || page <= 1} onClick={() => onChange(page - 1)} variant="secondary">Previous</Button>
        <Button disabled={disabled || page >= totalPages} onClick={() => onChange(page + 1)} variant="secondary">Next</Button>
      </div>
    </div>
  )
}
