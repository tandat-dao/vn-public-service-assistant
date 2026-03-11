import { create } from "zustand";
import type { PersonalData } from "../types/document";

type SessionState = {
  sessionId: string;
  personalData: PersonalData | null;
  completedProcedureIds: string[];
  setPersonalData: (data: PersonalData) => void;
  markProcedureComplete: (id: string) => void;
  reset: () => void;
};

export const useSessionStore = create<SessionState>((set) => ({
  sessionId: crypto.randomUUID(),
  personalData: null,
  completedProcedureIds: [],
  setPersonalData: (data) => set({ personalData: data }),
  markProcedureComplete: (id) =>
    set((state) => ({
      completedProcedureIds: state.completedProcedureIds.includes(id)
        ? state.completedProcedureIds
        : [...state.completedProcedureIds, id],
    })),
  reset: () =>
    set({ sessionId: crypto.randomUUID(), personalData: null, completedProcedureIds: [] }),
}));
