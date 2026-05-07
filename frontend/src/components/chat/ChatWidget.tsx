'use client'
import { useRef, useState, useEffect, useCallback } from 'react'
import { MessageCircle, X, Send, Paperclip, ChevronDown, Maximize2, RotateCcw } from 'lucide-react'
import Link from 'next/link'
import { useChatStore } from '@/lib/stores/chatStore'
import { streamChat, api } from '@/lib/api/client'
import { renderWithCitations } from '@/lib/renderCitations'
import type { Citation, FeedbackType, RetrievedSource } from '@/lib/types'

function AnimatedDots() {
  return (
    <span className="inline-flex items-end gap-[3px] h-4">
      <span
        className="w-1.5 h-1.5 rounded-full bg-[var(--gray-300)] animate-bounce"
        style={{ animationDelay: '0ms', animationDuration: '0.8s' }}
      />
      <span
        className="w-1.5 h-1.5 rounded-full bg-[var(--gray-300)] animate-bounce"
        style={{ animationDelay: '150ms', animationDuration: '0.8s' }}
      />
      <span
        className="w-1.5 h-1.5 rounded-full bg-[var(--gray-300)] animate-bounce"
        style={{ animationDelay: '300ms', animationDuration: '0.8s' }}
      />
    </span>
  )
}

