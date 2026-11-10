import { useCallback, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { CheckCircle2, Info, TriangleAlert, X } from 'lucide-react'
import { createPortal } from 'react-dom'

export type ToastTone = 'success' | 'error' | 'info'

export interface Toast {
  id: string
  title: string
  description?: string
  tone: ToastTone
}

const ICONS = {
  success: CheckCircle2,
  error: TriangleAlert,
  info: Info,
} as const

const TONE_STYLES: Record<ToastTone, string> = {
  success: 'text-positive',
  error: 'text-critical',
  info: 'text-electric',
}

/** Lightweight toast queue with auto-dismiss. */
export function useToasts() {
  const [toasts, setToasts] = useState<Toast[]>([])
  const counter = useRef(0)

  const dismiss = useCallback((id: string) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const push = useCallback(
    (toast: Omit<Toast, 'id'>) => {
      counter.current += 1
      const id = `toast-${counter.current}`
      setToasts((current) => [...current.slice(-3), { ...toast, id }])
      window.setTimeout(() => dismiss(id), toast.tone === 'error' ? 7000 : 4200)
      return id
    },
    [dismiss],
  )

  return { toasts, push, dismiss }
}

export function Toaster({
  toasts,
  onDismiss,
}: {
  toasts: Toast[]
  onDismiss: (id: string) => void
}) {
  if (typeof document === 'undefined') return null

  return createPortal(
    <div className="pointer-events-none fixed bottom-5 right-5 z-[80] flex w-[min(360px,calc(100vw-2.5rem))] flex-col gap-2">
      <AnimatePresence initial={false}>
        {toasts.map((toast) => {
          const Icon = ICONS[toast.tone]
          return (
            <motion.div
              key={toast.id}
              layout
              initial={{ opacity: 0, y: 14, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, x: 24, scale: 0.97 }}
              transition={{ type: 'spring', stiffness: 380, damping: 32 }}
              className="pointer-events-auto flex items-start gap-3 rounded-panel border border-hairline bg-elevated/95 px-3.5 py-3 shadow-float backdrop-blur-xl"
            >
              <Icon className={`mt-0.5 size-4 shrink-0 ${TONE_STYLES[toast.tone]}`} />
              <div className="min-w-0 flex-1">
                <p className="text-[13px] font-medium leading-snug text-ink">{toast.title}</p>
                {toast.description ? (
                  <p className="mt-0.5 text-[12px] leading-snug text-ink-faint">{toast.description}</p>
                ) : null}
              </div>
              <button
                type="button"
                onClick={() => onDismiss(toast.id)}
                aria-label="Dismiss notification"
                className="rounded-md p-1 text-ink-ghost transition-colors hover:bg-ink/5 hover:text-ink-muted"
              >
                <X className="size-3.5" />
              </button>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>,
    document.body,
  )
}
