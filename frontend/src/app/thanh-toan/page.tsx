import { Breadcrumb }    from '@/components/ui/Breadcrumb'
import { SectionTitle }  from '@/components/ui/SectionTitle'
import type { ServiceItem } from '@/lib/types'

const CONG_DAN: ServiceItem[] = [
  { id: 'tt1', label: 'Thanh toán phí, lệ phí TTHC',          icon: '💳', href: '/thanh-toan/phi-le-phi', group: 'cong-dan' },
  { id: 'tt2', label: 'Khai và nộp thuế thu nhập cá nhân',      icon: '📑', href: '/thanh-toan/thue-tncn',  group: 'cong-dan' },
  { id: 'tt3', label: 'Đóng BHXH tự nguyện và BHYT',           icon: '🏥', href: '/thanh-toan/bh',         group: 'cong-dan' },
  { id: 'tt4', label: 'Nộp thuế, lệ phí đất đai',              icon: '🏡', href: '/thanh-toan/dat-dai',    group: 'cong-dan' },
  { id: 'tt5', label: 'Nộp phạt vi phạm hành chính',           icon: '⚠️', href: '/thanh-toan/phat-vphc',  group: 'cong-dan' },
  { id: 'tt6', label: 'Thanh toán tiền điện, nước',             icon: '💡', href: '/thanh-toan/dien-nuoc',  group: 'cong-dan' },
  { id: 'tt7', label: 'Nộp tạm ứng án phí',                    icon: '⚖️', href: '/thanh-toan/an-phi',     group: 'cong-dan' },
]

const DOANH_NGHIEP: ServiceItem[] = [
  { id: 'dn-tt1', label: 'Nộp thuế doanh nghiệp',                  icon: '💼', href: '/thanh-toan/thue-dn',        group: 'doanh-nghiep' },
  { id: 'dn-tt2', label: 'Đóng bảo hiểm xã hội doanh nghiệp',     icon: '🛡️', href: '/thanh-toan/bhxh-dn',        group: 'doanh-nghiep' },
  { id: 'dn-tt3', label: 'Thanh toán phí cấp phép kinh doanh',     icon: '📋', href: '/thanh-toan/cap-phep',       group: 'doanh-nghiep' },
  { id: 'dn-tt4', label: 'Nộp phí môi trường',                     icon: '🌱', href: '/thanh-toan/moi-truong',     group: 'doanh-nghiep' },
  { id: 'dn-tt5', label: 'Thanh toán phí sử dụng đất',             icon: '🏗️', href: '/thanh-toan/phi-dat',        group: 'doanh-nghiep' },
  { id: 'dn-tt6', label: 'Nộp phạt vi phạm hành chính (DN)',       icon: '⚠️', href: '/thanh-toan/phat-dn',        group: 'doanh-nghiep' },
  { id: 'dn-tt7', label: 'Thanh toán tạm ứng án phí (DN)',         icon: '⚖️', href: '/thanh-toan/an-phi-dn',      group: 'doanh-nghiep' },
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

export default function ThanhToanPage() {
  return (
    <div className="max-w-container mx-auto px-4 py-4">
      <Breadcrumb items={[
        { label: 'Trang chủ', href: '/' },
        { label: 'Thanh toán trực tuyến' },
      ]} />

      <h1 className="text-xl font-bold text-[#1E2F41] mb-6">Thanh toán trực tuyến</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
        <div>
          <SectionTitle>Công dân</SectionTitle>
          {CONG_DAN.map((item) => <ServiceItemCard key={item.id} item={item} />)}
        </div>
        <div>
          <SectionTitle>Doanh nghiệp</SectionTitle>
          {DOANH_NGHIEP.map((item) => <ServiceItemCard key={item.id} item={item} />)}
        </div>
      </div>
    </div>
  )
}
