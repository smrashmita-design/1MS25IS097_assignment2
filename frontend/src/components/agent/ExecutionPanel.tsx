import { useMemo } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  BrainCircuit,
  CheckCircle2,
  CircleDashed,
  Eye,
  FileSearch,
  Inbox,
  Radio,
  Sparkles,
  SquareFunction,
  TriangleAlert,
  Wrench,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { TimelineStep, type StepTone } from '@/components/agent/TimelineStep'
import { ToolArguments, ToolResultCard } from '@/components/agent/ToolResultCard'
import { AgentStats } from '@/components/agent/AgentStats'
import type { AgentEvent, ToolObservationResult } from '@/types'

interface Presentation {
  icon: LucideIcon
  tone: StepTone
}

const PRESENTATION: Record<string, Presentation> = {
  agent_started: { icon: Inbox, tone: 'neutral' },
  planning: { icon: BrainCircuit, tone: 'accent' },
  tool_selected: { icon: Wrench, tone: 'electric' },
  tool_call: { icon: SquareFunction, tone: 'electric' },
  tool_started: { icon: Radio, tone: 'signal' },
  tool_result: { icon: FileSearch, tone: 'signal' },
  observation: { icon: Eye, tone: 'accent' },
  final_answer: { icon: Sparkles, tone: 'positive' },
  agent_completed: { icon: CheckCircle2, tone: 'positive' },
  agent_error: { icon: TriangleAlert, tone: 'critical' },
  agent_cancelled: { icon: CircleDashed, tone: 'caution' },
}

function extractResults(data: Record<string, unknown>): ToolObservationResult[] {
  const results = (data as { results?: unknown }).results
  return Array.isArray(results) ? (results as ToolObservationResult[]) : []
}

/**
 * The live execution timeline.
 *
 * Renders every stage of the ReAct cycle exactly as it happened on the backend:
 * reasoning, tool selection, the real search, the observations and the final
 * response. No step is simulated.
 */
