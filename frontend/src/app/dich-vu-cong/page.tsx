'use client'
import { useState } from 'react'
import { SearchBar } from '@/components/ui/SearchBar'
import { TabBar }    from '@/components/ui/TabBar'
import { Breadcrumb } from '@/components/ui/Breadcrumb'
import { ScoreBadge } from '@/components/ui/ScoreBadge'

const STAT_BOXES = [
  {
    color: '#3D9E8D',
    count: '1.965',
    label: 'Công dân',
    sub: ['983 DVC toàn trình', '982 DVC một phần'],
  },
  {
    color: '#CE7A58',
    count: '2.966',
    label: 'Doanh nghiệp',
    sub: ['1.600 DVC toàn trình', '1.366 DVC một phần'],
  },
  {
    color: '#4A7AA8',
    count: '636.949.779',
    label: 'Số hồ sơ đồng bộ trạng thái xử lý',
    sub: [],
  },
  {
    color: '#CE9058',
    count: '94.356.514',
    label: 'Số hồ sơ trực tuyến thực hiện',
    sub: [],
  },
]

const TABS = [
  { id: 'bo',     label: 'Bộ, cơ quan ngang Bộ' },
  { id: 'tinh',   label: 'Tỉnh, Thành phố' },
  { id: 'khac',   label: 'Cơ quan khác' },
]

const CU_TRU_PROCEDURES = [
  { href: '/thu-tuc/dang-ky-thuong-tru',  label: 'Đăng ký thường trú',               time: '5 ngày', fee: 'Miễn phí' },
  { href: '/thu-tuc/dang-ky-tam-tru',     label: 'Đăng ký tạm trú',                  time: '3 ngày', fee: 'Miễn phí' },
  { href: '/thu-tuc/xac-nhan-cu-tru',     label: 'Xác nhận thông tin về cư trú',     time: '1–2 ngày', fee: 'Miễn phí' },
]

const MOCK_ROWS = [
  { stt: 1,  organ: 'Bộ Công an',                    total: 342, full: 198, partial: 144, target: 300, remain: 0 },
  { stt: 2,  organ: 'Bộ Tư pháp',                    total: 285, full: 175, partial: 110, target: 250, remain: 0 },
  { stt: 3,  organ: 'Bộ Tài chính',                  total: 410, full: 220, partial: 190, target: 380, remain: 0 },
  { stt: 4,  organ: 'Bộ Lao động - TB & XH',         total: 196, full: 112, partial:  84, target: 180, remain: 0 },
  { stt: 5,  organ: 'Bộ Y tế',                       total: 178, full:  95, partial:  83, target: 160, remain: 0 },
  { stt: 6,  organ: 'Bộ Giáo dục và Đào tạo',        total: 145, full:  88, partial:  57, target: 130, remain: 0 },
  { stt: 7,  organ: 'Bộ Kế hoạch và Đầu tư',         total: 201, full: 130, partial:  71, target: 185, remain: 0 },
  { stt: 8,  organ: 'Bộ Nông nghiệp và PTNT',        total: 265, full: 148, partial: 117, target: 240, remain: 0 },
  { stt: 9,  organ: 'Bộ Giao thông vận tải',         total: 188, full:  99, partial:  89, target: 170, remain: 0 },
  { stt: 10, organ: 'Bộ Tài nguyên và Môi trường',   total: 234, full: 134, partial: 100, target: 210, remain: 0 },
]

const FILTER_SELECTS = [
  { label: 'Cơ quan', opts: ['-- Tất cả --', 'Cấp Trung ương', 'Cấp Tỉnh'] },
  { label: 'Đơn vị',  opts: ['-- Tất cả --'] },
  { label: 'Thời gian', opts: ['Năm 2026', 'Năm 2025', 'Năm 2024'] },
  { label: 'Đối tượng', opts: ['-- Tất cả --', 'Công dân', 'Doanh nghiệp'] },
  { label: 'Mức độ DVC', opts: ['-- Tất cả --', 'Toàn trình', 'Một phần'] },
]

