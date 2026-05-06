'use client'
import { ChatWidget } from '@/components/chat/ChatWidget'
import { ProcedureForm } from '@/components/procedure/ProcedureForm'

interface ProcedurePageLayoutProps {
  procedureId: string
  procedureName: string
  agency: string
  processingDays: string
  fee: string
  documentsSection: React.ReactNode
  chatContext: string
}

export function ProcedurePageLayout({
  procedureId,
  procedureName,
  agency,
  processingDays,
  fee,
  documentsSection,
  chatContext,
}: ProcedurePageLayoutProps) {
  return (
    <div className="min-h-screen bg-[var(--bg-page)]">
      {/* Procedure name banner */}
      <div className="bg-[var(--terracotta-lt)] border-t-4 border-[var(--terracotta)] px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <p className="text-[var(--terracotta)] text-xs uppercase tracking-widest font-medium mb-2">
            Thủ tục hành chính
          </p>
          <h1 className="text-[var(--navy)] text-xl font-semibold">
            {procedureName}
          </h1>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-8 space-y-5">

        {/* Section 1 — Basic Info Card */}
        <div className="bg-white border border-[var(--border-card)] rounded-xl overflow-hidden">
          <div className="bg-[var(--navy-faint)] border-b border-[var(--border-card)] px-6 py-3">
            <h2 className="text-xs font-semibold text-[var(--navy)] uppercase tracking-wider">
              Thông tin thủ tục
            </h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-0 divide-y sm:divide-y-0 sm:divide-x divide-[var(--border-card)]">
            <div className="px-6 py-4">
              <p className="text-xs text-[var(--text-muted)] uppercase tracking-wide mb-1">
                Cơ quan thực hiện
              </p>
              <p className="text-sm font-medium text-[var(--text-primary)]">{agency}</p>
            </div>
            <div className="px-6 py-4">
              <p className="text-xs text-[var(--text-muted)] uppercase tracking-wide mb-1">
                Thời hạn giải quyết
              </p>
              <p className="text-sm font-medium text-[var(--text-primary)]">{processingDays}</p>
            </div>
            <div className="px-6 py-4">
              <p className="text-xs text-[var(--text-muted)] uppercase tracking-wide mb-1">
                Lệ phí
              </p>
              <p className="text-sm font-medium text-[var(--text-primary)]">{fee}</p>
            </div>
          </div>
        </div>

        {/* Section 2 — Interactive Form */}
        <ProcedureForm procedureId={procedureId} />

        {/* Section 3 — Required Documents */}
        <div className="bg-white border border-[var(--border-card)] rounded-xl overflow-hidden">
          <div className="bg-[var(--navy-faint)] border-b border-[var(--border-card)] px-6 py-3">
            <h2 className="text-xs font-semibold text-[var(--navy)] uppercase tracking-wider">
              Hồ sơ cần chuẩn bị
            </h2>
          </div>
          <div className="p-6">
            {documentsSection}
          </div>
        </div>

        {/* Section 4 — Embedded Chat */}
        <div className="bg-white border border-[var(--border-card)] rounded-xl overflow-hidden">
          <div className="bg-[var(--navy-faint)] border-b border-[var(--border-card)] px-6 py-3">
            <h2 className="text-xs font-semibold text-[var(--navy)] uppercase tracking-wider">
              Hỏi trợ lý AI
            </h2>
          </div>
          <ChatWidget variant="inline" initialContext={chatContext} />
        </div>

      </div>
    </div>
  )
}
