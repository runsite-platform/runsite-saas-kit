export type RefreshHandler = () => Promise<string | null>
export type UnauthorizedHandler = () => void

let accessToken: string | null = null
let refreshHandler: RefreshHandler | null = null
let unauthorizedHandler: UnauthorizedHandler | null = null

export function getAccessToken(): string | null {
  return accessToken
}

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function setRefreshHandler(handler: RefreshHandler | null): void {
  refreshHandler = handler
}

export function getRefreshHandler(): RefreshHandler | null {
  return refreshHandler
}

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  unauthorizedHandler = handler
}

export function getUnauthorizedHandler(): UnauthorizedHandler | null {
  return unauthorizedHandler
}
