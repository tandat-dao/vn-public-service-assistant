'use client'
import { create } from 'zustand'
import type { BreadcrumbItem } from '@/lib/types'

interface NavigationStore {
  activeMainNav: string
  activeSubNav: string
  breadcrumbs: BreadcrumbItem[]
  setActiveMainNav: (v: string) => void
  setActiveSubNav:  (v: string) => void
  setBreadcrumbs:   (b: BreadcrumbItem[]) => void
}

export const useNavigationStore = create<NavigationStore>((set) => ({
  activeMainNav: '',
  activeSubNav:  '',
  breadcrumbs:   [],
  setActiveMainNav: (v) => set({ activeMainNav: v }),
  setActiveSubNav:  (v) => set({ activeSubNav: v }),
  setBreadcrumbs:   (b) => set({ breadcrumbs: b }),
}))
