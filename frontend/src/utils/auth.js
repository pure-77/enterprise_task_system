const TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'

function decodeJWTPayload(token) {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    const payload = parts[1]
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    const json = JSON.parse(decoded)
    // exp is in seconds; convert to ms for comparison
    return { ...json, expMs: (json.exp || 0) * 1000 }
  } catch {
    return null
  }
}

export const auth = {
  setToken(token) {
    localStorage.setItem(TOKEN_KEY, token)
  },

  getToken() {
    return localStorage.getItem(TOKEN_KEY)
  },

  setRefreshToken(token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, token)
  },

  getRefreshToken() {
    return localStorage.getItem(REFRESH_TOKEN_KEY)
  },

  removeToken() {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  },

  isAccessTokenExpired() {
    const token = this.getToken()
    if (!token) return true
    const payload = decodeJWTPayload(token)
    if (!payload) return true
    return Date.now() >= payload.expMs
  },

  isRefreshTokenExpired() {
    const token = this.getRefreshToken()
    if (!token) return true
    const payload = decodeJWTPayload(token)
    if (!payload) return true
    return Date.now() >= payload.expMs
  },

  isAuthenticated() {
    return !!this.getToken()
  }
}
