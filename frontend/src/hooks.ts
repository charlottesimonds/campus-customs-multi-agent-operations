import { useCallback, useEffect, useRef, useState } from 'react'

/** Calls `fn` now and then every `intervalMs` while mounted. Skips a tick if the last call is still running. */
export function usePolling(fn: () => Promise<void>, intervalMs: number, enabled = true) {
  const fnRef = useRef(fn)
  useEffect(() => {
    fnRef.current = fn
  }, [fn])
  useEffect(() => {
    if (!enabled) return
    let busy = false
    let cancelled = false
    const tick = async () => {
      if (busy || cancelled) return
      busy = true
      try {
        await fnRef.current()
      } finally {
        busy = false
      }
    }
    tick()
    const id = window.setInterval(tick, intervalMs)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [intervalMs, enabled])
}

const NAME_KEY = 'campus-customs-operator'

/** The operator's name, remembered between visits so approvals don't need retyping. */
export function useOperatorName() {
  const [name, setName] = useState(() => localStorage.getItem(NAME_KEY) ?? '')
  const save = useCallback((value: string) => {
    setName(value)
    localStorage.setItem(NAME_KEY, value.trim())
  }, [])
  return [name, save] as const
}

/** Re-renders every second while `active`, for live elapsed-time counters. */
export function useTicker(active: boolean) {
  const [, setNow] = useState(0)
  useEffect(() => {
    if (!active) return
    const id = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(id)
  }, [active])
}
