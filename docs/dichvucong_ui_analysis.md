# DichVuCong.gov.vn — UI & Frontend Analysis
## Coding Reference for the Mock AI Portal

**Source:** Live analysis of `https://dichvucong.gov.vn` (March 2026)
**Purpose:** This document is the definitive frontend reference for the mock portal project.
All component specs, color values, layout patterns, and page structures described here come
directly from the live site and must be faithfully replicated in the Next.js implementation.

---

## 1. Tech Stack (Live Site)

The live site is a jQuery/Bootstrap server-rendered portal — **not** a SPA. Our implementation
replaces this with Next.js 14 App Router while preserving the visual design exactly.

| Concern | Live Site | Our Implementation |
|---|---|---|
| Framework | jQuery 2.1.1 + Bootstrap 3 | Next.js 14 (App Router) |
| Templating | Handlebars.js | React Server Components |
| Charts | Highcharts | Recharts |
| Slider | Slick carousel | react-slick or Embla |
| Form validation | bootstrapValidator.js | React Hook Form + Zod |
| Icons | Font Awesome 4.x | Font Awesome 6 or react-icons/fa |
| State | jQuery DOM manipulation | Zustand |
| Images | SVG icons at `/theme/img/home/congdan/*.svg` | Replicate with SVG or Lucide equivalents |

---

## 2. Design Tokens — Color Palette

These are exact computed values extracted from the live site. Use these as CSS variables.

```css
/* globals.css */
:root {
  /* --- Brand Primary --- */
  --color-primary:           #CE7A58;  /* rgb(206, 122, 88) — sub-nav bg, hero bg, .btn-main */
  --color-primary-dark:      #903938;  /* rgb(144, 57, 56)  — footer bg */
  --color-primary-hover:     #B8694A;  /* darker tint for hover/active states */
  --color-primary-light:     #F5E8DF;  /* very light tint for backgrounds */

  /* --- CTA Yellow (hero buttons only) --- */
  --color-cta:               #FFC251;  /* rgb(255, 194, 81) — .btn-fourth */
  --color-cta-text:          #000000;

  /* --- Neutrals --- */
  --color-nav-bg:            #F5F5F5;  /* rgb(245, 245, 245) — top nav row */
  --color-text-primary:      #1E2F41;  /* rgb(30, 47, 65)   — all body text */
  --color-text-secondary:    #555555;
  --color-border:            #DDDDDD;
  --color-bg-page:           #FFFFFF;
  --color-bg-item:           #F5F5F5;  /* service item card bg */

  /* --- Links --- */
  --color-link:              #2A6EBB;  /* rgb(42, 110, 187) */
  --color-link-hover:        #1E4F8A;

  /* --- Category Icon Colors --- */
  --color-icon-congdan:      #3D9E8D;  /* teal — Công dân column icons */
  --color-icon-doanhnghiep:  #CE7A58;  /* orange — Doanh nghiệp column icons */
  --color-icon-hoso:         #4A7AA8;  /* steel blue — hồ sơ stat boxes */

  /* --- Footer --- */
  --color-footer-bg:         #903938;
  --color-footer-text:       #FFFFFF;

  /* --- UI States --- */
  --color-score-badge:       #28A745;
  --color-tab-active:        #CE7A58;
  --color-section-divider:   #CE7A58;  /* bottom border under section titles */
  --color-required:          #CC0000;  /* red asterisk on required fields */
}
```

### Color Usage Rules

| Color | Where Used |
|---|---|
| `#CE7A58` (primary orange-copper) | Sub-nav bar, hero section bg, `.btn-main`, active nav highlight, tab borders, section title dividers |
| `#FFC251` (CTA yellow) | Homepage hero buttons ONLY — all 3 large CTAs |
| `#903938` (dark red-brown) | Footer bar only |
| `#F5F5F5` (light grey) | Top nav row bg, service item card bg, search button bg |
| `#1E2F41` (dark navy) | All body text, headings, nav text |
| `#2A6EBB` (blue) | Hyperlinks |
| `#3D9E8D` (teal) | Công dân icon circles |
| `#FFFFFF` (white) | Header logo row, all page content areas, footer text |

---

## 3. Typography

```css
/* Load from Google Fonts in layout.tsx */
import { Nunito } from 'next/font/google';
const nunito = Nunito({ subsets: ['latin', 'vietnamese'], weight: ['400', '600', '700'] });
```

