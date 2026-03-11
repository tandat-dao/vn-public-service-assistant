'use client'
import { create } from 'zustand'
import type { ProcedureStep } from '@/lib/types'

interface ProcedureStore {
  selectedProcedureId: string | null
  executionPlan: ProcedureStep[]
  completedProcedureIds: string[]
  selectProcedure:  (id: string) => void
  setExecutionPlan: (plan: ProcedureStep[]) => void
  markCompleted:    (id: string) => void
  clearPlan:        () => void
}

export const useProcedureStore = create<ProcedureStore>((set) => ({
  selectedProcedureId: null,
  executionPlan:       [],
  completedProcedureIds: [],
  selectProcedure:  (id)   => set({ selectedProcedureId: id }),
  setExecutionPlan: (plan) => set({ executionPlan: plan }),
  markCompleted: (id) =>
    set((s) => ({ completedProcedureIds: [...s.completedProcedureIds, id] })),
  clearPlan: () => set({ executionPlan: [], selectedProcedureId: null }),
}))
