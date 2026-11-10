/**
 * Backend API client.
 *
 * The base URL is resolved at build time from `VITE_API_BASE_URL` and falls
 * back to the dev proxy (`/api`) so no secrets ever reach the bundle.
 */

import type {
  ChatRequest,
  Conversation,
  ConversationSummary,
  HealthResponse,
  SavedSearch,
  SettingsResponse,
  StatusResponse,
} from '@/types'

const RAW_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').trim()
export const API_BASE_URL = RAW_BASE.replace(/\/+$/, '')

const API_PREFIX = API_BASE_URL || ''

function url(path: string): string {
  return `${API_PREFIX}${path.startsWith('/') ? path : `/${path}`}`
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code = 'api_error',
    readonly details: unknown = null,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function parseError(response: Response): Promise<ApiError> {
  let message = `Request failed with status ${response.status}`
  let code = 'api_error'
  let details: unknown = null
  try {
    const body = await response.json()
    if (body && typeof body === 'object') {
      const record = body as Record<string, unknown>
      if (typeof record.message === 'string') message = record.message
      if (typeof record.code === 'string') code = record.code
      details = record.details ?? null
    }
  } catch {
    /* keep the default message */
  }
  return new ApiError(message, response.status, code, details)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(url(path), {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(init?.headers ?? {}),
      },
    })
  } catch (error) {
    throw new ApiError(
      error instanceof Error && error.name === 'AbortError'
        ? 'The request was cancelled.'
        : 'Cannot reach the NEXUS backend. Is it running on port 8000?',
      0,
      'network_error',
      error,
    )
  }
  if (!response.ok) throw await parseError(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  health: () => request<HealthResponse>('/api/health'),
  status: () => request<StatusResponse>('/api/status'),
  settings: () => request<SettingsResponse>('/api/settings'),
  models: () =>
    request<{ model: string; available: string[]; recommended: string[]; error?: string }>(
      '/api/models',
    ),

  listConversations: () => request<ConversationSummary[]>('/api/conversations'),
  getConversation: (id: string) => request<Conversation>(`/api/conversations/${id}`),
  createConversation: (title?: string) =>
    request<Conversation>('/api/conversations', {
      method: 'POST',
      body: JSON.stringify({ title: title ?? null }),
    }),
  renameConversation: (id: string, title: string) =>
    request<Conversation>(`/api/conversations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    }),
  deleteConversation: (id: string) =>
    request<{ deleted: boolean }>(`/api/conversations/${id}`, { method: 'DELETE' }),
  clearConversation: (id: string) =>
    request<Conversation>(`/api/conversations/${id}/messages`, { method: 'DELETE' }),

  listSavedSearches: () => request<SavedSearch[]>('/api/saved-searches'),
  addSavedSearch: (query: string, conversationId?: string) =>
    request<SavedSearch>('/api/saved-searches', {
      method: 'POST',
      body: JSON.stringify({ query, conversation_id: conversationId ?? null }),
    }),
  deleteSavedSearch: (id: string) =>
    request<{ deleted: boolean }>(`/api/saved-searches/${id}`, { method: 'DELETE' }),

  stopRun: (runId: string) =>
    request<{ run_id: string; stopped: boolean; detail: string }>('/api/chat/stop', {
      method: 'POST',
      body: JSON.stringify({ run_id: runId }),
    }),
}

/**
 * Open the SSE stream for a chat run.
 *
 * `EventSource` cannot issue POST requests, so the stream is consumed from a
 * `fetch` body and parsed with the standard SSE framing rules.
 */
export async function streamChat(
  payload: ChatRequest,
  handlers: {
    onEvent: (eventName: string, data: unknown) => void
    onError?: (error: Error) => void
    onClose?: () => void
  },
  signal?: AbortSignal,
): Promise<void> {
  let response: Response
  try {
    response = await fetch(url('/api/chat/stream'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify(payload),
      signal,
    })
  } catch (error) {
    if (signal?.aborted) {
      handlers.onClose?.()
      return
    }
    handlers.onError?.(
      new ApiError(
        'Cannot reach the NEXUS backend. Is it running on port 8000?',
        0,
        'network_error',
        error,
      ),
    )
    handlers.onClose?.()
    return
  }

  if (!response.ok || !response.body) {
    handlers.onError?.(await parseError(response))
    handlers.onClose?.()
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      let boundary = buffer.indexOf('\n\n')
      while (boundary !== -1) {
        const frame = buffer.slice(0, boundary)
        buffer = buffer.slice(boundary + 2)
        dispatchFrame(frame, handlers)
        boundary = buffer.indexOf('\n\n')
      }
    }
    if (buffer.trim()) dispatchFrame(buffer, handlers)
  } catch (error) {
    if (!signal?.aborted) {
      handlers.onError?.(
        error instanceof Error ? error : new Error('The agent stream was interrupted.'),
      )
    }
  } finally {
    try {
      reader.releaseLock()
    } catch {
      /* ignore */
    }
    handlers.onClose?.()
  }
}

function dispatchFrame(
  frame: string,
  handlers: { onEvent: (eventName: string, data: unknown) => void },
): void {
  let eventName = 'message'
  const dataLines: string[] = []

  for (const rawLine of frame.split('\n')) {
    const line = rawLine.replace(/\r$/, '')
    if (!line || line.startsWith(':')) continue
    if (line.startsWith('event:')) {
      eventName = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).replace(/^ /, ''))
    }
  }

  if (!dataLines.length) return
  const payload = dataLines.join('\n')
  try {
    handlers.onEvent(eventName, JSON.parse(payload))
  } catch {
    handlers.onEvent(eventName, payload)
  }
}