The site uses **Nunito** as its primary font with Arial as fallback. No other font families are used.

| Element | Weight | Size | Notes |
|---|---|---|---|
| Body text | 400 | 14px | Default for all paragraph/list text |
| Navigation items | 600 | 14px | |
| Sub-nav items | 400 | 13px | Slightly smaller |
| Section titles | 700 | 18px | All-caps, `letter-spacing: 1px` |
| Page H1 titles | 700 | 22–24px | |
| Breadcrumb | 400 | 13px | Secondary color |
| Table headers | 600 | 13px | |
| Stat counter numbers | 700 | 28–32px | `--color-primary` color |
| Button text | 600 | 14px | |
| FAQ question text | 400 | 14px | Single line |

---

## 4. Page Shell Layout (All Pages)

```
┌──────────────────────────────────────────────────────┐
│  .header                        height: ~90px        │
│  bg: #FFFFFF                                         │
│  [National emblem + Portal title]  [Đăng ký | Đăng nhập] │
├──────────────────────────────────────────────────────┤
│  nav.header-nav                 height: ~48px        │
│  bg: #F5F5F5                                         │
│  🏠 | Thông tin và dịch vụ ▾ | Thanh toán | ...     │
├──────────────────────────────────────────────────────┤
│  .header-bottom                 height: ~40px        │
│  bg: #CE7A58  (ABSENT on homepage)                   │
│  Thủ tục HC ▾ | Dịch vụ công TT | ... | Câu hỏi TG  │
├──────────────────────────────────────────────────────┤
│  [Page-specific content area]                        │
│  bg: #FFFFFF                                         │
│  max-width: 1170px, centered                         │
├──────────────────────────────────────────────────────┤
│  .section-hotro                 height: ~80px        │
│  [🪙 Câu hỏi thường gặp]  [🪙 Hướng dẫn sử dụng]  │
├──────────────────────────────────────────────────────┤
│  footer                         height: ~50px        │
│  bg: #903938, text: #FFFFFF                          │
│  Cơ quan chủ quản | URL | Tổng đài | Email           │
└──────────────────────────────────────────────────────┘
```

### Grid System
Bootstrap 3 / Tailwind equivalent: 12-column grid, `container` at `max-w-screen-xl mx-auto px-4`.

---

## 5. Header Component — Detailed Spec

### Row 1: `.header` (Logo + Auth)
- `background: #FFFFFF`, `padding: 12px 0`
- **Left side:**
  - National emblem image (Quốc huy): ~55×55px
  - Title text block:
    - Line 1: **"Cổng Dịch vụ Công Quốc Gia"** — decorative serif-adjacent style, `--color-primary-dark`, ~28px, bold
    - Line 2: *"Kết nối, cung cấp thông tin và dịch vụ công mọi lúc, mọi nơi"* — italic, `--color-primary`, 13px
- **Right side:** Two buttons side-by-side
  - `Đăng ký`: `border: 1px solid #1E2F41`, transparent bg, 3px radius
  - `Đăng nhập`: same style

### Row 2: `nav.header-nav` (Primary Navigation)
- `background: #F5F5F5`, `height: 48px`
- Items: 🏠 | Thông tin và dịch vụ | Thanh toán trực tuyến | Phản ánh kiến nghị | Đánh giá chất lượng phục vụ | Hỗ trợ
- **Active/hover state:** `background: #CE7A58`, `color: #FFFFFF`
- **Dropdown arrow:** Visible `▼` on items with sub-menus
- **Dropdown panel:** White bg, subtle box-shadow, 1px `#DDDDDD` border, `z-index: 500`
- Dropdown items: `padding: 8px 16px`, hover bg `#F5F5F5`

### Row 3: `.header-bottom` (Sub-navigation)
- `background: #CE7A58`, `height: 40px`
- `color: #1E2F41` (dark text on orange background)
- Items: Thủ tục hành chính (▼ flyout) | Dịch vụ công trực tuyến | Dịch vụ công nổi bật | Tra cứu hồ sơ | Tòa án nhân dân | Câu hỏi thường gặp
- **Active item:** slightly darker bg `#B8694A`
- **Rule: This row does NOT render on the homepage (`/`)**. Only on inner pages.

### Dropdown Submenus under "Thông tin và dịch vụ"
```
Thủ tục hành chính →
  Tra cứu TTHC
  Thủ tục hành chính
  Thủ tục hành chính liên thông
  Quyết định công bố
  Cơ quan

Dịch vụ công trực tuyến
Dịch vụ công nổi bật
Tra cứu hồ sơ
Tòa án nhân dân
Câu hỏi thường gặp
```

