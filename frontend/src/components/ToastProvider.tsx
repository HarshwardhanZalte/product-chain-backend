import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { AlertCircle, CheckCircle2, X } from 'lucide-react'

type ToastTone = 'success' | 'error'

interface ToastItem {
  id: number
  title: string
  message: string
  tone: ToastTone
}

interface ToastContextValue {
  notify: (message: string, tone?: ToastTone, title?: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])
  const notify = useCallback((message: string, tone: ToastTone = 'success', title?: string) => {
    const id = Date.now() + Math.random()
    setItems((current) => [...current, {
      id,
      title: title ?? (tone === 'error' ? 'Action could not be completed' : 'Saved'),
      message,
      tone,
    }])
    window.setTimeout(() => {
      setItems((current) => current.filter((item) => item.id !== id))
    }, 5000)
  }, [])
  const value = useMemo(() => ({ notify }), [notify])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-region" aria-live="polite">
        {items.map((item) => (
          <div className={`toast ${item.tone === 'error' ? 'error' : ''}`} key={item.id}>
            {item.tone === 'error' ? <AlertCircle size={16} /> : <CheckCircle2 size={16} />}
            <div>
              <strong>{item.title}</strong>
              <span>{item.message}</span>
            </div>
            <button
              aria-label="Dismiss notification"
              className="button-icon"
              onClick={() => setItems((current) => current.filter(({ id }) => id !== item.id))}
              type="button"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const value = useContext(ToastContext)
  if (!value) throw new Error('useToast must be used within ToastProvider.')
  return value
}
