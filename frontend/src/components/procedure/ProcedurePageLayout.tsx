'use client'
import { useState } from 'react'
import { useChatStore } from '@/lib/stores/chatStore'
import { api } from '@/lib/api/client'
import { ChatWidget } from '@/components/chat/ChatWidget'
import { ProcedureForm } from '@/components/procedure/ProcedureForm'

interface ProcedurePageLayoutProps {
  procedureId: string
  procedureName: string
  agency: string
  processingDays: string
  fee: string
  documentsSection: React.ReactNode
  showCccdUpload: boolean
  chatContext: string
}

export function ProcedurePageLayout({
  procedureId,
  procedureName,
  agency,
  processingDays,
  fee,
  documentsSection,
  showCccdUpload,
  chatContext,
}: ProcedurePageLayoutProps) {
  const { sessionId, citizenId } = useChatStore()
  const [cccdStatus, setCccdStatus] = useState<string | null>(null)

  const handleCccdUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setCccdStatus('Đang xử lý CCCD...')
    try {
      await api.documents.upload(file, sessionId, citizenId || undefined)
      setCccdStatus('✅ Đã đọc thông tin CCCD thành công')
    } catch {
      setCccdStatus('❌ Không thể đọc CCCD. Vui lòng thử lại.')
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">

        {/* Section 1 — Basic Info Card */}
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <h1 className="text-xl font-semibold text-gray-900 mb-4">{procedureName}</h1>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide">Cơ quan thực hiện</p>
              <p className="text-sm font-medium text-gray-800 mt-1">{agency}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide">Thời hạn giải quyết</p>
              <p className="text-sm font-medium text-gray-800 mt-1">{processingDays}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide">Lệ phí</p>
              <p className="text-sm font-medium text-gray-800 mt-1">{fee}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide">Mã thủ tục</p>
              <p className="text-sm font-medium text-gray-800 mt-1">{procedureId}</p>
            </div>
          </div>
        </div>

        {/* Section 2 — Interactive Form (renders nothing when no forms exist for this procedure) */}
        <ProcedureForm procedureId={procedureId} />

        {/* Section 3 — Required Documents */}
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Hồ sơ cần chuẩn bị</h2>
          {documentsSection}

          {showCccdUpload && (
            <div className="mt-4 border border-dashed border-gray-300 rounded-lg p-4 bg-gray-50">
              <p className="text-sm font-medium text-gray-700 mb-1">
                Tải lên CCCD để điền tự động
              </p>
              <p className="text-xs text-gray-500 mb-3">
                Hệ thống sẽ đọc thông tin từ CCCD và tự động điền vào mẫu đơn.
              </p>
              <label className="inline-flex items-center gap-2 cursor-pointer bg-white border border-gray-200 rounded-lg px-4 py-2 text-sm text-gray-700 hover:border-[#CE7A58] transition-colors">
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={handleCccdUpload}
                />
                Chọn ảnh CCCD
              </label>
              {cccdStatus && (
                <p className="text-xs mt-2 text-gray-600">{cccdStatus}</p>
              )}
            </div>
          )}
        </div>

        {/* Section 4 — Embedded Chat */}
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <h2 className="text-base font-semibold text-gray-900 p-6 pb-0">Hỏi trợ lý AI</h2>
          <ChatWidget variant="inline" initialContext={chatContext} />
        </div>

      </div>
    </div>
  )
}
