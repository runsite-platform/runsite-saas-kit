export const RETURN_PATH_PARAM = 'next'

const PENDING_INVITATION_KEY = 'pending-invitation-path'
const LAST_ORGANIZATION_KEY = 'last-organization-slug'
const INVITATION_PATH_PREFIX = '/invite/'

export function getSafeReturnPath(rawPath: string | null | undefined, fallback: string): string {
  if (!rawPath || !rawPath.startsWith('/') || rawPath.startsWith('//') || rawPath.startsWith('/\\')) {
    return fallback
  }
  return rawPath
}

export function withReturnPath(path: string, returnPath: string): string {
  return `${path}?${RETURN_PATH_PARAM}=${encodeURIComponent(returnPath)}`
}

function readStorage(getStorage: () => Storage, key: string): string | null {
  try {
    return getStorage().getItem(key)
  } catch {
    return null
  }
}

function writeStorage(getStorage: () => Storage, key: string, value: string | null): void {
  try {
    if (value === null) {
      getStorage().removeItem(key)
    } else {
      getStorage().setItem(key, value)
    }
  } catch {
    // Storage can be unavailable (private mode, blocked site data); the app works without it.
  }
}

const getSessionStorage = () => window.sessionStorage
const getLocalStorage = () => window.localStorage

export function rememberPendingInvitation(invitationPath: string): void {
  writeStorage(getSessionStorage, PENDING_INVITATION_KEY, invitationPath)
}

export function peekPendingInvitation(): string | null {
  const storedPath = readStorage(getSessionStorage, PENDING_INVITATION_KEY)
  return storedPath?.startsWith(INVITATION_PATH_PREFIX) ? storedPath : null
}

export function clearPendingInvitation(): void {
  writeStorage(getSessionStorage, PENDING_INVITATION_KEY, null)
}

export function rememberLastOrganization(slug: string): void {
  writeStorage(getLocalStorage, LAST_ORGANIZATION_KEY, slug)
}

export function getLastOrganization(): string | null {
  return readStorage(getLocalStorage, LAST_ORGANIZATION_KEY)
}
