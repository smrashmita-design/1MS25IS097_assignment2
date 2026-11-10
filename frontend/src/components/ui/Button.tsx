import { forwardRef } from 'react'
import clsx from 'clsx'
import type { ButtonHTMLAttributes } from 'react'
import { Spinner } from '@/components/ui/Spinner'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline'
type Size = 'sm' | 'md' | 'lg' | 'icon'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
}

const VARIANTS: Record<Variant, string> = {
  primary:
    'bg-ink text-canvas hover:bg-ink/90 active:bg-ink/80 shadow-[0_1px_0_rgba(255,255,255,0.12)_inset]',
  secondary:
    'bg-ink/6 text-ink hover:bg-ink/10 border border-hairline hover:border-hairline-strong',
  outline:
    'border border-hairline-strong text-ink-muted hover:text-ink hover:border-ink/25 hover:bg-ink/4',
  ghost: 'text-ink-muted hover:text-ink hover:bg-ink/6',
  danger:
    'bg-critical/12 text-critical border border-critical/25 hover:bg-critical/18 hover:border-critical/40',
}

const SIZES: Record<Size, string> = {
  sm: 'h-8 gap-1.5 px-2.5 text-[12.5px]',
  md: 'h-9.5 gap-2 px-3.5 text-[13.5px]',
  lg: 'h-11 gap-2 px-5 text-[14.5px]',
  icon: 'size-9 justify-center',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'secondary', size = 'md', loading, className, children, disabled, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={clsx(
        'inline-flex select-none items-center rounded-field font-medium transition-all duration-150',
        'disabled:pointer-events-none disabled:opacity-45',
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...rest}
    >
      {loading ? <Spinner className="size-3.5" /> : null}
      {children}
    </button>
  )
})
