export interface NavItem {
  label: string
  href?: string
  children?: NavItem[]
}

export interface BreadcrumbItem {
  label: string
  href?: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  timestamp: Date
  isStreaming?: boolean
}

export interface Citation {
  doc_id: string
  document_number: string
  article: string
  excerpt: string
}

export interface ProcedureStep {
  id: string
  name: string
  status: 'completed' | 'pending' | 'blocked'
  reason?: string
  required_documents?: string[]
  is_mandatory: boolean
}

export interface ServiceItem {
  id: string
  label: string
  icon: string
  href: string
  group?: string
}

export interface StatBox {
  icon: 'person' | 'business' | 'document' | 'online'
  count: string
  label: string
  subStats?: { label: string; value: string }[]
}

export interface ProcedureStat {
  organ: string
  total: number
  fullOnline: number
  partialOnline: number
  target: number
  remaining: number
}

export interface QualityIndex {
  rank: number
  province: string
  transparency: number
  progress: number
  onlineService: number
  satisfaction: number
  digitization: number
  totalScore: number
}

export interface FaqItem {
  id: string
  question: string
  answer?: string
  category: 'cong-dan' | 'doanh-nghiep' | 'to-chuc-khac' | 'all'
}

export interface NewsItem {
  id: string
  title: string
  date: string
  href?: string
}

export interface UploadedFile {
  file: File
  previewUrl?: string
  documentType?: string
}

// ── Residence Form Types ──────────────────────────────────────────────────────

export type FormType = 'thuong-tru' | 'tam-tru' | 'xac-nhan'
export type FieldSource = 'manual' | 'ai'

export interface FieldState {
  value: string
  source: FieldSource
  confidence: number    // 1.0 for manual; 0.0–1.0 for AI
  aiHighlight: boolean  // true when source === 'ai'
}

/** Mirrors backend ResidenceFormData — field names match PersonalData keys where shared */
export interface ResidenceFormData {
  ho_ten?: string
  ngay_sinh?: string
  gioi_tinh?: 'Nam' | 'Nữ' | ''
  so_cccd?: string
  // thuong-tru
  noi_thuong_tru_cu?: string
  dia_chi_thuong_tru_moi?: string
  quan_he_chu_ho?: string
  ten_chu_ho?: string
  cccd_chu_ho?: string
  // tam-tru
  dia_chi_thuong_tru?: string
  dia_chi_tam_tru?: string
  tu_ngay?: string
  den_ngay?: string
  muc_dich?: string
  // xac-nhan
  dia_chi_can_xac_nhan?: string
  loai_xac_nhan?: 'Thường trú' | 'Tạm trú' | ''
  muc_dich_xac_nhan?: string
}

export interface FormSubmissionResponse {
  ma_ho_so: string
  form_type: FormType
  submitted_at: string
  status: 'received' | 'processing' | 'completed'
  message: string
}
