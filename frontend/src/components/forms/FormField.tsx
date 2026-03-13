'use client'
import { forwardRef } from 'react'
import type {
  InputHTMLAttributes,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from 'react'
import { clsx } from 'clsx'

// ── Shared base props ─────────────────────────────────────────────────────────

interface BaseFieldProps {
  label: string
  required?: boolean
  error?: string
  /**
   * When true the field was filled by the AI agent.
   * Always false in Phase 1 (manual input only).
   * Phase 2: set to true when source === 'ai' in the form store.
   */
  aiHighlight?: boolean
  hint?: string
  className?: string
}

function FieldLabel({ label, required }: { label: string; required?: boolean }) {
  return (
    <label className="text-sm font-semibold text-[#1E2F41]">
      {label}
      {required && <span className="text-[#CC0000] ml-0.5">*</span>}
    </label>
  )
}

function AiCaption() {
  return (
    <span className="text-[11px] text-[#CE7A58]">Đã điền tự động bởi AI</span>
  )
}

function ErrorMsg({ id, message }: { id?: string; message: string }) {
  return (
    <span id={id} className="text-[11px] text-[#CC0000]" role="alert">
      {message}
    </span>
  )
}

function fieldClasses(aiHighlight: boolean, error: boolean) {
  return clsx(
    'border px-3 py-2 text-sm rounded focus:outline-none transition-colors',
    'text-[#1E2F41] bg-white placeholder:text-[#999]',
    aiHighlight
      ? 'border-[#CE7A58] bg-[#FFF8F5]'
      : error
      ? 'border-[#CC0000]'
      : 'border-[#DDDDDD] focus:border-[#CE7A58]',
  )
}

// ── FormInput ─────────────────────────────────────────────────────────────────

export interface FormInputProps
  extends BaseFieldProps,
    Omit<InputHTMLAttributes<HTMLInputElement>, 'className'> {}

export const FormInput = forwardRef<HTMLInputElement, FormInputProps>(
  ({ label, required, error, aiHighlight = false, hint, className, id, ...rest }, ref) => (
    <div className={clsx('flex flex-col gap-1', className)}>
      <FieldLabel label={label} required={required} />
      <input
        ref={ref}
        id={id}
        className={fieldClasses(aiHighlight, !!error)}
        aria-invalid={!!error}
        aria-describedby={error && id ? `${id}-error` : undefined}
        {...rest}
      />
      {aiHighlight && <AiCaption />}
      {error && <ErrorMsg id={id ? `${id}-error` : undefined} message={error} />}
      {hint && !error && (
        <span className="text-[11px] text-[#999]">{hint}</span>
      )}
    </div>
  ),
)
FormInput.displayName = 'FormInput'

// ── FormSelect ────────────────────────────────────────────────────────────────

export interface FormSelectProps
  extends BaseFieldProps,
    Omit<SelectHTMLAttributes<HTMLSelectElement>, 'className'> {
  options: { value: string; label: string }[]
}

export const FormSelect = forwardRef<HTMLSelectElement, FormSelectProps>(
  ({ label, required, error, aiHighlight = false, hint, options, className, id, ...rest }, ref) => (
    <div className={clsx('flex flex-col gap-1', className)}>
      <FieldLabel label={label} required={required} />
      <select
        ref={ref}
        id={id}
        className={clsx(fieldClasses(aiHighlight, !!error), 'cursor-pointer')}
        aria-invalid={!!error}
        {...rest}
      >
        <option value="">-- Chọn --</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {aiHighlight && <AiCaption />}
      {error && <ErrorMsg message={error} />}
      {hint && !error && (
        <span className="text-[11px] text-[#999]">{hint}</span>
      )}
    </div>
  ),
)
FormSelect.displayName = 'FormSelect'

// ── FormTextarea ──────────────────────────────────────────────────────────────

export interface FormTextareaProps
  extends BaseFieldProps,
    Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'className'> {}

export const FormTextarea = forwardRef<HTMLTextAreaElement, FormTextareaProps>(
  ({ label, required, error, aiHighlight = false, hint, className, id, ...rest }, ref) => (
    <div className={clsx('flex flex-col gap-1', className)}>
      <FieldLabel label={label} required={required} />
      <textarea
        ref={ref}
        id={id}
        rows={3}
        className={clsx(fieldClasses(aiHighlight, !!error), 'resize-none')}
        aria-invalid={!!error}
        {...rest}
      />
      {aiHighlight && <AiCaption />}
      {error && <ErrorMsg message={error} />}
      {hint && !error && (
        <span className="text-[11px] text-[#999]">{hint}</span>
      )}
    </div>
  ),
)
FormTextarea.displayName = 'FormTextarea'
