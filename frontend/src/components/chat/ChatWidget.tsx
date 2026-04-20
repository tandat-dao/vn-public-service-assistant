'use client'
import { useRef, useState, useEffect, useCallback } from 'react'
import { MessageCircle, X, Send, Paperclip, ChevronDown, Maximize2, RotateCcw } from 'lucide-react'
import Link from 'next/link'
import { useChatStore } from '@/lib/stores/chatStore'
import { streamChat, api } from '@/lib/api/client'
import type { Citation, RetrievedSource } from '@/lib/types'

/* ─── helpers ─────────────────────────────────────────────── */

/**
 * Render chat message content with legal citations highlighted.
 * Verified citations → bold orange span with ⚖️ prefix.
 *   When a matching RetrievedSource is found, adds a `title` tooltip with the
 *   chunk content (600-char cap enforced backend-side) and `cursor-help`.
 *   When no match, renders exactly as before with `cursor-default`.
 * Unverified citations → grey italic span with ⚠️ prefix. Never has a tooltip.
 * MUST only be called on completed messages (isStreaming=false).
 */
function renderWithCitations(
  content: string,
  retrievedSources: RetrievedSource[] = []
): React.ReactNode {
  const pattern = /(\[unverified:\s*[^\]]+\]|\[Điều\s+\d+[a-zA-Z]?,\s+[^\]]+\])/g
  const parts = content.split(pattern)
  return (
    <span className="whitespace-pre-wrap">
      {parts.map((part, i) => {
        if (/^\[unverified:/i.test(part)) {
          return (
            <span
              key={i}
              className="inline-flex items-center gap-0.5 italic text-gray-400 text-[0.85em] cursor-default"
              title="Trích dẫn chưa được xác minh trong tài liệu"
            >
              ⚠️ {part}
            </span>
          )
        }
        if (/^\[Điều/.test(part)) {
          const lowerPart = part.toLowerCase()
          const matchingSource = retrievedSources.find(
            (source) =>
              lowerPart.includes(source.article_number.toLowerCase()) &&
              lowerPart.includes(source.document_number.toLowerCase())
          )
          return (
            <span
              key={i}
              className={`inline-flex items-center gap-0.5 font-semibold text-[#B8694A] bg-[#FFF3EF] rounded px-1 text-[0.85em] ${matchingSource ? 'cursor-help' : 'cursor-default'}`}
              title={matchingSource ? matchingSource.content : 'Trích dẫn pháp lý đã xác minh'}
            >
              ⚖️ {part}
            </span>
          )
        }
        return <span key={i}>{part}</span>
      })}
    </span>
  )
}

/**
 * Render a completed administrative document draft in a styled monospace block.
 * Shows a header, the full document text in a scrollable pre, and a copy button.
 * renderWithCitations() is intentionally NOT applied here — the content is a
 * structured document, not prose with citation chips.
 */
function DocumentDraftBlock({ content }: { content: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // clipboard API not available (e.g. HTTP context) — silently ignore
    }
  }

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden mt-1">
      <div className="flex items-center justify-between px-3 py-2 bg-gray-50 border-b border-gray-200">
        <span className="text-sm font-semibold" style={{ color: '#CE7A58' }}>
          📄 Văn bản hành chính
        </span>
        <button
          onClick={handleCopy}
          className="text-xs text-gray-500 hover:text-gray-700 transition-colors"
        >
          {copied ? '✅ Đã sao chép' : '📋 Sao chép'}
        </button>
      </div>
      <pre className="p-4 text-xs leading-relaxed whitespace-pre-wrap font-mono text-gray-800 bg-white max-h-96 overflow-y-auto">
        {content}
      </pre>
    </div>
  )
}

function LoadingDots() {
  return (
    <div className="flex items-center gap-1 py-1">
      <span className="chat-dot w-2 h-2 rounded-full bg-[#CE7A58] inline-block" />
      <span className="chat-dot w-2 h-2 rounded-full bg-[#CE7A58] inline-block" />
      <span className="chat-dot w-2 h-2 rounded-full bg-[#CE7A58] inline-block" />
    </div>
  )
}

