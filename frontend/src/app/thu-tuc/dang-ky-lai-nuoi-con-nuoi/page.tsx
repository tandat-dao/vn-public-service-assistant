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
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Tờ khai đăng ký lại việc nuôi con nuôi. Tờ khai phải có cam đoan của người yêu cầu đăng ký lại về tính trung thực của việc đăng ký nuôi con nuôi trước đó và có chữ ký của ít nhất hai người làm chứng.</td>
            <td className="py-2 pr-4">
              <a
                href="/forms/7.Tkhaingklivicnuiconnui.doc"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-[#CE7A58] hover:underline"
              >
                7.Tkhaingklivicnuiconnui.doc
              </a>
            </td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Lưu ý: Khi nộp hồ sơ, trường hợp phải chứng minh nơi thường trú của cha mẹ nuôi và con nuôi, cán bộ, công chức, viên chức, cá nhân được giao trách nhiệm tiếp nhận, giải quyết hồ sơ phải khai thác, sử dụng thông tin về cư trú của công dân trong Cơ sở dữ liệu quốc gia về dân cư theo các phương thức nêu tại khoản 2 Điều 14 Nghị định số 104/2022/NĐ-CP ngày 21/12/2022 của Chính phủ. Trường hợp không thể khai thác được thông tin cư trú của công dân theo các phương thức trên thì có thể yêu cầu người nộp hồ sơ nộp bản sao hoặc xuất trình một trong các giấy tờ chứng minh thông tin về cư trú, bao gồm: Thẻ căn cước; Giấy xác nhận thông tin về cư trú, Giấy thông báo số định danh cá nhân và thông tin công dân trong Cơ sở dữ liệu quốc gia về dân cư.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
        </tbody>
      </table>
    </div>
  </>
)

export default function DangKyLaiNuoiConNuoiPage() {
  return (
    <ProcedurePageLayout
      procedureId="TTHC-AD-002"
      procedureName="Đăng ký lại việc nuôi con nuôi trong nước"
      agency="Ủy ban nhân dân cấp xã"
      processingDays="5 ngày làm việc"
      fee="Không"
      documentsSection={documentsSection}
      showCccdUpload={true}
      chatContext="Người dùng đang xem thủ tục Đăng ký lại việc nuôi con nuôi trong nước (TTHC-AD-002) tại TP. Hồ Chí Minh. Thủ tục này yêu cầu đã hoàn thành Đăng ký việc nuôi con nuôi (TTHC-AD-001). Hãy sẵn sàng trả lời câu hỏi về điều kiện, hồ sơ, và quy trình đăng ký lại."
    />
  )
}
