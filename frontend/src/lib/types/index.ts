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
