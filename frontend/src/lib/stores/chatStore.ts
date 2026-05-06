'use client'
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { v4 as uuidv4 } from 'uuid'
import type { ChatMessage, PersonalData, ProcedureStep, UploadedFile } from '@/lib/types'

// Stable cross-session identifier stored in localStorage (distinct from sessionId
// which lives in sessionStorage and is tab-scoped). Initialised once per browser
// profile; survives tab closes and browser restarts. Backend TTL: 24 hours.
function getOrCreateCitizenId(): string {
  if (typeof window === 'undefined') return ''
  const stored = localStorage.getItem('dvc_citizen_id')
  if (stored) return stored
  const newId = crypto.randomUUID()
  localStorage.setItem('dvc_citizen_id', newId)
  return newId
}

interface ChatStore {
  isOpen: boolean
  sessionId: string
  citizenId: string
  messages: ChatMessage[]
  isStreaming: boolean
  uploadedFile: UploadedFile | null
  procedurePlan: ProcedureStep[] | null
  guidedProcedureId: string | null
  guidedStep: number | null
  personalData: PersonalData | null
  open: () => void
  close: () => void
  toggle: () => void
  addMessage: (msg: Omit<ChatMessage, 'id' | 'timestamp'>) => string
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void
  removeLastMessage: () => void
  setStreaming: (v: boolean) => void
  setUploadedFile: (f: UploadedFile | null) => void
  setProcedurePlan: (plan: ProcedureStep[] | null) => void
  setPersonalData: (data: PersonalData | null) => void
  setGuidedProcedureId: (id: string | null) => void
  setGuidedStep: (step: number | null) => void
  injectWelcomeMessage: () => void
  clearSession: () => void
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      isOpen: false,
      sessionId: uuidv4(),
      citizenId: getOrCreateCitizenId(),
      messages: [],
      isStreaming: false,
      uploadedFile: null,
      procedurePlan: null,
      guidedProcedureId: null,
      guidedStep: null,
      personalData: null,

      open:   () => set({ isOpen: true }),
      close:  () => set({ isOpen: false }),
      toggle: () => set((s) => ({ isOpen: !s.isOpen })),

      addMessage: (msg) => {
        const id = uuidv4()
        set((s) => ({ messages: [...s.messages, { ...msg, id, timestamp: new Date() }] }))
        return id
      },

      updateMessage: (id, updates) =>
        set((s) => ({
          messages: s.messages.map((m) => (m.id === id ? { ...m, ...updates } : m)),
        })),

      removeLastMessage: () =>
        set((s) => ({ messages: s.messages.slice(0, -1) })),

      setStreaming:          (v) => set({ isStreaming: v }),
      setUploadedFile:       (f) => set({ uploadedFile: f }),
      setProcedurePlan:      (p) => set({ procedurePlan: p }),
      setPersonalData:       (data) => set({ personalData: data }),
      setGuidedProcedureId:  (id) => set({ guidedProcedureId: id }),
      setGuidedStep:         (step) => set({ guidedStep: step }),

      injectWelcomeMessage: () => {
        const { messages } = get()
        if (messages.length > 0) return
        const welcomeMessage: ChatMessage = {
          id: 'welcome',
          role: 'assistant',
          content:
            'Xin chào! Tôi là trợ lý AI hỗ trợ hướng dẫn ' +
            'thủ tục hành chính tại TP. Hồ Chí Minh. Bạn có thể ' +
            'hỏi tôi về các thủ tục đăng ký cư trú, hộ tịch, ' +
            'hoặc nuôi con nuôi.',
          timestamp: new Date(),
          isStreaming: false,
        }
        set({ messages: [welcomeMessage] })
      },

      clearSession: () =>
        set({
          messages: [],
          sessionId: uuidv4(),
          procedurePlan: null,
          uploadedFile: null,
          guidedProcedureId: null,
          guidedStep: null,
        }),
    }),
    {
      name: 'dvc-chat-session',
      storage: createJSONStorage(() =>
        typeof window !== 'undefined'
          ? sessionStorage
          : {
              getItem: () => null,
              setItem: () => {},
              removeItem: () => {},
            }
      ),
      // Persist only these fields. isStreaming is transient — always false on mount.
      // citizenId uses localStorage separately and is excluded here.
      partialize: (state) => ({
        sessionId: state.sessionId,
        messages: state.messages,
        guidedProcedureId: state.guidedProcedureId,
        guidedStep: state.guidedStep,
        personalData: state.personalData,
      }),
      // After rehydration, convert serialised timestamp strings back to Date objects
      // so that toLocaleTimeString() works correctly in the chat page.
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.messages = state.messages.map((m) => ({
            ...m,
            timestamp: m.timestamp instanceof Date ? m.timestamp : new Date(m.timestamp as unknown as string),
          }))
        }
      },
    }
  )
)
