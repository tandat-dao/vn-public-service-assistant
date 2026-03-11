import Link from 'next/link'
import type { BreadcrumbItem } from '@/lib/types'

export function Breadcrumb({ items }: { items: BreadcrumbItem[] }) {
  return (
    <div className="py-2.5 text-[13px] text-[#555]">
      {items.map((item, i) => (
        <span key={i}>
          {i > 0 && <span className="mx-1.5 text-[#999]">{'>'}</span>}
          {item.href && i < items.length - 1 ? (
            <Link href={item.href} className="text-[#2A6EBB] hover:underline">
              {item.label}
            </Link>
          ) : (
            <span className={i === items.length - 1 ? 'text-[#1E2F41]' : ''}>
              {item.label}
            </span>
          )}
        </span>
      ))}
    </div>
  )
}
