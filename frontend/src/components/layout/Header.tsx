'use client'
import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ChevronDown, Home, Menu, X } from 'lucide-react'

// ── Navigation data ───────────────────────────────────────────────────────────

const MAIN_NAV = [
  {
    id: 'thong-tin',
    label: 'Thông tin và dịch vụ',
    children: [
      {
        id: 'thu-tuc',
        label: 'Thủ tục hành chính',
        children: [
          { label: 'Tra cứu TTHC',                 href: '/thu-tuc-hanh-chinh' },
          { label: 'Thủ tục hành chính',            href: '/thu-tuc-hanh-chinh/danh-sach' },
          { label: 'TTHC liên thông',               href: '/thu-tuc-hanh-chinh/lien-thong' },
          { label: 'Quyết định công bố',            href: '/thu-tuc-hanh-chinh/quyet-dinh' },
          { label: 'Cơ quan',                       href: '/thu-tuc-hanh-chinh/co-quan' },
        ],
      },
      { label: 'Dịch vụ công trực tuyến', href: '/dich-vu-cong' },
      { label: 'Dịch vụ công nổi bật',    href: '/dich-vu-cong/noi-bat' },
      { label: 'Tra cứu hồ sơ',           href: '/tra-cuu-ho-so' },
      { label: 'Tòa án nhân dân',         href: '/toa-an' },
      { label: 'Câu hỏi thường gặp',      href: '/cau-hoi-thuong-gap' },
    ],
  },
  { id: 'thanh-toan', label: 'Thanh toán trực tuyến', href: '/thanh-toan' },
  {
    id: 'phan-anh',
    label: 'Phản ánh kiến nghị',
    children: [
      { label: 'Gửi PAKN',                    href: '/phan-anh-kien-nghi/gui' },
      { label: 'Tra cứu kết quả trả lời',     href: '/phan-anh-kien-nghi/tra-cuu' },
    ],
  },
  { id: 'danh-gia', label: 'Đánh giá chất lượng phục vụ', href: '/danh-gia-chat-luong' },
  {
    id: 'ho-tro',
    label: 'Hỗ trợ',
    children: [
      { label: 'Giới thiệu',         href: '/ho-tro/gioi-thieu' },
      { label: 'Điều khoản sử dụng', href: '/ho-tro/dieu-khoan' },
      { label: 'Hướng dẫn sử dụng',  href: '/ho-tro/huong-dan' },
      { label: 'Thông báo',          href: '/thong-bao' },
    ],
  },
]

const SUB_NAV = [
  { label: 'Thủ tục hành chính',      href: '/thu-tuc-hanh-chinh',  hasDropdown: true },
  { label: 'Dịch vụ công trực tuyến', href: '/dich-vu-cong' },
  { label: 'Dịch vụ công nổi bật',    href: '/dich-vu-cong/noi-bat' },
  { label: 'Tra cứu hồ sơ',           href: '/tra-cuu-ho-so' },
  { label: 'Tòa án nhân dân',         href: '/toa-an' },
  { label: 'Câu hỏi thường gặp',      href: '/cau-hoi-thuong-gap' },
]

// ── Component ─────────────────────────────────────────────────────────────────

