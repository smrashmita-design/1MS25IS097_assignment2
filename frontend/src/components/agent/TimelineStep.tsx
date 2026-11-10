import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronRight } from 'lucide-react'
import clsx from 'clsx'
import type { LucideIcon } from 'lucide-react'
import type { AgentEvent } from '@/types'

export type StepTone = 'neutral' | 'accent' | 'electric' | 'signal' | 'positive' | 'caution' | 'critical'

export type StepStatus = 'complete' | 'active' | 'pending' | 'error'

interface TimelineStepProps {
  event: AgentEvent
  status: StepStatus
  icon: LucideIcon
  tone: StepTone
  details?: React.ReactNode
  defaultOpen?: boolean
}

const TONE_RING: Record<StepTone, string> = {
  neutral: 'border-hairline-strong bg-ink/5 text-ink-muted',
  accent: 'border-accent/30 bg-accent-soft text-accent',
  electric: 'border-electric/30 bg-electric/10 text-electric',
  signal: 'border-signal/30 bg-signal/10 text-signal',
  positive: 'border-positive/30 bg-positive/10 text-positive',
  caution: 'border-caution/30 bg-caution/10 text-caution',
  critical: 'border-critical/30 bg-critical/10 text-critical',
}

const TONE_LINE: Record<StepTone, string> = {
  neutral: 'bg-ink-ghost',
  accent: 'bg-accent',
  electric: 'bg-electric',
  signal: 'bg-signal',
  positive: 'bg-positive',
  caution: 'bg-caution',
  critical: 'bg-critical',
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

/** One row of the execution timeline. */
export function TimelineStep({
  event,
  status,
  icon: Icon,
  tone,
  details,
  defaultOpen = false,
}: TimelineStepProps) {
  const [open, setOpen] = useState(defaultOpen)
  const hasDetails = Boolean(details)

  return (
    <motion.div
      layout="position"
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.26, ease: [0.22, 1, 0.36, 1] }}
      className="relative pl-8"
    >
      <span
        className={clsx(
          'absolute top-0.5 left-0 flex size-5 items-center justify-center rounded-full border transition-colors duration-300',
          status === 'pending' ? 'border-hairline bg-ink/5 text-ink-ghost' : TONE_RING[tone],
        )}
      >
        {status === 'active' ? (
          <span className="absolute inset-0 animate-ping rounded-full bg-current opacity-20" />
        ) : null}
        <Icon className="relative size-2.5" strokeWidth={2.4} />
      </span>

      <div className="pb-4">
        <button
          type="button"
          onClick={() => hasDetails && setOpen((value) => !value)}
          className={clsx(
            'flex w-full items-start gap-2 text-left',
            hasDetails && 'cursor-pointer',
          )}
          aria-expanded={hasDetails ? open : undefined}
        >
          <span className="min-w-0 flex-1">
            <span className="flex items-baseline gap-2">
              <span
                className={clsx(
                  'truncate text-[12.5px] font-medium',
                  status === 'pending' ? 'text-ink-ghost' : 'text-ink',
                )}
              >
                {event.title}
              </span>
              <span className="shrink-0 font-mono text-[10px] tabular-nums text-ink-ghost">
                {formatTime(event.timestamp)}
              </span>
            </span>
            {event.detail ? (
              <span className="mt-0.5 block text-[11.5px] leading-relaxed break-words text-ink-faint">
                {event.detail}
              </span>
            ) : null}
          </span>
          {hasDetails ? (
            <ChevronRight
              className={clsx(
                'mt-0.5 size-3.5 shrink-0 text-ink-ghost transition-transform duration-200',
                open && 'rotate-90',
              )}
            />
          ) : null}
        </button>

        <AnimatePresence initial={false}>
          {hasDetails && open ? (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
              className="overflow-hidden"
            >
              <div className="mt-2.5">{details}</div>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}

/** The vertical connector drawn between timeline rows. */
export function TimelineRail({ tone }: { tone: StepTone }) {
  return (
    <span
      className={clsx(
        'absolute top-5 bottom-0 left-2.5 w-px origin-top',
        TONE_LINE[tone],
        'opacity-25',
      )}
    />
  )
}