### Breadcrumb
- Below `.header-bottom` on inner pages only
- Pattern: `Trang chủ > [Page Name]` or `Trang chủ > Section > Page`
- Font: 13px, `--color-text-secondary`
- Current page is not a link

---

## 6. Homepage Sections

### 6.1 Hero Banner (`.hero-banner`)
- `background-color: #CE7A58`
- `background-image: url('/theme/img/home/banner.jpg')` — Vietnamese cultural pattern overlay (Dong Son drum motif + crane birds), semi-transparent over the orange
- Right side: Painted lotus flower artwork panel
- Height: ~220px
- **Content (centered, `max-width: 900px`):**
  - Search bar row: `<input placeholder="Nhập từ khoá tìm kiếm">` + `Tìm kiếm nâng cao` link + search icon button
  - 3 CTA buttons in a row (`col-sm-4` each):
    - "Dịch vụ công trực tuyến"
    - "Dịch vụ công trực tuyến của Đảng"
    - "Dịch vụ công liên thông: Khai sinh, Khai tử"
  - CTA button style: `background: #FFC251`, `color: #000`, `font-weight: 700`, `padding: 12px`, `border-radius: 4px`, `width: 100%`, `text-align: center`

### 6.2 News Strip (`.hotnews-top`)
- White background, sits directly below the hero
- Three news cards side-by-side, each showing headline + date
- Left `<` and right `>` arrow navigation (Slick slider pattern)
- Lotus painting image on the far right
- News date format: `Ngày DD/MM/YYYY`

### 6.3 Life Events Grid (`.targetgroup-area`)
- `padding: 40px 0`
- Two equal columns: `CÔNG DÂN` (left) and `DOANH NGHIỆP` (right)
- **Column header:**
  - Text: All-caps, `color: #CE7A58`, `font-size: 18px`, `font-weight: 700`, `letter-spacing: 1px`
  - Bottom border: `2px solid #CE7A58`, centered
- **Each item (`.item`):**
  - Rounded rectangle card, `background: #F5F5F5`, `border-radius: 6px`, `padding: 10px 14px`
  - `.icon` — SVG image, 28px, loaded from `/theme/img/home/congdan/*.svg`
  - `.text` — 14px, `--color-text-primary`
  - Items link to `/dvc-chi-tiet-nhom-su-kien-cho-cong-dan.html?group=XXX`

**Công dân items (in order):**
Có con nhỏ (`cocon.svg`), Học tập (`giaoduc.svg`), Việc làm (`vieclam.svg`),
Cư trú và giấy tờ tùy thân, Hôn nhân và gia đình, Điện lực/nhà ở/đất đai,
Sức khỏe và y tế, Phương tiện và người lái, Hưu trí, Người thân qua đời, Giải quyết khiếu kiện

**Doanh nghiệp items (in order):**
Khởi sự kinh doanh, Lao động và bảo hiểm xã hội, Tài chính doanh nghiệp,
Điện lực/đất đai/xây dựng, Thương mại/quảng cáo, Sở hữu trí tuệ/đăng ký tài sản,
Thành lập chi nhánh/văn phòng đại diện, Đấu thầu/mua sắm công,
Tái cấu trúc doanh nghiệp, Giải quyết tranh chấp hợp đồng, Tạm dừng/chấm dứt hoạt động

---

## 7. Inner Page Templates

### 7.1 Service Search Page (Dịch vụ công trực tuyến)
- H1 breadcrumb: "Cổng Dịch vụ công quốc gia > Dịch vụ công trực tuyến"
- Full-width search bar + orange `Tìm kiếm` button
- Filter row: 5 `<select>` dropdowns (Cơ quan, Đơn vị, Thời gian, Đối tượng, Mức độ DVC)
- **Stats row (4 boxes):**
  - Box 1: Teal circle icon + **1965** (huge) + "Công dân" label, sub-stats: 983 / 982
  - Box 2: Orange circle icon + **2966** + "Doanh nghiệp" label, sub-stats: 1.600 / 1.366
  - Box 3: Steel-blue icon + **636.949.779** + "Số hồ sơ đồng bộ trang thái xử lý..."
  - Box 4: Light-orange icon + **94.356.514** + "Số hồ sơ trực tuyến thực hiện..."
