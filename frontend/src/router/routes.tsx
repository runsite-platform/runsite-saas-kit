import { createBrowserRouter } from 'react-router-dom'
import { AdminIndexRedirect } from '@/components/admin/AdminIndexRedirect'
import { PageLoader } from '@/components/shared/PageLoader'
import { GuestOnly } from '@/router/GuestOnly'
import { RequireAuth } from '@/router/RequireAuth'
import { RequireOrganization } from '@/router/RequireOrganization'
import { RequirePlatformRole } from '@/router/RequirePlatformRole'
import { PLATFORM_STAFF_ROLES, SUPERADMIN_ROLES } from '@/utils/platformRoles'

export const router = createBrowserRouter([
  {
    HydrateFallback: PageLoader,
    children: [
      {
        path: '/',
        lazy: () => import('@/pages/LandingPage').then((module) => ({ Component: module.LandingPage })),
      },
      {
        lazy: () =>
          import('@/components/layout/PublicLayout').then((module) => ({ Component: module.PublicLayout })),
        children: [
          {
            path: 'pricing',
            lazy: () => import('@/pages/PricingPage').then((module) => ({ Component: module.PricingPage })),
          },
          {
            path: '*',
            lazy: () => import('@/pages/NotFoundPage').then((module) => ({ Component: module.NotFoundPage })),
          },
        ],
      },
      {
        lazy: () => import('@/components/layout/AuthLayout').then((module) => ({ Component: module.AuthLayout })),
        children: [
          {
            element: <GuestOnly />,
            children: [
              {
                path: '/login',
                lazy: () => import('@/pages/auth/LoginPage').then((module) => ({ Component: module.LoginPage })),
              },
              {
                path: '/register',
                lazy: () =>
                  import('@/pages/auth/RegisterPage').then((module) => ({ Component: module.RegisterPage })),
              },
              {
                path: '/forgot-password',
                lazy: () =>
                  import('@/pages/auth/ForgotPasswordPage').then((module) => ({
                    Component: module.ForgotPasswordPage,
                  })),
              },
            ],
          },
          {
            path: '/reset-password',
            lazy: () =>
              import('@/pages/auth/ResetPasswordPage').then((module) => ({ Component: module.ResetPasswordPage })),
          },
          {
            path: '/verify-email',
            lazy: () =>
              import('@/pages/auth/VerifyEmailPage').then((module) => ({ Component: module.VerifyEmailPage })),
          },
          {
            path: '/auth/callback',
            lazy: () =>
              import('@/pages/auth/AuthCallbackPage').then((module) => ({ Component: module.AuthCallbackPage })),
          },
        ],
      },
      {
        element: <RequireAuth />,
        children: [
          {
            path: '/app',
            children: [
              { index: true, lazy: () => import('@/pages/app/AppIndexPage').then(asDefaultComponent) },
              {
                path: ':orgSlug',
                element: <RequireOrganization />,
                children: [
                  {
                    lazy: () => import('@/components/layout/AppLayout').then(asDefaultComponent),
                    children: [
                      { index: true, lazy: () => import('@/pages/app/OverviewPage').then(asDefaultComponent) },
                      {
                        path: 'projects',
                        lazy: () =>
                          import('@/pages/app/ProjectsPage').then((module) => ({ Component: module.ProjectsPage })),
                      },
                      {
                        path: 'files',
                        lazy: () => import('@/pages/app/FilesPage').then((module) => ({ Component: module.FilesPage })),
                      },
                      { path: 'members', lazy: () => import('@/pages/app/MembersPage').then(asDefaultComponent) },
                      { path: 'billing', lazy: () => import('@/pages/app/BillingPage').then(asDefaultComponent) },
                      {
                        path: 'settings',
                        lazy: () => import('@/pages/app/OrganizationSettingsPage').then(asDefaultComponent),
                      },
                      {
                        path: 'notifications',
                        lazy: () => import('@/pages/app/NotificationsPage').then(asDefaultComponent),
                      },
                    ],
                  },
                ],
              },
            ],
          },
          {
            path: '/notifications',
            lazy: () => import('@/pages/app/NotificationsRedirect').then(asDefaultComponent),
          },
          {
            path: '/account',
            lazy: () => import('@/pages/account/AccountPage').then((module) => ({ Component: module.AccountPage })),
          },
          {
            path: '/admin',
            element: <RequirePlatformRole roles={PLATFORM_STAFF_ROLES} />,
            children: [
              {
                lazy: () =>
                  import('@/components/layout/AdminLayout').then((module) => ({ Component: module.AdminLayout })),
                children: [
                  { index: true, element: <AdminIndexRedirect /> },
                  {
                    path: 'dashboard',
                    element: <RequirePlatformRole roles={SUPERADMIN_ROLES} />,
                    children: [
                      {
                        index: true,
                        lazy: () =>
                          import('@/pages/admin/AdminDashboardPage').then((module) => ({
                            Component: module.AdminDashboardPage,
                          })),
                      },
                    ],
                  },
                  {
                    path: 'users',
                    lazy: () =>
                      import('@/pages/admin/AdminUsersPage').then((module) => ({ Component: module.AdminUsersPage })),
                  },
                  {
                    path: 'users/:userId',
                    lazy: () =>
                      import('@/pages/admin/AdminUserDetailPage').then((module) => ({
                        Component: module.AdminUserDetailPage,
                      })),
                  },
                  {
                    path: 'organizations',
                    lazy: () =>
                      import('@/pages/admin/AdminOrganizationsPage').then((module) => ({
                        Component: module.AdminOrganizationsPage,
                      })),
                  },
                  {
                    path: 'organizations/:organizationId',
                    lazy: () =>
                      import('@/pages/admin/AdminOrganizationDetailPage').then((module) => ({
                        Component: module.AdminOrganizationDetailPage,
                      })),
                  },
                  {
                    path: 'setup',
                    lazy: () =>
                      import('@/pages/admin/AdminSetupPage').then((module) => ({ Component: module.AdminSetupPage })),
                  },
                ],
              },
            ],
          },
        ],
      },
      { path: '/invite/:token', lazy: () => import('@/pages/AcceptInvitationPage').then(asDefaultComponent) },
    ],
  },
])

function asDefaultComponent<ComponentType>(module: { default: ComponentType }) {
  return { Component: module.default }
}
