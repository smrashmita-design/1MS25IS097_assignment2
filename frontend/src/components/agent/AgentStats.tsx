import { useMemo } from 'react'
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from 'recharts'
import clsx from 'clsx'
import type { AgentEvent } from '@/types'

interface MetricProps {
  label: string
  value: string
  tone?: 'default' | 'accent'
}

function Metric({ label, value, tone = 'default' }: MetricProps) {
  return (
    <div className="min-w-0">
      <p
        className={clsx(
          'font-mono text-[15px] leading-none font-medium tabular-nums',
          tone === 'accent' ? 'text-accent' : 'text-ink',
        )}
      >
        {value}
      </p>
      <p className="mt-1.5 truncate text-[10px] font-medium uppercase tracking-[0.11em] text-ink-ghost">
        {label}
      </p>
    </div>
  )
}

interface AgentStatsProps {
  iterations: number
  toolCalls: number
  sources: number
  durationMs: number
  events: AgentEvent[]
}

/**
 * Run statistics for the agent, including a chart of how long each stage took.
 *
 * The chart is derived from the real event timestamps emitted by the backend.
 */
export function AgentStats({
  iterations,
  toolCalls,
  sources,
  durationMs,
  events,
}: AgentStatsProps) {
  const chartData = useMemo(() => {
    const parsed = events
      .map((event) => new Date(event.timestamp).getTime())
      .filter((value) => !Number.isNaN(value))
    if (parsed.length < 2) return []

    const start = parsed[0]
    const buckets = new Map<number, number>()

    parsed.forEach((time) => {
      const bucket = Math.floor((time - start) / 1000)
      buckets.set(bucket, (buckets.get(bucket) ?? 0) + 1)
    })

    return [...buckets.entries()].map(([second, count]) => ({
      second: `${second}s`,
      steps: count,
    }))
  }, [events])

  const hasData = iterations > 0 || toolCalls > 0 || sources > 0

  return (
    <div className="border-t border-hairline px-4 py-3">
      <div className="grid grid-cols-4 gap-3">
        <Metric label="Iterations" value={String(iterations)} tone={iterations ? 'accent' : 'default'} />
        <Metric label="Tool calls" value={String(toolCalls)} />
        <Metric label="Sources" value={String(sources)} />
        <Metric
          label="Duration"
          value={durationMs ? `${(durationMs / 1000).toFixed(1)}s` : '—'}
        />
      </div>

      {hasData && chartData.length > 1 ? (
        <div className="mt-3.5">
          <p className="mb-1.5 text-[10px] font-medium uppercase tracking-[0.11em] text-ink-ghost">
            Steps per second
          </p>
          <div className="h-16 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
                <XAxis
                  dataKey="second"
                  tick={{ fill: 'var(--nx-ink-ghost)', fontSize: 9 }}
                  axisLine={false}
                  tickLine={false}
                  interval="preserveStartEnd"
                />
                <YAxis hide allowDecimals={false} />
                <RechartsTooltip
                  cursor={{ fill: 'var(--nx-ink)', fillOpacity: 0.04 }}
                  contentStyle={{
                    background: 'var(--nx-overlay)',
                    border: '1px solid var(--nx-hairline)',
                    borderRadius: 10,
                    fontSize: 11,
                    color: 'var(--nx-ink)',
                    boxShadow: 'var(--shadow-float)',
                  }}
                  labelStyle={{ color: 'var(--nx-ink-faint)', fontSize: 10 }}
                  formatter={(value) => [`${value} step${value === 1 ? '' : 's'}`]}
                />
                <Bar dataKey="steps" radius={[3, 3, 0, 0]} isAnimationActive={false}>
                  {chartData.map((_entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={
                        index === chartData.length - 1 ? 'var(--nx-accent)' : 'var(--nx-electric)'
                      }
                      fillOpacity={index === chartData.length - 1 ? 0.9 : 0.42}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : null}
    </div>
  )
}
