import { useCallback, useEffect, useState } from 'react'
import type { ThemePreference } from '@/types'

const STORAGE_KEY = 'nexus.theme'

function resolve(preference: ThemePreference): 'dark' | 'light' {
  if (preference === 'system') {
    if (typeof window === 'undefined') return 'dark'
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
  }
  return preference
}

/** Theme preference with persistence and live OS-colour-scheme syncing. */
export function useTheme() {
  const [preference, setPreference] = useState<ThemePreference>(() => {
    if (typeof window === 'undefined') return 'dark'
    const stored = window.localStorage.getItem(STORAGE_KEY) as ThemePreference | null
    return stored ?? 'dark'
  })
  const [theme, setTheme] = useState<'dark' | 'light'>(() => resolve(preference))

  useEffect(() => {
    const next = resolve(preference)
    setTheme(next)
    document.documentElement.setAttribute('data-theme', next)
    window.localStorage.setItem(STORAGE_KEY, preference)
  }, [preference])

  useEffect(() => {
    if (preference !== 'system') return
    const query = window.matchMedia('(prefers-color-scheme: light)')
    const handler = () => {
      const next = resolve('system')
      setTheme(next)
      document.documentElement.setAttribute('data-theme', next)
    }
    query.addEventListener('change', handler)
    return () => query.removeEventListener('change', handler)
  }, [preference])

  const toggle = useCallback(() => {
    setPreference((current) => (current === 'light' ? 'dark' : 'light'))
  }, [])

  return { preference, theme, setPreference, toggle }
}
