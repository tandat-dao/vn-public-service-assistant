export function Footer() {
  return (
    <>
      {/* Support strip */}
      <div className="bg-white border-t border-[#DDDDDD] py-5">
        <div className="max-w-container mx-auto px-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <a href="/cau-hoi-thuong-gap"
             className="flex items-center gap-3 p-4 border border-[#DDDDDD] rounded
                        hover:border-[#CE7A58] transition-colors group">
            <div className="w-12 h-12 rounded-full bg-[#F5E8DF] flex items-center justify-center
                            text-[#CE7A58] text-xl font-bold group-hover:bg-[#CE7A58]
                            group-hover:text-white transition-colors">
              ?
            </div>
            <span className="text-[#1E2F41] font-semibold text-sm">Câu hỏi thường gặp</span>
          </a>
          <a href="/ho-tro/huong-dan"
             className="flex items-center gap-3 p-4 border border-[#DDDDDD] rounded
                        hover:border-[#CE7A58] transition-colors group">
            <div className="w-12 h-12 rounded-full bg-[#F5E8DF] flex items-center justify-center
                            text-[#CE7A58] text-xl font-bold group-hover:bg-[#CE7A58]
                            group-hover:text-white transition-colors">
              ℹ
            </div>
            <span className="text-[#1E2F41] font-semibold text-sm">Hướng dẫn sử dụng</span>
          </a>
        </div>
      </div>

      {/* Main footer bar */}
      <footer className="bg-[#903938] text-white py-4">
        <div className="max-w-container mx-auto px-4">
          <p className="text-center text-sm leading-relaxed">
            Cơ quan chủ quản: Văn phòng Chính phủ&nbsp;&nbsp;|&nbsp;&nbsp;
            www.dichvucong.gov.vn&nbsp;&nbsp;|&nbsp;&nbsp;
            Tổng đài hỗ trợ: 18001096&nbsp;&nbsp;|&nbsp;&nbsp;
            Email: dichvucong@chinhphu.vn
          </p>
        </div>
      </footer>
    </>
  )
}
