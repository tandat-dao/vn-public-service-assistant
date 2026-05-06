'use client'

import { useState, useEffect } from 'react'
import { useChatStore } from '@/lib/stores/chatStore'
import { api } from '@/lib/api/client'
import {
  FORM_FILE_CONFIGS,
  PROCEDURE_FORM_FILES,
  type FormFileConfig,
} from '@/data/formFieldConfigs'

const BASE = process.env.NEXT_PUBLIC_API_URL_PUBLIC
  || process.env.NEXT_PUBLIC_API_URL
  || 'http://localhost:8000'

export interface ProcedureFormProps {
  procedureId: string
}

export function ProcedureForm({ procedureId }: ProcedureFormProps) {
  const formFiles = PROCEDURE_FORM_FILES[procedureId] ?? []
  const configs: FormFileConfig[] = formFiles.map(ff => FORM_FILE_CONFIGS[ff]).filter(Boolean)

  const [activeTab, setActiveTab] = useState(0)
  const [fieldValues, setFieldValues] = useState<Record<string, Record<string, string>>>(() => {
    const initial: Record<string, Record<string, string>> = {}
    for (const form of configs) {
      initial[form.form_file] = {}
      for (const field of form.fields) {
        initial[form.form_file][field.id] = ''
      }
    }
    return initial
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [cccdStatus, setCccdStatus] = useState<string | null>(null)
  const [recentlyFilled, setRecentlyFilled] = useState<Set<string>>(new Set())

  const { sessionId, citizenId, personalData, setPersonalData } = useChatStore()

  // Reactive: re-fill CCCD-sourced fields whenever personalData changes
  useEffect(() => {
    if (!personalData || configs.length === 0) return

    const pd = personalData as unknown as Record<string, unknown>

    setFieldValues(prev => {
      const updated = { ...prev }
      for (const form of configs) {
        updated[form.form_file] = { ...prev[form.form_file] }
        for (const field of form.fields) {
          if (field.cccd_source && pd[field.cccd_source] != null) {
            let value = String(pd[field.cccd_source])
            if (field.field_type === 'date' && value.includes('/')) {
              const parts = value.split('/')
              if (parts.length === 3) {
                value = `${parts[2]}-${parts[1]}-${parts[0]}`
              }
            }
            updated[form.form_file][field.id] = value
          }
        }
      }
      return updated
    })

    const filledIds = new Set(
      configs.flatMap(form =>
        form.fields
          .filter(f => f.cccd_source && pd[f.cccd_source] != null)
          .map(f => f.id)
      )
    )
    setRecentlyFilled(filledIds)
    setTimeout(() => setRecentlyFilled(new Set()), 2000)
  }, [personalData]) // eslint-disable-line react-hooks/exhaustive-deps

  if (configs.length === 0) return null

  const activeForm = configs[activeTab]
  const activeValues = fieldValues[activeForm?.form_file] ?? {}

  function setField(fieldId: string, value: string) {
    setFieldValues(prev => ({
      ...prev,
      [activeForm.form_file]: { ...(prev[activeForm.form_file] ?? {}), [fieldId]: value },
    }))
  }

  async function handleCccdUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setCccdStatus('Đang xử lý CCCD...')
    try {
      const result = await api.documents.upload(file, sessionId, citizenId || undefined)
      if (result.personal_data) {
        setPersonalData(result.personal_data)
      }
      setCccdStatus('✅ Đã đọc thông tin CCCD thành công')
    } catch {
      setCccdStatus('❌ Không thể đọc CCCD. Vui lòng thử lại.')
    }
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
          field_values: converted ?? {},
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
      a.download = activeForm.form_file.replace(/\.docx?$/i, '.pdf')
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error("Form download error:", err)
      setError(
        err instanceof Error
          ? err.message
          : 'Không thể kết nối đến máy chủ. Vui lòng thử lại.'
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="bg-white border border-[var(--border-card)] rounded-xl overflow-hidden">
      <div className="bg-[var(--navy-faint)] border-b border-[var(--border-card)] px-6 py-3">
        <h2 className="text-xs font-semibold text-[var(--navy)] uppercase tracking-wider">
          Tờ khai trực tuyến
        </h2>
      </div>

      <div className="p-6">
        {/* CCCD upload card */}
        <div className="mb-5 bg-[var(--terracotta-faint)] border border-[var(--terracotta-lt)] rounded-xl p-4">
          <p className="text-sm font-medium text-[var(--navy)] mb-1">
            Tải lên CCCD để điền tự động
          </p>
          <p className="text-xs text-[var(--text-muted)] mb-3">
            Hệ thống sẽ đọc thông tin và điền vào mẫu đơn.
          </p>
          <div className="flex items-center gap-3">
            <label className="inline-flex items-center gap-2 cursor-pointer bg-white border
                  border-[var(--border-card)] rounded-lg px-4 py-2 text-sm text-[var(--text-secondary)]
                  hover:border-[var(--terracotta)] transition-colors">
              <input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleCccdUpload}
              />
              Chọn ảnh CCCD
            </label>
            {cccdStatus && (
              <p className="text-xs text-[var(--text-secondary)]">{cccdStatus}</p>
            )}
          </div>
        </div>

        {/* Tabs — only shown when multiple forms */}
        {configs.length > 1 && (
          <div className="flex border-b border-[var(--border-card)] mb-5">
            {configs.map((form, idx) => (
              <button
                key={form.form_file}
                onClick={() => setActiveTab(idx)}
                className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
                  activeTab === idx
                    ? 'border-[var(--terracotta)] text-[var(--terracotta)]'
                    : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
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
                <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
                  {field.label}
                  {field.required && <span className="text-red-500 ml-1">*</span>}
                </label>

                {field.field_type === 'select' && field.options ? (
                  <select
                    value={activeValues[field.id] ?? ''}
                    onChange={e => setField(field.id, e.target.value)}
                    className={`w-full border border-[var(--border-card)] rounded-lg px-3 py-2 text-sm
                               focus:outline-none focus:border-[var(--terracotta)] focus:ring-1
                               focus:ring-[var(--terracotta)] bg-white${
                                 recentlyFilled.has(field.id)
                                   ? ' ring-2 ring-[var(--terracotta)] ring-opacity-50'
                                   : ''
                               }`}
                  >
                    <option value="">{field.placeholder}</option>
                    {field.options.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                ) : field.field_type === 'radio' && field.options ? (
                  <div className="flex flex-wrap gap-4 pt-1">
                    {field.options.map(opt => (
                      <label key={opt.value} className="flex items-center gap-1.5 text-sm cursor-pointer">
                        <input
                          type="radio"
                          name={field.id}
                          value={opt.value}
                          checked={activeValues[field.id] === opt.value}
                          onChange={() => setField(field.id, opt.value)}
                          className="accent-[var(--terracotta)]"
                        />
                        {opt.label}
                      </label>
                    ))}
                  </div>
                ) : field.field_type === 'textarea' ? (
                  <textarea
                    value={activeValues[field.id] ?? ''}
                    onChange={e => setField(field.id, e.target.value)}
                    placeholder={field.placeholder}
                    rows={3}
                    className={`w-full border border-[var(--border-card)] rounded-lg px-3 py-2 text-sm
                               focus:outline-none focus:border-[var(--terracotta)] focus:ring-1
                               focus:ring-[var(--terracotta)] resize-none${
                                 recentlyFilled.has(field.id)
                                   ? ' ring-2 ring-[var(--terracotta)] ring-opacity-50'
                                   : ''
                               }`}
                  />
                ) : (
                  <input
                    type={
                      field.field_type === 'date' ? 'date'
                      : field.field_type === 'email' ? 'email'
                      : field.field_type === 'tel' ? 'tel'
                      : 'text'
                    }
                    value={activeValues[field.id] ?? ''}
                    onChange={e => setField(field.id, e.target.value)}
                    placeholder={field.placeholder}
                    className={`w-full border border-[var(--border-card)] rounded-lg px-3 py-2 text-sm
                               focus:outline-none focus:border-[var(--terracotta)] focus:ring-1
                               focus:ring-[var(--terracotta)]${
                                 recentlyFilled.has(field.id)
                                   ? ' ring-2 ring-[var(--terracotta)] ring-opacity-50'
                                   : ''
                               }`}
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
            className="inline-flex items-center gap-2 bg-[var(--terracotta)] text-white px-6 py-2.5
                       rounded-lg text-sm font-medium hover:bg-[var(--terracotta-dk)] transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
          >
            {isSubmitting ? 'Đang xử lý...' : '📥 Tải xuống tờ khai đã điền'}
          </button>
          <p className="text-xs text-[var(--text-muted)]">
            Tệp PDF sẽ được tải xuống máy tính của bạn.
          </p>
        </div>
      </div>
    </div>
  )
}