- Tabs: "Bộ, cơ quan ngang Bộ" | "Tỉnh, Thành phố" | "Cơ quan khác"
- Table: ministry/province rows with 5 numeric columns

### 7.2 File Lookup Page (Tra cứu hồ sơ)
- Three horizontal tabs: "Tra cứu theo mã hồ sơ" | "Tra cứu theo cơ quan thực hiện" | "Tra cứu thông báo khuyến mại"
- Active tab: orange underline + bold
- Form layout (2-col): `Mã hồ sơ *` wide input | `Mã bảo mật *` narrow input + CAPTCHA image + ↻ refresh button
- `Tra cứu` button: `background: #CE7A58`, white text
- Right side watermark: faint crane bird illustration (Vietnamese motif)

### 7.3 FAQ Page (Câu hỏi thường gặp)
- Search: text input (wider) + Bộ ngành `<select>` + `🔍 Tìm kiếm` button row
- H1: "Câu hỏi thường gặp"
- Tabs: "Tất cả (9452)" | "Công dân (1133)" | "Doanh nghiệp (834)" | "Tổ chức khác (1492)"
- Each FAQ: `?` circle icon (grey) + question text on one line, clickable link
- No card/box wrappers — plain list

### 7.4 Quality Index Page (Đánh giá chất lượng phục vụ)
- Title: all-caps heavy heading `BỘ CHỈ SỐ PHỤC VỤ NGƯỜI DÂN, DOANH NGHIỆP...`
- Note text in red (important annotation about calculation method)
- Two dropdowns top-right: "Tỉnh, Thành phố" and "Danh sách"
- 4 filter selects: Nhóm chỉ tiêu | Loại thời gian | Năm | Tỉnh/thành phố
- Data table: STT | Tỉnh/Thành phố | Công khai minh bạch | Tiến độ giải quyết | Dịch vụ trực tuyến | Mức độ hài lòng | Số hóa hồ sơ | **Tổng điểm** (green badge)

### 7.5 Payment Page (Thanh toán trực tuyến)
- Identical two-column layout as the homepage life events grid
- Same section title styling: CÔNG DÂN (teal) | DOANH NGHIỆP (orange)
- Items: small square icon + text label in light-grey rounded cards
- Right side: Watermark artwork (Vietnamese crane)

---

## 8. Component Library Reference

### Button Classes

```tsx
// Primary action (search, submit, confirm)
<button className="bg-[#CE7A58] text-white font-semibold px-5 py-2 rounded hover:bg-[#B8694A]">
  Tìm kiếm
</button>

// Hero CTA (yellow, homepage only)
<a className="bg-[#FFC251] text-black font-bold py-3 px-4 rounded w-full text-center block">
  Dịch vụ công trực tuyến
</a>

// Auth buttons (outline)
<button className="border border-[#1E2F41] text-[#1E2F41] px-3 py-1.5 rounded text-sm">
  Đăng nhập
</button>
```

### Search Bar

```tsx
<div className="flex">
  <input
    className="flex-1 border border-[#DDDDDD] px-3 py-2 rounded-l text-sm focus:outline-none focus:border-[#CE7A58]"
    placeholder="Nhập từ khoá tìm kiếm"
  />
  <span className="text-xs text-[#2A6EBB] px-3 py-2 border-t border-b border-[#DDDDDD] flex items-center cursor-pointer">
    Tìm kiếm nâng cao
  </span>
  <button className="bg-[#F5F5F5] border border-[#DDDDDD] border-l-0 px-3 py-2 rounded-r">
    🔍
  </button>
</div>
```

### Tab Bar

```tsx
{/* Tab bar with orange active indicator */}
<div className="flex border-b border-[#DDDDDD]">
  <button className="px-4 py-2.5 text-[#CE7A58] font-bold border-b-2 border-[#CE7A58]">
    Tra cứu theo mã hồ sơ
  </button>
  <button className="px-4 py-2.5 text-[#555] hover:text-[#CE7A58]">
    Tra cứu theo cơ quan thực hiện
  </button>
</div>
```

### Service Item Card

```tsx
<a className="flex items-center gap-3 bg-[#F5F5F5] rounded-md px-4 py-3 mb-2 hover:bg-[#EBEBEB] transition-colors cursor-pointer">
  <img src="/icons/cocon.svg" alt="" className="w-8 h-8 flex-shrink-0" />
  <span className="text-[#1E2F41] text-sm">Có con nhỏ</span>
</a>
```

