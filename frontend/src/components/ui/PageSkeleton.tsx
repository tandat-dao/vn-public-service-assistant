"use client"

export function PageSkeleton() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6 animate-pulse">
      {/* Info card skeleton */}
      <div className="bg-white border border-[var(--border-card)] rounded-xl p-6">
        <div className="h-6 bg-[var(--gray-100)] rounded w-2/3 mb-4" />
        <div className="grid grid-cols-2 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i}>
              <div className="h-3 bg-[var(--gray-100)] rounded w-1/3 mb-2" />
              <div className="h-4 bg-[var(--gray-100)] rounded w-1/2" />
            </div>
          ))}
        </div>
      </div>
      {/* Form section skeleton */}
      <div className="bg-white border border-[var(--border-card)] rounded-xl p-6">
        <div className="h-5 bg-[var(--gray-100)] rounded w-1/4 mb-4" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-10 bg-[var(--gray-100)] rounded" />
          ))}
        </div>
      </div>
      {/* Document table skeleton */}
      <div className="bg-white border border-[var(--border-card)] rounded-xl p-6">
        <div className="h-5 bg-[var(--gray-100)] rounded w-1/3 mb-4" />
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-4 bg-[var(--gray-100)] rounded mb-3" />
        ))}
      </div>
    </div>
  )
}
