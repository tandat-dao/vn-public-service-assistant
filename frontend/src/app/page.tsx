'use client'
import Link from 'next/link'
import { ChatWidget } from '@/components/chat/ChatWidget'

const PROCEDURE_SECTIONS = [
  {
    label: 'Nhà ở',
    cards: [
      { title: 'Đăng ký thường trú',            href: '/thu-tuc/dang-ky-thuong-tru' },
      { title: 'Đăng ký tạm trú',               href: '/thu-tuc/dang-ky-tam-tru' },
      { title: 'Xác nhận thông tin về cư trú',  href: '/thu-tuc/xac-nhan-cu-tru' },
    ],
  },
  {
    label: 'Hộ tịch',
    cards: [
      { title: 'Đăng ký khai sinh',              href: '/thu-tuc/dang-ky-khai-sinh' },
      { title: 'Cấp bản sao Trích lục hộ tịch', href: '/thu-tuc/cap-ban-sao-trich-luc' },
    ],
  },
  {
    label: 'Nuôi con nuôi',
    cards: [
      { title: 'Đăng ký việc nuôi con nuôi trong nước',    href: '/thu-tuc/dang-ky-nuoi-con-nuoi' },
      { title: 'Đăng ký lại việc nuôi con nuôi trong nước', href: '/thu-tuc/dang-ky-lai-nuoi-con-nuoi' },
    ],
  },
]

export default function HomePage() {
  return (
    <div className="bg-[var(--bg-page)]">
      {/* Hero section */}
      <section className="bg-[var(--bg-page)] px-4 pt-12 pb-16 border-b border-[var(--border-card)]">
        <div className="max-w-4xl mx-auto">
          <p className="text-[var(--text-muted)] text-sm font-medium tracking-widest uppercase mb-3">
            Cổng Dịch Vụ Công · TP. Hồ Chí Minh
          </p>
          <h1 className="text-[var(--navy)] text-2xl font-semibold leading-snug mb-8 max-w-2xl">
            Trợ lý AI hướng dẫn thủ tục hành chính
          </h1>

          {/* Inline chat — embedded card */}
          <div className="border border-[var(--border-card)] shadow-sm rounded-2xl overflow-hidden">
            <ChatWidget variant="inline" />
          </div>
        </div>
      </section>

      {/* Procedure shortcut cards */}
      <section className="max-w-4xl mx-auto px-4 py-10">
        {PROCEDURE_SECTIONS.map((section) => (
          <div key={section.label} className="mb-8">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-1 h-5 bg-[var(--terracotta)] rounded-full" />
              <h2 className="text-sm font-semibold text-[var(--navy)] uppercase tracking-wider">
                {section.label}
              </h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {section.cards.map((card) => (
                <Link key={card.href} href={card.href}>
                  <div className="bg-white border border-[var(--border-card)] rounded-xl p-5
                                  hover:border-[var(--terracotta)] hover:shadow-md hover:-translate-y-0.5
                                  transition-all duration-200 cursor-pointer group">
                    <p className="text-sm font-medium text-[var(--text-primary)]
                                  group-hover:text-[var(--navy)] leading-snug mb-2">
                      {card.title}
                    </p>
                    <div className="w-8 h-0.5 bg-[var(--terracotta-lt)]
                                    group-hover:bg-[var(--terracotta)] group-hover:w-12
                                    transition-all duration-300 rounded-full" />
                  </div>
                </Link>
              ))}
            </div>
          </div>
        ))}
      </section>
    </div>
  )
}
