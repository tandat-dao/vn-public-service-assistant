import type { Metadata } from 'next'
import './globals.css'
import { Header } from '@/components/layout/Header'
import { Footer } from '@/components/layout/Footer'
import { FloatingChatWidget } from '@/components/chat/FloatingChatWidget'
import { NavigationProgress } from '@/components/ui/NavigationProgress'
import { PinGate } from '@/components/auth/PinGate'

export const metadata: Metadata = {
  title: 'Cổng Dịch vụ công Quốc gia',
  description: 'Kết nối, cung cấp thông tin và dịch vụ công mọi lúc, mọi nơi',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
      </head>
      <body className="min-h-screen flex flex-col">
        <PinGate />
        <NavigationProgress />
        <Header />
        <main className="flex-1">{children}</main>
        <Footer />
        <FloatingChatWidget />
      </body>
    </html>
  )
}
