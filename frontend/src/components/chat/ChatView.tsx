import { useEffect, useLayoutEffect, useRef } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { MessageBubble, MessageSkeleton } from '@/components/chat/MessageBubble'
import { WelcomeScreen } from '@/components/chat/WelcomeScreen'
import type { AgentEvent, Message, Source } from '@/types'

interface ChatViewProps {
  messages: Message[]
  running: boolean
  liveContent: string
  liveSources: Source[]
  liveEvents: AgentEvent[]
  onRegenerate: () => void
  onPickExample: (prompt: string) => void
}

export function ChatView({
  messages,
  running,
  liveContent,
  liveSources,
  liveEvents,
  onRegenerate,
  onPickExample,
}: ChatViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const pinnedRef = useRef(true)

  const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant')
  const showWelcome = messages.length === 0 && !running

  // Keep the viewport pinned to the bottom unless the user scrolled up.
  const handleScroll = () => {
    const node = scrollRef.current
    if (!node) return
    const distance = node.scrollHeight - node.scrollTop - node.clientHeight
    pinnedRef.current = distance < 120
  }

  useLayoutEffect(() => {
    if (!pinnedRef.current) return
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages.length, liveContent, liveEvents.length, running])

  useEffect(() => {
    if (running) pinnedRef.current = true
  }, [running])

  return (
    <div
      ref={scrollRef}
      onScroll={handleScroll}
      className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden"
    >
      {showWelcome ? (
        <WelcomeScreen onPick={onPickExample} />
      ) : (
        <div className="mx-auto w-full max-w-3xl px-4 pt-6 sm:px-6 sm:pt-8">
          <div className="space-y-7">
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                onRegenerate={
                  message.role === 'assistant' && message === lastAssistant ? onRegenerate : undefined
                }
              />
            ))}

            <AnimatePresence>
              {running ? (
                <motion.div
                  key="live"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.26 }}
                >
                  {!liveContent && liveEvents.length === 0 ? (
                    <MessageSkeleton />
                  ) : (
                    <MessageBubble
                      message={{
                        id: 'live-assistant',
                        role: 'assistant',
                        content: liveContent,
                        created_at: new Date().toISOString(),
                        sources: liveSources,
                        events: liveEvents,
                        iterations: 0,
                        tool_calls: liveEvents.filter((e) => e.type === 'tool_call').length,
                        duration_ms: 0,
                        status: 'streaming',
                        error: null,
                        model: '',
                        provider: '',
                      }}
                      streaming
                    />
                  )}
                </motion.div>
              ) : null}
            </AnimatePresence>
          </div>

          {messages.length > 0 && !running ? (
            <div className="mt-8 flex items-center justify-center gap-2 border-t border-hairline pt-5 text-[11px] text-ink-ghost">
              <span>End of conversation</span>
              <span className="text-ink-ghost/50">·</span>
              <span>
                {messages.length} message{messages.length === 1 ? '' : 's'}
              </span>
            </div>
          ) : null}

          <div ref={bottomRef} className="h-2" />
        </div>
      )}
    </div>
  )
}
