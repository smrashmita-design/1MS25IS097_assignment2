import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  AlertCircle,
  CheckCircle2,
  Cpu,
  ExternalLink,
  Globe,
  KeyRound,
  Moon,
  Monitor,
  RefreshCw,
  Search,
  Sun,
} from 'lucide-react'
import clsx from 'clsx'
import { Button } from '@/components/ui/Button'
import { StatusDot, type DotTone } from '@/components/ui/StatusDot'
import { Spinner } from '@/components/ui/Spinner'
import { api } from '@/services/api'
import type { SettingsResponse, StatusResponse, ThemePreference } from '@/types'

interface SettingsPageProps {
  theme: ThemePreference
  onThemeChange: (theme: ThemePreference) => void
  onClose: () => void
}

interface ModelInfo {
  model: string
  available: string[]
  recommended: string[]
  error?: string
}

function StatusRow({
  icon: Icon,
  label,
  value,
  detail,
  tone,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string
  detail?: string
  tone: DotTone
}) {
  return (
    <div className="flex items-start gap-3 border-b border-hairline px-4 py-3.5 last:border-b-0">
      <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg border border-hairline bg-ink/[0.03]">
        <Icon className="size-3.5 text-ink-muted" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-[12px] font-medium uppercase tracking-[0.1em] text-ink-ghost">
            {label}
          </span>
          <StatusDot tone={tone} pulse={tone === 'positive'} />
        </div>
        <p className="mt-1 font-mono text-[13px] break-all text-ink">{value}</p>
        {detail ? (
          <p className="mt-1 text-[11.5px] leading-relaxed text-ink-faint">{detail}</p>
        ) : null}
      </div>
    </div>
  )
}

