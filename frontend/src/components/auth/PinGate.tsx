'use client'
import { useState, useEffect, useRef } from 'react'

export function PinGate() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null)
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const stored = sessionStorage.getItem('dvc_pin_auth')
    setAuthenticated(stored === 'true')
  }, [])

  const handleSubmit = () => {
    const expected = process.env.NEXT_PUBLIC_ACCESS_PIN ?? '2026'
    if (pin === expected) {
      sessionStorage.setItem('dvc_pin_auth', 'true')
      setAuthenticated(true)
    } else {
      setError('Mã PIN không đúng. Vui lòng thử lại.')
      setPin('')
      setTimeout(() => inputRef.current?.focus(), 0)
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 4)
    setPin(value)
    setError('')
    if (value.length === 4) {
      const expected = process.env.NEXT_PUBLIC_ACCESS_PIN ?? '2026'
      if (value === expected) {
        sessionStorage.setItem('dvc_pin_auth', 'true')
        setAuthenticated(true)
      } else {
        setError('Mã PIN không đúng. Vui lòng thử lại.')
        setPin('')
        setTimeout(() => inputRef.current?.focus(), 0)
      }
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && pin.length === 4) handleSubmit()
  }

  if (authenticated === null) return null
  if (authenticated === true) return null

  return (
    <div className="fixed inset-0 bg-[var(--navy)]/95 backdrop-blur-sm z-[9999]
                    flex items-center justify-center">
      <div className="bg-white rounded-2xl p-8 w-full max-w-sm shadow-2xl mx-4">
        {/* Header */}
        <div className="text-center mb-6">
          <div className="w-12 h-1 bg-[var(--terracotta)] rounded-full mx-auto mb-4" />
          <h1 className="text-lg font-semibold text-[var(--navy)] mb-1">
            Cổng Dịch Vụ Công
          </h1>
          <p className="text-xs text-[var(--text-muted)] uppercase tracking-widest">
            TP. Hồ Chí Minh
          </p>
        </div>

        <p className="text-sm text-[var(--text-secondary)] text-center mb-3">
          Nhập mã PIN để tiếp tục
        </p>

        <input
          ref={inputRef}
          type="password"
          value={pin}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          maxLength={4}
          inputMode="numeric"
          pattern="[0-9]*"
          autoFocus
          className="text-center text-2xl tracking-[0.5em] border-2 border-[var(--border-card)]
                     rounded-xl px-4 py-3 w-full focus:border-[var(--terracotta)]
                     focus:outline-none transition-colors mb-3"
          placeholder="••••"
        />

        {error && (
          <p className="text-red-500 text-sm text-center mt-2">{error}</p>
        )}

        <button
          onClick={handleSubmit}
          disabled={pin.length !== 4}
          className="w-full bg-[var(--navy)] text-white rounded-xl py-3 font-medium
                     hover:bg-[var(--navy-mid)] transition-colors mt-4
                     disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Xác nhận
        </button>
      </div>
    </div>
  )
}
