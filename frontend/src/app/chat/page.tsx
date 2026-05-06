'use client'
import { useRef, useState, useEffect, useCallback } from 'react'
import {
  Send, Paperclip, Plus, ChevronRight,
  CheckCircle2, Clock, Lock,
} from 'lucide-react'
import { useChatStore } from '@/lib/stores/chatStore'
import { streamChat, api } from '@/lib/api/client'
import type { Citation, ProcedureStep } from '@/lib/types'

/* ─── Citation chips ────────────────────────────────────────── */
function CitationChips({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null
  return (
    <div className="mt-2 flex flex-wrap gap-1">
      {citations.map((c) => (
        <span key={c.doc_id} className="citation-chip" title={c.excerpt}>
          {c.article}, {c.document_number}
        </span>
      ))}
    </div>
  )
}

/* ─── Loading dots ───────────────────────────────────────────── */
function LoadingDots() {
  return (
    <div className="flex items-center gap-1 py-1">
      <span className="chat-dot w-2 h-2 rounded-full bg-[#CE7A58] inline-block" />
      <span className="chat-dot w-2 h-2 rounded-full bg-[#CE7A58] inline-block" />
      <span className="chat-dot w-2 h-2 rounded-full bg-[#CE7A58] inline-block" />
    </div>
  )
}

/* ─── Procedure step icon ────────────────────────────────────── */
function StepIcon({ status }: { status: ProcedureStep['status'] }) {
  if (status === 'completed')
    return <CheckCircle2 className="w-4 h-4 text-[#28A745] flex-shrink-0" />
  if (status === 'pending')
    return <Clock className="w-4 h-4 text-[#CE7A58] flex-shrink-0" />
  return <Lock className="w-4 h-4 text-[#999] flex-shrink-0" />
}

/* ─── Procedure plan panel ────────────────────────────────────── */
function ProcedurePlanPanel({
  plan,
  onClose,
}: {
  plan: ProcedureStep[]
  onClose: () => void
}) {
  return (
    <aside className="w-72 flex-shrink-0 border-l border-[#DDDDDD] flex flex-col bg-[#FAFAFA]">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#DDDDDD]">
        <span className="font-semibold text-sm text-[#1E2F41]">Kế hoạch thủ tục</span>
        <button onClick={onClose} className="text-[#999] hover:text-[#555] text-xs">
          Ẩn
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        {plan.map((step, i) => (
          <div
            key={step.id}
            className={`flex gap-2 p-2.5 rounded border text-xs
              ${step.status === 'completed'
                ? 'border-[#28A745]/30 bg-white'
                : step.status === 'pending'
                  ? 'border-[#CE7A58]/30 bg-white'
                  : 'border-[#DDDDDD] bg-[#F5F5F5] opacity-70'
              }`}
          >
            <div className="mt-0.5">
              <StepIcon status={step.status} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-[#1E2F41] leading-tight truncate">
                Bước {i + 1}: {step.name}
              </div>
              {step.reason && (
                <div className="text-[#999] mt-0.5 text-[11px]">{step.reason}</div>
              )}
              {step.required_documents && step.required_documents.length > 0 && (
                <ul className="mt-1 space-y-0.5">
                  {step.required_documents.map((doc) => (
                    <li key={doc} className="text-[#555] flex gap-1">
                      <ChevronRight className="w-3 h-3 mt-0.5 flex-shrink-0 text-[#CE7A58]" />
                      {doc}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        ))}
      </div>
    </aside>
  )
}

/* ─── Sidebar session list ───────────────────────────────────── */
function Sidebar({ onNewChat }: { onNewChat: () => void }) {
  return (
    <aside className="w-56 flex-shrink-0 border-r border-[#DDDDDD] flex flex-col bg-[#FAFAFA]">
      <div className="p-3 border-b border-[#DDDDDD]">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 py-2 px-3
                     bg-[#CE7A58] text-white text-sm rounded hover:bg-[#B8694A] transition-colors"
        >
          <Plus className="w-4 h-4" />
          Cuộc trò chuyện mới
        </button>
      </div>

      <div className="flex-1 overflow-y-auto py-2">
        <div className="text-sm text-gray-400 italic px-3 py-4">
          Chưa có lịch sử cuộc trò chuyện.
        </div>
      </div>
    </aside>
  )
}

/* ─── Main chat page ─────────────────────────────────────────── */
export default function ChatPage() {
  const {
    sessionId, messages, isStreaming, setStreaming,
    addMessage, updateMessage, uploadedFile,
    setUploadedFile, clearSession, procedurePlan,
  } = useChatStore()

  const [input, setInput]               = useState('')
  const [showPlan, setShowPlan]         = useState(false)
  const [lastUploadedPath, setLastUploadedPath] = useState<string | null>(null)
  const bottomRef  = useRef<HTMLDivElement>(null)
  const fileRef    = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (procedurePlan && procedurePlan.length > 0) setShowPlan(true)
  }, [procedurePlan])

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`
  }, [input])

  const handleSend = useCallback(async () => {
    const text = input.trim()
    if (!text || isStreaming) return

    setInput('')
    addMessage({ role: 'user', content: text, citations: [] })

    const assistantId = addMessage({
      role: 'assistant', content: '', citations: [], isStreaming: true,
    })

    setStreaming(true)

    // Step 1: upload file if attached
    let imagePath: string | null = lastUploadedPath
    if (uploadedFile) {
      try {
        const uploadResult = await api.documents.upload(uploadedFile.file, sessionId)
        setUploadedFile(null)
        imagePath = uploadResult.tmp_path
        setLastUploadedPath(uploadResult.tmp_path)
      } catch {
        updateMessage(assistantId, {
          content: 'Không thể tải lên tệp. Vui lòng thử lại.',
          isStreaming: false,
        })
        setStreaming(false)
        return
      }
    }

    if (!uploadedFile) setLastUploadedPath(null)

    // Step 2: stream chat
    try {
      let accumulated = ''
      for await (const chunk of streamChat(sessionId, text, imagePath ?? undefined)) {
        try {
          const parsed = JSON.parse(chunk)
          if ('content' in parsed && typeof parsed.content === 'string') {
            accumulated += parsed.content
            updateMessage(assistantId, { content: accumulated })
          } else if ('metadata' in parsed) {
            if (Array.isArray(parsed.metadata?.citations)) {
              updateMessage(assistantId, { citations: parsed.metadata.citations as Citation[] })
            }
            if (
              parsed.metadata?.mode === 'form_fill_complete' &&
              typeof parsed.metadata?.filled_form_path === 'string' &&
              parsed.metadata.filled_form_path
            ) {
              updateMessage(assistantId, { filledFormPath: parsed.metadata.filled_form_path as string })
            }
          }
        } catch {
          accumulated += chunk
          updateMessage(assistantId, { content: accumulated })
        }
      }
    } catch {
      updateMessage(assistantId, {
        content: 'Xin lỗi, đã xảy ra lỗi khi kết nối máy chủ. Vui lòng thử lại.',
        isStreaming: false,
      })
    } finally {
      updateMessage(assistantId, { isStreaming: false })
      setStreaming(false)
    }
  }, [input, isStreaming, sessionId, uploadedFile, lastUploadedPath, addMessage, updateMessage, setStreaming, setUploadedFile])

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploadedFile({ file, previewUrl: URL.createObjectURL(file) })
    e.target.value = ''
  }

  const SUGGESTIONS = [
    'Tôi muốn đăng ký thường trú tại TP.HCM, cần những gì?',
    'Lệ phí đăng ký khai sinh tại Hà Nội là bao nhiêu?',
    'Điều kiện để nhận con nuôi trong nước là gì?',
    'Hướng dẫn tôi làm thủ tục đăng ký khai sinh',
  ]

  return (
    <div className="max-w-container mx-auto px-4 py-4">
      <h1 className="text-xl font-bold text-[#1E2F41] mb-4">Trợ lý hành chính AI</h1>

      <div
        className="border border-[#DDDDDD] rounded-[6px] overflow-hidden flex"
        style={{ height: 'calc(100vh - 220px)', minHeight: '500px' }}
      >
        {/* Sidebar */}
        <Sidebar onNewChat={clearSession} />

        {/* Main chat area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center gap-4">
                <div className="text-5xl">🤖</div>
                <div>
                  <p className="font-semibold text-[#1E2F41] text-base mb-1">
                    Xin chào! Tôi là trợ lý hành chính AI
                  </p>
                  <p className="text-sm text-[#999] max-w-sm">
                    Tôi có thể giúp bạn tra cứu thủ tục, điền tờ khai, phân tích
                    hồ sơ và giải đáp câu hỏi về dịch vụ công.
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-2 max-w-md w-full mt-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => setInput(s)}
                      className="text-left text-xs border border-[#DDDDDD] rounded p-2.5
                                 hover:border-[#CE7A58] hover:text-[#CE7A58] transition-colors
                                 text-[#555] leading-snug"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="flex items-center gap-1.5 mb-1">
                    <div className="w-5 h-5 rounded-full bg-[#CE7A58] flex items-center justify-center">
                      <span className="text-white text-[10px] font-bold">AI</span>
                    </div>
                    <span className="text-[11px] text-[#999]">Trợ lý hành chính</span>
                  </div>
                )}

                <div
                  className={`max-w-[70%] px-4 py-2.5 rounded-[6px] text-sm leading-relaxed
                    ${msg.role === 'user'
                      ? 'bg-[#CE7A58] text-white'
                      : 'bg-[#F5F5F5] text-[#1E2F41]'
                    }`}
                >
                  {msg.isStreaming && !msg.content
                    ? <LoadingDots />
                    : <span className="whitespace-pre-wrap">{msg.content}</span>
                  }
                </div>

                {msg.role === 'assistant' && msg.citations && (
                  <CitationChips citations={msg.citations} />
                )}

                {msg.role === 'assistant' && !msg.isStreaming && msg.filledFormPath && (
                  <div className="mt-2">
                    <a
                      href={`${process.env.NEXT_PUBLIC_API_URL_PUBLIC || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/documents/download?path=${encodeURIComponent(msg.filledFormPath)}&session_id=${encodeURIComponent(sessionId)}`}
                      download
                      className="inline-flex items-center gap-2 px-3 py-2 rounded
                                 bg-[#CE7A58] text-white text-sm font-medium
                                 hover:bg-[#B8694A] transition-colors"
                    >
                      📄 Tải xuống tờ khai đã điền
                    </a>
                  </div>
                )}

                <span className="text-[10px] text-[#CCC] mt-1">
                  {msg.timestamp.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Uploaded file preview */}
          {uploadedFile && (
            <div className="flex items-center gap-2 px-4 py-2 border-t border-[#DDDDDD] bg-[#FFF8F5]">
              <Paperclip className="w-4 h-4 text-[#CE7A58] flex-shrink-0" />
              <span className="text-sm text-[#555] truncate flex-1">{uploadedFile.file.name}</span>
              <button
                onClick={() => setUploadedFile(null)}
                className="text-[#999] hover:text-[#555] text-xs"
              >
                Xóa
              </button>
            </div>
          )}

          {/* Input bar */}
          <div className="border-t border-[#DDDDDD] px-4 py-3 flex items-end gap-3 bg-white">
            <input
              ref={fileRef}
              type="file"
              accept="image/*,.pdf"
              className="hidden"
              onChange={handleFileChange}
            />

            <button
              onClick={() => fileRef.current?.click()}
              title="Đính kèm tệp (ảnh CCCD, PDF)"
              className="text-[#999] hover:text-[#CE7A58] transition-colors flex-shrink-0 self-end pb-2"
            >
              <Paperclip className="w-5 h-5" />
            </button>

            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Nhập câu hỏi hoặc mô tả thủ tục bạn cần… (Enter để gửi, Shift+Enter để xuống dòng)"
              rows={1}
              disabled={isStreaming}
              className="flex-1 resize-none border border-[#DDDDDD] rounded px-3 py-2.5 text-sm
                         focus:outline-none focus:border-[#CE7A58] disabled:opacity-50
                         max-h-[140px] overflow-y-auto leading-relaxed"
            />

            <button
              onClick={handleSend}
              disabled={!input.trim() || isStreaming}
              className="bg-[#CE7A58] text-white rounded px-4 py-2.5 text-sm font-semibold
                         flex items-center gap-1.5 flex-shrink-0 self-end
                         hover:bg-[#B8694A] disabled:opacity-40 disabled:cursor-not-allowed
                         transition-colors"
            >
              <Send className="w-4 h-4" />
              Gửi
            </button>
          </div>
        </div>

        {/* Procedure plan panel — shown when plan exists */}
        {showPlan && procedurePlan && procedurePlan.length > 0 && (
          <ProcedurePlanPanel
            plan={procedurePlan}
            onClose={() => setShowPlan(false)}
          />
        )}
      </div>
    </div>
  )
}
