import type { RetrievedSource } from '@/lib/types'

function stripMarkdownForHover(text: string): string {
  return text
    .replace(/#{1,6}\s+/gm, '')
    .replace(/\*{3}(.+?)\*{3}/g, '$1')
    .replace(/\*{2}(.+?)\*{2}/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/^[\-\*]\s+/gm, '')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

/**
 * Render chat message content with legal citations highlighted.
 * Verified citations with a matching source → orange chip with structured hover tooltip.
 * [unverified:...] markers → grey italic span with amber warning tooltip.
 * MUST only be called on completed messages (isStreaming=false).
 */
export function renderWithCitations(
  content: string,
  retrievedSources: RetrievedSource[] = []
): React.ReactNode {
  const pattern = /(\[unverified:\s*[^\]]+\]|\[[^\]]*(?:\/NQ-|\/TT-|\/NĐ-|\/QH|\/VBHN)[^\]]*\])/g
  const parts = content.split(pattern)

  const unverifiedTooltip = (
    <>
      <div className="absolute top-full left-0 w-full h-1" />
      <span className="absolute top-full mt-1 left-0 z-50 hidden group-hover:block hover:block w-64 bg-gray-900 rounded-lg shadow-lg p-3 text-left font-normal not-italic">
        <div className="text-amber-500 text-xs font-semibold">⚠️ Trích dẫn chưa xác minh</div>
        <p className="text-gray-400 text-xs mt-1">Không tìm thấy đoạn văn bản khớp trong kết quả truy xuất.</p>
      </span>
    </>
  )

  return (
    <span className="whitespace-pre-wrap">
      {parts.map((part, i) => {
        if (/^\[unverified:/i.test(part)) {
          return (
            <span
              key={i}
              className="relative group inline-flex items-center gap-0.5 italic text-gray-400 text-[0.85em] cursor-default"
            >
              ⚠️ {part}
              {unverifiedTooltip}
            </span>
          )
        }

        if (/\/(?:NQ-|TT-|NĐ-|QH|VBHN)/.test(part)) {
          const lowerPart = part.toLowerCase()
          const isDieuCitation = /^\[điều/i.test(part)
          const matchingSource = retrievedSources.find((source) =>
            isDieuCitation
              ? lowerPart.includes(source.article_number.toLowerCase()) &&
                lowerPart.includes(source.document_number.toLowerCase())
              : lowerPart.includes(source.document_number.toLowerCase())
          )
          if (matchingSource) {
            return (
              <span
                key={i}
                className="relative group inline-flex items-center gap-0.5 font-semibold text-[var(--terracotta-dk)] bg-[var(--terracotta-faint)] rounded px-1 text-[0.85em] cursor-help"
              >
                {part}
                <div className="absolute top-full left-0 w-full h-1" />
                <span className="absolute top-full mt-1 left-0 z-50 hidden group-hover:block hover:block w-72 max-w-sm bg-gray-900 rounded-lg shadow-lg p-3 text-left font-normal not-italic">
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span className="font-semibold text-[var(--terracotta)] text-xs leading-tight">{matchingSource.article_number}</span>
                    <span className="text-gray-400 text-[0.7em] whitespace-nowrap">{matchingSource.document_number}</span>
                  </div>
                  <hr className="border-gray-700 mb-1.5" />
                  <p className="citation-content text-xs text-gray-300 leading-relaxed max-h-48 overflow-y-auto">
                    {stripMarkdownForHover(matchingSource.content ?? '')}
                  </p>
                </span>
              </span>
            )
          }
          return (
            <span
              key={i}
              className="relative group inline-flex items-center gap-0.5 font-semibold text-[var(--terracotta-dk)] bg-[var(--terracotta-faint)] rounded px-1 text-[0.85em] cursor-default"
            >
              {part}
              {unverifiedTooltip}
            </span>
          )
        }

        // Plain text — strip any trailing ⚖️ that the LLM placed before a citation bracket
        return <span key={i}>{part.replace(/⚖️\s*$/, '')}</span>
      })}
    </span>
  )
}
