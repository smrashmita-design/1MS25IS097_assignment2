import { useCallback, useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { Sidebar } from '@/components/layout/Sidebar'
import { TopBar } from '@/components/layout/TopBar'
import { ChatView } from '@/components/chat/ChatView'
import { Composer } from '@/components/chat/Composer'
import { ExecutionPanel } from '@/components/agent/ExecutionPanel'
import { SettingsPage } from '@/pages/SettingsPage'
import { Toaster, useToasts } from '@/hooks/useToasts'
import { useTheme } from '@/hooks/useTheme'
import { useConversations } from '@/hooks/useConversations'
import { useAgentStream } from '@/hooks/useAgentStream'
import { useBreakpoint } from '@/hooks/useMediaQuery'
import { api } from '@/services/api'
import type { Message, StatusResponse } from '@/types'

export default function App() {
  const { preference, setPreference, toggle } = useTheme()
  const { toasts, push, dismiss } = useToasts()
  const conversations = useConversations()

  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [statusError, setStatusError] = useState<string | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobileSidebar, setMobileSidebar] = useState(false)
  const [panelOpen, setPanelOpen] = useState(true)
  const [mobilePanel, setMobilePanel] = useState(false)
  const [showSettings, setShowSettings] = useState(false)

  const isBelowLg = useBreakpoint(1024)
  const isBelowXl = useBreakpoint(1280)

  const panelInline = !isBelowXl
  const sidebarInline = !isBelowLg

  // --------------------------------------------------------- backend health
  const refreshStatus = useCallback(async () => {
    try {
      const result = await api.status()
      setStatus(result)
      setStatusError(null)
    } catch (error) {
      setStatusError(error instanceof Error ? error.message : 'Backend unreachable.')
    }
  }, [])

  useEffect(() => {
    void refreshStatus()
    const timer = window.setInterval(() => void refreshStatus(), 30000)
    return () => window.clearInterval(timer)
  }, [refreshStatus])

  // ------------------------------------------------------------ agent run
  const finalize = useCallback(
    async (payload: {
      content: string
      sources: Message['sources']
      events: Message['events']
      iterations: number
      toolCalls: number
      conversationId: string | null
      error?: string | null
      cancelled?: boolean
    }) => {
      const conversationId = payload.conversationId ?? conversations.activeId
      if (conversationId) {
        const conversation = await conversations.load(conversationId)
        if (conversation) conversations.setActiveId(conversation.id)
      }
      await conversations.refreshList()
      if (payload.error) {
        push({
          tone: 'error',
          title: 'The agent run failed',
          description: payload.error,
        })
      } else if (payload.cancelled) {
        push({ tone: 'info', title: 'Research stopped', description: 'You stopped the run.' })
      } else if (payload.toolCalls > 0) {
        push({
          tone: 'success',
          title: `Researched ${payload.toolCalls} source${payload.toolCalls === 1 ? '' : 's'}`,
          description: `${payload.iterations} iteration${payload.iterations === 1 ? '' : 's'} · ${payload.sources.length} citation${payload.sources.length === 1 ? '' : 's'}`,
        })
      }
    },
    [conversations, push],
  )

  const agent = useAgentStream({
    onComplete: (payload) => void finalize(payload),
    onError: (error) => {
      push({
        tone: 'error',
        title: 'Connection lost',
        description: error.message,
      })
    },
  })

  // -------------------------------------------------------------- actions
  const handleSend = useCallback(
    async (text: string) => {
      const trimmed = text.trim()
      if (!trimmed || agent.run.running) return

      let conversationId = conversations.activeId
      if (!conversationId) {
        const created = await conversations.startNew()
        conversationId = created?.id ?? null
      }
      if (!conversationId) {
        push({
          tone: 'error',
          title: 'Could not start a conversation',
          description: 'The backend did not accept the request.',
        })
        return
      }

      conversations.appendMessage({
        id: `local-user-${Date.now()}`,
        role: 'user',
        content: trimmed,
        created_at: new Date().toISOString(),
        sources: [],
        events: [],
        iterations: 0,
        tool_calls: 0,
        duration_ms: 0,
        status: 'complete',
        error: null,
        model: '',
        provider: '',
      })

      setShowSettings(false)
      await agent.send(trimmed, conversationId)
    },
    [agent, conversations, push],
  )

  const handleRegenerate = useCallback(() => {
    const lastUser = [...conversations.messages].reverse().find((m) => m.role === 'user')
    if (lastUser && !agent.run.running) {
      void handleSend(lastUser.content)
    }
  }, [agent.run.running, conversations.messages, handleSend])

  const handleNewChat = useCallback(() => {
    void conversations.startNew()
    setMobileSidebar(false)
    setShowSettings(false)
  }, [conversations])

  const handleSelectConversation = useCallback(
    async (id: string) => {
      await conversations.load(id)
      setMobileSidebar(false)
      setShowSettings(false)
    },
    [conversations],
  )

  const handleDeleteConversation = useCallback(
    async (id: string) => {
      try {
        await conversations.remove(id)
        push({ tone: 'success', title: 'Conversation deleted' })
      } catch (error) {
        push({
          tone: 'error',
          title: 'Could not delete the conversation',
          description: error instanceof Error ? error.message : undefined,
        })
      }
    },
    [conversations, push],
  )

  const handleRenameConversation = useCallback(
    async (id: string, title: string) => {
      try {
        await conversations.rename(id, title)
      } catch (error) {
        push({
          tone: 'error',
          title: 'Could not rename the conversation',
          description: error instanceof Error ? error.message : undefined,
        })
      }
    },
    [conversations, push],
  )

  const handleStop = useCallback(async () => {
    await agent.stop()
  }, [agent])

  const handleSaveSearch = useCallback(() => {
    const lastUser = [...conversations.messages].reverse().find((m) => m.role === 'user')
    if (!lastUser) return
    void conversations.saveSearch(lastUser.content)
    push({ tone: 'success', title: 'Search saved', description: 'Find it in Saved searches.' })
  }, [conversations, push])

  const activeTitle = useMemo(() => {
    if (showSettings) return 'Settings'
    const active = conversations.conversations.find((c) => c.id === conversations.activeId)
    if (active) return active.title
    return 'New research'
  }, [showSettings, conversations.conversations, conversations.activeId])

  // The panel shows the live trace while a run is in flight, and the persisted
  // trace of the last answer once the conversation is reloaded.
  const panelEvents = useMemo(() => {
    if (agent.run.events.length) return agent.run.events
    const lastAssistant = [...conversations.messages]
      .reverse()
      .find((message) => message.role === 'assistant')
    return lastAssistant?.events ?? []
  }, [agent.run.events, conversations.messages])

  const sidebar = (
    <Sidebar
      conversations={conversations.conversations}
      savedSearches={conversations.savedSearches}
      activeId={conversations.activeId}
      collapsed={sidebarCollapsed && sidebarInline}
      onToggleCollapse={() => setSidebarCollapsed((value) => !value)}
      onNewChat={handleNewChat}
      onSelect={(id) => void handleSelectConversation(id)}
      onRename={(id, title) => void handleRenameConversation(id, title)}
      onDelete={(id) => void handleDeleteConversation(id)}
      onUseSavedSearch={(query) => {
        void handleSend(query)
        setMobileSidebar(false)
      }}
      onDeleteSavedSearch={(id) => void conversations.removeSavedSearch(id)}
      onOpenSettings={() => {
        setShowSettings(true)
        setMobileSidebar(false)
      }}
      status={status}
      statusError={statusError}
    />
  )

  const executionPanel = (
    <ExecutionPanel
      events={panelEvents}
      running={agent.run.running}
      streamingText={agent.run.running ? agent.run.streamingText : ''}
      error={agent.run.error}
    />
  )

  return (
    <div className="flex h-full w-full overflow-hidden bg-canvas text-ink">
      {sidebarInline ? (
        sidebar
      ) : (
        <AnimatePresence>
          {mobileSidebar ? (
            <>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setMobileSidebar(false)}
                className="fixed inset-0 z-40 bg-black/55 backdrop-blur-[2px]"
              />
              <motion.div
                initial={{ x: '-100%' }}
                animate={{ x: 0 }}
                exit={{ x: '-100%' }}
                transition={{ type: 'spring', stiffness: 340, damping: 34 }}
                className="fixed inset-y-0 left-0 z-50"
              >
                {sidebar}
              </motion.div>
            </>
          ) : null}
        </AnimatePresence>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          title={activeTitle}
          status={status}
          statusError={statusError}
          theme={preference}
          onToggleTheme={toggle}
          onOpenSidebar={() => setMobileSidebar(true)}
          panelOpen={panelInline ? panelOpen : mobilePanel}
          onTogglePanel={() => {
            if (panelInline) setPanelOpen((value) => !value)
            else setMobilePanel((value) => !value)
          }}
          onSaveSearch={() => handleSaveSearch()}
          canSave={conversations.messages.some((message) => message.role === 'user')}
        />

        <div className="flex min-h-0 flex-1">
          <main className="flex min-w-0 flex-1 flex-col">
            <AnimatePresence mode="wait" initial={false}>
              {showSettings ? (
                <motion.div
                  key="settings"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="min-h-0 flex-1"
                >
                  <SettingsPage
                    theme={preference}
                    onThemeChange={setPreference}
                    onClose={() => setShowSettings(false)}
                  />
                </motion.div>
              ) : (
                <motion.div
                  key="chat"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex min-h-0 flex-1 flex-col"
                >
                  <ChatView
                    messages={conversations.messages}
                    running={agent.run.running}
                    liveContent={agent.run.streamingText}
                    liveSources={agent.run.sources}
                    liveEvents={agent.run.events}
                    onRegenerate={handleRegenerate}
                    onPickExample={(prompt) => void handleSend(prompt)}
                  />
                  <Composer
                    onSend={(text) => void handleSend(text)}
                    onStop={() => void handleStop()}
                    running={agent.run.running}
                    disabled={statusError !== null && status === null}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </main>

          {panelInline ? (
            <AnimatePresence initial={false}>
              {panelOpen ? (
                <motion.aside
                  key="panel"
                  initial={{ width: 0, opacity: 0 }}
                  animate={{ width: 400, opacity: 1 }}
                  exit={{ width: 0, opacity: 0 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 34 }}
                  className="hidden shrink-0 overflow-hidden border-l border-hairline bg-canvas-soft/60 backdrop-blur-xl xl:block"
                >
                  <div className="h-full w-[400px]">{executionPanel}</div>
                </motion.aside>
              ) : null}
            </AnimatePresence>
          ) : (
            <AnimatePresence>
              {mobilePanel ? (
                <>
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={() => setMobilePanel(false)}
                    className="fixed inset-0 z-40 bg-black/55 backdrop-blur-[2px]"
                  />
                  <motion.aside
                    initial={{ x: '100%' }}
                    animate={{ x: 0 }}
                    exit={{ x: '100%' }}
                    transition={{ type: 'spring', stiffness: 340, damping: 34 }}
                    className="fixed inset-y-0 right-0 z-50 flex w-[min(400px,92vw)] flex-col border-l border-hairline bg-canvas-soft"
                  >
                    <button
                      type="button"
                      onClick={() => setMobilePanel(false)}
                      aria-label="Close execution panel"
                      className="absolute top-3.5 right-3 z-10 flex size-7 items-center justify-center rounded-md text-ink-ghost transition-colors hover:bg-ink/6 hover:text-ink-muted"
                    >
                      <X className="size-4" />
                    </button>
                    {executionPanel}
                  </motion.aside>
                </>
              ) : null}
            </AnimatePresence>
          )}
        </div>
      </div>

      <Toaster toasts={toasts} onDismiss={dismiss} />
    </div>
  )
}
