import { clsx } from 'clsx'
import { type ButtonHTMLAttributes, forwardRef } from 'react'

type Variant = 'primary' | 'cta' | 'auth' | 'search'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  fullWidth?: boolean
}

const variantClasses: Record<Variant, string> = {
  primary: 'bg-[#CE7A58] text-white hover:bg-[#B8694A] font-semibold',
  cta:     'bg-[#FFC251] text-black hover:bg-[#F0B340] font-bold',
  auth:    'border border-[#1E2F41] text-[#1E2F41] bg-transparent hover:bg-[#F5F5F5]',
  search:  'bg-[#F5F5F5] text-[#1E2F41] border border-[#DDDDDD] hover:bg-[#E8E8E8]',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', fullWidth = false, className, children, ...props }, ref) => (
    <button
      ref={ref}
      className={clsx(
        'px-4 py-2 rounded text-sm transition-colors duration-150 focus:outline-none',
        variantClasses[variant],
        fullWidth && 'w-full',
        className,
      )}
      {...props}
    >
      {children}
    </button>
  ),
)
Button.displayName = 'Button'
