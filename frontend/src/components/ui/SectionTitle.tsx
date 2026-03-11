export function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-center mb-2">
      <h2 className="section-title">{children}</h2>
    </div>
  )
}
