import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowUpRight, Globe } from 'lucide-react'
import clsx from 'clsx'
import type { Source } from '@/types'

function Favicon({ domain, title }: { domain: string; title: string }) {
  const [failed, setFailed] = useState(false)
  const initial = (title || domain || '?').trim().charAt(0).toUpperCase()

  if (!domain || failed) {
    return (
      <span className="flex size-6 shrink-0 items-center justify-center rounded-md border border-hairline bg-ink/5 text-[10px] font-semibold text-ink-faint">
        {initial}
      </span>
    )
  }

  return (
    <img
      src={`https://icons.duckduckgo.com/ip3/${domain}.ico`}
      alt=""
      loading="lazy"
      width={16}
      height={16}
      className="size-6 shrink-0 rounded-md border border-hairline bg-white/90 object-contain p-0.5"
      onError={() => setFailed(true)}
    />
  )
}

function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url.slice(0, 40)
  }
}

/** Citation chips rendered under an assistant answer. */
export function SourceList({
  sources,
  expanded = false,
  onToggle,
}: {
  sources: Source[]
  expanded?: boolean
  onToggle?: () => void
}) {
  if (!sources.length) return null

  const visible = expanded ? sources : sources.slice(0, 4)
  const hidden = sources.length - visible.length

  return (
    <div className="mt-4">
      <div className="mb-2 flex items-center gap-2">
        <Globe className="size-3.5 text-ink-ghost" />
        <span className="text-[11px] font-medium uppercase tracking-[0.13em] text-ink-ghost">
          Sources
        </span>
        <span className="rounded-full border border-hairline px-1.5 py-px text-[10.5px] font-medium tabular-nums text-ink-faint">
          {sources.length}
        </span>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {visible.map((source, index) => (
          <motion.a
            key={source.url}
            href={source.url}
            target="_blank"
            rel="noopener noreferrer nofollow"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(index * 0.04, 0.3), duration: 0.22 }}
            className="group/src inline-flex max-w-full items-center gap-2 rounded-field border border-hairline bg-ink/[0.035] py-1 pr-2 pl-1.5 text-[12px] text-ink-muted transition-colors hover:border-hairline-strong hover:bg-ink/[0.06] hover:text-ink"
            title={source.title}
          >
            <Favicon domain={source.domain || hostOf(source.url)} title={source.title} />
            <span className="max-w-[190px] truncate">{source.domain || hostOf(source.url)}</span>
            <ArrowUpRight className="size-3 shrink-0 opacity-0 transition-opacity group-hover/src:opacity-70" />
          </motion.a>
        ))}

        {hidden > 0 && onToggle ? (
          <button
            type="button"
            onClick={onToggle}
            className="rounded-field border border-dashed border-hairline-strong px-2.5 py-1 text-[12px] text-ink-faint transition-colors hover:border-ink/25 hover:text-ink-muted"
          >
            +{hidden} more
          </button>
        ) : null}
      </div>
    </div>
  )
}

/** A full, scrollable list of the cited sources. */
export function SourceCards({ sources }: { sources: Source[] }) {
  if (!sources.length) return null

  return (
    <div className="grid gap-2 sm:grid-cols-2">
      <AnimatePresence initial={false}>
        {sources.map((source, index) => (
          <motion.a
            key={source.url}
            href={source.url}
            target="_blank"
            rel="noopener noreferrer nofollow"
            layout
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(index * 0.03, 0.25), duration: 0.24 }}
            className="group/card flex flex-col gap-1.5 rounded-panel border border-hairline bg-elevated/60 p-3 transition-colors hover:border-hairline-strong hover:bg-elevated"
          >
            <div className="flex items-start gap-2">
              <Favicon domain={source.domain || hostOf(source.url)} title={source.title} />
              <span className="min-w-0 flex-1 text-[12.5px] font-medium leading-snug text-ink line-clamp-2">
                {source.title}
              </span>
              <ArrowUpRight className="mt-0.5 size-3.5 shrink-0 text-ink-ghost transition-colors group-hover/card:text-ink-muted" />
            </div>
            <span className="truncate font-mono text-[10.5px] text-ink-ghost">
              {source.domain || hostOf(source.url)}
            </span>
            {source.snippet ? (
              <p className={clsx('text-[11.5px] leading-relaxed text-ink-faint line-clamp-2')}>
                {source.snippet}
              </p>
            ) : null}
          </motion.a>
        ))}
      </AnimatePresence>
    </div>
  )
}
