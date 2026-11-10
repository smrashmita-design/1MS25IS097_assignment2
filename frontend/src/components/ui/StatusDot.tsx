import clsx from 'clsx'

export type DotTone = 'positive' | 'caution' | 'critical' | 'idle'

const TONE_MAP: Record<DotTone, string> = {
  positive: 'bg-positive',
  caution: 'bg-caution',
  critical: 'bg-critical',
  idle: 'bg-ink-ghost',
}

/** A small status indicator with an optional pulse. */
export function StatusDot({
  tone,
  pulse = false,
  className,
}: {
  tone: DotTone
  pulse?: boolean
  className?: string
}) {
  return (
    <span className={clsx('relative inline-flex size-2 shrink-0', className)}>
      {pulse ? (
        <span
          className={clsx(
            'nx-ping-soft absolute inset-0 rounded-full opacity-70',
            TONE_MAP[tone],
          )}
        />
      ) : null}
      <span className={clsx('relative size-2 rounded-full', TONE_MAP[tone])} />
    </span>
  )
}
