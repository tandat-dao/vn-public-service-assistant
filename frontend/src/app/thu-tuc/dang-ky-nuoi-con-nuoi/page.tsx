'use client'
import { ProcedurePageLayout } from '@/components/procedure/ProcedurePageLayout'

const documentsSection = (
  <>
    <p className="text-sm font-semibold text-gray-700 mt-4 mb-2">Giấy tờ phải nộp:</p>
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
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">- Giấy chứng sinh; trường hợp không có Giấy chứng sinh thì nộp văn bản của người làm chứng xác nhận về việc sinh; nếu không có người làm chứng thì phải có giấy cam đoan về việc sinh.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Trường hợp người yêu cầu đã nộp bản điện tử Giấy chứng sinh hoặc cơ quan đăng ký hộ tịch đã khai thác được dữ liệu điện tử có ký số của Giấy chứng sinh thì không phải nộp bản giấy.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">- Trường hợp trẻ em bị bỏ rơi thì phải có biên bản về việc trẻ bị bỏ rơi do cơ quan có thẩm quyền lập.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">- Trường hợp khai sinh cho trẻ em sinh ra do mang thai hộ phải có văn bản xác nhận của cơ sở y tế đã thực hiện kỹ thuật hỗ trợ sinh sản cho việc mang thai hộ.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">- Văn bản ủy quyền (được chứng thực) theo quy định của pháp luật trong trường hợp ủy quyền thực hiện việc đăng ký khai sinh. Trường hợp người được ủy quyền là ông, bà, cha, mẹ, con, vợ, chồng, anh, chị, em ruột của người ủy quyền thì văn bản ủy quyền không phải chứng thực.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p className="text-sm font-semibold text-gray-700 mt-4 mb-2">Giấy tờ phải xuất trình:</p>
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
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">- Hộ chiếu/Thẻ căn cước công dân/Thẻ căn cước/Căn cước điện tử/Giấy chứng nhận căn cước hoặc các giấy tờ khác có dán ảnh và thông tin cá nhân do cơ quan có thẩm quyền cấp, còn giá trị sử dụng (sau đây gọi tắt là giấy tờ tùy thân) để chứng minh về nhân thân khi làm thủ tục trực tiếp tại cơ quan đăng ký hộ tịch.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Trường hợp giấy tờ tùy thân sử dụng là: Hộ chiếu, Thẻ căn cước, Căn cước công dân, Giấy chứng nhận căn cước thì người có yêu cầu đăng ký hộ tịch chỉ cần cung cấp thông tin số định danh cá nhân hoặc thông tin về giấy tờ (số, ngày/tháng/năm cấp), cơ quan đăng ký hộ tịch có trách nhiệm tra cứu thông tin thông qua kết nối với Cơ sở dữ liệu hộ tịch điện tử, Cơ sở dữ liệu quốc gia về dân cư hoặc cơ sở dữ liệu khác có liên quan để đối chiếu, khai thác dữ liệu.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Trường hợp không khai thác được thông tin hoặc thông tin khai thác được không đầy đủ, không chính xác thì cơ quan đăng ký hộ tịch yêu cầu người đi đăng ký hộ tịch xuất trình bản chính giấy tờ để chứng minh, đồng thời đề nghị người đi đăng ký hộ tịch cập nhật, điều chỉnh thông tin trong các cơ sở dữ liệu theo quy định của pháp luật.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Trường hợp các thông tin cá nhân trong các giấy tờ này đã có trong Cơ sở dữ liệu quốc gia về dân cư, Cơ sở dữ liệu hộ tịch điện tử, được hệ thống điền tự động thì không phải tải lên (theo hình thức trực tuyến)</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">- Giấy tờ có giá trị chứng minh thông tin về cư trú trong trường hợp cơ quan đăng ký hộ tịch không thể khai thác được thông tin về nơi cư trú của công dân theo các phương thức quy định tại khoản 2 Điều 14 Nghị định số 104/2022/NĐ-CP ngày 21/12/2022 của Chính phủ. Trường hợp các thông tin về giấy tờ chứng minh nơi cư trú đã được khai thác từ Cơ sở dữ liệu quốc gia về dân cư bằng các phương thức này thì người có yêu cầu không phải xuất trình (theo hình thức trực tiếp) hoặc tải lên (theo hình thức trực tuyến).</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">- Trường hợp gửi hồ sơ qua hệ thống bưu chính thì phải gửi kèm theo bản sao có chứng thực các giấy tờ phải xuất trình nêu trên.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
        </tbody>
      </table>
    </div>

    <p className="text-sm font-semibold text-gray-700 mt-4 mb-2">Lưu ý:</p>
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
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">- Cá nhân có quyền lựa chọn thực hiện thủ tục hành chính về hộ tịch tại cơ quan đăng ký hộ tịch nơi cư trú; nơi cư trú của cá nhân được xác định theo quy định của pháp luật về cư trú. Trường hợp cá nhân lựa chọn thực hiện thủ tục hành chính về hộ tịch không phải tại Ủy ban nhân dân cấp xã nơi thường trú hoặc nơi tạm trú thì Ủy ban nhân dân cấp xã nơi tiếp nhận yêu cầu có trách nhiệm hỗ trợ người dân nộp hồ sơ đăng ký hộ tịch trực tuyến đến đúng cơ quan có thẩm quyền theo quy định.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">- Đối với giấy tờ nộp, xuất trình nếu người yêu cầu nộp hồ sơ theo hình thức trực tiếp:</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">+ Người yêu cầu đăng ký hộ tịch có thể nộp bản sao được chứng thực từ bản chính hoặc bản sao được cấp từ sổ gốc (sau đây gọi là bản sao) hoặc bản chụp kèm theo bản chính, bản điện tử các giấy tờ này, bao gồm cả giấy tờ được tích hợp, hiển thị trên Ứng dụng định danh điện tử (VneID).</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Trường hợp người yêu cầu nộp bản chụp kèm theo bản chính giấy tờ thì người tiếp nhận có trách nhiệm kiểm tra, đối chiếu bản chụp với bản chính và ký xác nhận, không được yêu cầu nộp bản sao giấy tờ đó.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Đối với giấy tờ xuất trình khi đăng ký hộ tịch, người tiếp nhận có trách nhiệm kiểm tra, đối chiếu, ghi lại thông tin hoặc chụp lại, ký xác nhận để lưu trong hồ sơ và trả lại cho người xuất trình, không được yêu cầu nộp bản sao hoặc bản chụp giấy tờ đó.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">+ Người tiếp nhận có trách nhiệm tiếp nhận đúng, đủ hồ sơ đăng ký hộ tịch theo quy định của pháp luật hộ tịch, không được yêu cầu người đăng ký hộ tịch nộp thêm giấy tờ mà pháp luật hộ tịch không quy định phải nộp .</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Người tiếp nhận hồ sơ thực hiện khai thác thông tin trong Cơ sở dữ liệu quốc gia về dân cư theo quy định pháp luật nếu người yêu cầu đăng ký hộ tịch đã cung cấp họ, chữ đệm, tên; ngày, tháng, năm sinh; số định danh cá nhân/căn cước công dân/thẻ căn cước/chứng minh nhân dân. Trường hợp các thông tin cần khai thác không có trong Cơ sở dữ liệu quốc gia về dân cư thì đề nghị người yêu cầu kê khai đầy đủ .</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">- Đối với giấy tờ gửi kèm theo nếu người yêu cầu nộp hồ sơ theo hình thức trực tuyến:</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">+ Bản chụp các giấy tờ gửi kèm theo hồ sơ đăng ký khai sinh trực tuyến phải bảo đảm rõ nét, đầy đủ, toàn vẹn về nội dung, là bản chụp bằng máy ảnh, điện thoại hoặc được chụp, được quét bằng thiết bị điện tử, từ giấy tờ được cấp hợp lệ, còn giá trị sử dụng.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">+ Trường hợp giấy tờ, tài liệu phải gửi kèm trong hồ sơ đăng ký khai sinh trực tuyến đã có bản sao điện tử hoặc đã có bản điện tử giấy tờ hộ tịch thì người yêu cầu được sử dụng bản điện tử này.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">- Trường hợp người yêu cầu đăng ký hộ tịch lựa chọn nhận kết quả tại Trung tâm Phục vụ hành chính công thì người yêu cầu đăng ký hộ tịch phải xuất trình giấy tờ tuỳ thân, nộp các giấy tờ là thành phần hồ sơ theo quy định; Trường hợp người yêu cầu đăng ký hộ tịch không lựa chọn nhận kết quả tại Trung tâm Phục vụ hành chính công thì người yêu cầu đăng ký hộ tịch nộp các giấy tờ là thành phần hồ sơ theo quy định trước khi nhận kết quả.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">- Trường hợp người yêu cầu đăng ký hộ tịch không cung cấp được giấy tờ theo quy định hoặc giấy tờ nộp, xuất trình bị tẩy xóa, sửa chữa, làm giả thì cơ quan đăng ký hộ tịch có thẩm quyền hủy bỏ kết quả đăng ký hộ tịch.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">- Giấy tờ do cơ quan có thẩm quyền của nước ngoài cấp, công chứng hoặc xác nhận để sử dụng cho việc đăng ký hộ tịch tại Việt Nam phải được hợp pháp hóa lãnh sự theo quy định của pháp luật, trừ trường hợp được miễn theo điều ước quốc tế mà Việt Nam là thành viên.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">- Trường hợp người đi đăng ký khai sinh cho trẻ em là ông, bà, người thân thích khác thì không phải có văn bản ủy quyền của cha, mẹ trẻ em, nhưng phải thống nhất với cha, mẹ trẻ em về các nội dung khai sinh.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">- Đối với việc xác định họ, dân tộc, quê quán, đặt tên cho trẻ:</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">+ Việc xác định họ, dân tộc, đặt tên cho trẻ em phải phù hợp với pháp luật và yêu cầu giữ gìn bản sắc dân tộc, tập quán, truyền thống văn hóa tốt đẹp của Việt Nam; không đặt tên quá dài, khó sử dụng.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">+ Trường hợp cha, mẹ không thỏa thuận được về họ, dân tộc, quê quán của con khi đăng ký khai sinh thì họ, dân tộc, quê quán của con được xác định theo tập quán nhưng phải bảo đảm theo họ, dân tộc, quê quán của cha hoặc mẹ.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">- Trường hợp cho phép người yêu cầu đăng ký hộ tịch lập văn bản cam đoan về nội dung yêu cầu đăng ký hộ tịch thì cơ quan đăng ký hộ tịch phải giải thích rõ cho người lập văn bản cam đoan về trách nhiệm, hệ quả pháp lý của việc cam đoan không đúng sự thật.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">Cơ quan đăng ký hộ tịch từ chối giải quyết hoặc đề nghị cơ quan có thẩm quyền hủy bỏ kết quả đăng ký hộ tịch, nếu có cơ sở xác định nội dung cam đoan không đúng sự thật.</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
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
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">- Tờ khai đăng ký khai sinh theo mẫu (nếu người có yêu cầu lựa chọn nộp hồ sơ theo hình thức trực tiếp hoặc gửi hồ sơ qua hệ thống bưu chính);</td>
            <td className="py-2 pr-4">
              <a
                href="/forms/1.TKngkkhaisinh.doc"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-[#CE7A58] hover:underline"
              >
                1.TKngkkhaisinh.doc
              </a>
            </td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">- Mẫu hộ tịch điện tử tương tác đăng ký khai sinh (do người yêu cầu cung cấp thông tin theo hướng dẫn trên Cổng dịch vụ công, nếu người có yêu cầu lựa chọn nộp hồ sơ theo hình thức trực tuyến)</td>
            <td className="py-2 pr-4">
              <a
                href="/forms/1.TTT-ngkkhaisinh.doc"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-[#CE7A58] hover:underline"
              >
                1.TTT-ngkkhaisinh.doc
              </a>
            </td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line">{"Bản chính: 1\nBản sao: 0"}</td>
          </tr>
          <tr className="border-b border-gray-100 align-top">
            <td className="py-2 pr-4 text-gray-800 text-sm leading-relaxed">- Người có yêu cầu đăng ký khai sinh thực hiện việc nộp/xuất trình (theo hình thức trực tiếp) hoặc tải lên (theo hình thức trực tuyến) các giấy tờ sau:</td>
            <td className="py-2 pr-4"></td>
            <td className="py-2 text-gray-600 text-xs whitespace-pre-line"></td>
          </tr>
        </tbody>
      </table>
    </div>
  </>
)

export default function DangKyNuoiConNuoiPage() {
  return (
    <ProcedurePageLayout
      procedureId="TTHC-AD-001"
      procedureName="Đăng ký việc nuôi con nuôi trong nước"
      agency="Ủy ban nhân dân cấp xã"
      processingDays="30 ngày làm việc"
      fee="Không"
      documentsSection={documentsSection}
      showCccdUpload={true}
      chatContext="Người dùng đang xem thủ tục Đăng ký việc nuôi con nuôi trong nước (TTHC-AD-001) tại TP. Hồ Chí Minh. Hãy sẵn sàng trả lời câu hỏi về điều kiện nhận nuôi, hồ sơ, thủ tục thẩm định, và quy định theo Luật Nuôi con nuôi 2010."
    />
  )
}
