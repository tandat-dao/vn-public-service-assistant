import { SectionTitle } from '@/components/ui/SectionTitle'
import type { ServiceItem } from '@/lib/types'

const CONG_DAN: ServiceItem[] = [
  { id: '750', label: 'Có con nhỏ',                    icon: '👶', href: '/su-kien/750', group: 'cong-dan' },
  { id: '751', label: 'Học tập',                        icon: '🎓', href: '/su-kien/751', group: 'cong-dan' },
  { id: '752', label: 'Việc làm',                       icon: '💼', href: '/su-kien/752', group: 'cong-dan' },
  { id: '753a', label: 'Đăng ký thường trú',          icon: '🏠', href: '/thu-tuc/dang-ky-thuong-tru', group: 'cong-dan' },
  { id: '753b', label: 'Đăng ký tạm trú',             icon: '🏡', href: '/thu-tuc/dang-ky-tam-tru',    group: 'cong-dan' },
  { id: '753c', label: 'Xác nhận thông tin cư trú',   icon: '📋', href: '/thu-tuc/xac-nhan-cu-tru',    group: 'cong-dan' },
  { id: '754', label: 'Hôn nhân và gia đình',           icon: '💑', href: '/su-kien/754', group: 'cong-dan' },
  { id: '755', label: 'Điện lực, nhà ở, đất đai',      icon: '⚡', href: '/su-kien/755', group: 'cong-dan' },
  { id: '756', label: 'Sức khỏe và y tế',              icon: '🏥', href: '/su-kien/756', group: 'cong-dan' },
  { id: '757', label: 'Phương tiện và người lái',       icon: '🚗', href: '/su-kien/757', group: 'cong-dan' },
  { id: '758', label: 'Hưu trí',                        icon: '👴', href: '/su-kien/758', group: 'cong-dan' },
  { id: '759', label: 'Người thân qua đời',             icon: '🕊️', href: '/su-kien/759', group: 'cong-dan' },
  { id: '760', label: 'Giải quyết khiếu kiện',          icon: '⚖️', href: '/su-kien/760', group: 'cong-dan' },
]

const DOANH_NGHIEP: ServiceItem[] = [
  { id: 'dn1',  label: 'Khởi sự kinh doanh',                      icon: '🚀', href: '/su-kien/dn1',  group: 'doanh-nghiep' },
  { id: 'dn2',  label: 'Lao động và bảo hiểm xã hội',             icon: '👷', href: '/su-kien/dn2',  group: 'doanh-nghiep' },
  { id: 'dn3',  label: 'Tài chính doanh nghiệp',                  icon: '💰', href: '/su-kien/dn3',  group: 'doanh-nghiep' },
  { id: 'dn4',  label: 'Điện lực, đất đai, xây dựng',             icon: '🏗️', href: '/su-kien/dn4',  group: 'doanh-nghiep' },
  { id: 'dn5',  label: 'Thương mại, quảng cáo',                   icon: '📢', href: '/su-kien/dn5',  group: 'doanh-nghiep' },
  { id: 'dn6',  label: 'Sở hữu trí tuệ, đăng ký tài sản',        icon: '📋', href: '/su-kien/dn6',  group: 'doanh-nghiep' },
  { id: 'dn7',  label: 'Thành lập chi nhánh, văn phòng đại diện', icon: '🏢', href: '/su-kien/dn7',  group: 'doanh-nghiep' },
  { id: 'dn8',  label: 'Đấu thầu, mua sắm công',                  icon: '📊', href: '/su-kien/dn8',  group: 'doanh-nghiep' },
  { id: 'dn9',  label: 'Tái cấu trúc doanh nghiệp',               icon: '🔄', href: '/su-kien/dn9',  group: 'doanh-nghiep' },
  { id: 'dn10', label: 'Giải quyết tranh chấp hợp đồng',          icon: '⚖️', href: '/su-kien/dn10', group: 'doanh-nghiep' },
  { id: 'dn11', label: 'Tạm dừng, chấm dứt hoạt động',            icon: '⏸️', href: '/su-kien/dn11', group: 'doanh-nghiep' },
]

function ServiceItemCard({ item }: { item: ServiceItem }) {
  return (
    <a href={item.href} className="service-item">
      <span className="text-xl w-8 text-center flex-shrink-0"
            style={{ color: item.group === 'cong-dan' ? '#3D9E8D' : '#CE7A58' }}>
        {item.icon}
      </span>
      <span className="text-sm text-[#1E2F41]">{item.label}</span>
    </a>
  )
}

export function LifeEventsGrid() {
  return (
    <section className="py-10 bg-white">
      <div className="max-w-container mx-auto px-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-12">
          <div className="max-w-sm ml-auto w-full">
            <SectionTitle>Công dân</SectionTitle>
            {CONG_DAN.map((item) => <ServiceItemCard key={item.id} item={item} />)}
          </div>
          <div className="max-w-sm mr-auto w-full">
            <SectionTitle>Doanh nghiệp</SectionTitle>
            {DOANH_NGHIEP.map((item) => <ServiceItemCard key={item.id} item={item} />)}
          </div>
        </div>
      </div>
    </section>
  )
}
