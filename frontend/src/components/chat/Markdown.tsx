import { memo, useCallback, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import clsx from 'clsx'
import { Check, Copy } from 'lucide-react'

interface CodeBlockProps {
  children: React.ReactNode
  language?: string
}

/** A fenced code block with a language chip and a copy-to-clipboard action. */
function CodeBlock({ children, language }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)
  const timer = useRef<number | null>(null)

  const copy = useCallback(() => {
    const text = extractText(children)
    if (!text) return
    void navigator.clipboard?.writeText(text).then(() => {
      setCopied(true)
      if (timer.current) window.clearTimeout(timer.current)
      timer.current = window.setTimeout(() => setCopied(false), 1800)
    })
  }, [children])

  return (
    <div className="group/code relative my-4 overflow-hidden rounded-field border border-hairline bg-canvas/60">
      <div className="flex items-center justify-between border-b border-hairline px-3 py-1.5">
        <span className="font-mono text-[10.5px] uppercase tracking-[0.13em] text-ink-ghost">
          {language ?? 'code'}
        </span>
        <button
          type="button"
          onClick={copy}
          aria-label={copied ? 'Copied' : 'Copy code'}
          className="inline-flex items-center gap-1.5 rounded-md px-1.5 py-1 text-[11px] font-medium text-ink-faint transition-colors hover:bg-ink/6 hover:text-ink-muted"
        >
          {copied ? (
            <Check className="size-3.5 text-positive" />
          ) : (
            <Copy className="size-3.5" />
          )}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="nx-prose-pre overflow-x-auto px-3.5 py-3 font-mono text-[12.5px] leading-[1.65]">
        {children}
      </pre>
    </div>
  )
}

function extractText(node: React.ReactNode): string {
  if (node === null || node === undefined || node === false) return ''
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(extractText).join('')
  if (typeof node === 'object' && 'props' in node) {
    const props = (node as { props?: { children?: React.ReactNode } }).props
    return extractText(props?.children ?? '')
  }
  return ''
}

/** Render assistant markdown with GFM tables, syntax highlighting and copy actions. */
export const Markdown = memo(function Markdown({ content }: { content: string }) {
  return (
    <div className="nx-prose">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeHighlight, { detect: true, ignoreMissing: true }]]}
        components={{
          pre({ children }) {
            const child = Array.isArray(children) ? children[0] : children
            const className =
              child && typeof child === 'object' && 'props' in child
                ? ((child as { props?: { className?: string } }).props?.className ?? '')
                : ''
            const language = /language-([\w+-]+)/.exec(className)?.[1]
            return <CodeBlock language={language}>{children}</CodeBlock>
          },
          code({ children, className }) {
            // Inline code only — block code is handled by the `pre` override.
            const isBlock = /language-/.test(className ?? '')
            if (isBlock) return <code className={className}>{children}</code>
            return <code className={className}>{children}</code>
          },
          a({ children, href, ...rest }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer nofollow"
                {...rest}
                className={clsx('inline-flex items-baseline gap-0.5')}
              >
                {children}
              </a>
            )
          },
          table({ children, ...rest }) {
            return (
              <div className="my-4 overflow-x-auto rounded-field border border-hairline">
                <table {...rest}>{children}</table>
              </div>
            )
          },
          img({ children, ...rest }) {
            return (
              <span className="inline-block overflow-hidden rounded-field border border-hairline">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img {...rest} className="max-w-full" />
                {children}
              </span>
            )
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
})
