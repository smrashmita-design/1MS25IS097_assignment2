import { motion } from 'framer-motion'
import {
  ArrowRight,
  Cpu,
  GitCompareArrows,
  Search,
  Sparkles,
  Zap,
} from 'lucide-react'
import { Logo } from '@/components/ui/Logo'

export const EXAMPLE_PROMPTS = [
  {
    icon: Sparkles,
    title: 'AI research',
    prompt: 'Research the latest developments in artificial intelligence.',
  },
  {
    icon: GitCompareArrows,
    title: 'Framework comparison',
    prompt: 'Compare FastAPI and Flask for production applications.',
  },
  {
    icon: Cpu,
    title: 'Agent frameworks',
    prompt: 'Find the best open-source agent frameworks.',
  },
  {
    icon: Zap,
    title: 'Renewable energy',
    prompt: 'Research the latest developments in renewable energy.',
  },
]

const LOOP_STEPS = [
  { label: 'Reason', icon: Cpu },
  { label: 'Act', icon: Zap },
  { label: 'Observe', icon: Search },
  { label: 'Iterate', icon: ArrowRight },
]

export function WelcomeScreen({ onPick }: { onPick: (prompt: string) => void }) {
  return (
    <div className="relative flex min-h-full flex-col items-center justify-center px-4 py-10 sm:px-6">
      <div className="nx-aurora pointer-events-none absolute inset-0" />
      <div className="nx-grid-field pointer-events-none absolute inset-0 [mask-image:radial-gradient(ellipse_65%_55%_at_50%_45%,black,transparent)]" />

      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="relative z-10 w-full max-w-2xl text-center"
      >
        <div className="mb-7 flex items-center justify-center">
          <div className="nx-accent-ring rounded-2xl border border-hairline bg-elevated/70 p-2.5 backdrop-blur-xl">
            <Logo className="size-8" />
          </div>
        </div>

        <h1 className="text-[30px] leading-[1.15] font-semibold tracking-[-0.03em] text-ink sm:text-[38px]">
          What should Nexus{' '}
          <span className="bg-gradient-to-r from-accent via-electric to-signal bg-clip-text text-transparent">
            research
          </span>{' '}
          for you?
        </h1>

        <p className="mx-auto mt-3.5 max-w-lg text-[14px] leading-relaxed text-ink-muted">
          Nexus is a ReAct agent. It reasons about what to look up, calls a real web-search
          tool, reads the results, searches again when it needs more, and answers with
          citations you can open.
        </p>

        <div className="mt-7 flex flex-wrap items-center justify-center gap-1.5">
          {LOOP_STEPS.map((step, index) => (
            <motion.div
              key={step.label}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 + index * 0.07, duration: 0.35 }}
              className="flex items-center gap-1.5"
            >
              <span className="inline-flex items-center gap-1.5 rounded-full border border-hairline bg-elevated/60 px-2.5 py-1 text-[11.5px] font-medium text-ink-muted backdrop-blur-sm">
                <step.icon className="size-3 text-accent" />
                {step.label}
              </span>
              {index < LOOP_STEPS.length - 1 ? (
                <span className="text-ink-ghost">·</span>
              ) : null}
            </motion.div>
          ))}
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.22, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="relative z-10 mt-9 grid w-full max-w-3xl gap-2 sm:grid-cols-2"
      >
        {EXAMPLE_PROMPTS.map((example, index) => (
          <motion.button
            key={example.prompt}
            type="button"
            onClick={() => onPick(example.prompt)}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.28 + index * 0.06, duration: 0.4 }}
            whileHover={{ y: -2 }}
            whileTap={{ scale: 0.985 }}
            className="group/ex group flex items-start gap-3 rounded-panel border border-hairline bg-elevated/55 p-3.5 text-left backdrop-blur-sm transition-colors hover:border-hairline-strong hover:bg-elevated/85"
          >
            <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg border border-hairline bg-ink/[0.04] transition-colors group-hover/ex:border-accent/30 group-hover/ex:bg-accent-soft">
              <example.icon className="size-4 text-ink-muted transition-colors group-hover/ex:text-accent" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-[11px] font-medium uppercase tracking-[0.12em] text-ink-ghost">
                {example.title}
              </span>
              <span className="mt-1 block text-[13px] leading-snug text-ink-muted transition-colors group-hover/ex:text-ink">
                {example.prompt}
              </span>
            </span>
            <ArrowRight className="mt-1 size-3.5 shrink-0 text-ink-ghost opacity-0 transition-all duration-200 group-hover/ex:translate-x-0.5 group-hover/ex:opacity-70" />
          </motion.button>
        ))}
      </motion.div>
    </div>
  )
}
