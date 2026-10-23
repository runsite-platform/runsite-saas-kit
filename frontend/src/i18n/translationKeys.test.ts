import i18next from 'i18next'
import { describe, expect, it } from 'vitest'
import '@/i18n'

const EXPECTED_NAMESPACES = [
  'common',
  'errors',
  'auth',
  'account',
  'organizations',
  'projects',
  'files',
  'billing',
  'overview',
  'admin',
  'landing',
  'notifications',
] as const

const API_ERROR_CODES = [
  'not_found',
  'forbidden',
  'email_taken',
  'invalid_credentials',
  'user_blocked',
  'email_not_verified',
  'invalid_token',
  'not_authenticated',
  'rate_limited',
  'google_login_disabled',
  'oauth_failed',
  'slug_taken',
  'owner_cannot_be_removed',
  'already_member',
  'invitation_email_mismatch',
  'plan_limit_reached',
  'plan_upgrade_required',
  'active_subscription',
  'storage_disabled',
  'file_too_large',
  'unsupported_file_type',
  'billing_disabled',
  'plan_unavailable',
  'billing_provider_error',
  'cannot_impersonate',
  'validation_error',
  'network_error',
  'unknown_error',
] as const

type TranslationValue = string | string[] | TranslationTree
interface TranslationTree {
  [key: string]: TranslationValue
}

interface UsedKey {
  file: string
  candidateNamespaces: string[]
  key: string
}

const DEFAULT_NAMESPACE = 'common'
const MAX_TRANSLATION_DEPTH = 10

const namespaceFiles = import.meta.glob<TranslationTree>('./locales/en/*.json', {
  eager: true,
  import: 'default',
})

const sourceFiles = import.meta.glob<string>(['../**/*.{ts,tsx}', '!../**/*.test.{ts,tsx}', '!../**/*.d.ts'], {
  eager: true,
  query: '?raw',
  import: 'default',
})

const NAMESPACED_KEY_PATTERN = new RegExp(`(['"\`])(${EXPECTED_NAMESPACES.join('|')}):([A-Za-z0-9_.-]+)\\1`, 'g')
// useTranslation() resolves bare keys against 'common'; useTranslation('ns') and useTranslation(['ns', 'errors'])
// resolve them against the first namespace.
const USE_TRANSLATION_PATTERN = /useTranslation\(\s*\[?\s*(?:(['"])([A-Za-z]+)\1)?/g
const BARE_KEY_PATTERN = /\bt\(\s*(['"])([A-Za-z][A-Za-z0-9_.-]*)\1/g

function namespaceFromPath(path: string): string {
  return path.slice(path.lastIndexOf('/') + 1, -'.json'.length)
}

function flattenTranslations(tree: TranslationTree, prefix = '', depth = 0): Map<string, string[]> {
  if (depth > MAX_TRANSLATION_DEPTH) throw new Error(`Translations nested deeper than ${MAX_TRANSLATION_DEPTH}: ${prefix}`)
  const flatTranslations = new Map<string, string[]>()
  for (const [key, value] of Object.entries(tree)) {
    const fullKey = prefix ? `${prefix}.${key}` : key
    if (typeof value === 'string') {
      flatTranslations.set(fullKey, [value])
    } else if (Array.isArray(value)) {
      flatTranslations.set(fullKey, value)
    } else {
      for (const [nestedKey, nestedValue] of flattenTranslations(value, fullKey, depth + 1)) {
        flatTranslations.set(nestedKey, nestedValue)
      }
    }
  }
  return flatTranslations
}

const translationsByNamespace = new Map<string, Map<string, string[]>>(
  Object.entries(namespaceFiles).map(([path, tree]) => [namespaceFromPath(path), flattenTranslations(tree)]),
)

function hasTranslation(namespace: string, key: string): boolean {
  const translations = translationsByNamespace.get(namespace)
  if (!translations) return false
  if (translations.has(key) || translations.has(`${key}_one`) || translations.has(`${key}_other`)) return true
  return [...translations.keys()].some((existingKey) => existingKey.startsWith(`${key}.`))
}

function collectUsedKeys(file: string, source: string): UsedKey[] {
  const usedKeys: UsedKey[] = []
  for (const match of source.matchAll(NAMESPACED_KEY_PATTERN)) {
    usedKeys.push({ file, candidateNamespaces: [match[2]], key: match[3] })
  }
  // A file may hold several components with different namespaces; a bare key passes when it exists in the
  // default namespace of any useTranslation call in the same file. Files without useTranslation are skipped.
  const fileNamespaces = [
    ...new Set([...source.matchAll(USE_TRANSLATION_PATTERN)].map((match) => match[2] ?? DEFAULT_NAMESPACE)),
  ]
  if (fileNamespaces.length > 0) {
    for (const match of source.matchAll(BARE_KEY_PATTERN)) {
      usedKeys.push({ file, candidateNamespaces: fileNamespaces, key: match[2] })
    }
  }
  return usedKeys
}

describe('translations', () => {
  it('scans the source tree', () => {
    expect(Object.keys(sourceFiles).length).toBeGreaterThan(10)
  })

  it('has one JSON file per expected namespace', () => {
    expect([...translationsByNamespace.keys()].sort()).toEqual([...EXPECTED_NAMESPACES].sort())
  })

  it('registers every namespace with i18next', () => {
    const unregistered = EXPECTED_NAMESPACES.filter((namespace) => !i18next.hasResourceBundle('en', namespace))
    expect(unregistered).toEqual([])
  })

  it('has no empty translation values', () => {
    const emptyKeys: string[] = []
    for (const [namespace, translations] of translationsByNamespace) {
      for (const [key, values] of translations) {
        const hasEmptyValue =
          values.length === 0 || values.some((value) => typeof value !== 'string' || value.trim() === '')
        if (hasEmptyValue) emptyKeys.push(`${namespace}:${key}`)
      }
    }
    expect(emptyKeys).toEqual([])
  })

  it('defines every translation key used in the source code', () => {
    const missingKeys = Object.entries(sourceFiles)
      .flatMap(([file, source]) => collectUsedKeys(file, source))
      .filter((usedKey) => !usedKey.candidateNamespaces.some((namespace) => hasTranslation(namespace, usedKey.key)))
      .map((usedKey) => `${usedKey.file} → ${usedKey.candidateNamespaces.join('|')}:${usedKey.key}`)
    expect([...new Set(missingKeys)]).toEqual([])
  })

  it('defines a message for every API error code', () => {
    const missingCodes = API_ERROR_CODES.filter((code) => !hasTranslation('errors', code))
    expect(missingCodes).toEqual([])
  })
})