export function SettingsPage({ theme, onThemeChange, onClose }: SettingsPageProps) {
  const [settings, setSettings] = useState<SettingsResponse | null>(null)
  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [models, setModels] = useState<ModelInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const [settingsResult, statusResult, modelsResult] = await Promise.allSettled([
        api.settings(),
        api.status(),
        api.models(),
      ])
      if (settingsResult.status === 'fulfilled') setSettings(settingsResult.value)
      else setError(settingsResult.reason?.message ?? 'Could not load settings.')

      if (statusResult.status === 'fulfilled') setStatus(statusResult.value)

      if (modelsResult.status === 'fulfilled') setModels(modelsResult.value as ModelInfo)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const themeOptions: { value: ThemePreference; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
    { value: 'dark', label: 'Dark', icon: Moon },
    { value: 'light', label: 'Light', icon: Sun },
    { value: 'system', label: 'System', icon: Monitor },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 12 }}
      transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
      className="flex h-full min-h-0 flex-col"
    >
      <div className="flex items-center justify-between gap-3 border-b border-hairline px-5 py-3.5">
        <div>
          <h2 className="text-[15px] font-semibold text-ink">Settings</h2>
          <p className="mt-0.5 text-[11.5px] text-ink-ghost">
            Backend configuration and appearance. Secrets never leave the server.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => void load()} disabled={loading}>
            {loading ? <Spinner className="size-3.5" /> : <RefreshCw className="size-3.5" />}
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={onClose}>
            Done
          </Button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
        <div className="mx-auto max-w-2xl space-y-5">
          {error ? (
            <div className="flex items-start gap-2.5 rounded-panel border border-critical/25 bg-critical/[0.07] px-3.5 py-3">
              <AlertCircle className="mt-0.5 size-4 shrink-0 text-critical" />
              <p className="text-[12.5px] leading-relaxed text-ink-muted">{error}</p>
            </div>
          ) : null}

          <section className="overflow-hidden rounded-panel border border-hairline bg-surface/60">
            <div className="border-b border-hairline px-4 py-2.5">
              <h3 className="text-[12px] font-semibold tracking-[0.06em] text-ink">
                Connections
              </h3>
            </div>
            {loading && !status ? (
              <div className="space-y-3 px-4 py-4">
                {[0, 1, 2].map((index) => (
                  <div key={index} className="nx-shimmer h-9 rounded-field bg-ink/5" />
                ))}
              </div>
            ) : (
              <>
                <StatusRow
                  icon={Cpu}
                  label="LLM"
                  value={status?.llm.name ?? 'Google Gemini'}
                  detail={
                    status?.llm.detail ??
                    'Set GEMINI_API_KEY in backend/.env to enable the agent.'
                  }
                  tone={
                    status?.llm.connected
                      ? 'positive'
                      : status?.llm.configured
                        ? 'caution'
                        : 'critical'
                  }
                />
                <StatusRow
                  icon={Globe}
                  label="Search provider"
                  value={status?.search.name ?? 'Unknown'}
                  detail={status?.search.detail}
                  tone={
                    status?.search.connected
                      ? 'positive'
                      : status?.search.configured
                        ? 'caution'
                        : 'critical'
                  }
                />
                <StatusRow
                  icon={KeyRound}
                  label="Selected model"
                  value={settings?.model ?? status?.model ?? '—'}
                  detail={
                    models?.error
                      ? models.error
                      : models?.recommended?.length
                        ? `${models.recommended.length} compatible model${models.recommended.length === 1 ? '' : 's'} available on this key.`
                        : 'Model configured via GEMINI_MODEL.'
                  }
                  tone={status?.llm.connected ? 'positive' : 'idle'}
                />
              </>
            )}
          </section>

          <section className="overflow-hidden rounded-panel border border-hairline bg-surface/60">
            <div className="border-b border-hairline px-4 py-2.5">
              <h3 className="text-[12px] font-semibold tracking-[0.06em] text-ink">
                Agent behaviour
              </h3>
            </div>
            <div className="grid gap-px bg-hairline sm:grid-cols-2">
              <div className="bg-surface px-4 py-3.5">
                <p className="text-[11px] font-medium uppercase tracking-[0.1em] text-ink-ghost">
                  Max agent iterations
                </p>
                <p className="mt-1.5 font-mono text-[20px] leading-none tabular-nums text-ink">
                  {settings?.max_agent_iterations ?? '—'}
                </p>
                <p className="mt-2 text-[11.5px] leading-relaxed text-ink-faint">
                  The maximum number of reason → act → observe cycles per question.
                </p>
              </div>
              <div className="bg-surface px-4 py-3.5">
                <p className="text-[11px] font-medium uppercase tracking-[0.1em] text-ink-ghost">
                  Results per search
                </p>
                <p className="mt-1.5 font-mono text-[20px] leading-none tabular-nums text-ink">
                  {settings?.max_search_results ?? '—'}
                </p>
                <p className="mt-2 text-[11.5px] leading-relaxed text-ink-faint">
                  How many sources each tool call returns to the model.
                </p>
              </div>
              <div className="bg-surface px-4 py-3.5">
                <p className="text-[11px] font-medium uppercase tracking-[0.1em] text-ink-ghost">
                  Search backend
                </p>
                <p className="mt-1.5 font-mono text-[14px] leading-none text-ink">
                  {settings?.search_provider ?? '—'}
                </p>
                <p className="mt-2 text-[11.5px] leading-relaxed text-ink-faint">
                  Available: {(settings?.search_providers_available ?? []).join(', ') || '—'}.
                </p>
              </div>
              <div className="bg-surface px-4 py-3.5">
                <p className="text-[11px] font-medium uppercase tracking-[0.1em] text-ink-ghost">
                  Request timeout
                </p>
                <p className="mt-1.5 font-mono text-[14px] leading-none text-ink">
                  {settings?.agent_request_timeout_seconds ?? '—'}s
                </p>
                <p className="mt-2 text-[11.5px] leading-relaxed text-ink-faint">
                  Upper bound for a complete research run.
                </p>
              </div>
            </div>
          </section>

          <section className="overflow-hidden rounded-panel border border-hairline bg-surface/60">
            <div className="border-b border-hairline px-4 py-2.5">
              <h3 className="text-[12px] font-semibold tracking-[0.06em] text-ink">Appearance</h3>
            </div>
            <div className="p-4">
              <div className="grid grid-cols-3 gap-2">
                {themeOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => onThemeChange(option.value)}
                    className={clsx(
                      'flex flex-col items-center gap-2 rounded-field border px-3 py-3 transition-all duration-150',
                      theme === option.value
                        ? 'border-accent/40 bg-accent-soft text-ink'
                        : 'border-hairline bg-ink/[0.02] text-ink-muted hover:border-hairline-strong hover:text-ink',
                    )}
                  >
                    <option.icon className="size-4" />
                    <span className="text-[12px] font-medium">{option.label}</span>
                    {theme === option.value ? (
                      <CheckCircle2 className="size-3.5 text-accent" />
                    ) : (
                      <span className="size-3.5" />
                    )}
                  </button>
                ))}
              </div>
            </div>
          </section>

          <section className="overflow-hidden rounded-panel border border-hairline bg-surface/60">
            <div className="border-b border-hairline px-4 py-2.5">
              <h3 className="text-[12px] font-semibold tracking-[0.06em] text-ink">
                Available Gemini models
              </h3>
            </div>
            <div className="max-h-56 overflow-y-auto px-4 py-3">
              {models?.error ? (
                <p className="text-[12px] text-ink-faint">{models.error}</p>
              ) : models?.available?.length ? (
                <ul className="space-y-1">
                  {models.available.map((model) => (
                    <li key={model}>
                      <div className="flex items-center gap-2 rounded px-1.5 py-1 hover:bg-ink/[0.03]">
                        <Search className="size-3 shrink-0 text-ink-ghost" />
                        <span className="min-w-0 flex-1 truncate font-mono text-[11.5px] text-ink-muted">
                          {model}
                        </span>
                        {model === settings?.model ? (
                          <span className="rounded border border-accent/30 bg-accent-soft px-1.5 py-px text-[9.5px] font-medium text-accent">
                            active
                          </span>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-[12px] text-ink-faint">
                  No model list available — the API key may be missing.
                </p>
              )}
            </div>
          </section>

          <p className="pb-2 text-center text-[11px] leading-relaxed text-ink-ghost">
            Secrets are read from the backend environment and are never returned by the API.
            <br />
            <a
              href="https://aistudio.google.com/apikey"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-ink-faint underline underline-offset-2 transition-colors hover:text-ink-muted"
            >
              Get a Gemini API key
              <ExternalLink className="size-3" />
            </a>
          </p>
        </div>
      </div>
    </motion.div>
  )
}
