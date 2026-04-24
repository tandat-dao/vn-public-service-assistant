'use client'
import Link from 'next/link'
import { ChatWidget } from '@/components/chat/ChatWidget'

const PROCEDURE_SECTIONS = [
  {
    label: 'Nhà ở',
    cards: [
      { title: 'Đăng ký thường trú',            code: 'TTHC-001', href: '/thu-tuc/dang-ky-thuong-tru' },
      { title: 'Đăng ký tạm trú',               code: 'TTHC-002', href: '/thu-tuc/dang-ky-tam-tru' },
      { title: 'Xác nhận thông tin về cư trú',  code: 'TTHC-003', href: '/thu-tuc/xac-nhan-cu-tru' },
    ],
  },
  {
    label: 'Hộ tịch',
    cards: [
      { title: 'Đăng ký khai sinh',                code: 'TTHC-CR-001', href: '/thu-tuc/dang-ky-khai-sinh' },
      { title: 'Cấp bản sao Trích lục hộ tịch',   code: 'TTHC-CR-002', href: '/thu-tuc/cap-ban-sao-trich-luc' },
    ],
  },
  {
    label: 'Nuôi con nuôi',
    cards: [
      { title: 'Đăng ký việc nuôi con nuôi trong nước',    code: 'TTHC-AD-001', href: '/thu-tuc/dang-ky-nuoi-con-nuoi' },
      { title: 'Đăng ký lại việc nuôi con nuôi trong nước', code: 'TTHC-AD-002', href: '/thu-tuc/dang-ky-lai-nuoi-con-nuoi' },
    ],
  },
]

export default function HomePage() {
  return (
    <>
      {/* Headline */}
      <div className="text-center py-6">
        <p className="text-xl font-medium text-gray-700">
          Trợ lý AI hướng dẫn thủ tục hành chính tại TP. Hồ Chí Minh
        </p>
      </div>

      {/* Inline chat */}
      <div className="w-full max-w-4xl mx-auto px-4 mt-2 mb-8">
        <ChatWidget variant="inline" />
      </div>

      {/* Procedure shortcut cards */}
      <div className="w-full max-w-4xl mx-auto px-4 pb-12">
        {PROCEDURE_SECTIONS.map((section) => (
          <div key={section.label} className="mb-8">
            <p className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
              {section.label}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {section.cards.map((card) => (
                <Link
                  key={card.code}
                  href={card.href}
                  className="bg-white border border-gray-200 rounded-lg p-4 hover:border-[#CE7A58] hover:shadow-sm transition-all cursor-pointer"
                >
                  <p
                    className="text-sm font-medium text-gray-800 overflow-hidden"
                    style={{
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical' as const,
                    }}
                  >
                    {card.title}
                  </p>

                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>
    </>
  )
}
