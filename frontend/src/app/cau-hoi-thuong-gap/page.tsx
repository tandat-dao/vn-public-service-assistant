'use client'
import { useState } from 'react'
import { Search } from 'lucide-react'
import { TabBar } from '@/components/ui/TabBar'
import { Breadcrumb } from '@/components/ui/Breadcrumb'
import type { FaqItem } from '@/lib/types'

const TABS = [
  { id: 'all',          label: 'Tất cả',          count: 9452 },
  { id: 'cong-dan',     label: 'Công dân',         count: 1133 },
  { id: 'doanh-nghiep', label: 'Doanh nghiệp',     count: 834  },
  { id: 'to-chuc-khac', label: 'Tổ chức khác',     count: 1492 },
]

const MOCK_FAQ: FaqItem[] = [
  { id: '1', question: 'Thủ tục đăng ký khai sinh cho trẻ em như thế nào?', category: 'cong-dan' },
  { id: '2', question: 'Hồ sơ đăng ký kết hôn cần những giấy tờ gì?',       category: 'cong-dan' },
  { id: '3', question: 'Cách tra cứu tình trạng xử lý hồ sơ trực tuyến?',   category: 'all' },
  { id: '4', question: 'Thủ tục đăng ký thành lập doanh nghiệp mới nhất?',  category: 'doanh-nghiep' },
  { id: '5', question: 'Quy trình cấp giấy phép xây dựng nhà ở?',           category: 'cong-dan' },
  { id: '6', question: 'Hướng dẫn nộp thuế thu nhập cá nhân trực tuyến',    category: 'cong-dan' },
  { id: '7', question: 'Điều kiện để được miễn giảm phí, lệ phí TTHC?',    category: 'all' },
  { id: '8', question: 'Doanh nghiệp nước ngoài đăng ký hoạt động tại Việt Nam như thế nào?', category: 'doanh-nghiep' },
  { id: '9', question: 'Thủ tục xin cấp Căn cước công dân gắn chip?',       category: 'cong-dan' },
  { id: '10', question: 'Đổi giấy phép lái xe hạng B1 sang B2 cần gì?',     category: 'cong-dan' },
]

export default function CauHoiThuongGapPage() {
  const [activeTab, setActiveTab] = useState('all')
  const [query, setQuery] = useState('')
  const [ministry, setMinistry] = useState('')

  const filtered = MOCK_FAQ.filter((f) => {
    const matchTab = activeTab === 'all' || f.category === activeTab
    const matchQ   = !query || f.question.toLowerCase().includes(query.toLowerCase())
    return matchTab && matchQ
  })

  return (
    <div className="max-w-container mx-auto px-4 py-4">
      <Breadcrumb items={[
        { label: 'Trang chủ', href: '/' },
        { label: 'Câu hỏi thường gặp' },
      ]} />

      {/* Search row */}
      <div className="flex gap-2 mb-5">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Nhập từ khoá câu hỏi"
          className="flex-1 border border-[#DDDDDD] px-3 py-2 text-sm rounded
                     focus:outline-none focus:border-[#CE7A58]"
        />
        <select
          value={ministry}
          onChange={(e) => setMinistry(e.target.value)}
          className="border border-[#DDDDDD] px-3 py-2 text-sm rounded focus:outline-none
                     focus:border-[#CE7A58] bg-white min-w-[160px]"
        >
          <option value="">-- Bộ, ngành --</option>
          <option>Bộ Công an</option>
          <option>Bộ Tư pháp</option>
          <option>Bộ Y tế</option>
          <option>Bộ Giáo dục và Đào tạo</option>
        </select>
        <button className="bg-[#CE7A58] text-white px-4 py-2 rounded text-sm font-semibold
                           hover:bg-[#B8694A] transition-colors flex items-center gap-1">
          <Search className="w-4 h-4" /> Tìm kiếm
        </button>
      </div>

      <h1 className="text-xl font-bold text-[#1E2F41] mb-4">Câu hỏi thường gặp</h1>
      <TabBar tabs={TABS} activeTab={activeTab} onChange={setActiveTab} className="mb-4" />

      <div className="mt-2">
        {filtered.length === 0 && (
          <p className="py-8 text-center text-[#999] text-sm">Không tìm thấy kết quả.</p>
        )}
        {filtered.map((item) => (
          <div key={item.id}
               className="flex gap-3 py-3 border-b border-[#F0F0F0] cursor-pointer
                          hover:bg-[#FAFAFA] -mx-2 px-2 transition-colors">
            <div className="w-[22px] h-[22px] rounded-full border border-[#CCC] flex items-center
                            justify-center text-[#999] text-xs font-bold flex-shrink-0 mt-0.5">
              ?
            </div>
            <p className="text-sm text-[#2A6EBB] hover:underline leading-relaxed">
              {item.question}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
