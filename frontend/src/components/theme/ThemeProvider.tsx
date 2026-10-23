import type { ReactNode } from 'react'
import { ThemeProvider as NextThemesProvider } from 'next-themes'

export const THEME_STORAGE_KEY = 'saaskit-theme'

export function ThemeProvider({ children }: { children: ReactNode }) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="light"
      enableSystem
      disableTransitionOnChange
      storageKey={THEME_STORAGE_KEY}
    >
      {children}
    </NextThemesProvider>
  )
}