### Section Title with Divider

```tsx
<div className="text-center mb-5">
  <h2 className="text-[#CE7A58] text-lg font-bold uppercase tracking-wider pb-2 border-b-2 border-[#CE7A58] inline-block">
    CÔNG DÂN
  </h2>
</div>
```

### Stat Counter Box

```tsx
<div className="flex items-center gap-3 border border-[#DDDDDD] rounded p-4">
  <div className="w-12 h-12 rounded-full bg-[#3D9E8D] flex items-center justify-center flex-shrink-0">
    {/* icon */}
  </div>
  <div>
    <div className="text-[#CE7A58] text-3xl font-bold">1965</div>
    <div className="text-[#555] text-xs">Công dân</div>
  </div>
</div>
```

### Score Badge

```tsx
<span className="bg-[#28A745] text-white text-sm font-bold px-2 py-1 rounded">
  96.66
</span>
```

### Data Table

```tsx
<table className="w-full border-collapse text-sm">
  <thead>
    <tr className="border-b-2 border-[#DDDDDD]">
      <th className="py-3 px-3 text-left font-semibold text-[#1E2F41] bg-[#F5F5F5]">STT</th>
      <th className="py-3 px-3 text-left font-semibold text-[#1E2F41] bg-[#F5F5F5]">Tỉnh/Thành phố</th>
      {/* more headers */}
    </tr>
  </thead>
  <tbody>
    <tr className="border-b border-[#EEEEEE] hover:bg-[#FAFAFA]">
      <td className="py-2.5 px-3">1</td>
      <td className="py-2.5 px-3">UBND tỉnh Vĩnh Long</td>
    </tr>
  </tbody>
</table>
```

---

## 9. Navigation Structure & Next.js Routes

### Primary Nav Items + Dropdowns (source of truth)

```
🏠 Home → /

Thông tin và dịch vụ ▾
  Thủ tục hành chính ▸
    Tra cứu TTHC → /thu-tuc-hanh-chinh
    Thủ tục hành chính → /thu-tuc-hanh-chinh/danh-sach
    TTHC liên thông → /thu-tuc-hanh-chinh/lien-thong
    Quyết định công bố → /thu-tuc-hanh-chinh/quyet-dinh
    Cơ quan → /thu-tuc-hanh-chinh/co-quan
  Dịch vụ công trực tuyến → /dich-vu-cong
  Dịch vụ công nổi bật → /dich-vu-cong/noi-bat
  Tra cứu hồ sơ → /tra-cuu-ho-so
  Tòa án nhân dân → /toa-an
  Câu hỏi thường gặp → /cau-hoi-thuong-gap

Thanh toán trực tuyến → /thanh-toan

Phản ánh kiến nghị ▾
  Gửi PAKN → /phan-anh-kien-nghi/gui
  Tra cứu kết quả trả lời → /phan-anh-kien-nghi/tra-cuu

Đánh giá chất lượng phục vụ → /danh-gia-chat-luong

Hỗ trợ ▾
  Giới thiệu → /ho-tro/gioi-thieu
  Điều khoản sử dụng → /ho-tro/dieu-khoan
  Hướng dẫn sử dụng → /ho-tro/huong-dan
  Thông báo → /thong-bao
```

### App Router File Structure

```
app/
├── layout.tsx                        ← Shell: header + footer + chat widget
├── page.tsx                          ← Homepage
├── thu-tuc-hanh-chinh/
│   ├── page.tsx                      ← TTHC search
│   ├── danh-sach/page.tsx
│   ├── lien-thong/page.tsx
│   └── [id]/page.tsx                 ← Procedure detail + dependency plan
├── dich-vu-cong/
│   ├── page.tsx                      ← DVC search + stats + table
│   └── noi-bat/page.tsx
├── tra-cuu-ho-so/
│   └── page.tsx                      ← File lookup (CAPTCHA form)
├── cau-hoi-thuong-gap/
│   └── page.tsx                      ← FAQ list + search
├── thanh-toan/
│   └── page.tsx                      ← Payment categories
├── danh-gia-chat-luong/
│   └── page.tsx                      ← Quality index table
├── phan-anh-kien-nghi/
│   ├── gui/page.tsx
│   └── tra-cuu/page.tsx
├── ho-tro/
│   ├── gioi-thieu/page.tsx
│   ├── dieu-khoan/page.tsx
│   └── huong-dan/page.tsx
└── chat/
    └── page.tsx                      ← Full-page AI assistant (new)
```

