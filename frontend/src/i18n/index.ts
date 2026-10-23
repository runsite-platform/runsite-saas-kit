import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import account from '@/i18n/locales/en/account.json'
import admin from '@/i18n/locales/en/admin.json'
import auth from '@/i18n/locales/en/auth.json'
import billing from '@/i18n/locales/en/billing.json'
import common from '@/i18n/locales/en/common.json'
import errors from '@/i18n/locales/en/errors.json'
import files from '@/i18n/locales/en/files.json'
import landing from '@/i18n/locales/en/landing.json'
import notifications from '@/i18n/locales/en/notifications.json'
import organizations from '@/i18n/locales/en/organizations.json'
import overview from '@/i18n/locales/en/overview.json'
import projects from '@/i18n/locales/en/projects.json'

export const defaultNamespace = 'common'

export const resources = {
  en: {
    common,
    errors,
    auth,
    account,
    organizations,
    projects,
    files,
    billing,
    overview,
    admin,
    landing,
    notifications,
  },
} as const

void i18n.use(initReactI18next).init({
  resources,
  lng: 'en',
  fallbackLng: 'en',
  ns: Object.keys(resources.en),
  defaultNS: defaultNamespace,
  interpolation: { escapeValue: false },
})

export default i18n
