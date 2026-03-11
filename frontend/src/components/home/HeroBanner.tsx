'use client'
import { useRouter } from 'next/navigation'
import { SearchBar } from '@/components/ui/SearchBar'

const CTA_BUTTONS = [
  { label: 'Dịch vụ công trực tuyến',                    href: '/dich-vu-cong' },
  { label: 'Dịch vụ công trực tuyến của Đảng',           href: '/dich-vu-cong/dang' },
  { label: 'Dịch vụ công liên thông: Khai sinh, Khai tử', href: '/dich-vu-cong/lien-thong' },
]

export function HeroBanner() {
  const router = useRouter()

  return (
    <div
      className="relative min-h-[220px] flex items-center"
      style={{
        backgroundColor: '#CE7A58',
        backgroundImage: `
          radial-gradient(circle at 15% 50%, rgba(255,255,255,0.06) 0%, transparent 50%),
          radial-gradient(circle at 85% 50%, rgba(255,255,255,0.04) 0%, transparent 40%)
        `,
      }}
    >
      <div className="max-w-container mx-auto px-4 py-8 w-full flex flex-col items-center">
        <div className="max-w-[860px]">
          <SearchBar
            onSearch={(q) => router.push(`/tim-kiem?q=${encodeURIComponent(q)}`)}
            className="mb-5"
          />
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {CTA_BUTTONS.map((btn) => (
              <a key={btn.href} href={btn.href}
                 className="bg-[#FFC251] text-black font-bold text-center py-3 px-4 rounded
                            hover:bg-[#F0B340] transition-colors flex items-center justify-center text-sm leading-snug">
                {btn.label}
              </a>
            ))}
          </div>
        </div>
      </div>

      {/* Decorative right panel (lotus placeholder) */}
      <div className="absolute right-0 top-0 bottom-0 w-[180px] hidden lg:flex items-center
                      justify-center overflow-hidden">
        <div className="text-white/15 text-[90px] select-none">🌸</div>
      </div>
    </div>
  )
}
