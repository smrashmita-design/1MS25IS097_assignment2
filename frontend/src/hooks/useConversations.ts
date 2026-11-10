import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '@/services/api'
import type { Conversation, ConversationSummary, SavedSearch } from '@/types'

/**
 * Conversation state with backend persistence.
 *
 * The store keeps the full conversation (including the ReAct timelines) in
 * memory and mirrors it to the backend so history survives a reload.
 */
export function useConversations() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Conversation['messages']>([])
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refreshList = useCallback(async () => {
    try {
      const list = await api.listConversations()
      setConversations(list)
      return list
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load conversations.')
      return []
    }
  }, [])

  const refreshSaved = useCallback(async () => {
    try {
      setSavedSearches(await api.listSavedSearches())
    } catch {
      /* saved searches are optional */
    }
  }, [])

  const load = useCallback(async (id: string) => {
    try {
      const conversation = await api.getConversation(id)
      setActiveId(conversation.id)
      setMessages(conversation.messages)
      return conversation
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not open that conversation.')
      return null
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      const list = await refreshList()
      await refreshSaved()
      if (cancelled) return
      if (list.length) {
        const first = await load(list[0].id)
        if (!cancelled && first) setMessages(first.messages)
      }
      if (!cancelled) setLoading(false)
    })()
    return () => {
      cancelled = true
    }
  }, [load, refreshList, refreshSaved])

  const startNew = useCallback(async () => {
    try {
      const conversation = await api.createConversation()
      setActiveId(conversation.id)
      setMessages([])
      await refreshList()
      return conversation
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start a new conversation.')
      return null
    }
  }, [refreshList])

  const rename = useCallback(
    async (id: string, title: string) => {
      const updated = await api.renameConversation(id, title)
      setMessages(updated.messages)
      await refreshList()
      return updated
    },
    [refreshList],
  )

  const remove = useCallback(
    async (id: string) => {
      await api.deleteConversation(id)
      const list = await refreshList()
      if (id === activeId) {
        if (list.length) {
          const next = await load(list[0].id)
          setMessages(next?.messages ?? [])
        } else {
          setActiveId(null)
          setMessages([])
        }
      }
    },
    [activeId, load, refreshList],
  )

  const clear = useCallback(async () => {
    if (!activeId) return
    const updated = await api.clearConversation(activeId)
    setMessages(updated.messages)
  }, [activeId])

  const saveSearch = useCallback(
    async (query: string) => {
      try {
        await api.addSavedSearch(query, activeId ?? undefined)
        await refreshSaved()
      } catch {
        /* non-critical */
      }
    },
    [activeId, refreshSaved],
  )

  const removeSavedSearch = useCallback(
    async (id: string) => {
      try {
        await api.deleteSavedSearch(id)
        await refreshSaved()
      } catch {
        /* non-critical */
      }
    },
    [refreshSaved],
  )

  const appendMessage = useCallback((message: Conversation['messages'][number]) => {
    setMessages((current) => [...current, message])
  }, [])

  const updateMessage = useCallback(
    (id: string, patch: Partial<Conversation['messages'][number]>) => {
      setMessages((current) =>
        current.map((message) => (message.id === id ? { ...message, ...patch } : message)),
      )
    },
    [],
  )

  return useMemo(
    () => ({
      conversations,
      activeId,
      messages,
      savedSearches,
      loading,
      error,
      setActiveId,
      setMessages,
      refreshList,
      refreshSaved,
      load,
      startNew,
      rename,
      remove,
      clear,
      saveSearch,
      removeSavedSearch,
      appendMessage,
      updateMessage,
    }),
    [
      conversations,
      activeId,
      messages,
      savedSearches,
      loading,
      error,
      refreshList,
      refreshSaved,
      load,
      startNew,
      rename,
      remove,
      clear,
      saveSearch,
      removeSavedSearch,
      appendMessage,
      updateMessage,
    ],
  )
}
