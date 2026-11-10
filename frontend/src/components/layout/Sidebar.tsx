import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  ChevronLeft,
  Pencil,
  Plus,
  Search,
  Settings,
  Trash2,
  X,
} from 'lucide-react'
import clsx from 'clsx'
import { Logo, Wordmark } from '@/components/ui/Logo'
import { StatusDot, type DotTone } from '@/components/ui/StatusDot'
import { Button } from '@/components/ui/Button'
import type { ConversationSummary, SavedSearch, StatusResponse } from '@/types'

interface SidebarProps {
  conversations: ConversationSummary[]
  savedSearches: SavedSearch[]
  activeId: string | null
  collapsed: boolean
  onToggleCollapse: () => void
  onNewChat: () => void
  onSelect: (id: string) => void
  onRename: (id: string, title: string) => void
  onDelete: (id: string) => void
  onUseSavedSearch: (query: string) => void
  onDeleteSavedSearch: (id: string) => void
  onOpenSettings: () => void
  status: StatusResponse | null
  statusError: string | null
}

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return ''
  const seconds = Math.floor((Date.now() - then) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return new Date(iso).toLocaleDateString([], { month: 'short', day: 'numeric' })
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-ghost">
      {children}
    </p>
  )
}

export function Sidebar({
  conversations,
  savedSearches,
  activeId,
  collapsed,
  onToggleCollapse,
  onNewChat,
  onSelect,
  onRename,
  onDelete,
  onUseSavedSearch,
  onDeleteSavedSearch,
  onOpenSettings,
  status,
  statusError,
}: SidebarProps) {
  const [editing, setEditing] = useState<string | null>(null)
  const [draft, setDraft] = useState('')

  const llmTone: DotTone = statusError
    ? 'critical'
    : status?.llm.connected
      ? 'positive'
      : status?.llm.configured
        ? 'caution'
        : 'idle'

  const searchTone: DotTone = statusError
    ? 'critical'
    : status?.search.connected
      ? 'positive'
      : status?.search.configured
        ? 'caution'
        : 'idle'

  const commitRename = (id: string) => {
    const title = draft.trim()
    if (title) onRename(id, title)
    setEditing(null)
    setDraft('')
  }

  return (
    <motion.aside
      animate={{ width: collapsed ? 62 : 272 }}
      initial={false}
      transition={{ type: 'spring', stiffness: 320, damping: 34 }}
      className="relative z-20 flex h-full shrink-0 flex-col border-r border-hairline bg-canvas-soft/80 backdrop-blur-xl"
    >
      {/* ---------------------------------------------------------- header */}
      <div className="flex h-14 shrink-0 items-center gap-2 border-b border-hairline px-3">
        {collapsed ? (
          <button
            type="button"
            onClick={onToggleCollapse}
            aria-label="Expand sidebar"
            className="mx-auto flex size-8 items-center justify-center rounded-lg transition-colors hover:bg-ink/6"
          >
            <Logo className="size-6" />
          </button>
        ) : (
          <>
            <Wordmark />
            <button
              type="button"
              onClick={onToggleCollapse}
              aria-label="Collapse sidebar"
              className="ml-auto flex size-7 items-center justify-center rounded-md text-ink-ghost transition-colors hover:bg-ink/6 hover:text-ink-muted"
            >
              <ChevronLeft className="size-4" />
            </button>
          </>
        )}
      </div>

      {/* -------------------------------------------------------- new chat */}
      <div className={clsx('shrink-0 px-3 pt-3 pb-1', collapsed && 'px-2.5')}>
        {collapsed ? (
          <button
            type="button"
            onClick={onNewChat}
            aria-label="New research"
            className="mx-auto flex size-9 items-center justify-center rounded-field border border-hairline bg-ink/[0.04] text-ink-muted transition-colors hover:border-accent/35 hover:bg-accent-soft hover:text-accent"
          >
            <Plus className="size-4" />
          </button>
        ) : (
          <Button
            onClick={onNewChat}
            variant="secondary"
            size="md"
            className="w-full justify-start hover:border-accent/30"
          >
            <Plus className="size-4" />
            New research
          </Button>
        )}
      </div>

      {/* ---------------------------------------------------------- lists */}
      <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-2.5 py-3">
        {!collapsed ? (
          <section className="mb-4">
            <SectionLabel>Recent conversations</SectionLabel>
            {conversations.length === 0 ? (
              <p className="px-2 py-1.5 text-[11.5px] leading-relaxed text-ink-ghost">
                Your research sessions will appear here.
              </p>
            ) : (
              <ul className="space-y-0.5">
                <AnimatePresence initial={false}>
                  {conversations.map((conversation) => {
                    const isActive = conversation.id === activeId
                    const isEditing = editing === conversation.id
                    return (
                      <motion.li
                        key={conversation.id}
                        layout
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="relative"
                      >
                        <div
                          className={clsx(
                            'group/item flex items-center gap-2 rounded-field px-2 py-1.5 transition-colors',
                            isActive ? 'bg-ink/[0.07]' : 'hover:bg-ink/[0.04]',
                          )}
                        >
                          <button
                            type="button"
                            onClick={() => onSelect(conversation.id)}
                            className="min-w-0 flex-1 text-left"
                          >
                            {isEditing ? (
                              <input
                                autoFocus
                                value={draft}
                                onChange={(event) => setDraft(event.target.value)}
                                onBlur={() => commitRename(conversation.id)}
                                onKeyDown={(event) => {
                                  if (event.key === 'Enter') commitRename(conversation.id)
                                  if (event.key === 'Escape') setEditing(null)
                                }}
                                onClick={(event) => event.stopPropagation()}
                                className="w-full rounded border border-hairline-strong bg-canvas px-1.5 py-0.5 text-[12.5px] text-ink outline-none"
                              />
                            ) : (
                              <>
                                <span
                                  className={clsx(
                                    'block truncate text-[12.5px] transition-colors',
                                    isActive ? 'text-ink' : 'text-ink-muted group-hover/item:text-ink',
                                  )}
                                >
                                  {conversation.title}
                                </span>
                                <span className="mt-0.5 block truncate text-[10.5px] text-ink-ghost">
                                  {conversation.message_count} message
                                  {conversation.message_count === 1 ? '' : 's'} ·{' '}
                                  {relativeTime(conversation.updated_at)}
                                </span>
                              </>
                            )}
                          </button>

                          {!isEditing ? (
                            <div className="flex items-center opacity-0 transition-opacity group-hover/item:opacity-100 focus-within:opacity-100">
                              <button
                                type="button"
                                aria-label="Rename conversation"
                                onClick={() => {
                                  setEditing(conversation.id)
                                  setDraft(conversation.title)
                                }}
                                className="rounded p-1 text-ink-ghost transition-colors hover:text-ink-muted"
                              >
                                <Pencil className="size-3" />
                              </button>
                              <button
                                type="button"
                                aria-label="Delete conversation"
                                onClick={() => {
                                  onDelete(conversation.id)
                                }}
                                className="rounded p-1 text-ink-ghost transition-colors hover:text-critical"
                              >
                                <Trash2 className="size-3" />
                              </button>
                            </div>
                          ) : null}
                        </div>
                      </motion.li>
                    )
                  })}
                </AnimatePresence>
              </ul>
            )}
          </section>
        ) : null}

        {!collapsed ? (
          <section className="mb-4">
            <SectionLabel>Agent activity</SectionLabel>
            <ul className="space-y-1">
              {conversations.slice(0, 4).map((conversation) => (
                <li key={conversation.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(conversation.id)}
                    className="flex w-full items-center gap-2 rounded-field px-2 py-1 text-left transition-colors hover:bg-ink/[0.04]"
                  >
                    <span className="flex size-4 shrink-0 items-center justify-center">
                      <StatusDot tone={conversation.message_count ? 'positive' : 'idle'} />
                    </span>
                    <span className="min-w-0 flex-1 truncate text-[11.5px] text-ink-faint">
                      {conversation.preview || conversation.title}
                    </span>
                  </button>
                </li>
              ))}
              {conversations.length === 0 ? (
                <li className="px-2 py-1 text-[11.5px] text-ink-ghost">No runs recorded yet.</li>
              ) : null}
            </ul>
          </section>
        ) : null}

        {!collapsed ? (
          <section className="mb-4">
            <SectionLabel>Saved searches</SectionLabel>
            {savedSearches.length === 0 ? (
              <p className="px-2 py-1.5 text-[11.5px] leading-relaxed text-ink-ghost">
                Save a query to reuse it later.
              </p>
            ) : (
              <ul className="space-y-0.5">
                {savedSearches.map((search) => (
                  <li
                    key={search.id}
                    className="group/saved flex items-center gap-2 rounded-field px-2 py-1.5 transition-colors hover:bg-ink/[0.04]"
                  >
                    <button
                      type="button"
                      onClick={() => onUseSavedSearch(search.query)}
                      className="flex min-w-0 flex-1 items-center gap-2 text-left"
                    >
                      <Search className="size-3 shrink-0 text-ink-ghost" />
                      <span className="min-w-0 flex-1 truncate text-[11.5px] text-ink-muted">
                        {search.query}
                      </span>
                    </button>
                    <button
                      type="button"
                      aria-label="Remove saved search"
                      onClick={() => onDeleteSavedSearch(search.id)}
                      className="rounded p-1 text-ink-ghost opacity-0 transition-opacity group-hover/saved:opacity-100 hover:text-critical"
                    >
                      <X className="size-3" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        ) : null}
      </div>

      {/* ---------------------------------------------------------- footer */}
      <div className="shrink-0 border-t border-hairline px-2.5 py-2.5">
        {collapsed ? (
          <div className="flex flex-col items-center gap-1.5">
            <button
              type="button"
              onClick={onOpenSettings}
              aria-label="Settings"
              className="flex size-9 items-center justify-center rounded-lg text-ink-ghost transition-colors hover:bg-ink/6 hover:text-ink-muted"
            >
              <Settings className="size-4" />
            </button>
            <StatusDot tone={llmTone} pulse={llmTone === 'positive'} />
          </div>
        ) : (
          <>
            <button
              type="button"
              onClick={onOpenSettings}
              className="mb-2 flex w-full items-center gap-2 rounded-field px-2 py-1.5 text-left transition-colors hover:bg-ink/[0.04]"
            >
              <Settings className="size-3.5 text-ink-ghost" />
              <span className="text-[12.5px] text-ink-muted">Settings</span>
            </button>

            <div className="rounded-field border border-hairline bg-ink/[0.02] px-2.5 py-2">
              <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.13em] text-ink-ghost">
                API configuration
              </p>
              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <StatusDot tone={llmTone} pulse={llmTone === 'positive'} />
                  <span className="min-w-0 flex-1 truncate text-[11.5px] text-ink-muted">
                    {status?.llm.name ?? 'Google Gemini'}
                  </span>
                  <span
                    className={clsx(
                      'shrink-0 font-mono text-[10px]',
                      llmTone === 'positive'
                        ? 'text-positive'
                        : llmTone === 'caution'
                          ? 'text-caution'
                          : llmTone === 'critical'
                            ? 'text-critical'
                            : 'text-ink-ghost',
                    )}
                  >
                    {statusError ? 'offline' : status?.llm.connected ? 'live' : 'idle'}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <StatusDot tone={searchTone} pulse={searchTone === 'positive'} />
                  <span className="min-w-0 flex-1 truncate text-[11.5px] text-ink-muted">
                    {status?.search.name ?? 'Search provider'}
                  </span>
                  <span
                    className={clsx(
                      'shrink-0 font-mono text-[10px]',
                      searchTone === 'positive'
                        ? 'text-positive'
                        : searchTone === 'caution'
                          ? 'text-caution'
                          : searchTone === 'critical'
                            ? 'text-critical'
                            : 'text-ink-ghost',
                    )}
                  >
                    {statusError ? 'offline' : status?.search.connected ? 'live' : 'idle'}
                  </span>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </motion.aside>
  )
}
