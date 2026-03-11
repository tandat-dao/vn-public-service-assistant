'use client'

interface Tab {
  id: string
  label: string
  count?: number
}

interface TabBarProps {
  tabs: Tab[]
  activeTab: string
  onChange: (id: string) => void
  className?: string
}

export function TabBar({ tabs, activeTab, onChange, className = '' }: TabBarProps) {
  return (
    <div className={`flex border-b border-[#DDDDDD] ${className}`}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={`px-4 py-2.5 text-sm transition-colors whitespace-nowrap
            ${activeTab === tab.id
              ? 'text-[#CE7A58] font-bold border-b-2 border-[#CE7A58] -mb-px'
              : 'text-[#555] hover:text-[#CE7A58]'
            }`}
        >
          {tab.label}
          {tab.count !== undefined && (
            <span className="ml-1 text-xs">({tab.count.toLocaleString('vi-VN')})</span>
          )}
        </button>
      ))}
    </div>
  )
}
