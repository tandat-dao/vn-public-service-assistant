'use client'
import { ProcedurePageLayout } from '@/components/procedure/ProcedurePageLayout'

const documentsSection = (
  <>
    <p className="text-sm font-semibold text-gray-700 mt-4 mb-2">Bao gồm</p>
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left py-2 pr-4 text-xs font-semibold text-gray-500 w-1/2">Tên giấy tờ</th>
            <th className="text-left py-2 pr-4 text-xs font-semibold text-gray-500 w-1/4">Mẫu đơn, tờ khai</th>
            <th className="text-left py-2 text-xs font-semibold text-gray-500 w-1/4">Số lượng</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Tờ khai thay đổi thông tin cư trú (Mẫu CT01 ban hành kèm theo Thông tư số 53/2025/TT-BCA).</td>
            <td className="py-2 pr-4">
              <a
                href="/forms/1.MuCT01banhnhkmtheoThngts53.doc"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-[#CE7A58] hover:underline"
              >
                1.MuCT01banhnhkmtheoThngts53.doc
              </a>
            </td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">*Lưu ý: Khi nộp hồ sơ trực tuyến, công dân khai báo thông tin theo biểu mẫu điện tử được cung cấp sẵn, không đính kèm biểu mẫu CT01.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
        </tbody>
      </table>
    </div>
  </>
)

export default function XacNhanCuTruPage() {
  return (
    <ProcedurePageLayout
      procedureId="TTHC-003"
      procedureName="Xác nhận thông tin về cư trú"
      agency="Công an phường/xã/thị trấn"
      processingDays="3 ngày làm việc"
      fee="Không"
      documentsSection={documentsSection}
      showCccdUpload={true}
      chatContext="Người dùng đang xem thủ tục Xác nhận thông tin về cư trú (TTHC-003) tại TP. Hồ Chí Minh. Hãy sẵn sàng trả lời các câu hỏi về mục đích xác nhận, hồ sơ cần chuẩn bị, và quy trình thực hiện."
    />
  )
}