export function ExecutionPanel({
  events,
  running,
  streamingText,
  error,
}: {
  events: AgentEvent[]
  running: boolean
  streamingText?: string
  error?: string | null
}) {
  const visible = useMemo(
    () => events.filter((event) => event.type !== 'token'),
    [events],
  )

  const tokenCount = useMemo(
    () => events.filter((event) => event.type === 'token').length,
    [events],
  )

  const toolResults = useMemo(
    () => events.filter((event) => event.type === 'tool_result'),
    [events],
  )

  const sourceCount = useMemo(() => {
    const urls = new Set<string>()
    toolResults.forEach((event) =>
      extractResults(event.data).forEach((result) => {
        if (result.url) urls.add(result.url)
      }),
    )
    return urls.size
  }, [toolResults])

  const iterations = useMemo(() => {
    const values = events
      .map((event) => (event.data as { iteration?: number }).iteration)
      .filter((value): value is number => typeof value === 'number')
    return values.length ? Math.max(...values) : 0
  }, [events])

  const totalDuration = useMemo(() => {
    const explicit = events
      .map((event) => (event.data as { duration_ms?: number }).duration_ms)
      .filter((value): value is number => typeof value === 'number')
    if (explicit.length) return explicit[explicit.length - 1]
    return 0
  }, [events])

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center justify-between gap-3 border-b border-hairline px-4 py-3">
        <div className="min-w-0">
          <h2 className="text-[12.5px] font-semibold tracking-[0.04em] text-ink">
            Agent execution
          </h2>
          <p className="mt-0.5 text-[11px] text-ink-ghost">
            {running
              ? 'Live ReAct trace'
              : visible.length
                ? `${visible.length} steps · ${iterations} iteration${iterations === 1 ? '' : 's'}`
                : 'Waiting for a query'}
          </p>
        </div>
        {running ? (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-accent/25 bg-accent-soft px-2 py-1 text-[10.5px] font-medium text-accent">
            <span className="nx-breathe size-1.5 rounded-full bg-accent" />
            running
          </span>
        ) : null}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
        {visible.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center px-4 text-center">
            <span className="mb-3 flex size-10 items-center justify-center rounded-xl border border-hairline bg-ink/[0.03]">
              <CircleDashed className="size-4 text-ink-ghost" />
            </span>
            <p className="text-[12.5px] font-medium text-ink-muted">No execution yet</p>
            <p className="mt-1 text-[11.5px] leading-relaxed text-ink-ghost">
              Ask a question and every stage of the agent's reasoning, tool calls and
              observations will appear here in real time.
            </p>
          </div>
        ) : (
          <div className="relative">
            {visible.map((event, index) => {
              const presentation = PRESENTATION[event.type] ?? {
                icon: CircleDashed,
                tone: 'neutral' as StepTone,
              }
              const isLast = index === visible.length - 1
              const status =
                event.type === 'agent_error'
                  ? 'error'
                  : running && isLast
                    ? 'active'
                    : 'complete'

              const results = extractResults(event.data)
              const args = (event.data as { args?: Record<string, unknown> }).args

              const details =
                event.type === 'tool_result' ? (
                  <ToolResultCard
                    results={results}
                    ok={Boolean((event.data as { ok?: boolean }).ok)}
                    error={(event.data as { error?: string | null }).error ?? null}
                    durationMs={(event.data as { duration_ms?: number }).duration_ms}
                  />
                ) : event.type === 'tool_call' || event.type === 'tool_selected' ? (
                  args ? <ToolArguments args={args} /> : null
                ) : event.type === 'agent_started' ? (
                  <ToolArguments
                    args={{
                      model: (event.data as { model?: string }).model ?? '—',
                      search_provider:
                        (event.data as { search_provider?: string }).search_provider ?? '—',
                      tools: ((event.data as { tools?: string[] }).tools ?? []).join(', ') || '—',
                    }}
                  />
                ) : null

              return (
                <div key={event.id} className="relative">
                  {!isLast ? (
                    <span className="absolute top-5 bottom-0 left-2.5 w-px bg-ink/10" />
                  ) : null}
                  <TimelineStep
                    event={event}
                    status={status}
                    icon={presentation.icon}
                    tone={presentation.tone}
                    details={details}
                    defaultOpen={
                      event.type === 'tool_result' && results.length > 0 && running
                    }
                  />
                </div>
              )
            })}

            <AnimatePresence>
              {running ? (
                <motion.div
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="relative pl-8"
                >
                  <span className="absolute top-0.5 left-0 flex size-5 items-center justify-center rounded-full border border-accent/30 bg-accent-soft">
                    <span className="absolute inset-0 animate-ping rounded-full bg-accent opacity-25" />
                    <Sparkles className="relative size-2.5 text-accent" />
                  </span>
                  <div className="pb-4">
                    <p className="text-[12.5px] font-medium text-ink">
                      {streamingText ? 'Writing the final response…' : 'Working…'}
                    </p>
                    <p className="mt-0.5 text-[11.5px] text-ink-ghost">
                      {tokenCount > 0
                        ? `${tokenCount} streamed chunk${tokenCount === 1 ? '' : 's'}`
                        : 'Waiting for the model'}
                    </p>
                    {streamingText ? (
                      <p className="mt-1.5 line-clamp-3 text-[11.5px] leading-relaxed text-ink-faint">
                        {streamingText.slice(-260)}
                      </p>
                    ) : null}
                  </div>
                </motion.div>
              ) : null}
            </AnimatePresence>
          </div>
        )}

        {error ? (
          <div className="mt-3 flex items-start gap-2.5 rounded-field border border-critical/25 bg-critical/[0.07] px-3 py-2.5">
            <TriangleAlert className="mt-0.5 size-3.5 shrink-0 text-critical" />
            <p className="text-[11.5px] leading-relaxed text-ink-muted">{error}</p>
          </div>
        ) : null}
      </div>

      <AgentStats
        iterations={iterations}
        toolCalls={toolResults.length}
        sources={sourceCount}
        durationMs={totalDuration}
        events={visible}
      />
    </div>
  )
}
