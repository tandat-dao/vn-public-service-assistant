'use client'
import { useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useRouter } from 'next/navigation'
import { Breadcrumb } from '@/components/ui/Breadcrumb'
import { FormInput, FormSelect } from '@/components/forms/FormField'
import { thuongTruSchema, type ThuongTruFormValues } from '@/lib/schemas/residence-forms'
import { useFormStore } from '@/lib/stores/formStore'
import { useChatStore } from '@/lib/stores/chatStore'
import { api } from '@/lib/api/client'

const FORM_TYPE = 'thuong-tru' as const

type OcrStatus = 'idle' | 'loading' | 'success' | 'partial' | 'error'

const GIOI_TINH_OPTIONS = [
  { value: 'Nam', label: 'Nam' },
  { value: 'Nữ', label: 'Nữ' },
]

export default function DangKyThuongTruPage() {
  const router = useRouter()
  const store = useFormStore()
  const { sessionId } = useChatStore()
  const [submitError, setSubmitError] = useState<string | null>(null)

  // OCR upload state
  const [ocrStatus, setOcrStatus] = useState<OcrStatus>('idle')
  const [ocrMessage, setOcrMessage] = useState<string>('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  async function handleOcrUpload(file: File) {
    setOcrStatus('loading')
    setOcrMessage('')
    try {
      const result = await api.documents.upload(file, sessionId)
      if (result.status === 'success' && result.personal_data) {
        const pd = result.personal_data
        const confidence = result.ocr_confidence ?? 0

        // Build formatted date (YYYY-MM-DD → DD/MM/YYYY)
        let formattedDob = ''
        if (pd.date_of_birth) {
          const parts = String(pd.date_of_birth).split('-')
          if (parts.length === 3) formattedDob = `${parts[2]}/${parts[1]}/${parts[0]}`
        }

        // Build address string (old permanent address → noi_thuong_tru_cu)
        let addressStr = ''
        if (pd.raw_address) {
          addressStr = pd.raw_address
        } else if (pd.permanent_address) {
          const a = pd.permanent_address
          addressStr = [a.street, a.ward, a.district, a.province || a.city]
            .filter(Boolean)
            .join(', ')
        }

        const extracted: Record<string, { value: string; confidence: number }> = {}
        if (pd.full_name) extracted.ho_ten = { value: pd.full_name, confidence }
        if (formattedDob) extracted.ngay_sinh = { value: formattedDob, confidence }
        if (pd.gender) extracted.gioi_tinh = { value: pd.gender, confidence }
        if (pd.id_number) extracted.so_cccd = { value: pd.id_number, confidence }
        if (addressStr) extracted.noi_thuong_tru_cu = { value: addressStr, confidence }

        store.applyAIExtraction(FORM_TYPE, extracted)
        setOcrStatus('success')
        setOcrMessage(`Đã trích xuất thông tin. Độ chính xác: ${Math.round(confidence * 100)}%`)
      } else if (result.status === 'partial') {
        setOcrStatus('partial')
        setOcrMessage('⚠️ Không đọc được thông tin từ ảnh. Vui lòng chụp ảnh rõ hơn (đủ sáng, không mờ, thẻ căn cước nằm thẳng) và thử lại.')
      } else {
        setOcrStatus('error')
        setOcrMessage('❌ Lỗi máy chủ khi xử lý ảnh. Vui lòng thử lại.')
      }
    } catch (err: any) {
      const status = err?.status
      setOcrStatus('error')
      if (status === 422) {
        setOcrMessage('❌ Tệp không hợp lệ. Chỉ chấp nhận ảnh JPG, PNG, WebP dưới 5MB.')
      } else if (status === 500) {
        setOcrMessage('❌ Lỗi máy chủ khi xử lý ảnh. Vui lòng thử lại.')
      } else {
        setOcrMessage('❌ Không thể kết nối đến máy chủ. Kiểm tra kết nối mạng.')
      }
    }
  }

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ThuongTruFormValues>({
    resolver: zodResolver(thuongTruSchema),
    defaultValues: store.getFormValues(FORM_TYPE) as ThuongTruFormValues,
  })

  // Re-sync when AI fills the store (Phase 2 hook point)
  const storeFields = store.fields[FORM_TYPE]
  useEffect(() => {
    const vals = store.getFormValues(FORM_TYPE)
    if (Object.keys(vals).length > 0) reset(vals as ThuongTruFormValues)
  }, [storeFields]) // eslint-disable-line react-hooks/exhaustive-deps

  async function onSubmit(data: ThuongTruFormValues) {
    store.setSubmitting(FORM_TYPE, true)
    setSubmitError(null)
    try {
      for (const [key, value] of Object.entries(data)) {
        store.setFieldValue(FORM_TYPE, key as keyof ThuongTruFormValues, value ?? '', 'manual', 1.0)
      }
      const result = await api.forms.submit({
        form_type: FORM_TYPE,
        session_id: sessionId,
        submission_mode: 'manual',
        form_data: data as Record<string, string | undefined>,
      })
      store.setSubmissionResult(FORM_TYPE, {
        ...result,
        form_type: FORM_TYPE,
        status: result.status as 'received' | 'processing' | 'completed',
      })
      router.push(`/tra-cuu-ho-so?ma=${encodeURIComponent(result.ma_ho_so)}`)
    } catch (err: any) {
      const status = err?.status
      if (status === 422) {
        setSubmitError('Vui lòng kiểm tra lại thông tin đã nhập.')
      } else if (status === 500) {
        setSubmitError('Lỗi hệ thống khi nộp hồ sơ. Vui lòng thử lại sau.')
      } else {
        setSubmitError('Không thể kết nối. Kiểm tra kết nối mạng.')
      }
    } finally {
      store.setSubmitting(FORM_TYPE, false)
    }
  }

  const ai = (key: string) => storeFields?.[key]?.aiHighlight ?? false

  return (
    <main className="max-w-container mx-auto px-4 py-6">
      <Breadcrumb
        items={[
          { label: 'Trang chủ', href: '/' },
          { label: 'Thủ tục hành chính' },
          { label: 'Đăng ký thường trú' },
        ]}
      />

      <h1 className="text-xl font-bold text-[#1E2F41] mt-4 mb-1">
        Đăng ký thường trú
      </h1>
      <p className="text-sm text-[#555] mb-4">
        Thủ tục đăng ký thường trú cho công dân. Vui lòng điền đầy đủ thông tin theo mẫu dưới đây.
      </p>

      {/* ── OCR Upload Card ── */}
      <div className="border-2 border-dashed border-[#DDDDDD] rounded p-4 mb-6 bg-[#FAFAFA]">
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="flex-1 text-sm text-[#555]">
            {ocrStatus === 'idle' && 'Tải lên ảnh CCCD để điền thông tin tự động'}
            {ocrStatus === 'loading' && (
              <span className="text-[#1E2F41]">Đang đọc thông tin CCCD...</span>
            )}
            {ocrStatus === 'success' && (
              <span className="text-[#28A745]">{ocrMessage}</span>
            )}
            {ocrStatus === 'partial' && (
              <span className="text-[#D97706]">{ocrMessage}</span>
            )}
            {ocrStatus === 'error' && (
              <span className="text-[#CC0000]">{ocrMessage}</span>
            )}
          </div>
          <div className="flex-shrink-0">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) handleOcrUpload(file)
                e.target.value = ''
              }}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={ocrStatus === 'loading'}
              className="bg-[#1E2F41] text-white hover:bg-[#2a3f57] font-medium px-4 py-2 rounded text-sm transition-colors disabled:opacity-50 whitespace-nowrap"
            >
              {ocrStatus === 'loading' ? 'Đang đọc thông tin CCCD...' : 'Tải lên CCCD để điền tự động'}
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* ── Form ── */}
        <form
          onSubmit={handleSubmit(onSubmit)}
          noValidate
          className="md:col-span-2 space-y-6"
        >
          {/* Personal info */}
          <section>
            <h2 className="text-sm font-bold text-[#CE7A58] uppercase tracking-wide mb-3">
              Thông tin cá nhân
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormInput
                {...register('ho_ten')}
                id="ho_ten"
                label="Họ và tên"
                required
                placeholder="Nguyễn Văn A"
                error={errors.ho_ten?.message}
                aiHighlight={ai('ho_ten')}
                className="sm:col-span-2"
              />
              <FormInput
                {...register('ngay_sinh')}
                id="ngay_sinh"
                label="Ngày sinh"
                required
                placeholder="DD/MM/YYYY"
                error={errors.ngay_sinh?.message}
                aiHighlight={ai('ngay_sinh')}
              />
              <FormSelect
                {...register('gioi_tinh')}
                id="gioi_tinh"
                label="Giới tính"
                required
                options={GIOI_TINH_OPTIONS}
                error={errors.gioi_tinh?.message}
                aiHighlight={ai('gioi_tinh')}
              />
              <FormInput
                {...register('so_cccd')}
                id="so_cccd"
                label="Số CCCD/CMND"
                required
                placeholder="9 hoặc 12 chữ số"
                hint="Chấp nhận CCCD 12 số hoặc CMND 9 số"
                error={errors.so_cccd?.message}
                aiHighlight={ai('so_cccd')}
                className="sm:col-span-2"
              />
            </div>
          </section>

          {/* Registration info */}
          <section>
            <h2 className="text-sm font-bold text-[#CE7A58] uppercase tracking-wide mb-3">
              Thông tin đăng ký
            </h2>
            <div className="grid grid-cols-1 gap-4">
              <FormInput
                {...register('noi_thuong_tru_cu')}
                id="noi_thuong_tru_cu"
                label="Nơi thường trú cũ"
                placeholder="Địa chỉ thường trú hiện tại (nếu có)"
                error={errors.noi_thuong_tru_cu?.message}
                aiHighlight={ai('noi_thuong_tru_cu')}
              />
              <FormInput
                {...register('dia_chi_thuong_tru_moi')}
                id="dia_chi_thuong_tru_moi"
                label="Địa chỉ thường trú mới"
                required
                placeholder="Số nhà, đường, phường/xã, quận/huyện, tỉnh/thành phố"
                error={errors.dia_chi_thuong_tru_moi?.message}
                aiHighlight={ai('dia_chi_thuong_tru_moi')}
              />
            </div>
          </section>

          {/* Household head info (optional) */}
          <section>
            <h2 className="text-sm font-bold text-[#CE7A58] uppercase tracking-wide mb-3">
              Thông tin chủ hộ <span className="text-[#999] font-normal normal-case">(nếu đăng ký vào hộ khẩu người khác)</span>
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormInput
                {...register('quan_he_chu_ho')}
                id="quan_he_chu_ho"
                label="Quan hệ với chủ hộ"
                placeholder="Vd: Con, Vợ/chồng, Anh/chị..."
                error={errors.quan_he_chu_ho?.message}
                aiHighlight={ai('quan_he_chu_ho')}
              />
              <FormInput
                {...register('ten_chu_ho')}
                id="ten_chu_ho"
                label="Họ tên chủ hộ"
                placeholder="Họ và tên đầy đủ"
                error={errors.ten_chu_ho?.message}
                aiHighlight={ai('ten_chu_ho')}
              />
              <FormInput
                {...register('cccd_chu_ho')}
                id="cccd_chu_ho"
                label="Số CCCD/CMND chủ hộ"
                placeholder="9 hoặc 12 chữ số"
                error={errors.cccd_chu_ho?.message}
                aiHighlight={ai('cccd_chu_ho')}
              />
            </div>
          </section>

          {submitError && (
            <p className="text-sm text-[#CC0000] border border-[#CC0000] rounded px-3 py-2">
              {submitError}
            </p>
          )}

          <button
            type="submit"
            disabled={store.isSubmitting[FORM_TYPE]}
            className="bg-[#CE7A58] text-[#1E2F41] hover:bg-[#B8694A] font-semibold px-8 py-2 rounded text-sm transition-colors disabled:opacity-50"
          >
            {store.isSubmitting[FORM_TYPE] ? 'Đang nộp...' : 'Nộp hồ sơ'}
          </button>
        </form>

        {/* ── Sidebar ── */}
        <aside className="space-y-4">
          <div className="border border-[#DDDDDD] rounded p-4 text-sm space-y-2">
            <p className="font-bold text-[#1E2F41] mb-2">Thông tin thủ tục</p>
            <div className="flex justify-between">
              <span className="text-[#555]">Thời gian xử lý</span>
              <span className="font-semibold">5 ngày làm việc</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#555]">Lệ phí</span>
              <span className="font-semibold text-[#28A745]">Miễn phí</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[#555]">Cơ quan thực hiện</span>
              <span className="font-semibold text-right">UBND Phường/Xã</span>
            </div>
          </div>

          <div className="border border-[#DDDDDD] rounded p-4 text-sm">
            <p className="font-bold text-[#1E2F41] mb-2">Hồ sơ cần nộp</p>
            <ul className="space-y-1 text-[#555] list-disc list-inside">
              <li>Tờ khai thay đổi thông tin cư trú (mẫu CT01)</li>
              <li>CCCD/CMND còn hiệu lực</li>
              <li>Giấy tờ chứng minh chỗ ở hợp pháp</li>
              <li>Sổ hộ khẩu (nếu còn)</li>
            </ul>
          </div>

          <div className="border border-[#DDDDDD] rounded p-4 text-sm text-[#555]">
            <p className="font-bold text-[#1E2F41] mb-1">Lưu ý</p>
            <p>Sau khi nộp hồ sơ trực tuyến, bạn cần mang bản gốc các giấy tờ đến UBND để xác nhận.</p>
          </div>
        </aside>
      </div>
    </main>
  )
}
