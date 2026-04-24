'use client'

import { useState, useEffect } from 'react'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

interface FormFieldConfig {
  id: string
  label: string
  field_type: 'text' | 'date' | 'select' | 'textarea'
  cccd_source: string | null
  placeholder: string
  required: boolean
  options: string[] | null
}

interface FormConfig {
  form_file: string
  tab_label: string
  fields: FormFieldConfig[]
}

export interface ProcedureFormProps {
  procedureId: string
}

export function ProcedureForm({ procedureId }: ProcedureFormProps) {
  const [forms, setForms] = useState<FormConfig[]>([])
  const [activeTab, setActiveTab] = useState(0)
  const [fieldValues, setFieldValues] = useState<Record<string, Record<string, string>>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetch(`${BASE}/api/v1/forms/configs/${procedureId}`)
        if (!res.ok) { setForms([]); return }
        const data = await res.json()
        const loadedForms: FormConfig[] = data.forms ?? []
        setForms(loadedForms)
        const initial: Record<string, Record<string, string>> = {}
        for (const form of loadedForms) {
          initial[form.form_file] = {}
          for (const field of form.fields) {
            initial[form.form_file][field.id] = ''
          }
        }
        setFieldValues(initial)
      } catch {
        setForms([])
      } finally {
        setIsLoading(false)
      }
    }
    load()
  }, [procedureId])

  if (isLoading || forms.length === 0) return null

  const activeForm = forms[activeTab]
  const activeValues = fieldValues[activeForm?.form_file] ?? {}

  function setField(fieldId: string, value: string) {
    setFieldValues(prev => ({
      ...prev,
      [activeForm.form_file]: { ...(prev[activeForm.form_file] ?? {}), [fieldId]: value },
    }))
  }

  async function handleDownload() {
    if (!activeForm) return
    setIsSubmitting(true)
    setError(null)

    const converted: Record<string, string> = {}
    for (const field of activeForm.fields) {
      const val = activeValues[field.id] ?? ''
      if (field.field_type === 'date' && val) {
        const [y, m, d] = val.split('-')
        converted[field.id] = `${d}/${m}/${y}`
      } else {
        converted[field.id] = val
      }
    }

    try {
      const res = await fetch(`${BASE}/api/v1/forms/fill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          procedure_id: procedureId,
          form_file: activeForm.form_file,
          field_values: converted,
        }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        setError(body.detail ?? 'Không thể tải xuống mẫu đơn. Vui lòng thử lại.')
        return
      }

      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = activeForm.form_file
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch {
      setError('Không thể kết nối đến máy chủ. Vui lòng thử lại.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6">
      <h2 className="text-base font-semibold text-gray-900 mb-4">Tờ khai trực tuyến</h2>

      {/* Tabs — only shown when multiple forms */}
      {forms.length > 1 && (
        <div className="flex gap-0 border-b border-gray-200 mb-5">
          {forms.map((form, idx) => (
            <button
              key={form.form_file}
              onClick={() => setActiveTab(idx)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                activeTab === idx
                  ? 'border-[#CE7A58] text-[#CE7A58]'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {form.tab_label}
            </button>
          ))}
        </div>
      )}

      {/* Fields */}
      {activeForm && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {activeForm.fields.map(field => (
            <div
              key={field.id}
              className={field.field_type === 'textarea' ? 'sm:col-span-2' : ''}
            >
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {field.label}
                {field.required && <span className="text-red-500 ml-1">*</span>}
              </label>

              {field.field_type === 'select' && field.options ? (
                <select
                  value={activeValues[field.id] ?? ''}
                  onChange={e => setField(field.id, e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                             focus:outline-none focus:border-[#CE7A58] bg-white"
                >
                  <option value="">{field.placeholder}</option>
                  {field.options.map(opt => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              ) : field.field_type === 'textarea' ? (
                <textarea
                  value={activeValues[field.id] ?? ''}
                  onChange={e => setField(field.id, e.target.value)}
                  placeholder={field.placeholder}
                  rows={3}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                             focus:outline-none focus:border-[#CE7A58] resize-none"
                />
              ) : (
                <input
                  type={field.field_type === 'date' ? 'date' : 'text'}
                  value={activeValues[field.id] ?? ''}
                  onChange={e => setField(field.id, e.target.value)}
                  placeholder={field.placeholder}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                             focus:outline-none focus:border-[#CE7A58]"
                />
              )}
            </div>
          ))}
        </div>
      )}

      {error && (
        <p className="mt-3 text-sm text-red-600">{error}</p>
      )}

      <div className="mt-6 flex items-center gap-4">
        <button
          onClick={handleDownload}
          disabled={isSubmitting}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg
                     bg-[#CE7A58] text-white text-sm font-medium
                     hover:bg-[#B8694A] disabled:opacity-50 disabled:cursor-not-allowed
                     transition-colors"
        >
          {isSubmitting ? 'Đang xử lý...' : '📥 Tải xuống tờ khai đã điền'}
        </button>
        <p className="text-xs text-gray-500">
          Tệp .doc sẽ được tải xuống máy tính của bạn.
        </p>
      </div>
    </div>
  )
}
