import clsx from 'clsx'

/** The NEXUS mark: a central node wired to three satellites. */
export function Logo({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      className={clsx('size-7', className)}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="nexus-mark" x1="4" y1="2" x2="28" y2="30" gradientUnits="userSpaceOnUse">
          <stop stopColor="var(--nx-accent)" />
          <stop offset="0.55" stopColor="var(--nx-electric)" />
          <stop offset="1" stopColor="var(--nx-signal)" />
        </linearGradient>
      </defs>
      <rect
        x="1.25"
        y="1.25"
        width="29.5"
        height="29.5"
        rx="9"
        stroke="url(#nexus-mark)"
        strokeOpacity="0.42"
        strokeWidth="1.2"
        fill="url(#nexus-mark)"
        fillOpacity="0.07"
      />
      <path
        d="M16 16 9.5 9.5M16 16l7.4-5.6M16 16v7.6"
        stroke="url(#nexus-mark)"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeOpacity="0.85"
      />
      <circle cx="16" cy="16" r="3.1" fill="url(#nexus-mark)" />
      <circle cx="9.5" cy="9.5" r="1.85" fill="var(--nx-accent)" />
      <circle cx="23.4" cy="10.4" r="1.85" fill="var(--nx-electric)" />
      <circle cx="16" cy="23.6" r="1.85" fill="var(--nx-signal)" />
    </svg>
  )
}

/** The full wordmark used in the sidebar header. */
export function Wordmark({ className }: { className?: string }) {
  return (
    <div className={clsx('flex items-center gap-2.5', className)}>
      <Logo />
      <div className="flex flex-col leading-none">
        <span className="text-[14px] font-semibold tracking-[0.16em] text-ink">NEXUS</span>
        <span className="mt-1 text-[9.5px] font-medium uppercase tracking-[0.19em] text-ink-ghost">
          ReAct Intelligence
        </span>
      </div>
    </div>
  )
}
