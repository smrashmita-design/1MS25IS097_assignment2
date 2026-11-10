/** Shared types mirroring the backend contracts. */

export type AgentEventType =
  | 'agent_started'
  | 'planning'
  | 'tool_selected'
  | 'tool_call'
  | 'tool_started'
  | 'tool_result'
  | 'observation'
  | 'token'
  | 'final_answer'
  | 'agent_completed'
  | 'agent_error'
  | 'agent_cancelled'

export interface AgentEvent {
  id: string
  type: AgentEventType
  timestamp: string
  step: number
  title: string
  detail?: string | null
  data: Record<string, unknown>
}

export interface Source {
  title: string
  url: string
  snippet: string
  source: string
  domain: string
  rank: number
  published_at?: string | null
}

export type MessageStatus = 'pending' | 'streaming' | 'complete' | 'error' | 'cancelled'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  sources: Source[]
  events: AgentEvent[]
  iterations: number
  tool_calls: number
  duration_ms: number
  status: MessageStatus
  error?: string | null
  model: string
  provider: string
}

export interface Conversation {
  id: string
  title: string
  created_at: string
  updated_at: string
  messages: Message[]
  pinned: boolean
}

export interface ConversationSummary {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
  preview: string
}

export interface SavedSearch {
  id: string
  query: string
  created_at: string
  conversation_id?: string | null
  run_count: number
}

export interface ToolObservationResult {
  position?: number
  title: string
  url: string
  snippet: string
  domain: string
  published_at?: string | null
}

export interface ComponentStatus {
  name: string
  configured: boolean
  connected: boolean
  detail: string
  latency_ms?: number | null
}

export interface StatusResponse {
  status: string
  llm: ComponentStatus
  search: ComponentStatus
  model: string
  search_provider: string
  max_iterations: number
  max_search_results: number
  checked_at: string
}

export interface SettingsResponse {
  app_name: string
  app_version: string
  environment: string
  model: string
  search_provider: string
  search_providers_available: string[]
  max_agent_iterations: number
  max_search_results: number
  llm_timeout_seconds: number
  agent_request_timeout_seconds: number
  theme_options: string[]
  feature_flags: Record<string, boolean>
}

export interface HealthResponse {
  status: string
  app: string
  version: string
  environment: string
  uptime_seconds: number
}

export type ThemePreference = 'dark' | 'light' | 'system'

export interface ChatRequest {
  message: string
  conversation_id?: string | null
  run_id?: string | null
  max_iterations?: number | null
  save_search?: boolean
}
