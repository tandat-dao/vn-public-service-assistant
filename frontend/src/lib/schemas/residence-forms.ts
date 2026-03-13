import { z } from 'zod'

// ── Shared validators ─────────────────────────────────────────────────────────

const dateVN = z
  .string()
  .min(1, 'Ngày là bắt buộc')
  .regex(/^\d{2}\/\d{2}\/\d{4}$/, 'Định dạng ngày phải là DD/MM/YYYY')
  .refine((val) => {
    const [d, m, y] = val.split('/').map(Number)
    const date = new Date(y, m - 1, d)
    return (
      date.getFullYear() === y &&
      date.getMonth() === m - 1 &&
      date.getDate() === d
    )
  }, 'Ngày không hợp lệ')

const cccd = z
  .string()
  .min(1, 'Số CCCD/CMND là bắt buộc')
  .regex(/^\d{9}$|^\d{12}$/, 'Số CCCD/CMND phải có 9 hoặc 12 chữ số')

const cccdOptional = z
  .string()
  .optional()
  .refine(
    (val) => !val || /^\d{9}$|^\d{12}$/.test(val),
    'Số CCCD/CMND phải có 9 hoặc 12 chữ số'
  )

// ── Đăng ký thường trú ────────────────────────────────────────────────────────

export const thuongTruSchema = z.object({
  ho_ten:                 z.string().min(1, 'Họ và tên là bắt buộc'),
  ngay_sinh:              dateVN,
  gioi_tinh:              z.enum(['Nam', 'Nữ'], {
    errorMap: () => ({ message: 'Giới tính là bắt buộc' }),
  }),
  so_cccd:                cccd,
  noi_thuong_tru_cu:      z.string().optional(),
  dia_chi_thuong_tru_moi: z.string().min(1, 'Địa chỉ thường trú mới là bắt buộc'),
  quan_he_chu_ho:         z.string().optional(),
  ten_chu_ho:             z.string().optional(),
  cccd_chu_ho:            cccdOptional,
})

export type ThuongTruFormValues = z.infer<typeof thuongTruSchema>

// ── Đăng ký tạm trú ───────────────────────────────────────────────────────────

export const tamTruSchema = z
  .object({
    ho_ten:             z.string().min(1, 'Họ và tên là bắt buộc'),
    ngay_sinh:          dateVN,
    gioi_tinh:          z.enum(['Nam', 'Nữ'], {
      errorMap: () => ({ message: 'Giới tính là bắt buộc' }),
    }),
    so_cccd:            cccd,
    dia_chi_thuong_tru: z.string().min(1, 'Địa chỉ thường trú là bắt buộc'),
    dia_chi_tam_tru:    z.string().min(1, 'Địa chỉ tạm trú là bắt buộc'),
    tu_ngay:            dateVN,
    den_ngay:           dateVN,
    muc_dich:           z.string().optional(),
  })
  .refine(
    (data) => {
      const parse = (s: string) => {
        const [d, m, y] = s.split('/').map(Number)
        return new Date(y, m - 1, d).getTime()
      }
      return parse(data.den_ngay) > parse(data.tu_ngay)
    },
    { message: 'Đến ngày phải sau Từ ngày', path: ['den_ngay'] }
  )

export type TamTruFormValues = z.infer<typeof tamTruSchema>

// ── Xác nhận thông tin cư trú ─────────────────────────────────────────────────

export const xacNhanSchema = z.object({
  ho_ten:               z.string().min(1, 'Họ và tên là bắt buộc'),
  ngay_sinh:            dateVN,
  gioi_tinh:            z.enum(['Nam', 'Nữ'], {
    errorMap: () => ({ message: 'Giới tính là bắt buộc' }),
  }),
  so_cccd:              cccd,
  dia_chi_can_xac_nhan: z.string().min(1, 'Địa chỉ cần xác nhận là bắt buộc'),
  loai_xac_nhan:        z.enum(['Thường trú', 'Tạm trú'], {
    errorMap: () => ({ message: 'Loại xác nhận là bắt buộc' }),
  }),
  muc_dich_xac_nhan:    z.string().min(1, 'Mục đích xác nhận là bắt buộc'),
})

export type XacNhanFormValues = z.infer<typeof xacNhanSchema>
