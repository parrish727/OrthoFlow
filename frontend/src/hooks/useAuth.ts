import { useMemo } from 'react'

interface AuthPayload {
  role: string
  userId: string
  practiceId: string
  isDoctor: boolean
  isDA: boolean
  isFrontDesk: boolean
  isOwner: boolean
  isManager: boolean
}

function decodeJwtPayload(token: string): Record<string, string> | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    const payload = parts[1]
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decoded)
  } catch {
    return null
  }
}

export function useAuth(): AuthPayload {
  const token = localStorage.getItem('token')

  return useMemo(() => {
    const empty: AuthPayload = {
      role: '',
      userId: '',
      practiceId: '',
      isDoctor: false,
      isDA: false,
      isFrontDesk: false,
      isOwner: false,
      isManager: false,
    }

    if (!token) return empty

    const payload = decodeJwtPayload(token)
    if (!payload) return empty

    const role = payload.role || ''
    const userId = payload.sub || ''
    const practiceId = payload.practice_id || ''

    return {
      role,
      userId,
      practiceId,
      isDoctor: role === 'doctor',
      isDA: role === 'dental_assistant',
      isFrontDesk: role === 'front_desk',
      isOwner: role === 'owner',
      isManager: role === 'office_manager',
    }
  }, [token])
}
