import { useCallback, useEffect, useRef, useState } from 'react'
import { api, streamChat } from '@/services/api'
import type { AgentEvent, Source } from '@/types'

export interface AgentRun {
  running: boolean
  runId: string | null
  events: AgentEvent[]
  streamingText: string
  sources: Source[]
  iterations: number
  toolCalls: number
  error: string | null
  cancelled: boolean
}

const EMPTY_RUN: AgentRun = {
  running: false,
  runId: null,
  events: [],
  streamingText: '',
  sources: [],
  iterations: 0,
  toolCalls: 0,
  error: null,
  cancelled: false,
}

interface Options {
  onComplete?: (payload: {
    content: string
    sources: Source[]
    events: AgentEvent[]
    iterations: number
    toolCalls: number
    conversationId: string | null
    runId: string
    error?: string | null
    cancelled?: boolean
  }) => void
  onError?: (error: Error) => void
}

/**
 * Drives a single agent run and exposes its live execution state.
 *
 * The hook owns the SSE connection, the cancellation signal and the
 * accumulation of streamed text, tool observations and sources.
 */
export function useAgentStream(options: Options = {}) {
  const [run, setRun] = useState<AgentRun>(EMPTY_RUN)
  const controllerRef = useRef<AbortController | null>(null)
  const runIdRef = useRef<string | null>(null)
  const serverConversationRef = useRef<string | null>(null)
  const runRef = useRef<AgentRun>(EMPTY_RUN)
  const optionsRef = useRef(options)
  optionsRef.current = options

  const applyRun = useCallback((updater: (current: AgentRun) => AgentRun) => {
    setRun((current) => {
      const next = updater(current)
      runRef.current = next
      return next
    })
  }, [])

  const reset = useCallback(() => {
    setRun(EMPTY_RUN)
    runRef.current = EMPTY_RUN
    runIdRef.current = null
  }, [])

  const stop = useCallback(async () => {
    const runId = runIdRef.current
    if (runId) {
      try {
        await api.stopRun(runId)
      } catch {
        /* the abort below is the real cancellation */
      }
    }
    controllerRef.current?.abort()
    controllerRef.current = null
    applyRun((current) => ({ ...current, running: false, cancelled: true }))
  }, [applyRun])

  const send = useCallback(
    async (message: string, conversationId: string | null) => {
      if (!message.trim()) return

      controllerRef.current?.abort()
      const controller = new AbortController()
      controllerRef.current = controller

      const runId = `run-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
      runIdRef.current = runId
      serverConversationRef.current = conversationId

      setRun({
        ...EMPTY_RUN,
        running: true,
        runId,
      })
      runRef.current = { ...EMPTY_RUN, running: true, runId }

      await streamChat(
        {
          message,
          conversation_id: conversationId,
          run_id: runId,
        },
        {
          onEvent: (eventName, raw) => {
            const payload = raw as { type?: string } & Partial<AgentEvent>
            const event: AgentEvent = {
              id: payload.id ?? `${runId}-${eventName}`,
              type: (payload.type ?? eventName) as AgentEvent['type'],
              timestamp: payload.timestamp ?? new Date().toISOString(),
              step: payload.step ?? 0,
              title: payload.title ?? '',
              detail: payload.detail ?? null,
              data: payload.data ?? {},
            }

            applyRun((current) => {
              if (!current.running && current.runId !== runId) return current
              const events = [...current.events, event]
              const data = event.data as Record<string, never>

              switch (event.type) {
                case 'agent_started': {
                  // The backend is authoritative about which conversation the
                  // run belongs to (it may have created one).
                  const serverId = (data as { conversation_id?: string }).conversation_id
                  if (serverId) serverConversationRef.current = serverId
                  return { ...current, events }
                }
                case 'token': {
                  const text = (data as { text?: string }).text ?? ''
                  return { ...current, events, streamingText: current.streamingText + text }
                }
                case 'tool_selected':
                case 'tool_call': {
                  // The model pivoted to a tool: any partial prose belongs to the
                  // plan, not to the final answer, so the live buffer is reset.
                  return { ...current, events, streamingText: '' }
                }
                case 'tool_result':
                case 'observation': {
                  const results = (data as { results?: unknown[] }).results ?? []
                  const incoming = results as Array<{
                    url?: string
                    title?: string
                    snippet?: string
                    source?: string
                    domain?: string
                    position?: number
                    published_at?: string | null
                  }>
                  const merged = new Map(current.sources.map((s) => [s.url, s]))
                  incoming.forEach((item, index) => {
                    if (!item.url || merged.has(item.url)) return
                    merged.set(item.url, {
                      title: item.title ?? item.url,
                      url: item.url,
                      snippet: item.snippet ?? '',
                      source: item.source ?? item.domain ?? '',
                      domain: item.domain ?? '',
                      rank: item.position ?? current.sources.length + index + 1,
                      published_at: item.published_at ?? null,
                    })
                  })
                  return { ...current, events, sources: [...merged.values()] }
                }
                case 'planning': {
                  const iteration = (data as { iteration?: number }).iteration
                  return {
                    ...current,
                    events,
                    iterations: iteration ? Math.max(current.iterations, iteration) : current.iterations,
                  }
                }
                case 'final_answer': {
                  const content = (data as { content?: string }).content ?? ''
                  return { ...current, events, streamingText: content }
                }
                case 'agent_completed': {
                  const iterations = (data as { iterations?: number }).iterations ?? current.iterations
                  const toolCalls = (data as { tool_calls?: number }).tool_calls ?? current.toolCalls
                  return { ...current, events, iterations, toolCalls }
                }
                case 'agent_error': {
                  return {
                    ...current,
                    events,
                    error: event.detail ?? 'The agent run failed.',
                  }
                }
                default:
                  return { ...current, events }
              }
            })
          },
          onError: (error) => {
            optionsRef.current.onError?.(error)
            applyRun((current) => ({
              ...current,
              running: false,
              error: error.message,
            }))
          },
        },
        controller.signal,
      )

      applyRun((current) => {
        if (current.runId !== runId) return current
        return { ...current, running: false }
      })

      const finalState = runRef.current
      optionsRef.current.onComplete?.({
        content: finalState.streamingText,
        sources: finalState.sources,
        events: finalState.events,
        iterations: finalState.iterations,
        toolCalls: finalState.toolCalls,
        conversationId: serverConversationRef.current ?? conversationId,
        runId,
        error: finalState.error,
        cancelled: finalState.cancelled,
      })
    },
    [applyRun],
  )

  useEffect(
    () => () => {
      controllerRef.current?.abort()
    },
    [],
  )

  return { run, send, stop, reset }
}
