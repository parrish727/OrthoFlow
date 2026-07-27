/**
 * Role-Based Access Control — Permission Matrix
 * Defines which routes and nav sections each role can access.
 */

export type Role = 'owner' | 'doctor' | 'office_manager' | 'dental_assistant' | 'front_desk'

export interface RolePermissions {
  label: string
  navSections: string[]
  allowedRoutes: string[]
  homePage: string
}

export const ROLE_PERMISSIONS: Record<Role, RolePermissions> = {
  owner: {
    label: 'Owner / Doctor',
    navSections: ['main', 'clinical', 'finance', 'comms', 'insights'],
    allowedRoutes: ['*'],
    homePage: '/',
  },
  doctor: {
    label: 'Doctor',
    navSections: ['main', 'clinical', 'finance', 'comms', 'insights'],
    allowedRoutes: ['*'],
    homePage: '/',
  },
  office_manager: {
    label: 'Office Manager',
    navSections: ['main', 'clinical', 'finance', 'comms', 'insights'],
    allowedRoutes: ['*'],
    homePage: '/',
  },
  dental_assistant: {
    label: 'Dental Assistant',
    navSections: ['main', 'clinical', 'comms'],
    allowedRoutes: [
      '/', '/schedule', '/patients', '/patients/:id', '/time-tracking',
      '/imaging', '/imaging/alerts', '/appliances', '/recall', '/cdt-codes',
      '/da-chat', '/communications',
      '/help',
    ],
    homePage: '/',
  },
  front_desk: {
    label: 'Front Desk',
    navSections: ['main', 'finance', 'comms'],
    allowedRoutes: [
      '/', '/schedule', '/patients', '/patients/:id', '/time-tracking',
      '/ledger', '/invoices', '/insurance', '/claims', '/payments',
      '/communications', '/da-chat',
      '/portal-admin', '/help',
    ],
    homePage: '/',
  },
}

/**
 * Check if a role can access a given route path.
 */
export function canAccessRoute(role: Role, path: string): boolean {
  const perms = ROLE_PERMISSIONS[role]
  if (!perms) return false
  if (perms.allowedRoutes.includes('*')) return true

  // Check exact match first
  if (perms.allowedRoutes.includes(path)) return true

  // Check parameterized routes (e.g. /patients/:id matches /patients/abc-123)
  return perms.allowedRoutes.some(route => {
    if (!route.includes(':')) return false
    const regex = new RegExp('^' + route.replace(/:[^/]+/g, '[^/]+') + '$')
    return regex.test(path)
  })
}

/**
 * Check if a role can see a given nav section.
 */
export function canSeeSection(role: Role, section: string): boolean {
  const perms = ROLE_PERMISSIONS[role]
  if (!perms) return false
  return perms.navSections.includes(section)
}
