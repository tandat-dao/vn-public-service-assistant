'use client'
import { ProcedurePageLayout } from '@/components/procedure/ProcedurePageLayout'

const documentsSection = (
  <>
    <p className="text-sm font-semibold text-gray-700 mt-4 mb-2">Người sinh sống, người làm nghề lưu động trên phương tiện được đăng ký thường trú tại phương tiện</p>
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
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Giấy chứng nhận đăng ký phương tiện và giấy chứng nhận an toàn kỹ thuật và bảo vệ môi trường của phương tiện hoặc văn bản xác nhận của Ủy ban nhân dân cấp xã về việc sử dụng phương tiện đó vào mục đích để ở đối với phương tiện không thuộc đối tượng phải đăng ký, đăng kiểm (nội dung xác nhận tại mục 2 của Ủy ban nhân dân cấp xã tại Tờ khai đề nghị xác nhận nơi thường xuyên đậu, đỗ; sử dụng phương tiện vào mục đích để ở theo Mẫu số 01 ban hành kèm theo Nghị định số 154/2024/NĐ-CP).</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Văn bản xác nhận của Ủy ban nhân dân cấp xã về địa điểm phương tiện đăng ký đậu, đỗ thường xuyên trong trường hợp phương tiện không phải đăng ký hoặc nơi đăng ký phương tiện không trùng với nơi thường xuyên đậu, đỗ (nội dung xác nhận tại mục 1 của Ủy ban nhân dân cấp xã tại Tờ khai đề nghị xác nhận nơi thường xuyên đậu, đỗ; sử dụng phương tiện vào mục đích để ở theo Mẫu số 01 ban hành kèm theo Nghị định số 154/2024/NĐ-CP).</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p className="text-sm font-semibold text-gray-700 mt-4 mb-2">Người được chăm sóc, nuôi dưỡng, trợ giúp được đăng ký thường trú tại cơ sở trợ giúp xã hội hoặc được đăng ký thường trú vào hộ gia đình nhận chăm sóc, nuôi dưỡng, trợ giúp</p>
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
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Văn bản đề nghị của người đứng đầu cơ sở trợ giúp xã hội đối với người được cơ sở trợ giúp xã hội nhận chăm sóc, nuôi dưỡng, trợ giúp.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Giấy tờ, tài liệu xác nhận về việc chăm sóc, nuôi dưỡng, trợ giúp.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p className="text-sm font-semibold text-gray-700 mt-4 mb-2">Đăng ký thường trú tại chỗ ở hợp pháp không thuộc quyền sở hữu của mình đối với những trường hợp quy định tại khoản 2 Điều 20 Luật Cư trú</p>
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
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Thông tin chứng minh quan hệ nhân thân với chủ hộ, thành viên hộ gia đình được khai thác trong căn cước điện tử, tài khoản định danh điện tử trên hệ thống định danh và xác thực điện tử qua Ứng dụng định danh quốc gia hoặc trong Cơ sở dữ liệu quốc gia về dân cư, Cơ sở dữ liệu về cư trú, Kho quản lý dữ liệu điện tử tổ chức, cá nhân trên Cổng dịch vụ công quốc gia, Hệ thống thông tin giải quyết thủ tục hành chính cấp bộ, cấp tỉnh hoặc cơ sở dữ liệu quốc gia, cơ sở dữ liệu chuyên ngành khác. Trường hợp không khai thác được thông tin thì công dân xuất trình giấy tờ, tài liệu chứng minh quan hệ nhân thân với chủ hộ, thành viên hộ gia đình theo quy định tại khoản 2, khoản 3 Điều 6 Nghị định 154/2024/NĐ-CP ngày 26/11/2024 của Chính phủ. Ví dụ: Trường hợp giấy tờ, tài liệu chứng minh quan hệ nhân thân với chủ hộ, thành viên hộ gia đình là giấy chứng nhận kết hôn, giấy xác nhận tình trạng hôn nhân, giấy khai sinh được khai thác trong Cơ sở dữ liệu hộ tịch điện tử thì không phải xuất trình giấy tờ, tài liệu chứng minh quan hệ nhân thân.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p className="text-sm font-semibold text-gray-700 mt-4 mb-2">Đăng ký thường trú tại cơ sở tín ngưỡng, cơ sở tôn giáo có công trình phụ trợ là nhà ở</p>
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
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Trường hợp quy định tại điểm a, b, c khoản 4 Điều 20 Luật Cư trú đăng ký thường trú tại cơ sở tín ngưỡng, cơ sở tôn giáo có công trình phụ trợ giúp là nhà ở, hồ sơ gồm:</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Giấy tờ, tài liệu chứng minh là nhà tu hành, chức sắc, chức việc hoặc người khác hoạt động tôn giáo và được hoạt động tại cơ sở tôn giáo đó theo quy định của pháp luật về tín ngưỡng, tôn giáo đối với người quy định tại điểm a khoản 4 Điều 20 Luật Cư trú; giấy tờ, tài liệu chứng minh là người đại diện cơ sở tín ngưỡng đối với người quy định tại điểm b khoản 4 Điều 20 Luật Cư trú.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Văn bản xác nhận của Ủy ban nhân dân cấp xã về việc trong cơ sở tín ngưỡng, cơ sở tôn giáo có công trình phụ trợ là nhà ở.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Trường hợp quy định tại điểm d khoản 4 Điều 20 Luật Cư trú đăng ký thường trú tại cơ sở tín ngưỡng, cơ sở tôn giáo có công trình phụ trợ giúp là nhà ở, hồ sơ gồm:</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Văn bản xác nhận của Ủy ban nhân dân cấp xã về việc người đăng ký thường trú thuộc đối tượng quy định tại khoản 2 Điều 17 Luật Cư trú và việc trong cơ sở tín ngưỡng, cơ sở tôn giáo có công trình phụ trợ là nhà ở.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p className="text-sm font-semibold text-gray-700 mt-4 mb-2">Đăng ký thường trú tại nơi đơn vị đóng quân trong Công an nhân dân, Quân đội nhân nhân nhân (đơn vị đóng quân, nhà ở công vụ)</p>
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
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Tờ khai thay đổi thông tin cư trú (mẫu CT01 ban hành kèm theo Thông tư số 53/2025/TT-BCA).</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Đối với Công an nhân dân: Giấy giới thiệu của Thủ trưởng đơn vị quản lý trực tiếp ghi rõ nội dung để làm thủ tục đăng ký thường trú và đơn vị có chỗ ở cho cán bộ chiến sĩ (ký tên, đóng dấu).</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Đối với Quân đội nhân dân: Giấy giới thiệu đăng ký thường trú của cơ quan, đơn vị cấp trung đoàn và tương đương trở lên (ký tên, đóng dấu).</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p className="text-sm font-semibold text-gray-700 mt-4 mb-2">Đăng ký thường trú vào chỗ ở hợp pháp do thuê, mượn, ở nhờ</p>
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
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Hợp đồng, văn bản về việc cho thuê, cho mượn, cho ở nhờ được công chứng hoặc chứng thực theo quy định của pháp luật.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Thông tin chứng minh đủ diện tích nhà ở để đăng ký thường trú tại chỗ ở hợp pháp do thuê, mượn, ở nhờ được khai thác trong căn cước điện tử, tài khoản định danh điện tử trên hệ thống định danh và xác thực điện tử qua Ứng dụng định danh quốc gia hoặc trong Cơ sở dữ liệu quốc gia về dân cư, Cơ sở dữ liệu về cư trú, Kho quản lý dữ liệu điện tử tổ chức, cá nhân trên Cổng dịch vụ công quốc gia, Hệ thống thông tin giải quyết thủ tục hành chính cấp bộ, cấp tỉnh hoặc cơ sở dữ liệu quốc gia, cơ sở dữ liệu chuyên ngành khác. Trường hợp không khai thác được thông tin thì công dân xuất trình giấy tờ, tài liệu quy định tại khoản 2 Điều 5 Nghị định số 154/2024/NĐ-CP, trong đó có thể hiện diện tích nhà ở hoặc xác nhận của Ủy ban nhân dân cấp xã về điều kiện diện tích bình quân bảo đảm theo quy định của Hội đồng nhân dân tỉnh, thành phố trực thuộc trung ương theo Mẫu số 02 ban hành kèm theo Nghị định số 154/2024/NĐ-CP. Ví dụ: Trường hợp giấy tờ, tài liệu chứng minh đủ diện tích nhà ở để đăng ký thường trú theo quy định là giấy tờ, tài liệu chứng nhận về quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất do cơ quan có thẩm quyền cấp qua các thời kỳ theo quy định của pháp luật về đất đai và nhà ở được khai thác trong Cơ sở dữ liệu quốc gia về đất đai thì không phải xuất trình giấy tờ, tài liệu chứng minh đủ diện tích nhà ở.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p className="text-sm font-semibold text-gray-700 mt-4 mb-2">Đăng ký thường trú vào chỗ ở hợp pháp thuộc quyền sở hữu của mình</p>
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
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Tờ khai thay đổi thông tin cư trú (mẫu CT01 ban hành kèm theo Thông tư số 53/2025/TT-BCA) hoặc Tờ khai thay đổi thông tin về cư trú dùng cho công dân Việt Nam định cư ở nước ngoài không có hộ chiếu Việt Nam còn giá trị sử dụng (mẫu CT02 ban hành kèm theo Thông tư số 53/2025/TT-BCA).</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Thông tin chứng minh về chỗ ở hợp pháp được khai thác trong căn cước điện tử, tài khoản định danh điện tử trên hệ thống định danh và xác thực điện tử qua Ứng dụng định danh quốc gia hoặc trong Cơ sở dữ liệu quốc gia về dân cư, Cơ sở dữ liệu về cư trú, Kho quản lý dữ liệu điện tử tổ chức, cá nhân trên Cổng dịch vụ công quốc gia, Hệ thống thông tin giải quyết thủ tục hành chính cấp bộ, cấp tỉnh hoặc cơ sở dữ liệu quốc gia, cơ sở dữ liệu chuyên ngành khác. Trường hợp không khai thác được thông tin thì công dân xuất trình giấy tờ, tài liệu chứng minh chỗ ở hợp pháp theo quy định tại khoản 2 Điều 5 Nghị định 154/2024/NĐ-CP ngày 26/11/2024 của Chính phủ. Ví dụ: Trường hợp giấy tờ, tài liệu chứng minh chỗ ở hợp pháp là giấy tờ, tài liệu chứng nhận về quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất do cơ quan có thẩm quyền cấp qua các thời kỳ theo quy định của pháp luật về đất đai và nhà ở được khai thác trong Cơ sở dữ liệu quốc gia về đất đai thì không phải xuất trình giấy tờ, tài liệu chứng minh chỗ ở hợp pháp.</td>
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
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">*Lưu ý: - Không yêu cầu xuất trình Giấy khai sinh đối với trường hợp trẻ em mới sinh đăng ký thường trú lần đầu. - Trong thời hạn tối đa 60 ngày kể từ ngày người chưa thành niên được đăng ký khai sinh thì phải thực hiện thủ tục đăng ký cư trú. - Trường hợp người cao tuổi, người chưa thành niên đã có thông tin về ngày, tháng, năm sinh trong Cơ sở dữ liệu quốc gia về dân cư thì không yêu cầu xuất trình giấy tờ chứng minh. - Trường hợp công dân đăng ký thường trú vào chỗ ở hợp pháp thuộc quyền sở hữu của mình mà chỗ ở hợp pháp đó có nhiều hơn một chủ sở hữu thì không cần có ý kiến đồng ý của những người đồng sở hữu. - Trường hợp đăng ký thường trú theo quy định tại điểm a khoản 2 Điều 20 Luật Cư trú mà chỗ ở hợp pháp có nhiều hơn một chủ sở hữu thì chỉ cần ý kiến đồng ý của ít nhất một chủ sở hữu. - Trường hợp đăng ký thường trú vào chỗ ở hợp pháp của chủ sở hữu là người bị mất năng lực hành vi dân sự, người có khó khăn trong nhận thức, làm chủ hành vi theo quy định của Bộ luật Dân sự, người dưới 18 tuổi, người bị tuyên bố mất tích, người đã chết thì chỉ cần lấy ý kiến đồng ý của một trong những người đại diện hợp pháp, người thừa kế của chủ sở hữu theo quy định của pháp luật. - Người có mối quan hệ với chủ sở hữu chỗ ở hợp pháp theo quy định tại điểm a khoản 2 Điều 20 Luật Cư trú mà đăng ký thường trú vào chỗ ở chưa có hộ gia đình đăng ký thường trú và không thuộc trường hợp quy định tại Điều 23 Luật Cư trú hoặc người đăng ký thường trú có mối quan hệ với chủ hộ, thành viên hộ gia đình theo quy định tại điểm a khoản 2 Điều 20 Luật Cư trú mà nơi thường trú của chủ hộ, thành viên hộ gia đình đó là chỗ ở hợp pháp do thuê, mượn, ở nhờ thì hồ sơ đăng ký thường trú thực hiện theo khoản 2 Điều 21 Luật Cư trú. - Người đăng ký thường trú theo điều kiện quy định tại điểm a khoản 2 Điều 20 Luật Cư trú mà chỗ ở đăng ký thường trú là địa điểm quy định tại Điều 23 Luật Cư trú thì hồ sơ đăng ký thường trú không cần phải có ý kiến đồng ý của chủ sở hữu chỗ ở hợp pháp đó trong trường hợp không xác định được chủ sở hữu. - Trường hợp người đăng ký thường trú là người Việt Nam định cư ở nước ngoài còn quốc tịch Việt Nam thì trong hồ sơ đăng ký thường trú phải có hộ chiếu Việt Nam còn giá trị sử dụng; trường hợp không có hộ chiếu Việt Nam còn giá trị sử dụng thì phải có giấy tờ, tài liệu chứng minh có quốc tịch Việt Nam theo quy định của pháp luật Việt Nam về quốc tịch và văn bản đồng ý cho giải quyết thường trú của cơ quan quản lý xuất nhập cảnh của Bộ Công an. - Trường hợp người nước ngoài được nhập quốc tịch Việt Nam khi đăng ký thường trú lần đầu phải có Quyết định của Chủ tịch nước về việc cho nhập quốc tịch Việt Nam. Người gốc Việt Nam được trở lại quốc tịch Việt Nam khi đăng ký thường trú lần đầu sau khi được cho trở lại quốc tịch Việt Nam phải có Quyết định của Chủ tịch nước về việc cho trở lại quốc tịch Việt Nam trừ trường hợp đã khai thác được thông tin trong Cơ sở dữ liệu quốc tịch. - Sĩ quan nghiệp vụ, hạ sĩ quan nghiệp vụ, sĩ quan chuyên môn kỹ thuật, hạ sĩ quan chuyên môn kĩ thuật, công nhân công an đã đăng ký thường trú tại đơn vị đóng quân mà chuyển đến chỗ ở hợp pháp mới ngoài đơn vị đóng quân và đủ điều kiện đăng ký thường trú, đề nghị đăng ký thường trú tại chỗ ở mới thì hồ sơ đăng ký thường trú phải kèm Giấy giới thiệu của Thủ trưởng đơn vị quản lý trực tiếp (ký tên và đóng dấu). - Sĩ quan, quân nhân chuyên nghiệp, công nhân, viên chức quốc phòng đã đăng ký thường trú vào nhà ở công vụ, đơn vị đóng quân khi chuyển đăng ký thường trú ra chỗ ở hợp pháp ngoài nơi nhà ở công vụ, nơi đơn vị đóng quân thì hồ sơ đăng ký thường trú tại chỗ ở mới phải kèm theo Giấy giới thiệu đăng ký thường trú của đơn vị đang công tác (ký tên và đóng dấu).</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
        </tbody>
      </table>
    </div>
  </>
)

export default function DangKyThuongTruPage() {
  return (
    <ProcedurePageLayout
      procedureId="TTHC-001"
      procedureName="Đăng ký thường trú"
      agency="Công an phường/xã/thị trấn"
      processingDays="7 ngày làm việc"
      fee="Không"
      documentsSection={documentsSection}
      showCccdUpload={false}
      chatContext="Người dùng đang xem thủ tục Đăng ký thường trú (TTHC-001) tại TP. Hồ Chí Minh. Hãy sẵn sàng trả lời các câu hỏi về hồ sơ, điều kiện, và quy trình đăng ký thường trú."
    />
  )
}
