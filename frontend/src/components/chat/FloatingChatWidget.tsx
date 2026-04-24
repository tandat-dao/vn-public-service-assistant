'use client'
import { usePathname } from 'next/navigation'
import { ChatWidget } from './ChatWidget'

export function FloatingChatWidget() {
  const pathname = usePathname()
  if (pathname === '/') return null
  return <ChatWidget />
}
