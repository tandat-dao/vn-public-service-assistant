'use client'
import { useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { NewsItem } from '@/lib/types'

const MOCK_NEWS: NewsItem[] = [
  {
    id: '1',
    title: 'Công bố dữ liệu quốc gia về bảo hiểm và hướng dẫn kết nối, khai thác sử dụng dữ liệu bảo hiểm',
    date: '11/03/2026',
  },
  {
    id: '2',
    title: 'Công bố và hướng dẫn kết nối để khai thác, sử dụng dữ liệu đăng ký doanh nghiệp quốc gia',
    date: '10/03/2026',
  },
  {
    id: '3',
    title: 'Công bố dữ liệu, hướng dẫn khai thác, sử dụng dữ liệu số sức khỏe người dân',
    date: '09/03/2026',
  },
]

export function NewsStrip() {
  const [current, setCurrent] = useState(0)

  const prev = () => setCurrent((c) => (c === 0 ? MOCK_NEWS.length - 1 : c - 1))
  const next = () => setCurrent((c) => (c === MOCK_NEWS.length - 1 ? 0 : c + 1))

  return (
    <div className="bg-white border-b border-[#DDDDDD]">
      <div className="max-w-container mx-auto px-4 py-4">
        <div className="flex items-center gap-2">
          <button onClick={prev}
                  className="text-[#999] hover:text-[#CE7A58] transition-colors flex-shrink-0">
            <ChevronLeft className="w-5 h-5" />
          </button>

          <div className="flex-1 grid grid-cols-1 sm:grid-cols-3 gap-5">
            {MOCK_NEWS.map((item) => (
              <div key={item.id} className="cursor-pointer hover:opacity-80 transition-opacity">
                <p className="text-[13px] text-[#1E2F41] leading-snug mb-1 line-clamp-2">
                  {item.title}
                </p>
                <p className="text-[12px] text-[#999]">Ngày {item.date}</p>
              </div>
            ))}
          </div>

          <button onClick={next}
                  className="text-[#999] hover:text-[#CE7A58] transition-colors flex-shrink-0">
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  )
}
