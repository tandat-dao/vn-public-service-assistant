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
      <div className="bg-[var(--terracotta)] border-b border-black/10">
        <div className="max-w-container mx-auto px-6 py-3 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 no-underline">
            <div className="w-[55px] h-[55px] flex-shrink-0 flex items-center justify-center">
              <div className="w-[55px] h-[55px] rounded-full bg-white/20 flex items-center
                              justify-center text-white text-2xl font-bold select-none">
                ★
              </div>
            </div>
            <div>
              <div className="text-white text-2xl font-semibold leading-tight tracking-wide"
                   style={{ fontFamily: "'Be Vietnam Pro', sans-serif" }}>
                Cổng Dịch vụ Công Quốc Gia
              </div>
              <div className="text-white/60 text-[13px]">
                Kết nối, cung cấp thông tin và dịch vụ công mọi lúc, mọi nơi
              </div>
            </div>
          </Link>

          {/* Auth buttons */}
          <div className="hidden sm:flex items-center gap-3">
            <Link href="/dang-ky"
                  className="bg-white text-[var(--terracotta)] hover:bg-white/90 text-sm font-medium px-4 py-1.5 rounded-lg transition-colors">
              Đăng ký
            </Link>
            <Link href="/dang-nhap"
                  className="text-white/80 hover:text-white text-sm transition-colors">
              Đăng nhập
            </Link>
            <button
              onClick={() => {
                sessionStorage.removeItem('dvc_pin_auth')
                window.location.reload()
              }}
              className="text-white/60 hover:text-white/90 text-sm transition-colors cursor-pointer"
            >
              Đăng xuất
            </button>
          </div>

          {/* Mobile hamburger */}
          <button className="sm:hidden text-white" onClick={() => setMobileOpen(!mobileOpen)}>
            {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* ── Row 2: Primary Navigation ───────────────────────────── */}
      <nav className="bg-[var(--terracotta-dk)] border-b border-black/10 hidden sm:block">
        <div className="max-w-container mx-auto px-4">
          <ul className="flex items-stretch h-12">
            <li>
              <Link href="/"
                    className={`flex items-center justify-center px-4 h-full transition-colors
                      ${pathname === '/'
                        ? 'text-white font-medium bg-white/15'
                        : 'text-white/80 hover:text-white hover:bg-white/10'}`}>
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
                              ? 'text-white font-medium bg-white/15'
                              : 'text-white/80 hover:text-white hover:bg-white/10'}`}>
                      {item.label}
                    </Link>
                  ) : (
                    <button className={`flex items-center gap-1 px-4 h-full text-sm transition-colors
                              ${isActive || openDropdown === item.id
                                ? 'text-white font-medium bg-white/15'
                                : 'text-white/80 hover:text-white hover:bg-white/10'}`}>
                      {item.label}
                      <ChevronDown className="w-3 h-3 ml-0.5" />
                    </button>
                  )}

                  {/* Level-1 dropdown */}
                  {item.children && openDropdown === item.id && (
                    <div className="absolute top-full left-0 z-50 bg-white border border-[var(--border-card)]
                                    shadow-lg min-w-[220px]">
                      {item.children.map((child, ci) =>
                        'children' in child && child.children ? (
                          <div key={ci} className="relative group">
                            <div className="flex items-center justify-between px-4 py-2 text-sm
                                            text-[var(--text-secondary)] hover:bg-[var(--terracotta-faint)] cursor-default">
                              {child.label}
                              <ChevronDown className="w-3 h-3 -rotate-90" />
                            </div>
                            {/* Level-2 flyout */}
                            <div className="hidden group-hover:block absolute left-full top-0
                                            bg-white border border-[var(--border-card)] shadow-lg min-w-[240px]">
                              {child.children.map((sub, si) => (
                                <Link key={si} href={sub.href}
                                      className="block px-4 py-2 text-sm text-[var(--text-secondary)]
                                                 hover:bg-[var(--terracotta-faint)] hover:text-[var(--terracotta)]">
                                  {sub.label}
                                </Link>
                              ))}
                            </div>
                          </div>
                        ) : (
                          <Link key={ci} href={(child as any).href}
                                className="block px-4 py-2 text-sm text-[var(--text-secondary)]
                                           hover:bg-[var(--terracotta-faint)] hover:text-[var(--terracotta)]">
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
        <div className="bg-[var(--terracotta-dk)] border-b border-black/10 hidden sm:block">
          <div className="max-w-container mx-auto px-4">
            <ul className="flex items-stretch h-10">
              {SUB_NAV.map((item, i) => {
                const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
                return (
                  <li key={i}>
                    <Link href={item.href}
                          className={`flex items-center gap-0.5 px-4 h-full text-[13px] transition-colors
                            ${isActive
                              ? 'text-white font-semibold'
                              : 'text-white/60 hover:text-white'}`}>
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
        <div className="sm:hidden bg-[var(--terracotta)] border-t border-black/10 shadow-lg">
          <div className="py-2">
            {MAIN_NAV.map((item) => (
              <div key={item.id}>
                {item.href ? (
                  <Link href={item.href} onClick={() => setMobileOpen(false)}
                        className="block px-4 py-3 text-sm text-white/70 border-b border-white/10
                                   hover:text-white hover:bg-white/10">
                    {item.label}
                  </Link>
                ) : (
                  <div className="px-4 py-3 text-sm font-semibold text-white/50
                                  border-b border-white/10">
                    {item.label}
                  </div>
                )}
                {item.children?.map((child, ci) =>
                  'href' in child && child.href ? (
                    <Link key={ci} href={child.href} onClick={() => setMobileOpen(false)}
                          className="block px-8 py-2.5 text-sm text-white/60 border-b border-white/10
                                     hover:text-white hover:bg-white/10">
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