---

## 10. AI Assistant Widget (New — Not in Original Site)

The AI assistant is a **net new feature** layered on top of the existing design.
It must visually belong to the portal — same color palette, same typography.

### Floating Trigger Button
```tsx
// Position: fixed bottom-right, above footer
<button
  className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-[#CE7A58] text-white 
             shadow-lg hover:bg-[#903938] transition-colors flex items-center justify-center"
  onClick={() => chatStore.open()}
>
  <ChatBubbleIcon className="w-6 h-6" />
</button>
```

### Chat Slide-Up Window
- `position: fixed`, `bottom: 88px`, `right: 24px`
- `width: 380px`, `height: 520px`, `z-index: 49`
- `border-radius: 8px`, `box-shadow: 0 8px 32px rgba(0,0,0,0.18)`
- **Header bar:** `background: #CE7A58`, white text "Trợ lý Dịch vụ Công", ✕ close button
- **Message area:** `background: #FFFFFF`, scrollable
- **User bubbles:** Right-aligned, `background: #CE7A58`, white text, `border-radius: 16px 16px 4px 16px`
- **AI bubbles:** Left-aligned, `background: #F5F5F5`, dark text, `border-radius: 16px 16px 16px 4px`
- **Citation chips:** Below AI messages — small orange-bordered inline chips `[Điều X, NĐ YYY]`
- **Loading indicator:** 3-dot animation in `#CE7A58`
- **Input bar:** White bg, top border `1px solid #DDDDDD`, text input + 📎 upload icon + send button

### Dedicated Chat Page (`/chat`)
Full-page layout:
```
┌────────────────────────────────────────────────────┐
│  [Header shell]                                    │
├──────────────┬─────────────────────────────────────┤
│ Sidebar      │ Chat messages area                  │
│ (session     │                                     │
│  history)    │  [message bubbles]                  │
│              │                                     │
│              ├─────────────────────────────────────┤
│              │ [Input: text + upload + send]        │
└──────────────┴─────────────────────────────────────┘
```
When `intent = procedure_inquiry`, a collapsible right panel shows the
**Procedure Execution Plan** tree with step statuses (✅ completed / ⏳ pending / 🔒 blocked).

---

## 11. Responsive Behaviour

| Breakpoint | Behaviour |
|---|---|
| `< 768px` | Stack to 1 column; hamburger menu (☰); hero CTAs stack vertically; chat window goes full-screen |
| `768px – 991px` | Sub-nav wraps to 2 rows; life events grid maintained 2-col |
| `≥ 992px` | Full 3-row header; horizontal sub-nav; 2-col grid |
| `≥ 1200px` | `container` locks at 1170px, centered; no layout changes |

Tailwind config breakpoints to match Bootstrap 3: `sm: 768px`, `md: 992px`, `lg: 1200px`

---

## 12. Decorative Vietnamese Motifs

These elements give the portal its distinctive cultural identity and must be replicated:

| Element | Where | Implementation |
|---|---|---|
| National emblem (Quốc huy) | Header logo row | SVG or PNG, ~55×55px |
| Portal title calligraphy font | Header | The site uses a custom decorative font for "Cổng Dịch vụ Công Quốc Gia" — approximate with a serif variant or use an SVG text |
| Cultural pattern overlay | Hero banner bg | A semi-transparent pattern of Dong Son drum/Lac Hong motifs over `#CE7A58`. Can approximate with a CSS geometric SVG pattern or an actual image |
| Lotus painting panel | News strip right side | Rectangular panel with watercolour lotus art — use as a static image |
| Crane bird watermark | Tra cứu hồ sơ page, right side | Light grey/transparent crane SVG, `opacity: 0.08`, absolutely positioned |
| Page decoration | Some inner pages — top-right behind breadcrumb | Same crane, larger, `opacity: 0.06` |

For the mock, the hero banner decoration can be approximated with:
```css
.hero-banner {
  background-color: #CE7A58;
  background-image: url('/images/banner-pattern.png');  /* tiled Dong Son pattern */
  background-blend-mode: overlay;
  background-size: cover;
}
```

---

## 13. Footer

