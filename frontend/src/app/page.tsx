import { HeroBanner }     from '@/components/home/HeroBanner'
import { NewsStrip }      from '@/components/home/NewsStrip'
import { LifeEventsGrid } from '@/components/home/LifeEventsGrid'

export default function HomePage() {
  return (
    <>
      <HeroBanner />
      <NewsStrip />
      <LifeEventsGrid />
    </>
  )
}
