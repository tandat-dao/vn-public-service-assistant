'use client'
import { ProcedurePageLayout } from '@/components/procedure/ProcedurePageLayout'

const documentsSection = (
  <>
    <p className="text-sm font-semibold text-gray-700 mt-4 mb-2">* Hồ sơ đăng ký tạm trú gồm:</p>
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
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Tờ khai thay đổi thông tin cư trú (Mẫu CT01 ban hành kèm theo Thông tư số 53/2025/TT-BCA); đối với người đăng ký tạm trú là người chưa thành niên thì trong tờ khai phải ghi rõ ý kiến đồng ý của cha, mẹ hoặc người giám hộ, trừ trường hợp đã có ý kiến đồng ý bằng văn bản;</td>
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
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Thông tin chứng minh về chỗ ở hợp pháp được khai thác trong căn cước điện tử, tài khoản định danh điện tử trên hệ thống định danh và xác thực điện tử qua Ứng dụng định danh quốc gia hoặc trong Cơ sở dữ liệu quốc gia về dân cư, Cơ sở dữ liệu về cư trú, Kho quản lý dữ liệu điện tử tổ chức, cá nhân trên Cổng dịch vụ công quốc gia, Hệ thống thông tin giải quyết thủ tục hành chính cấp bộ, cấp tỉnh hoặc cơ sở dữ liệu quốc gia, cơ sở dữ liệu chuyên ngành khác. Trường hợp không khai thác được thông tin thì công dân xuất trình giấy tờ, tài liệu chứng minh chỗ ở hợp pháp theo quy định tại khoản 3 Điều 5 Nghị định 154/2024/NĐ-CP ngày 26/11/2024 của Chính phủ.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Ví dụ: Trường hợp giấy tờ, tài liệu chứng minh chỗ ở hợp pháp là giấy tờ, tài liệu chứng nhận về quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất do cơ quan có thẩm quyền cấp qua các thời kỳ theo quy định của pháp luật về đất đai và nhà ở được khai thác trong Cơ sở dữ liệu quốc gia về đất đai thì không phải xuất trình giấy tờ, tài liệu chứng minh chỗ ở hợp pháp.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
        </tbody>
      </table>
    </div>

    <p className="text-sm font-semibold text-gray-700 mt-4 mb-2">* Đăng ký tạm trú theo danh sách, hồ sơ gồm:</p>
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
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Tờ khai thay đổi thông tin cư trú (của từng người) (Mẫu CT01 ban hành kèm theo Thông tư số 53/2025/TT-BCA).</td>
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
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Văn bản đề nghị đăng ký tạm trú, trong đó ghi rõ thông tin về chỗ ở hợp pháp kèm danh sách người tạm trú. Danh sách bao gồm những thông tin cơ bản của từng người: họ, chữ đệm và tên; ngày, tháng, năm sinh; giới tính; số định danh cá nhân và thời hạn tạm trú.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 1"}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p className="text-sm font-semibold text-gray-700 mt-4 mb-2">Đăng ký tạm trú tại nơi đơn vị đóng quân trong Công an nhân dân, Quân đội nhân nhân (đơn vị đóng quân, nhà ở công vụ) hồ sơ gồm:</p>
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
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Đối với Công an nhân dân: Giấy giới thiệu của Thủ trưởng đơn vị quản lý trực tiếp ghi rõ nội dung để làm thủ tục đăng ký tạm trú và đơn vị có chỗ ở cho cán bộ chiến sĩ (ký tên, đóng dấu).</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Đối với Quân đội nhân dân: Giấy giới thiệu đăng ký tạm trú của đơn vị cấp trung đoàn và tương đương trở lên.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
        </tbody>
      </table>
    </div>

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
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">*Lưu ý: - Trường hợp giấy tờ, tài liệu chứng minh chỗ ở hợp pháp để đăng ký tạm trú là văn bản cho thuê, cho mượn, cho ở nhờ nhà ở, nhà khác của cá nhân, tổ chức thì văn bản đó không bắt buộc phải công chứng hoặc chứng thực. - Người nước ngoài được nhập quốc tịch Việt Nam khi đăng ký tạm trú lần đầu phải có Quyết định của Chủ tịch nước về việc cho nhập quốc tịch Việt Nam. Người gốc Việt Nam được trở lại quốc tịch Việt Nam khi đăng ký tạm trú lần đầu sau khi được cho trở lại quốc tịch Việt Nam phải có Quyết định của Chủ tịch nước về việc cho trở lại quốc tịch Việt Nam trừ trường hợp đã khai thác được thông tin trong Cơ sở dữ liệu quốc tịch. - Công dân đăng ký tạm trú về với hộ gia đình thuộc trường hợp quy định tại khoản 2 Điều 20 Luật Cư trú khi chủ hộ, chủ sở hữu chỗ ở hợp pháp đồng ý và không phải xuất trình, cung cấp giấy tờ chứng minh chỗ ở hợp pháp. - Trong thời hạn tối đa 60 ngày kể từ ngày người chưa thành niên được đăng ký khai sinh thì phải thực hiện thủ tục đăng ký cư trú.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
        </tbody>
      </table>
    </div>
  </>
)

export default function DangKyTamTruPage() {
  return (
    <ProcedurePageLayout
      procedureId="TTHC-002"
      procedureName="Đăng ký tạm trú"
      agency="Công an phường/xã/thị trấn"
      processingDays="3 ngày làm việc"
      fee="Không"
      documentsSection={documentsSection}
      showCccdUpload={true}
      chatContext="Người dùng đang xem thủ tục Đăng ký tạm trú (TTHC-002) tại TP. Hồ Chí Minh. Hãy sẵn sàng trả lời các câu hỏi về hồ sơ, điều kiện, thời hạn tạm trú, và quy trình đăng ký."
    />
  )
}