export default function DichVuCongPage() {
  const [activeTab, setActiveTab] = useState('bo')

  return (
    <div className="max-w-container mx-auto px-4 py-4">
      <Breadcrumb items={[
        { label: 'Trang chủ', href: '/' },
        { label: 'Dịch vụ công trực tuyến' },
      ]} />

      <h1 className="text-xl font-bold text-[#1E2F41] mb-4">Dịch vụ công trực tuyến</h1>

      {/* Search bar */}
      <SearchBar
        onSearch={(q) => {}}
        className="mb-4"
      />

      {/* Filter row */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mb-6">
        {FILTER_SELECTS.map((f) => (
          <select key={f.label}
                  className="border border-[#DDDDDD] text-sm text-[#1E2F41] px-2 py-2 rounded
                             focus:outline-none focus:border-[#CE7A58] bg-white">
            {f.opts.map((o) => <option key={o}>{o}</option>)}
          </select>
        ))}
      </div>

      {/* Stat boxes */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        {STAT_BOXES.map((box, i) => (
          <div key={i} className="flex items-center gap-3 border border-[#DDDDDD] rounded p-3">
            <div className="w-11 h-11 rounded-full flex items-center justify-center flex-shrink-0 text-white text-lg font-bold"
                 style={{ backgroundColor: box.color }}>
              {i === 0 ? '👤' : i === 1 ? '🏢' : i === 2 ? '📂' : '💻'}
            </div>
            <div>
              <div className="text-[#CE7A58] font-bold text-xl leading-tight">{box.count}</div>
              <div className="text-[#555] text-[11px] leading-snug">{box.label}</div>
              {box.sub.map((s) => (
                <div key={s} className="text-[11px] text-[#999]">{s}</div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Cư trú procedures — direct links */}
      <div className="mb-6">
        <h2 className="text-sm font-bold text-[#CE7A58] uppercase tracking-wide mb-3">
          Thủ tục cư trú trực tuyến
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {CU_TRU_PROCEDURES.map((p) => (
            <a
              key={p.href}
              href={p.href}
              className="border border-[#DDDDDD] rounded p-4 hover:border-[#CE7A58] transition-colors block"
            >
              <p className="text-sm font-semibold text-[#2A6EBB] hover:underline mb-1">{p.label}</p>
              <p className="text-[11px] text-[#555]">Thời gian: {p.time} · Lệ phí: {p.fee}</p>
            </a>
          ))}
        </div>
      </div>

      {/* Tabs + Table */}
      <TabBar tabs={TABS} activeTab={activeTab} onChange={setActiveTab} className="mb-4" />

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b-2 border-[#DDDDDD]">
              {['STT', 'Đơn vị', 'Tổng số TTHC', 'DVC toàn trình', 'DVC một phần', 'Mức độ 3', 'Mức độ 4'].map((h) => (
                <th key={h} className="py-3 px-3 text-left text-[13px] font-semibold text-[#1E2F41] bg-[#F5F5F5]">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {MOCK_ROWS.map((row) => (
              <tr key={row.stt} className="border-b border-[#EEEEEE] hover:bg-[#FAFAFA]">
                <td className="py-2.5 px-3 text-[13px] text-[#555]">{row.stt}</td>
                <td className="py-2.5 px-3 text-[13px] text-[#2A6EBB] cursor-pointer hover:underline">{row.organ}</td>
                <td className="py-2.5 px-3 text-[13px]">{row.total}</td>
                <td className="py-2.5 px-3 text-[13px]">{row.full}</td>
                <td className="py-2.5 px-3 text-[13px]">{row.partial}</td>
                <td className="py-2.5 px-3 text-[13px]">{row.target}</td>
                <td className="py-2.5 px-3 text-[13px]"><ScoreBadge score={row.stt * 9.1} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
