import { useEffect, useState } from 'react'

/** Subscribe to a CSS media query. */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => {
    if (typeof window === 'undefined') return false
    return window.matchMedia(query).matches
  })

  useEffect(() => {
    const list = window.matchMedia(query)
    const handler = (event: MediaQueryListEvent) => setMatches(event.matches)
    setMatches(list.matches)
    list.addEventListener('change', handler)
    return () => list.removeEventListener('change', handler)
  }, [query])

  return matches
}

/** True on viewports narrower than the given breakpoint (Tailwind `lg` = 1024px). */
export function useBreakpoint(px: number): boolean {
  return useMediaQuery(`(max-width: ${px - 0.02}px)`)
}