export function Header() {
  const pathname = usePathname()
  const isHomepage = pathname === '/'
  const [openDropdown, setOpenDropdown] = useState<string | null>(null)
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <header className="w-full">
      {/* ── Row 1: Logo + Auth ──────────────────────────────────── */}
      <div className="bg-white border-b border-[#DDDDDD]">
        <div className="max-w-container mx-auto px-4 py-3 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 no-underline">
            <div className="w-[55px] h-[55px] flex-shrink-0 flex items-center justify-center">
              {/* Red star circle — placeholder for Quoc Hy */}
              <div className="w-[55px] h-[55px] rounded-full bg-[#CC0000] flex items-center
                              justify-center text-white text-2xl font-bold select-none">
                ★
              </div>
            </div>
            <div>
              <div className="text-[#903938] text-2xl font-bold leading-tight tracking-wide"
                   style={{ fontFamily: 'Arial, sans-serif' }}>
                Cổng Dịch vụ Công Quốc Gia
              </div>
              <div className="text-[#CE7A58] text-[13px] italic">
                Kết nối, cung cấp thông tin và dịch vụ công mọi lúc, mọi nơi
              </div>
            </div>
          </Link>

          {/* Auth buttons */}
          <div className="hidden sm:flex items-center gap-2">
            <Link href="/dang-ky"
                  className="px-3 py-1.5 text-sm border border-[#1E2F41] text-[#1E2F41]
                             rounded-sm hover:bg-[#F5F5F5] transition-colors">
              Đăng ký
            </Link>
            <Link href="/dang-nhap"
                  className="px-3 py-1.5 text-sm border border-[#1E2F41] text-[#1E2F41]
                             rounded-sm hover:bg-[#F5F5F5] transition-colors">
              Đăng nhập
            </Link>
          </div>

          {/* Mobile hamburger */}
          <button className="sm:hidden text-[#1E2F41]" onClick={() => setMobileOpen(!mobileOpen)}>
            {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* ── Row 2: Primary Navigation ───────────────────────────── */}
      <nav className="bg-[#F5F5F5] border-b border-[#DDDDDD] hidden sm:block">
        <div className="max-w-container mx-auto px-4">
          <ul className="flex items-stretch h-12">
            <li>
              <Link href="/"
                    className={`flex items-center justify-center px-4 h-full transition-colors
                      ${pathname === '/'
                        ? 'bg-[#CE7A58] text-white'
                        : 'text-[#1E2F41] hover:bg-[#CE7A58] hover:text-white'}`}>
                <Home className="w-4 h-4" />
              </Link>
            </li>

            {MAIN_NAV.map((item) => {
              const isActive = item.href
                ? pathname.startsWith(item.href)
                : item.children?.some((c) =>
                    'href' in c && typeof c.href === 'string' && pathname.startsWith(c.href)
                  )

              return (
                <li key={item.id} className="relative"
                    onMouseEnter={() => item.children && setOpenDropdown(item.id)}
                    onMouseLeave={() => setOpenDropdown(null)}>
                  {item.href ? (
                    <Link href={item.href}
                          className={`flex items-center gap-1 px-4 h-full text-sm transition-colors
                            ${isActive
                              ? 'bg-[#CE7A58] text-white'
                              : 'text-[#1E2F41] hover:bg-[#CE7A58] hover:text-white'}`}>
                      {item.label}
                    </Link>
                  ) : (
                    <button className={`flex items-center gap-1 px-4 h-full text-sm transition-colors
                              ${isActive || openDropdown === item.id
                                ? 'bg-[#CE7A58] text-white'
                                : 'text-[#1E2F41] hover:bg-[#CE7A58] hover:text-white'}`}>
                      {item.label}
                      <ChevronDown className="w-3 h-3 ml-0.5" />
                    </button>
                  )}

                  {/* Level-1 dropdown */}
                  {item.children && openDropdown === item.id && (
                    <div className="absolute top-full left-0 z-50 bg-white border border-[#DDDDDD]
                                    shadow-md min-w-[220px]">
                      {item.children.map((child, ci) =>
                        'children' in child && child.children ? (
                          <div key={ci} className="relative group">
                            <div className="flex items-center justify-between px-4 py-2 text-sm
                                            text-[#1E2F41] hover:bg-[#F5F5F5] cursor-default">
                              {child.label}
                              <ChevronDown className="w-3 h-3 -rotate-90" />
                            </div>
                            {/* Level-2 flyout */}
                            <div className="hidden group-hover:block absolute left-full top-0
                                            bg-white border border-[#DDDDDD] shadow-md min-w-[240px]">
                              {child.children.map((sub, si) => (
                                <Link key={si} href={sub.href}
                                      className="block px-4 py-2 text-sm text-[#1E2F41]
                                                 hover:bg-[#F5F5F5] hover:text-[#CE7A58]">
                                  {sub.label}
                                </Link>
                              ))}
                            </div>
                          </div>
                        ) : (
                          <Link key={ci} href={(child as any).href}
                                className="block px-4 py-2 text-sm text-[#1E2F41]
                                           hover:bg-[#F5F5F5] hover:text-[#CE7A58]">
                            {child.label}
                          </Link>
                        )
                      )}
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        </div>
      </nav>

      {/* ── Row 3: Sub-navigation (absent on homepage) ──────────── */}
      {!isHomepage && (
        <div className="bg-[#CE7A58] hidden sm:block">
          <div className="max-w-container mx-auto px-4">
            <ul className="flex items-stretch h-10">
              {SUB_NAV.map((item, i) => {
                const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
                return (
                  <li key={i}>
                    <Link href={item.href}
                          className={`flex items-center gap-0.5 px-4 h-full text-[13px] transition-colors
                            ${isActive
                              ? 'bg-[#B8694A] text-[#1E2F41] font-semibold'
                              : 'text-[#1E2F41] hover:bg-[#B8694A]'}`}>
                      {item.label}
                      {item.hasDropdown && <ChevronDown className="w-3 h-3 ml-0.5" />}
                    </Link>
                  </li>
                )
              })}
            </ul>
          </div>
        </div>
      )}

      {/* ── Mobile menu ──────────────────────────────────────────── */}
      {mobileOpen && (
        <div className="sm:hidden bg-white border-t border-[#DDDDDD] shadow-lg">
          <div className="py-2">
            {MAIN_NAV.map((item) => (
              <div key={item.id}>
                {item.href ? (
                  <Link href={item.href} onClick={() => setMobileOpen(false)}
                        className="block px-4 py-3 text-sm text-[#1E2F41] border-b border-[#F5F5F5]
                                   hover:bg-[#F5F5F5]">
                    {item.label}
                  </Link>
                ) : (
                  <div className="px-4 py-3 text-sm font-semibold text-[#1E2F41]
                                  border-b border-[#F5F5F5] bg-[#FAFAFA]">
                    {item.label}
                  </div>
                )}
                {item.children?.map((child, ci) =>
                  'href' in child && child.href ? (
                    <Link key={ci} href={child.href} onClick={() => setMobileOpen(false)}
                          className="block px-8 py-2.5 text-sm text-[#555] border-b border-[#F5F5F5]
                                     hover:bg-[#F5F5F5]">
                      {child.label}
                    </Link>
                  ) : null
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </header>
  )
}