```tsx
<footer className="bg-[#903938] text-white py-4">
  <div className="container mx-auto max-w-screen-xl px-4">
    <p className="text-center text-sm">
      Cơ quan chủ quản: Văn phòng Chính phủ &nbsp;|&nbsp;
      www.dichvucong.gov.vn &nbsp;|&nbsp;
      Tổng đài hỗ trợ: 18001096 &nbsp;|&nbsp;
      Email: dichvucong@chinhphu.vn
    </p>
  </div>
</footer>
```

---

## 14. API Connection Points

| Page | Endpoint | Data |
|---|---|---|
| Dịch vụ công trực tuyến | `GET /api/v1/procedures/stats` | Counter boxes |
| | `GET /api/v1/procedures?organ=&level=&year=` | Table data |
| Thủ tục hành chính `[id]` | `GET /api/v1/procedures/{id}` | Procedure detail |
| Tra cứu hồ sơ | `GET /api/v1/submissions/{ma_ho_so}` | Submission status |
| Câu hỏi thường gặp | `GET /api/v1/faq?q=&category=` | FAQ list (RAG-powered) |
| Đánh giá chất lượng | `GET /api/v1/quality-index?year=&province=` | Rankings table |
| AI Chat | `POST /api/v1/chat` (SSE stream) | Full multi-agent pipeline |
| Document Upload | `POST /api/v1/documents/upload` | OCR + PersonalData extraction |
| Form Fill | `GET /api/v1/forms/{id}/fill` | Filled PDF download URL |

---

## 15. Zustand Store Structure

```typescript
// frontend/lib/stores/chatStore.ts
interface ChatStore {
  isOpen: boolean;
  sessionId: string | null;
  messages: ChatMessage[];
  isStreaming: boolean;
  uploadedFile: File | null;
  procedurePlan: ProcedureStep[] | null;
  actions: {
    open: () => void;
    close: () => void;
    sendMessage: (text: string, file?: File) => Promise<void>;
    clearSession: () => void;
  };
}

// frontend/lib/stores/navigationStore.ts
interface NavigationStore {
  activeMainNav: string;
  activeSubNav: string;
  breadcrumbs: { label: string; href?: string }[];
}

// frontend/lib/stores/procedureStore.ts
interface ProcedureStore {
  selectedProcedureId: string | null;
  executionPlan: ProcedureStep[];
  completedProcedureIds: string[];
  actions: {
    selectProcedure: (id: string) => void;
    markCompleted: (id: string) => void;
  };
}
```

---

## 16. Implementation Priority Order

Build in this order to ship working visual fidelity fastest:

1. `globals.css` — All CSS tokens from Section 2 + Nunito font
2. `Header` component — All 3 rows, dropdowns wired to routes
3. `Footer` component
4. Homepage — Hero banner + news strip stub + life events 2-col grid
5. Sub-navigation bar (conditionally hidden on `/`)
6. `Breadcrumb` component
7. `/dich-vu-cong` page — search + filters + stat boxes + tabs + table
8. `/tra-cuu-ho-so` page — tab form + CAPTCHA placeholder
9. `/cau-hoi-thuong-gap` page — FAQ list + search
10. AI chat floating widget + `/chat` full page
11. `/thu-tuc-hanh-chinh/[id]` — procedure detail + dependency plan view
12. Responsive pass

---

## 17. Hard Rules — Do Not Violate

- **Font:** `Nunito` only. Never Inter, Roboto, or system fonts.
- **Color:** Never purple, blue gradients, or "AI aesthetic" palettes. The palette is warm copper, dark red-brown, and white.
- **Header:** The 3-row structure is the portal's visual identity. Never collapse or combine these rows on desktop.
- **Border-radius:** Never exceed `6px` on any component. The site is intentionally angular and formal.
- **Card shadows:** The life events grid uses flat `#F5F5F5` cards — no `box-shadow`. Only the chat window and dropdowns get shadow.
- **Table alignment:** All table content is left-aligned. Only the score badge (Tổng điểm) column is center-aligned.
- **Sub-nav visibility:** `.header-bottom` must NOT render on the homepage (`/`). It renders on all other routes.
- **AI chat widget:** Must not cover navigation elements. `z-index: 49` for the window, `z-index: 50` for the trigger button; always `bottom-6 right-6`.
- **CTA yellow (`#FFC251`):** Used ONLY for the 3 homepage hero buttons. Not for any other buttons elsewhere in the app.
- **Text on primary (#CE7A58) surfaces:** Use `#1E2F41` (dark navy) — NOT white. Sub-nav uses dark text on the orange bar.
