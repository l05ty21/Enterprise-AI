import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)

  function toggleSidebar(): void {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setSidebar(value: boolean): void {
    sidebarCollapsed.value = value
  }

  return { sidebarCollapsed, toggleSidebar, setSidebar }
})
