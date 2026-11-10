import { memo, useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Check, Copy, RefreshCw, TriangleAlert } from 'lucide-react'
import { Markdown } from '@/components/chat/Markdown'
import { SourceList } from '@/components/chat/SourceList'
import { Logo } from '@/components/ui/Logo'
import type { Message } from '@/types'

function CopyButton({ value, label }: { value: string; label: string }) {
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!copied) return
    const timer = window.setTimeout(() => setCopied(false), 1800)
    return () => window.clearTimeout(timer)
  }, [copied])

  return (
    <button
      type="button"
      onClick={() => {
        if (!value) return
        void navigator.clipboard?.writeText(value).then(() => setCopied(true))
      }}
      aria-label={label}
      title={label}
      className="inline-flex size-7 items-center justify-center rounded-md text-ink-ghost transition-colors hover:bg-ink/6 hover:text-ink-muted"
    >
      {copied ? <Check className="size-3.5 text-positive" /> : <Copy className="size-3.5" />}
    </button>
  )
}

interface MessageBubbleProps {
  message: Message
  streaming?: boolean
  onRegenerate?: () => void
}

/** A single turn in the conversation. */
export const MessageBubble = memo(function MessageBubble({
  message,
  streaming = false,
  onRegenerate,
}: MessageBubbleProps) {
  const [expandedSources, setExpandedSources] = useState(false)
  const isUser = message.role === 'user'

  return (
    <motion.article
      layout="position"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
      className="group/msg flex w-full gap-3.5 sm:gap-4"
    >
      <div className="flex size-7 shrink-0 items-center justify-center rounded-lg border border-hairline sm:size-8">
        {isUser ? (
          <span className="text-[11px] font-semibold tracking-wide text-ink-faint">YOU</span>
        ) : (
          <Logo className="size-4 sm:size-4.5" />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <div className="mb-1.5 flex items-center gap-2">
          <span className="text-[12.5px] font-semibold text-ink">
            {isUser ? 'You' : 'Nexus'}
          </span>
          {!isUser && message.model ? (
            <span className="rounded-md border border-hairline px-1.5 py-px font-mono text-[10px] text-ink-ghost">
              {message.model}
            </span>
          ) : null}
          {!isUser && message.tool_calls > 0 ? (
            <span className="rounded-md border border-hairline px-1.5 py-px text-[10px] font-medium text-ink-ghost">
              {message.tool_calls} tool call{message.tool_calls === 1 ? '' : 's'}
            </span>
          ) : null}
        </div>

        {isUser ? (
          <div className="text-[14.5px] leading-[1.68] whitespace-pre-wrap text-ink">
            {message.content}
          </div>
        ) : (
          <>
            {message.content ? (
              <Markdown content={message.content} />
            ) : streaming ? (
              <div className="flex items-center gap-2 py-1">
                <span className="nx-breathe size-1.5 rounded-full bg-accent" />
                <span className="nx-breathe size-1.5 rounded-full bg-electric [animation-delay:160ms]" />
                <span className="nx-breathe size-1.5 rounded-full bg-signal [animation-delay:320ms]" />
                <span className="ml-1 text-[12px] text-ink-ghost">Researching…</span>
              </div>
            ) : null}

            {message.status === 'error' && message.error ? (
              <div className="mt-3 flex items-start gap-2.5 rounded-field border border-critical/25 bg-critical/8 px-3 py-2.5">
                <TriangleAlert className="mt-0.5 size-4 shrink-0 text-critical" />
                <div className="min-w-0">
                  <p className="text-[12.5px] font-medium text-critical">The agent run failed</p>
                  <p className="mt-0.5 text-[12px] leading-relaxed text-ink-muted">{message.error}</p>
                </div>
              </div>
            ) : null}

            {message.status === 'cancelled' ? (
              <p className="mt-3 text-[12.5px] text-ink-ghost">
                Stopped before the agent finished researching.
              </p>
            ) : null}

            <SourceList
              sources={message.sources}
              expanded={expandedSources}
              onToggle={() => setExpandedSources((value) => !value)}
            />

            <div className="mt-2 flex items-center gap-0.5 opacity-0 transition-opacity duration-150 group-hover/msg:opacity-100 focus-within:opacity-100">
              <CopyButton value={message.content} label="Copy response" />
              {onRegenerate && !streaming ? (
                <button
                  type="button"
                  onClick={onRegenerate}
                  aria-label="Regenerate response"
                  title="Regenerate response"
                  className="inline-flex size-7 items-center justify-center rounded-md text-ink-ghost transition-colors hover:bg-ink/6 hover:text-ink-muted"
                >
                  <RefreshCw className="size-3.5" />
                </button>
              ) : null}
              {message.duration_ms > 0 ? (
                <span className="ml-1 font-mono text-[10.5px] tabular-nums text-ink-ghost">
                  {(message.duration_ms / 1000).toFixed(1)}s
                </span>
              ) : null}
            </div>
          </>
        )}
      </div>
    </motion.article>
  )
})

/** A shimmering placeholder used while the first answer is being prepared. */
export function MessageSkeleton() {
  return (
    <div className="flex w-full gap-3.5 sm:gap-4">
      <div className="size-7 shrink-0 rounded-lg border border-hairline sm:size-8" />
      <div className="flex-1 space-y-2.5 pt-1">
        <div className="nx-shimmer h-3 w-24 rounded-full bg-ink/5" />
        <div className="nx-shimmer h-3 w-full rounded-full bg-ink/5" />
        <div className="nx-shimmer h-3 w-4/5 rounded-full bg-ink/5" />
      </div>
    </div>
  )
}

export function StreamingCursor() {
  return (
    <span className="ml-0.5 inline-block h-3.5 w-[2px] translate-y-[2px] rounded-full bg-accent align-baseline">
      <motion.span
        className="absolute inset-0 rounded-full bg-accent"
        animate={{ opacity: [0.25, 1, 0.25] }}
        transition={{ duration: 1.1, repeat: Infinity }}
      />
    </span>
  )
}

export function TypingIndicator({ label = 'Nexus is reasoning' }: { label?: string }) {
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={label}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="flex items-center gap-2.5 py-1"
      >
        <div className="flex items-center gap-1">
          {[0, 1, 2].map((index) => (
            <span
              key={index}
              className="nx-breathe size-1.5 rounded-full bg-ink-faint"
              style={{ animationDelay: `${index * 150}ms` }}
            />
          ))}
        </div>
        <span className="text-[12.5px] text-ink-ghost">{label}</span>
      </motion.div>
    </AnimatePresence>
  )
}
