'use client'
import { useState } from 'react'
import { Search } from 'lucide-react'

interface SearchBarProps {
  placeholder?: string
  onSearch: (query: string) => void
  showAdvanced?: boolean
  className?: string
}

export function SearchBar({
  placeholder = 'Nhập từ khoá tìm kiếm',
  onSearch,
  showAdvanced = true,
  className = '',
}: SearchBarProps) {
  const [value, setValue] = useState('')

  return (
    <div className={`flex w-full ${className}`}>
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && onSearch(value)}
        placeholder={placeholder}
        className="flex-1 border border-[#DDDDDD] px-3 py-2 text-sm text-[#1E2F41]
                   rounded-l focus:outline-none focus:border-[#CE7A58]
                   placeholder:text-[#999] bg-white"
      />
      {showAdvanced && (
        <span className="flex items-center px-3 py-2 text-xs text-[#2A6EBB] cursor-pointer
                         border-t border-b border-[#DDDDDD] whitespace-nowrap hover:underline
                         bg-white">
          Tìm kiếm nâng cao
        </span>
      )}
      <button
        onClick={() => onSearch(value)}
        className="bg-[#F5F5F5] border border-[#DDDDDD] border-l-0 px-3 py-2
                   rounded-r hover:bg-[#E8E8E8] transition-colors"
      >
        <Search className="w-4 h-4 text-[#1E2F41]" />
      </button>
    </div>
  )
}
