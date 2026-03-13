'use client'
import { create } from 'zustand'
import type {
  FieldSource,
  FieldState,
  FormSubmissionResponse,
  FormType,
  ResidenceFormData,
} from '@/lib/types'

type FieldRegistry = Record<FormType, Record<string, FieldState>>

interface FormStore {
  // State
  fields: FieldRegistry
  submissionResult: Record<FormType, FormSubmissionResponse | null>
  isSubmitting: Record<FormType, boolean>

  /**
   * Set a single field value.
   * Called by user input (source='manual', confidence=1.0) and by the AI
   * form-filler node in Phase 2 (source='ai', confidence=0–1).
   */
  setFieldValue: (
    formType: FormType,
    fieldKey: keyof ResidenceFormData,
    value: string,
    source: FieldSource,
    confidence: number,
  ) => void

  /**
   * Bulk-apply AI extraction results.
   * Implements carry-forward merge rule: higher confidence wins.
   * Called by the agent after OCR extraction (Phase 2).
   */
  applyAIExtraction: (
    formType: FormType,
    extracted: Partial<Record<keyof ResidenceFormData, { value: string; confidence: number }>>,
  ) => void

  /** Clear AI highlight flags once user has acknowledged the AI-filled values. */
  clearAIHighlights: (formType: FormType) => void

  /**
   * Return field values as a plain object for react-hook-form reset().
   * Populated fields take precedence; unset fields are omitted.
   */
  getFormValues: (formType: FormType) => Partial<ResidenceFormData>

  // Submission lifecycle
  setSubmitting: (formType: FormType, v: boolean) => void
  setSubmissionResult: (formType: FormType, result: FormSubmissionResponse | null) => void

  /** Reset all field state and submission result for a form type. */
  resetForm: (formType: FormType) => void
}

const FORM_TYPES: FormType[] = ['thuong-tru', 'tam-tru', 'xac-nhan']

function emptyRegistry(): FieldRegistry {
  return Object.fromEntries(FORM_TYPES.map((t) => [t, {}])) as FieldRegistry
}

export const useFormStore = create<FormStore>((set, get) => ({
  fields: emptyRegistry(),
  submissionResult: { 'thuong-tru': null, 'tam-tru': null, 'xac-nhan': null },
  isSubmitting: { 'thuong-tru': false, 'tam-tru': false, 'xac-nhan': false },

  setFieldValue: (formType, fieldKey, value, source, confidence) =>
    set((s) => ({
      fields: {
        ...s.fields,
        [formType]: {
          ...s.fields[formType],
          [fieldKey]: { value, source, confidence, aiHighlight: source === 'ai' },
        },
      },
    })),

  applyAIExtraction: (formType, extracted) =>
    set((s) => {
      const current = { ...s.fields[formType] }
      for (const [key, ext] of Object.entries(extracted)) {
        if (!ext) continue
        const existing = current[key]
        // Carry-forward merge rule: higher confidence wins (mirrors SessionDataAccumulator.merge())
        if (!existing || ext.confidence >= existing.confidence) {
          current[key] = { value: ext.value, source: 'ai', confidence: ext.confidence, aiHighlight: true }
        }
      }
      return { fields: { ...s.fields, [formType]: current } }
    }),

  clearAIHighlights: (formType) =>
    set((s) => ({
      fields: {
        ...s.fields,
        [formType]: Object.fromEntries(
          Object.entries(s.fields[formType]).map(([k, v]) => [k, { ...v, aiHighlight: false }])
        ),
      },
    })),

  getFormValues: (formType) => {
    const registry = get().fields[formType]
    return Object.fromEntries(
      Object.entries(registry).map(([k, v]) => [k, v.value])
    ) as Partial<ResidenceFormData>
  },

  setSubmitting: (formType, v) =>
    set((s) => ({ isSubmitting: { ...s.isSubmitting, [formType]: v } })),

  setSubmissionResult: (formType, result) =>
    set((s) => ({ submissionResult: { ...s.submissionResult, [formType]: result } })),

  resetForm: (formType) =>
    set((s) => ({
      fields: { ...s.fields, [formType]: {} },
      submissionResult: { ...s.submissionResult, [formType]: null },
    })),
}))
