import { RouterProvider } from 'react-router-dom'
import { ThemeProvider } from '@/components/theme/ThemeProvider'
import { Toaster } from '@/components/ui/sonner'
import { AuthProvider } from '@/contexts/AuthContext'
import { PublicConfigProvider } from '@/contexts/PublicConfigContext'
import { router } from '@/router/routes'

export function App() {
  return (
    <ThemeProvider>
      <PublicConfigProvider>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </PublicConfigProvider>
      <Toaster richColors closeButton />
    </ThemeProvider>
  )
}
