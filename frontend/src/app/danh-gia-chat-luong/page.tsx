'use client'
import { useState } from 'react'
import { Breadcrumb } from '@/components/ui/Breadcrumb'
import { ScoreBadge } from '@/components/ui/ScoreBadge'
import type { QualityIndex } from '@/lib/types'

const MOCK_DATA: QualityIndex[] = [
  { rank:  1, province: 'UBND tỉnh Vĩnh Long',       transparency: 97.2, progress: 96.8, onlineService: 98.1, satisfaction: 95.4, digitization: 97.9, totalScore: 97.08 },
  { rank:  2, province: 'UBND tỉnh Đồng Tháp',       transparency: 96.5, progress: 97.1, onlineService: 97.3, satisfaction: 94.8, digitization: 96.7, totalScore: 96.48 },
  { rank:  3, province: 'UBND tỉnh Hà Nam',           transparency: 95.8, progress: 96.2, onlineService: 96.9, satisfaction: 95.1, digitization: 96.3, totalScore: 96.06 },
  { rank:  4, province: 'UBND tỉnh Quảng Ninh',       transparency: 95.1, progress: 95.7, onlineService: 97.0, satisfaction: 94.5, digitization: 95.8, totalScore: 95.62 },
  { rank:  5, province: 'UBND TP Hải Phòng',          transparency: 94.7, progress: 95.3, onlineService: 96.2, satisfaction: 93.9, digitization: 95.4, totalScore: 95.10 },
  { rank:  6, province: 'UBND tỉnh Thừa Thiên Huế',  transparency: 94.3, progress: 94.8, onlineService: 95.6, satisfaction: 93.4, digitization: 94.9, totalScore: 94.60 },
  { rank:  7, province: 'UBND tỉnh Bắc Ninh',         transparency: 93.9, progress: 94.2, onlineService: 95.1, satisfaction: 92.8, digitization: 94.3, totalScore: 94.06 },
  { rank:  8, province: 'UBND TP Đà Nẵng',            transparency: 93.5, progress: 93.8, onlineService: 94.7, satisfaction: 92.3, digitization: 93.8, totalScore: 93.62 },
  { rank:  9, province: 'UBND tỉnh Lào Cai',          transparency: 93.1, progress: 93.4, onlineService: 94.2, satisfaction: 91.8, digitization: 93.3, totalScore: 93.16 },
  { rank: 10, province: 'UBND tỉnh Bình Dương',       transparency: 92.7, progress: 93.0, onlineService: 93.8, satisfaction: 91.3, digitization: 92.8, totalScore: 92.72 },
]

const TABLE_HEADERS = ['STT', 'Tỉnh/Thành phố', 'Công khai minh bạch', 'Tiến độ giải quyết',
  'Dịch vụ trực tuyến', 'Mức độ hài lòng', 'Số hóa hồ sơ', 'Tổng điểm']

export default function DanhGiaChatLuongPage() {
  const [year, setYear]         = useState('2026')
  const [province, setProvince] = useState('')

  return (
    <div className="max-w-container mx-auto px-4 py-4">
      <Breadcrumb items={[
        { label: 'Trang chủ', href: '/' },
        { label: 'Đánh giá chất lượng phục vụ' },
      ]} />

      <h1 className="text-[15px] font-bold text-[#1E2F41] uppercase tracking-wide mb-2">
        Bộ chỉ số phục vụ người dân, doanh nghiệp trong thực hiện thủ tục hành chính, dịch vụ công
      </h1>
      <p className="text-[12px] text-[#CC0000] italic mb-4">
        * Số liệu được tính toán dựa trên dữ liệu thực tế từ hệ thống thông tin giải quyết TTHC.
        Chỉ số được cập nhật hàng ngày.
      </p>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-5">
        <select className="border border-[#DDDDDD] px-3 py-2 text-sm rounded focus:outline-none
                           focus:border-[#CE7A58] bg-white">
          <option>-- Nhóm chỉ tiêu --</option>
          <option>Nhóm 1: Công khai minh bạch</option>
          <option>Nhóm 2: Tiến độ giải quyết</option>
        </select>
        <select className="border border-[#DDDDDD] px-3 py-2 text-sm rounded focus:outline-none
                           focus:border-[#CE7A58] bg-white">
          <option>-- Loại thời gian --</option>
          <option>Theo tháng</option>
          <option>Theo quý</option>
        </select>
        <select value={year} onChange={(e) => setYear(e.target.value)}
                className="border border-[#DDDDDD] px-3 py-2 text-sm rounded focus:outline-none
                           focus:border-[#CE7A58] bg-white">
          <option>2026</option><option>2025</option><option>2024</option>
        </select>
        <select value={province} onChange={(e) => setProvince(e.target.value)}
                className="border border-[#DDDDDD] px-3 py-2 text-sm rounded focus:outline-none
                           focus:border-[#CE7A58] bg-white">
          <option value="">-- Tỉnh/Thành phố --</option>
          {MOCK_DATA.map((d) => <option key={d.rank}>{d.province}</option>)}
        </select>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b-2 border-[#DDDDDD]">
              {TABLE_HEADERS.map((h) => (
                <th key={h} className="py-3 px-3 text-left text-[13px] font-semibold
                                       text-[#1E2F41] bg-[#F5F5F5] whitespace-nowrap">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {MOCK_DATA
              .filter((d) => !province || d.province === province)
              .map((row) => (
              <tr key={row.rank} className="border-b border-[#EEEEEE] hover:bg-[#FAFAFA]">
                <td className="py-2.5 px-3 text-[13px] text-[#555]">{row.rank}</td>
                <td className="py-2.5 px-3 text-[13px] text-[#1E2F41]">{row.province}</td>
                <td className="py-2.5 px-3 text-[13px]">{row.transparency.toFixed(1)}</td>
                <td className="py-2.5 px-3 text-[13px]">{row.progress.toFixed(1)}</td>
                <td className="py-2.5 px-3 text-[13px]">{row.onlineService.toFixed(1)}</td>
                <td className="py-2.5 px-3 text-[13px]">{row.satisfaction.toFixed(1)}</td>
                <td className="py-2.5 px-3 text-[13px]">{row.digitization.toFixed(1)}</td>
                <td className="py-2.5 px-3 text-center"><ScoreBadge score={row.totalScore} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
