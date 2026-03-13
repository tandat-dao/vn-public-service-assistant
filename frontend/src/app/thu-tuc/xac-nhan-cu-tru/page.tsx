'use client'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useRouter } from 'next/navigation'
import { Breadcrumb } from '@/components/ui/Breadcrumb'
import { FormInput, FormSelect, FormTextarea } from '@/components/forms/FormField'
import { xacNhanSchema, type XacNhanFormValues } from '@/lib/schemas/residence-forms'
import { useFormStore } from '@/lib/stores/formStore'
import { useChatStore } from '@/lib/stores/chatStore'
import { api } from '@/lib/api/client'

const FORM_TYPE = 'xac-nhan' as const

const GIOI_TINH_OPTIONS = [
  { value: 'Nam', label: 'Nam' },
  { value: 'Nữ', label: 'Nữ' },
]

const LOAI_XAC_NHAN_OPTIONS = [
  { value: 'Thường trú', label: 'Thường trú' },
  { value: 'Tạm trú', label: 'Tạm trú' },
]

export default function XacNhanCuTruPage() {
  const router = useRouter()
  const store = useFormStore()
  const { sessionId } = useChatStore()
  const [submitError, setSubmitError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<XacNhanFormValues>({
    resolver: zodResolver(xacNhanSchema),
    defaultValues: store.getFormValues(FORM_TYPE) as XacNhanFormValues,
  })

  const storeFields = store.fields[FORM_TYPE]
  useEffect(() => {
    const vals = store.getFormValues(FORM_TYPE)
    if (Object.keys(vals).length > 0) reset(vals as XacNhanFormValues)
  }, [storeFields]) // eslint-disable-line react-hooks/exhaustive-deps

  async function onSubmit(data: XacNhanFormValues) {
    store.setSubmitting(FORM_TYPE, true)
    setSubmitError(null)
    try {
      for (const [key, value] of Object.entries(data)) {
        store.setFieldValue(FORM_TYPE, key as keyof XacNhanFormValues, value ?? '', 'manual', 1.0)
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
    } catch {
      setSubmitError('Đã xảy ra lỗi khi nộp hồ sơ. Vui lòng thử lại.')
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
          { label: 'Xác nhận thông tin về cư trú' },
        ]}
      />

      <h1 className="text-xl font-bold text-[#1E2F41] mt-4 mb-1">
        Xác nhận thông tin về cư trú
      </h1>
      <p className="text-sm text-[#555] mb-6">
        Thủ tục xác nhận tình trạng cư trú (thường trú hoặc tạm trú) phục vụ các mục đích hành chính.
      </p>

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

          {/* Confirmation info */}
          <section>
            <h2 className="text-sm font-bold text-[#CE7A58] uppercase tracking-wide mb-3">
              Thông tin xác nhận
            </h2>
            <div className="grid grid-cols-1 gap-4">
              <FormInput
                {...register('dia_chi_can_xac_nhan')}
                id="dia_chi_can_xac_nhan"
                label="Địa chỉ cần xác nhận"
                required
                placeholder="Địa chỉ cần được xác nhận tình trạng cư trú"
                error={errors.dia_chi_can_xac_nhan?.message}
                aiHighlight={ai('dia_chi_can_xac_nhan')}
              />
              <FormSelect
                {...register('loai_xac_nhan')}
                id="loai_xac_nhan"
                label="Loại xác nhận"
                required
                options={LOAI_XAC_NHAN_OPTIONS}
                error={errors.loai_xac_nhan?.message}
                aiHighlight={ai('loai_xac_nhan')}
              />
              <FormTextarea
                {...register('muc_dich_xac_nhan')}
                id="muc_dich_xac_nhan"
                label="Mục đích xác nhận"
                required
                placeholder="Vd: Làm hồ sơ vay vốn, xin học bổng, thủ tục hành chính..."
                error={errors.muc_dich_xac_nhan?.message}
                aiHighlight={ai('muc_dich_xac_nhan')}
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
              <span className="font-semibold">1–2 ngày làm việc</span>
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
              <li>Đơn đề nghị xác nhận thông tin cư trú</li>
              <li>CCCD/CMND còn hiệu lực</li>
              <li>Giấy tờ liên quan đến mục đích xác nhận (nếu có)</li>
            </ul>
          </div>

          <div className="border border-[#DDDDDD] rounded p-4 text-sm text-[#555]">
            <p className="font-bold text-[#1E2F41] mb-1">Lưu ý</p>
            <p>Giấy xác nhận cư trú có giá trị trong vòng 6 tháng kể từ ngày cấp.</p>
          </div>
        </aside>
      </div>
    </main>
  )
}