function CitationChips({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null
  return (
    <div className="mt-1.5 flex flex-wrap gap-1">
      {citations.map((c) => (
        <span key={c.doc_id} className="citation-chip" title={c.excerpt}>
          {c.article}, {c.document_number}
        </span>
      ))}
    </div>
  )
}

const GUIDED_PROCEDURE_NAMES: Record<string, string> = {
  'TTHC-001': 'Đăng ký thường trú',
  'TTHC-002': 'Đăng ký tạm trú',
  'TTHC-003': 'Xác nhận thông tin cư trú',
}

const GUIDED_STEP_LABELS = [
  'Giới thiệu thủ tục',
  'Tải lên CCCD',
  'Điền tờ khai',
  'Hoàn thành',
]

function GuidedProgressBar({
  procedureId,
  step,
  onExit,
}: {
  procedureId: string
  step: number | null
  onExit: () => void
}) {
  const procedureName = GUIDED_PROCEDURE_NAMES[procedureId] ?? procedureId
  const currentStep = step ?? 0
  const totalSteps = GUIDED_STEP_LABELS.length

  return (
    <div className="px-4 py-2 bg-[#FFF8F5] border-b border-[#DDDDDD]">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[0.7rem] font-semibold text-[#CE7A58] truncate">
          Hướng dẫn: {procedureName}
        </span>
        <button
          onClick={onExit}
          className="text-[0.65rem] text-[#999] hover:text-[#555] transition-colors whitespace-nowrap ml-2"
          title="Thoát chế độ hướng dẫn"
        >
          Thoát hướng dẫn
        </button>
      </div>
      {/* Step dots */}
      <div className="flex items-center gap-1">
        {GUIDED_STEP_LABELS.map((label, i) => {
          const isCompleted = i < currentStep
          const isCurrent = i === currentStep
          return (
            <div key={i} className="flex items-center" style={{ flex: i < totalSteps - 1 ? '1' : 'none' }}>
              <div
                className={`w-4 h-4 rounded-full flex-shrink-0 flex items-center justify-center text-[0.55rem] font-bold
                  ${isCompleted ? 'bg-green-500 text-white' : isCurrent ? 'bg-[#CE7A58] text-white' : 'bg-[#DDD] text-[#999]'}`}
                title={label}
              >
                {isCompleted ? '✓' : i + 1}
              </div>
              {i < totalSteps - 1 && (
                <div className={`flex-1 h-px mx-0.5 ${i < currentStep ? 'bg-green-500' : 'bg-[#DDD]'}`} />
              )}
            </div>
          )
        })}
      </div>
      <p className="text-[0.65rem] text-[#777] mt-0.5">
        Bước {currentStep + 1}/{totalSteps}: {GUIDED_STEP_LABELS[currentStep] ?? 'Hoàn thành'}
      </p>
    </div>
  )
}

/* ─── component ───────────────────────────────────────────── */

export function ChatWidget() {
  const {
    isOpen, toggle, close,
    sessionId, citizenId, messages,
    isStreaming, setStreaming,
    addMessage, updateMessage,
    uploadedFile, setUploadedFile,
    clearSession,
    guidedProcedureId, setGuidedProcedureId,
    guidedStep, setGuidedStep,
  } = useChatStore()

  const [input, setInput] = useState('')
  const [lastUploadedPath, setLastUploadedPath] = useState<string | null>(null)
  const bottomRef     = useRef<HTMLDivElement>(null)
  const fileRef       = useRef<HTMLInputElement>(null)
  const textareaRef   = useRef<HTMLTextAreaElement>(null)
  const warmupTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  /* auto-scroll to bottom on new messages */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isOpen])

  /* auto-resize textarea */
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`
  }, [input])

  const handleSend = useCallback(async () => {
    const text = input.trim()
    if (!text || isStreaming) return

    setInput('')
    addMessage({ role: 'user', content: text, citations: [] })

    const assistantId = addMessage({
      role: 'assistant',
      content: '',
      citations: [],
      isStreaming: true,
    })

    setStreaming(true)

    // Start warmup timer — if no SSE content arrives within 5 seconds,
    // show a Vietnamese waiting message so the user knows the system is
    // starting up (e.g. embedding model cold start).  Cleared on first
    // real content chunk and in all exit paths.
    warmupTimerRef.current = setTimeout(() => {
      updateMessage(assistantId, {
        content: 'Đang khởi động hệ thống AI, vui lòng chờ giây lát...',
      })
    }, 5000)

    // Step 1: upload file if attached
    let imagePath: string | null = lastUploadedPath
    if (uploadedFile) {
      try {
        const uploadResult = await api.documents.upload(uploadedFile.file, sessionId, citizenId || undefined)
        setUploadedFile(null)
        imagePath = uploadResult.tmp_path
        setLastUploadedPath(uploadResult.tmp_path)
        if (uploadResult.status === 'partial') {
          updateMessage(assistantId, {
            content: 'Tệp đã được lưu nhưng không đọc được thông tin. Tôi sẽ trả lời dựa trên câu hỏi của bạn.\n\n',
          })
        }
      } catch {
        updateMessage(assistantId, {
          content: 'Không thể tải lên tệp. Vui lòng thử lại.',
          isStreaming: false,
        })
        setStreaming(false)
        return
      }
    }

    // Consume the stored path on this send — subsequent messages should
    // not re-send the same image_path unless a new file is uploaded.
    if (!uploadedFile) setLastUploadedPath(null)

    // Step 2: send chat message (SSE streaming)
    // Pass image_path so the backend OCR node can locate the uploaded file
    // without relying solely on the Redis session fallback.
    try {
      let accumulated = ''
      for await (const chunk of streamChat(sessionId, text, imagePath ?? undefined, citizenId || undefined)) {
        try {
          const parsed = JSON.parse(chunk)
          if ('content' in parsed && typeof parsed.content === 'string') {
            // Clear warmup timer on first real content — prevents placeholder
            // message from overwriting real content if it fires late.
            if (warmupTimerRef.current) {
              clearTimeout(warmupTimerRef.current)
              warmupTimerRef.current = null
            }
            // Chunks are 1–3 Unicode code points. Vietnamese diacritics are single
            // code points — no broken characters possible at this chunk size.
            accumulated += parsed.content
            updateMessage(assistantId, { content: accumulated })
          } else if ('metadata' in parsed) {
            if (Array.isArray(parsed.metadata?.citations)) {
              updateMessage(assistantId, { citations: parsed.metadata.citations as Citation[] })
            }
            // Surface filled form path so the download button can be rendered.
            // Also shown in guided mode when form fill completes (guided_step mode).
            if (
              (parsed.metadata?.mode === 'form_fill_complete' ||
               parsed.metadata?.mode === 'guided_step') &&
              typeof parsed.metadata?.filled_form_path === 'string' &&
              parsed.metadata.filled_form_path
            ) {
              updateMessage(assistantId, { filledFormPath: parsed.metadata.filled_form_path as string })
            }
            // Store response mode so the render loop can select the correct
            // presentation (e.g. document_draft uses DocumentDraftBlock).
            if (parsed.metadata?.mode) {
              updateMessage(assistantId, { messageMode: parsed.metadata.mode as string })
            }
            // When RAG returns no results, append a guidance tip so the user
            // knows how to rephrase their question.
            if (
              parsed.metadata?.mode === 'error' &&
              accumulated.includes('Không tìm thấy văn bản pháp lý')
            ) {
              const tip = '\n\n💡 Thử đặt câu hỏi cụ thể hơn, ví dụ: \'Điều kiện đăng ký thường trú là gì?\''
              accumulated += tip
              updateMessage(assistantId, { content: accumulated })
            }
            // Update guided procedure wizard state from SSE metadata — TASK-APP-18
            if (parsed.metadata?.guided_procedure_id !== undefined) {
              setGuidedProcedureId(parsed.metadata.guided_procedure_id ?? null)
            }
            if (parsed.metadata?.guided_step !== undefined) {
              setGuidedStep(parsed.metadata.guided_step ?? null)
            }
            // Store retrieved chunk content for citation hover tooltips — TASK-APP-17
            if (
              Array.isArray(parsed.metadata?.retrieved_sources) &&
              parsed.metadata.retrieved_sources.length > 0
            ) {
              updateMessage(assistantId, {
                retrievedSources: parsed.metadata.retrieved_sources as RetrievedSource[],
              })
            }
          }
        } catch {
          // plain text chunk (non-JSON fallback)
          if (warmupTimerRef.current) {
            clearTimeout(warmupTimerRef.current)
            warmupTimerRef.current = null
          }
          accumulated += chunk
          updateMessage(assistantId, { content: accumulated })
        }
      }
    } catch (err: any) {
      if (warmupTimerRef.current) {
        clearTimeout(warmupTimerRef.current)
        warmupTimerRef.current = null
      }
      const status = err?.status
      let errorMessage = 'Xin lỗi, đã có lỗi khi kết nối đến máy chủ. Vui lòng thử lại.'
      if (status === 429) {
        errorMessage = 'Hệ thống đang bận, vui lòng thử lại sau 30 giây.'
      } else if (status === 500) {
        errorMessage = 'Đã xảy ra lỗi hệ thống. Vui lòng thử lại.'
      } else if (status === 422) {
        errorMessage = 'Yêu cầu không hợp lệ. Vui lòng thử lại.'
      }
      updateMessage(assistantId, {
        content: errorMessage,
        isStreaming: false,
      })
    } finally {
      if (warmupTimerRef.current) {
        clearTimeout(warmupTimerRef.current)
        warmupTimerRef.current = null
      }
      updateMessage(assistantId, { isStreaming: false })
      setStreaming(false)
    }
  }, [input, isStreaming, sessionId, uploadedFile, addMessage, updateMessage, setStreaming, setUploadedFile])

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  /** Send the exit phrase to the backend to clear guided mode server-side. */
  const handleExitGuided = useCallback(() => {
    setInput('thoát')
    // Trigger send on next tick so input state is flushed
    setTimeout(() => handleSend(), 0)
  }, [handleSend])

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploadedFile({ file, previewUrl: URL.createObjectURL(file) })
    e.target.value = ''
  }

  return (
    <>
      {/* Floating toggle button */}
      <button
        onClick={toggle}
        aria-label="Mở hộp trợ lý ảo"
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-[#CE7A58]
                   flex items-center justify-center text-white
                   hover:bg-[#B8694A] transition-colors"
      >
        {isOpen
          ? <ChevronDown className="w-6 h-6" />
          : <MessageCircle className="w-6 h-6" />
        }
      </button>

      {/* Widget panel */}
      {isOpen && (
        <div
          className="fixed bottom-24 right-6 z-50 w-[360px] flex flex-col
                     bg-white border border-[#DDDDDD] rounded-[6px]
                     overflow-hidden"
          style={{ height: '520px' }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-[#CE7A58]">
            <div className="flex items-center gap-2">
              <MessageCircle className="w-5 h-5 text-white" />
              <span className="text-white font-semibold text-sm">Trợ lý hành chính</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={clearSession}
                title="Cuộc trò chuyện mới"
                className="text-white/80 hover:text-white transition-colors"
                aria-label="Cuộc trò chuyện mới"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
              <Link
                href="/chat"
                onClick={close}
                title="Mở trang chat đầy đủ"
                className="text-white/80 hover:text-white transition-colors"
              >
                <Maximize2 className="w-4 h-4" />
              </Link>
              <button
                onClick={close}
                className="text-white/80 hover:text-white transition-colors"
                aria-label="Đóng"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Guided procedure progress bar — TASK-APP-18 */}
          {guidedProcedureId && (
            <GuidedProgressBar
              procedureId={guidedProcedureId}
              step={guidedStep}
              onExit={handleExitGuided}
            />
          )}

          {/* Messages area */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
            {messages.length === 0 && (
              <div className="py-6 text-center text-[#999] text-xs leading-relaxed">
                <p className="text-2xl mb-2">🤖</p>
                <p>Xin chào! Tôi có thể giúp bạn tra cứu thủ tục hành chính,
                  điền tờ khai, hoặc giải đáp các câu hỏi về dịch vụ công.</p>
              </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
              >
                <div
                  className={`max-w-[80%] px-3 py-2 rounded-[6px] text-sm leading-relaxed
                    ${msg.role === 'user'
                      ? 'bg-[#CE7A58] text-white'
                      : 'bg-[#F5F5F5] text-[#1E2F41]'
                    }`}
                >
                  {msg.isStreaming && !msg.content
                    ? <LoadingDots />
                    : msg.isStreaming
                      ? <span className="whitespace-pre-wrap">{msg.content}</span>
                      : msg.messageMode === 'document_draft'
                        ? <DocumentDraftBlock content={msg.content} />
                        : renderWithCitations(msg.content, msg.retrievedSources ?? [])
                  }
                </div>

                {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                  <CitationChips citations={msg.citations} />
                )}

                {msg.role === 'assistant' && !msg.isStreaming && msg.filledFormPath && (
                  <div className="mt-2">
                    <a
                      href={`${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/api/v1/documents/download?path=${encodeURIComponent(msg.filledFormPath)}&session_id=${encodeURIComponent(sessionId)}`}
                      download
                      className="inline-flex items-center gap-2 px-3 py-2 rounded
                                 bg-[#CE7A58] text-white text-sm font-medium
                                 hover:bg-[#B8694A] transition-colors"
                    >
                      📄 Tải xuống tờ khai đã điền
                    </a>
                  </div>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Uploaded file preview */}
          {uploadedFile && (
            <div className="flex items-center gap-2 px-4 py-2 bg-[#FFF8F5] border-t border-[#DDDDDD]">
              <Paperclip className="w-3.5 h-3.5 text-[#CE7A58] flex-shrink-0" />
              <span className="text-xs text-[#555] truncate flex-1">{uploadedFile.file.name}</span>
              <button
                onClick={() => setUploadedFile(null)}
                className="text-[#999] hover:text-[#555] transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Input area */}
          <div className="border-t border-[#DDDDDD] px-3 py-2 flex items-end gap-2">
            {/* Hidden file input */}
            <input
              ref={fileRef}
              type="file"
              accept="image/*,.pdf"
              className="hidden"
              onChange={handleFileChange}
            />

            <button
              onClick={() => fileRef.current?.click()}
              title="Đính kèm tệp"
              className="text-[#999] hover:text-[#CE7A58] transition-colors p-1 flex-shrink-0 self-end mb-0.5"
            >
              <Paperclip className="w-4 h-4" />
            </button>

            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Nhập câu hỏi… (Enter để gửi)"
              rows={1}
              disabled={isStreaming}
              className="flex-1 resize-none border border-[#DDDDDD] rounded px-2.5 py-2 text-sm
                         focus:outline-none focus:border-[#CE7A58] disabled:opacity-50
                         max-h-[120px] overflow-y-auto leading-snug"
            />

            <button
              onClick={handleSend}
              disabled={!input.trim() || isStreaming}
              className="bg-[#CE7A58] text-white rounded p-2 flex-shrink-0 self-end
                         hover:bg-[#B8694A] disabled:opacity-40 disabled:cursor-not-allowed
                         transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </>
  )
}