function CitationChips({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null
  return (
    <div className="mt-1.5 flex flex-wrap gap-1">
      {citations.map((c) => (
        <span
          key={c.doc_id}
          className="inline-block bg-[var(--navy-faint)] text-[var(--navy)]
                     border border-[var(--navy-light)] hover:bg-[var(--navy-light)]
                     text-[11px] px-1.5 py-0.5 rounded cursor-default transition-colors"
          title={c.excerpt}
        >
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
    <div className="px-4 py-2 bg-[var(--terracotta-faint)] border-b border-[var(--border-card)]">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[0.7rem] font-semibold text-[var(--terracotta)] truncate">
          Hướng dẫn: {procedureName}
        </span>
        <button
          onClick={onExit}
          className="text-[0.65rem] text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors whitespace-nowrap ml-2"
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
                  ${isCompleted ? 'bg-green-500 text-white' : isCurrent ? 'bg-[var(--terracotta)] text-white' : 'bg-[var(--gray-200)] text-[var(--gray-500)]'}`}
                title={label}
              >
                {isCompleted ? '✓' : i + 1}
              </div>
              {i < totalSteps - 1 && (
                <div className={`flex-1 h-px mx-0.5 ${i < currentStep ? 'bg-green-500' : 'bg-[var(--gray-200)]'}`} />
              )}
            </div>
          )
        })}
      </div>
      <p className="text-[0.65rem] text-[var(--text-muted)] mt-0.5">
        Bước {currentStep + 1}/{totalSteps}: {GUIDED_STEP_LABELS[currentStep] ?? 'Hoàn thành'}
      </p>
    </div>
  )
}

/* ─── types ───────────────────────────────────────────────── */

export interface ChatWidgetProps {
  variant?: 'floating' | 'inline'
  initialContext?: string
}

/* ─── component ───────────────────────────────────────────── */

export function ChatWidget({ variant = 'floating', initialContext }: ChatWidgetProps) {
  const {
    isOpen, toggle, close,
    sessionId, citizenId, messages,
    isStreaming, setStreaming,
    addMessage, updateMessage, removeLastMessage,
    uploadedFile, setUploadedFile,
    clearSession,
    guidedProcedureId, setGuidedProcedureId,
    guidedStep, setGuidedStep,
    injectWelcomeMessage,
  } = useChatStore()

  const [input, setInput] = useState('')
  const [lastUploadedPath, setLastUploadedPath] = useState<string | null>(null)
  const [lastFailedMessage, setLastFailedMessage] = useState<string | null>(null)
  const fileRef            = useRef<HTMLInputElement>(null)
  const textareaRef        = useRef<HTMLTextAreaElement>(null)
  const warmupTimerRef     = useRef<ReturnType<typeof setTimeout> | null>(null)

  /* auto-resize textarea */
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`
  }, [input])

  /* silent priming — fires once on mount when initialContext is provided and
     the session has no prior messages. The context is sent as the message body
     but never rendered as a user bubble; the assistant reply is the first
     visible message. */
  useEffect(() => {
    if (!initialContext || messages.length > 0) return
    const doSilentPrime = async () => {
      const assistantId = addMessage({ role: 'assistant', content: '', citations: [], isStreaming: true })
      setStreaming(true)
      try {
        let accumulated = ''
        for await (const chunk of streamChat(sessionId, initialContext, undefined, citizenId || undefined)) {
          try {
            const parsed = JSON.parse(chunk)
            if ('content' in parsed && typeof parsed.content === 'string') {
              accumulated += parsed.content
              updateMessage(assistantId, { content: accumulated })
            } else if ('metadata' in parsed && Array.isArray(parsed.metadata?.citations)) {
              updateMessage(assistantId, { citations: parsed.metadata.citations as Citation[] })
            }
          } catch {
            accumulated += chunk
            updateMessage(assistantId, { content: accumulated })
          }
        }
      } catch {
        updateMessage(assistantId, {
          content: 'Xin lỗi, không thể tải thông tin thủ tục. Vui lòng thử lại.',
          isStreaming: false,
        })
      } finally {
        updateMessage(assistantId, { isStreaming: false })
        setStreaming(false)
      }
    }
    doSilentPrime()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  /* inject static welcome message on homepage inline chat — fires once on
     mount, guard inside injectWelcomeMessage prevents double-injection */
  useEffect(() => {
    if (variant !== 'inline') return
    injectWelcomeMessage()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSend = useCallback(async (overrideText?: string) => {
    const text = overrideText ?? input.trim()
    if (!text || isStreaming) return

    if (!overrideText) setInput('')
    if (!overrideText) addMessage({ role: 'user', content: text, citations: [] })

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
        content: '...',
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
      // Tracks whether the backend sent a final metadata event (synthesizer mode).
      // If the stream closes before this is set and we have partial content,
      // the connection dropped mid-stream.
      let receivedFinalMetadata = false

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
            // Store response mode for render path selection.
            if (parsed.metadata?.mode) {
              updateMessage(assistantId, { messageMode: parsed.metadata.mode as string })
              receivedFinalMetadata = true
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

      // Mid-stream connection drop: stream closed normally but no final metadata
      // event arrived, and content was already streaming — treat as error.
      if (!receivedFinalMetadata && accumulated.length > 0) {
        if (warmupTimerRef.current) {
          clearTimeout(warmupTimerRef.current)
          warmupTimerRef.current = null
        }
        updateMessage(assistantId, {
          content: 'Đã xảy ra lỗi khi xử lý yêu cầu của bạn. Vui lòng thử lại.',
          isStreaming: false,
          isError: true,
        })
        setLastFailedMessage(text)
        setStreaming(false)
        return
      }
    } catch (err: any) {
      if (warmupTimerRef.current) {
        clearTimeout(warmupTimerRef.current)
        warmupTimerRef.current = null
      }
      const status = err?.status
      let errorMessage = 'Đã xảy ra lỗi khi xử lý yêu cầu của bạn. Vui lòng thử lại.'
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
        isError: true,
      })
      setLastFailedMessage(text)
    } finally {
      if (warmupTimerRef.current) {
        clearTimeout(warmupTimerRef.current)
        warmupTimerRef.current = null
      }
      updateMessage(assistantId, { isStreaming: false })
      setStreaming(false)
    }
  }, [input, isStreaming, sessionId, uploadedFile, addMessage, updateMessage, setStreaming, setUploadedFile, setLastFailedMessage])

  const handleRetry = useCallback(async () => {
    if (!lastFailedMessage) return
    removeLastMessage()
    setLastFailedMessage(null)
    await handleSend(lastFailedMessage)
  }, [lastFailedMessage, handleSend, removeLastMessage])

  const handleGeneralRetry = useCallback(() => {
    const lastUser = [...messages].reverse().find(m => m.role === 'user')
    if (!lastUser || isStreaming) return
    removeLastMessage()
    handleSend(lastUser.content)
  }, [messages, isStreaming, removeLastMessage, handleSend])

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

  const handleFeedback = useCallback(async (messageId: string, feedback: FeedbackType) => {
    updateMessage(messageId, { feedback })
    try {
      await fetch('/api/v1/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message_id: messageId,
          feedback,
          timestamp: new Date().toISOString(),
        }),
      })
    } catch {
      // Silently ignore — feedback is best-effort
    }
  }, [sessionId, updateMessage])

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploadedFile({ file, previewUrl: URL.createObjectURL(file) })
    e.target.value = ''
  }

  /* ─── shared body (messages + file preview + input) ──────── */

  function renderBody() {
    return (
      <>
        {/* Guided procedure progress bar — TASK-APP-18 */}
        {guidedProcedureId && (
          <GuidedProgressBar
            procedureId={guidedProcedureId}
            step={guidedStep}
            onExit={handleExitGuided}
          />
        )}

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 bg-[var(--warm-white)]">
          {messages.length === 0 && (
            <div className="py-6 text-center text-[var(--text-muted)] text-xs leading-relaxed">
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
                    ? 'bg-[var(--navy)] text-white'
                    : msg.isError
                      ? 'bg-red-50 border border-red-200 text-[var(--text-primary)]'
                      : 'bg-white border border-[var(--border-card)] text-[var(--text-primary)]'
                  }`}
              >
                {msg.isStreaming && (!msg.content || msg.content === '...')
                  ? (
                    <>
                      <p className="text-sm text-[var(--text-muted)] italic mb-1.5">Đang sinh câu trả lời</p>
                      <AnimatedDots />
                    </>
                  )
                  : msg.isStreaming
                    ? <span className="whitespace-pre-wrap">{msg.content}</span>
                    : msg.isError
                      ? <span className="whitespace-pre-wrap">⚠️ {msg.content}</span>
                      : renderWithCitations(msg.content, msg.retrievedSources ?? [])
                }
                {msg.isError && lastFailedMessage && (
                  <button
                    onClick={() => handleRetry()}
                    className="mt-2 text-xs text-[var(--terracotta)] hover:underline flex items-center gap-1"
                  >
                    Thử lại
                  </button>
                )}
              </div>

              {!msg.isStreaming && !msg.isError && msg.role === 'assistant' && (
                <div className="flex items-center gap-2 mt-1 ml-1">
                  <button
                    onClick={() => handleFeedback(msg.id, 'helpful')}
                    disabled={msg.feedback !== undefined}
                    className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                      msg.feedback === 'helpful'
                        ? 'bg-green-50 border-green-200 text-green-600'
                        : 'border-[var(--border-card)] text-[var(--text-muted)] hover:border-green-300 hover:text-green-500'
                    }`}
                  >
                    👍
                  </button>
                  <button
                    onClick={() => handleFeedback(msg.id, 'unhelpful')}
                    disabled={msg.feedback !== undefined}
                    className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                      msg.feedback === 'unhelpful'
                        ? 'bg-red-50 border-red-200 text-red-500'
                        : 'border-[var(--border-card)] text-[var(--text-muted)] hover:border-red-300 hover:text-red-400'
                    }`}
                  >
                    👎
                  </button>
                  {msg.feedback && (
                    <span className="text-xs text-[var(--text-muted)]">
                      {msg.feedback === 'helpful' ? 'Cảm ơn phản hồi của bạn' : 'Chúng tôi sẽ cải thiện'}
                    </span>
                  )}
                </div>
              )}

              {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                <CitationChips citations={msg.citations} />
              )}

              {msg.role === 'assistant' && !msg.isStreaming && msg.filledFormPath && (
                <div className="mt-2">
                  <a
                    href={`${process.env.NEXT_PUBLIC_API_URL_PUBLIC || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/documents/download?path=${encodeURIComponent(msg.filledFormPath)}&session_id=${encodeURIComponent(sessionId)}`}
                    download
                    className="inline-flex items-center gap-2 px-3 py-2 rounded
                               bg-[var(--terracotta)] text-white text-sm font-medium
                               hover:bg-[var(--terracotta-dk)] transition-colors"
                  >
                    📄 Tải xuống tờ khai đã điền
                  </a>
                </div>
              )}
            </div>
          ))}

          {/* Thử lại — visible only after a completed (non-error) assistant message */}
          {messages.length > 0 &&
            messages[messages.length - 1]?.role === 'assistant' &&
            !messages[messages.length - 1]?.isStreaming &&
            !isStreaming &&
            !messages[messages.length - 1]?.isError && (
              <div className="flex justify-start">
                <button
                  onClick={handleGeneralRetry}
                  className="flex items-center gap-1 text-xs text-[var(--text-muted)] hover:text-[var(--terracotta)] transition-colors py-1"
                >
                  <RotateCcw className="w-3 h-3" />
                  Thử lại
                </button>
              </div>
            )}
        </div>

        {/* Uploaded file preview */}
        {uploadedFile && (
          <div className="flex items-center gap-2 px-4 py-2 bg-[var(--terracotta-faint)] border-t border-[var(--border-card)]">
            <Paperclip className="w-3.5 h-3.5 text-[var(--terracotta)] flex-shrink-0" />
            <span className="text-xs text-[var(--text-secondary)] truncate flex-1">{uploadedFile.file.name}</span>
            <button
              onClick={() => setUploadedFile(null)}
              className="text-[var(--text-muted)] hover:text-[var(--text-secondary)] transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Input area */}
        <div className="border-t border-[var(--border-card)] bg-white px-3 py-3 flex items-end gap-2">
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
            className="text-[var(--text-muted)] hover:text-[var(--terracotta)] transition-colors p-1 flex-shrink-0 self-end mb-0.5"
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
            className="flex-1 resize-none bg-[var(--warm-white)] border border-[var(--border-card)]
                       rounded-xl px-4 py-2.5 text-sm focus:outline-none
                       focus:border-[var(--terracotta)] transition-colors disabled:opacity-50
                       max-h-[120px] overflow-y-auto leading-snug"
          />

          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isStreaming}
            className="bg-[var(--terracotta)] hover:bg-[var(--terracotta-dk)] text-white
                       rounded-xl px-4 py-2.5 text-sm font-medium transition-colors
                       flex-shrink-0 self-end
                       disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </>
    )
  }

  /* ─── inline variant ──────────────────────────────────────── */

  if (variant === 'inline') {
    return (
      <div className="w-full h-[520px] border border-[var(--border-card)] rounded-2xl bg-[var(--warm-white)] flex flex-col overflow-hidden">
        {/* Header with new-conversation + expand buttons */}
        <div className="flex items-center justify-between px-4 py-3 bg-[var(--terracotta)] flex-shrink-0">
          <div>
            <p className="text-white font-medium text-sm">Trợ lý AI</p>
            <p className="text-white/70 text-xs">Dịch vụ công TP. Hồ Chí Minh</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={clearSession}
              title="Cuộc trò chuyện mới"
              aria-label="Cuộc trò chuyện mới"
              className="text-white/80 hover:text-white transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <Link
              href="/chat"
              title="Mở rộng"
              aria-label="Mở rộng"
              className="text-white/80 hover:text-white transition-colors"
            >
              <Maximize2 className="w-4 h-4" />
            </Link>
          </div>
        </div>
        {renderBody()}
      </div>
    )
  }

  /* ─── floating variant (default) ─────────────────────────── */

  return (
    <>
      {/* Floating toggle button */}
      <button
        onClick={toggle}
        aria-label="Mở hộp trợ lý ảo"
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-[var(--navy)]
                   flex items-center justify-center text-white
                   hover:bg-[var(--navy-mid)] transition-colors shadow-lg"
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
          <div className="flex items-center justify-between px-4 py-3 bg-[var(--terracotta)]">
            <div>
              <p className="text-white font-medium text-sm">Trợ lý AI</p>
              <p className="text-white/70 text-xs">Dịch vụ công TP. Hồ Chí Minh</p>
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
                className="text-white/80 hover:text-white hover:bg-[var(--terracotta-dk)] transition-colors"
                aria-label="Đóng"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {renderBody()}
        </div>
      )}
    </>
  )
}
