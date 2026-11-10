import { motion } from 'framer-motion'
import { Bookmark, Menu, Moon, PanelRightClose, PanelRightOpen, Sun } from 'lucide-react'
import clsx from 'clsx'
import { StatusDot, type DotTone } from '@/components/ui/StatusDot'
import { Button } from '@/components/ui/Button'
import type { StatusResponse, ThemePreference } from '@/types'

interface TopBarProps {
  title: string
  status: StatusResponse | null
  statusError: string | null
  theme: ThemePreference
  onToggleTheme: () => void
  onOpenSidebar: () => void
  panelOpen: boolean
  onTogglePanel: () => void
  onSaveSearch: () => void
  canSave: boolean
}

export function TopBar({
  title,
  status,
  statusError,
  theme,
  onToggleTheme,
  onOpenSidebar,
  panelOpen,
  onTogglePanel,
  onSaveSearch,
  canSave,
}: TopBarProps) {
  const tone: DotTone = statusError
    ? 'critical'
    : status?.llm.connected && status?.search.connected
      ? 'positive'
      : status
        ? 'caution'
        : 'idle'

  const label = statusError
    ? 'Backend offline'
    : status
      ? status.status === 'operational'
        ? 'All systems operational'
        : 'Degraded'
      : 'Connecting…'

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-hairline bg-canvas-soft/60 px-3 backdrop-blur-xl sm:px-4">
      <button
        type="button"
        onClick={onOpenSidebar}
        aria-label="Open sidebar"
        className="flex size-8 items-center justify-center rounded-lg text-ink-muted transition-colors hover:bg-ink/6 lg:hidden"
      >
        <Menu className="size-4.5" />
      </button>

      <div className="min-w-0 flex-1">
        <h1 className="truncate text-[13.5px] font-semibold text-ink">{title}</h1>
        <div className="mt-0.5 flex items-center gap-1.5">
          <StatusDot tone={tone} pulse={tone === 'positive'} />
          <span className="truncate text-[11px] text-ink-ghost">{label}</span>
        </div>
      </div>

      <div className="flex items-center gap-1.5">
        {canSave ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={onSaveSearch}
            className="hidden sm:inline-flex"
            title="Save this search"
          >
            <Bookmark className="size-3.5" />
            Save
          </Button>
        ) : null}

        <button
          type="button"
          onClick={onToggleTheme}
          aria-label="Toggle colour theme"
          className="relative flex size-8 items-center justify-center rounded-lg text-ink-muted transition-colors hover:bg-ink/6 hover:text-ink"
        >
          <motion.span
            key={theme}
            initial={{ opacity: 0, rotate: -35, scale: 0.8 }}
            animate={{ opacity: 1, rotate: 0, scale: 1 }}
            transition={{ duration: 0.24 }}
            className="flex items-center justify-center"
          >
            {theme === 'light' ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </motion.span>
        </button>

        <button
          type="button"
          onClick={onTogglePanel}
          aria-label={panelOpen ? 'Hide execution panel' : 'Show execution panel'}
          title={panelOpen ? 'Hide execution panel' : 'Show execution panel'}
          className={clsx(
            'flex size-8 items-center justify-center rounded-lg transition-colors hover:bg-ink/6',
            panelOpen ? 'text-accent' : 'text-ink-muted hover:text-ink',
          )}
        >
          {panelOpen ? <PanelRightClose className="size-4" /> : <PanelRightOpen className="size-4" />}
        </button>
      </div>
    </header>
  )
}
