'use client'
import { useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { TabBar } from '@/components/ui/TabBar'
import { Breadcrumb } from '@/components/ui/Breadcrumb'
import { Button } from '@/components/ui/Button'

const TABS = [
  { id: 'ma-ho-so',    label: 'Tra cứu theo mã hồ sơ' },
  { id: 'co-quan',     label: 'Tra cứu theo cơ quan thực hiện' },
  { id: 'khuyen-mai',  label: 'Tra cứu thông báo khuyến mại' },
]

// Simple deterministic CAPTCHA-like display
const CAPTCHA_CHARS = 'AB2K7MX9'

export default function TraCuuHoSoPage() {
  const [activeTab, setActiveTab] = useState('ma-ho-so')
  const [maHoSo, setMaHoSo] = useState('')
  const [captcha, setCaptcha] = useState('')
  const [captchaKey, setCaptchaKey] = useState(0)

  function refreshCaptcha() { setCaptchaKey((k) => k + 1) }

  return (
    <div className="max-w-container mx-auto px-4 py-4">
      <Breadcrumb items={[
        { label: 'Trang chủ', href: '/' },
        { label: 'Tra cứu hồ sơ' },
      ]} />

      <h1 className="text-xl font-bold text-[#1E2F41] mb-4">Tra cứu hồ sơ</h1>
      <TabBar tabs={TABS} activeTab={activeTab} onChange={setActiveTab} className="mb-6" />

      {activeTab === 'ma-ho-so' && (
        <div className="relative max-w-2xl">
          {/* Crane watermark */}
          <div className="absolute top-0 right-0 text-[120px] leading-none opacity-5 select-none pointer-events-none">
            🦢
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4 relative z-10">
            <div className="sm:col-span-2">
              <label className="block text-sm font-semibold text-[#1E2F41] mb-1">
                Mã hồ sơ <span className="text-[#CC0000]">*</span>
              </label>
              <input
                value={maHoSo}
                onChange={(e) => setMaHoSo(e.target.value)}
                placeholder="Nhập mã hồ sơ"
                className="w-full border border-[#DDDDDD] px-3 py-2 text-sm rounded
                           focus:outline-none focus:border-[#CE7A58]"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-[#1E2F41] mb-1">
                Mã bảo mật <span className="text-[#CC0000]">*</span>
              </label>
              <div className="flex gap-2">
                <input
                  value={captcha}
                  onChange={(e) => setCaptcha(e.target.value)}
                  placeholder="Nhập mã"
                  className="flex-1 border border-[#DDDDDD] px-3 py-2 text-sm rounded
                             focus:outline-none focus:border-[#CE7A58] w-24"
                  maxLength={8}
                />
                {/* Captcha display */}
                <div
                  key={captchaKey}
                  className="flex items-center justify-center px-3 py-2 bg-[#F5F5F5]
                             border border-[#DDDDDD] rounded min-w-[80px] select-none
                             font-mono text-sm font-bold tracking-widest relative overflow-hidden"
                >
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full h-px bg-[#999] opacity-50" />
                  </div>
                  <span className="relative z-10 text-[#1E2F41]">{CAPTCHA_CHARS}</span>
                </div>
                <button onClick={refreshCaptcha}
                        className="text-[#CE7A58] hover:text-[#B8694A] transition-colors p-2"
                        title="Làm mới mã">
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          <Button variant="primary" className="px-8">
            Tra cứu
          </Button>
        </div>
      )}

      {activeTab !== 'ma-ho-so' && (
        <div className="py-12 text-center text-[#999] text-sm">
          Chức năng đang được phát triển.
        </div>
      )}
    </div>
  )
}
