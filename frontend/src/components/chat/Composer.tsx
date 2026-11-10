import { useCallback, useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowUp, CornerDownLeft, Square } from 'lucide-react'
import clsx from 'clsx'

interface ComposerProps {
  onSend: (message: string) => void
  onStop: () => void
  running: boolean
  disabled?: boolean
  placeholder?: string
}

const MAX_LENGTH = 4000

export function Composer({
  onSend,
  onStop,
  running,
  disabled = false,
  placeholder = "Ask Nexus anything. I'll research it for you...",
}: ComposerProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const resize = useCallback(() => {
    const node = textareaRef.current
    if (!node) return
    node.style.height = 'auto'
    node.style.height = `${Math.min(node.scrollHeight, 220)}px`
  }, [])

  useEffect(() => {
    resize()
  }, [value, resize])

  useEffect(() => {
    if (!running) textareaRef.current?.focus()
  }, [running])

  const submit = useCallback(() => {
    const text = value.trim()
    if (!text || running || disabled) return
    onSend(text)
    setValue('')
    requestAnimationFrame(() => {
      if (textareaRef.current) textareaRef.current.style.height = 'auto'
    })
  }, [value, running, disabled, onSend])

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
        event.preventDefault()
        submit()
      }
    },
    [submit],
  )

  const remaining = MAX_LENGTH - value.length
  const canSend = value.trim().length > 0 && !running && !disabled

  return (
    <div className="px-4 pb-4 sm:px-6 sm:pb-6">
      <div className="mx-auto w-full max-w-3xl">
        <motion.div
          layout
          className={clsx(
            'relative rounded-[16px] border bg-elevated/70 backdrop-blur-xl transition-colors duration-200',
            'shadow-[0_1px_0_0_rgba(255,255,255,0.04)_inset,0_20px_50px_-30px_rgba(0,0,0,0.9)]',
            running ? 'border-accent/30' : 'border-hairline focus-within:border-hairline-strong',
          )}
        >
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            spellCheck
            aria-label="Message Nexus"
            className={clsx(
              'nx-surface-glass block max-h-[220px] w-full resize-none rounded-[16px] bg-transparent px-4 pt-3.5 pb-2',
              'text-[14.5px] leading-[1.6] text-ink placeholder:text-ink-ghost',
              'focus:outline-none disabled:opacity-50',
            )}
          />

          <div className="flex items-center justify-between gap-3 px-2.5 pb-2.5">
            <div className="flex items-center gap-2 text-[11px] text-ink-ghost">
              <kbd className="inline-flex items-center gap-1 rounded border border-hairline bg-ink/[0.04] px-1.5 py-0.5 font-sans text-[10.5px] text-ink-faint">
                <CornerDownLeft className="size-2.5" />
                send
              </kbd>
              <span className="hidden sm:inline">·</span>
              <span className="hidden sm:inline">shift + enter for a new line</span>
              {remaining < 400 ? (
                <span className={clsx('tabular-nums', remaining < 80 ? 'text-critical' : 'text-ink-ghost')}>
                  {remaining}
                </span>
              ) : null}
            </div>

            <AnimatePresence mode="wait" initial={false}>
              {running ? (
                <motion.button
                  key="stop"
                  type="button"
                  onClick={onStop}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ duration: 0.16 }}
                  className="inline-flex h-8 items-center gap-1.5 rounded-field border border-critical/30 bg-critical/12 px-3 text-[12.5px] font-medium text-critical transition-colors hover:bg-critical/18"
                >
                  <Square className="size-3 fill-current" />
                  Stop
                </motion.button>
              ) : (
                <motion.button
                  key="send"
                  type="button"
                  onClick={submit}
                  disabled={!canSend}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ duration: 0.16 }}
                  aria-label="Send message"
                  className={clsx(
                    'inline-flex size-8 items-center justify-center rounded-field transition-all duration-150',
                    canSend
                      ? 'bg-ink text-canvas hover:bg-ink/88 active:scale-95'
                      : 'cursor-not-allowed bg-ink/8 text-ink-ghost',
                  )}
                >
                  <ArrowUp className="size-4" strokeWidth={2.4} />
                </motion.button>
              )}
            </AnimatePresence>
          </div>
        </motion.div>

        <p className="mt-2.5 text-center text-[11px] leading-relaxed text-ink-ghost">
          Nexus searches the live web before answering — every claim is linked to a source.
        </p>
      </div>
    </div>
  )
}
