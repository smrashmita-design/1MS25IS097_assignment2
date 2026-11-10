import { ExternalLink, FileSearch, TriangleAlert } from 'lucide-react'
import clsx from 'clsx'
import type { ToolObservationResult } from '@/types'

function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url.slice(0, 48)
  }
}

/**
 * The observable output of a tool call.
 *
 * This renders the *actual* results returned by the search backend — never a
 * simulation — so the user can audit exactly what the agent saw.
 */
export function ToolResultCard({
  results,
  ok,
  error,
  durationMs,
}: {
  results: ToolObservationResult[]
  ok: boolean
  error?: string | null
  durationMs?: number
}) {
  if (!ok) {
    return (
      <div className="flex items-start gap-2.5 rounded-field border border-critical/25 bg-critical/[0.07] px-3 py-2.5">
        <TriangleAlert className="mt-0.5 size-3.5 shrink-0 text-critical" />
        <div className="min-w-0">
          <p className="text-[11.5px] font-medium text-critical">Tool execution failed</p>
          <p className="mt-0.5 text-[11.5px] leading-relaxed break-words text-ink-muted">
            {error ?? 'The tool reported an error.'}
          </p>
        </div>
      </div>
    )
  }

  if (!results.length) {
    return (
      <div className="rounded-field border border-hairline bg-ink/[0.03] px-3 py-2.5 text-[11.5px] text-ink-faint">
        The tool returned no results.
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-field border border-hairline bg-canvas/45">
      <div className="flex items-center gap-2 border-b border-hairline px-2.5 py-1.5">
        <FileSearch className="size-3 text-ink-ghost" />
        <span className="text-[10.5px] font-medium uppercase tracking-[0.12em] text-ink-ghost">
          Observed sources
        </span>
        <span className="ml-auto font-mono text-[10px] tabular-nums text-ink-ghost">
          {results.length}
          {durationMs ? ` · ${durationMs}ms` : ''}
        </span>
      </div>
      <ul className="divide-y divide-hairline">
        {results.map((result, index) => (
          <li key={`${result.url}-${index}`}>
            <a
              href={result.url}
              target="_blank"
              rel="noopener noreferrer nofollow"
              className="group/res flex items-start gap-2.5 px-2.5 py-2 transition-colors hover:bg-ink/[0.04]"
            >
              <span className="mt-0.5 w-4 shrink-0 text-right font-mono text-[10px] tabular-nums text-ink-ghost">
                {result.position ?? index + 1}
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-start gap-1.5">
                  <span className="line-clamp-2 flex-1 text-[11.5px] leading-snug font-medium text-ink-muted transition-colors group-hover/res:text-ink">
                    {result.title}
                  </span>
                  <ExternalLink className="mt-0.5 size-3 shrink-0 text-ink-ghost opacity-0 transition-opacity group-hover/res:opacity-70" />
                </span>
                <span className="mt-0.5 block truncate font-mono text-[10px] text-ink-ghost">
                  {result.domain || hostOf(result.url)}
                </span>
                {result.snippet ? (
                  <span className="mt-1 block text-[11px] leading-relaxed text-ink-faint line-clamp-2">
                    {result.snippet}
                  </span>
                ) : null}
              </span>
            </a>
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Renders the JSON arguments a tool was called with. */
export function ToolArguments({ args }: { args: Record<string, unknown> }) {
  const entries = Object.entries(args ?? {})
  if (!entries.length) {
    return (
      <p className="text-[11.5px] text-ink-faint">No arguments were supplied.</p>
    )
  }

  return (
    <dl className="space-y-1.5 rounded-field border border-hairline bg-canvas/45 px-2.5 py-2">
      {entries.map(([key, value]) => (
        <div key={key} className="flex flex-col gap-0.5 sm:flex-row sm:gap-3">
          <dt className="shrink-0 font-mono text-[10.5px] text-ink-ghost sm:w-28">{key}</dt>
          <dd
            className={clsx(
              'min-w-0 flex-1 font-mono text-[11px] break-words text-ink-muted',
              typeof value === 'string' ? 'font-sans text-[11.5px]' : '',
            )}
          >
            {typeof value === 'string' ? value : JSON.stringify(value)}
          </dd>
        </div>
      ))}
    </dl>
  )
}
