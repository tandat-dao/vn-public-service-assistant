'use client'
import { create } from 'zustand'
import { v4 as uuidv4 } from 'uuid'
import type { ChatMessage, ProcedureStep, UploadedFile } from '@/lib/types'

interface ChatStore {
  isOpen: boolean
  sessionId: string
  messages: ChatMessage[]
  isStreaming: boolean
  uploadedFile: UploadedFile | null
  procedurePlan: ProcedureStep[] | null
  open: () => void
  close: () => void
  toggle: () => void
  addMessage: (msg: Omit<ChatMessage, 'id' | 'timestamp'>) => string
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void
  setStreaming: (v: boolean) => void
  setUploadedFile: (f: UploadedFile | null) => void
  setProcedurePlan: (plan: ProcedureStep[] | null) => void
  clearSession: () => void
}

export const useChatStore = create<ChatStore>((set) => ({
  isOpen: false,
  sessionId: uuidv4(),
  messages: [],
  isStreaming: false,
  uploadedFile: null,
  procedurePlan: null,

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

  setStreaming:     (v) => set({ isStreaming: v }),
  setUploadedFile:  (f) => set({ uploadedFile: f }),
  setProcedurePlan: (p) => set({ procedurePlan: p }),

  clearSession: () =>
    set({ messages: [], sessionId: uuidv4(), procedurePlan: null, uploadedFile: null }),
}))
