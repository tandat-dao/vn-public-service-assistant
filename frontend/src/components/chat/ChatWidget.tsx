'use client'
import { useRef, useState, useEffect, useCallback } from 'react'
import { MessageCircle, X, Send, Paperclip, ChevronDown, Maximize2 } from 'lucide-react'
import Link from 'next/link'
import { useChatStore } from '@/lib/stores/chatStore'
import { streamChat } from '@/lib/api/client'
import type { Citation } from '@/lib/types'

/* ─── helpers ─────────────────────────────────────────────── */

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

/* ─── component ───────────────────────────────────────────── */

export function ChatWidget() {
  const {
    isOpen, toggle, close,
    sessionId, messages,
    isStreaming, setStreaming,
    addMessage, updateMessage,
    uploadedFile, setUploadedFile,
  } = useChatStore()

  const [input, setInput] = useState('')
  const bottomRef  = useRef<HTMLDivElement>(null)
  const fileRef    = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

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
    setUploadedFile(null)
    addMessage({ role: 'user', content: text, citations: [] })

    const assistantId = addMessage({
      role: 'assistant',
      content: '',
      citations: [],
      isStreaming: true,
    })

    setStreaming(true)
    try {
      let accumulated = ''
      for await (const chunk of streamChat(sessionId, text, uploadedFile?.file)) {
        try {
          const parsed = JSON.parse(chunk)
          if (parsed.type === 'text') {
            accumulated += parsed.content
            updateMessage(assistantId, { content: accumulated })
          } else if (parsed.type === 'citations') {
            updateMessage(assistantId, { citations: parsed.citations as Citation[] })
          }
        } catch {
          // plain text chunk (non-JSON fallback)
          accumulated += chunk
          updateMessage(assistantId, { content: accumulated })
        }
      }
    } catch (err) {
      updateMessage(assistantId, {
        content: 'Xin lỗi, đã có lỗi khi kết nối đến máy chủ. Vui lòng thử lại.',
        isStreaming: false,
      })
    } finally {
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
                    : <span className="whitespace-pre-wrap">{msg.content}</span>
                  }
                </div>

                {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                  <CitationChips citations={msg.citations} />
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
