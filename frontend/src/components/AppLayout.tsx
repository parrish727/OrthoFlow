import { useState, useEffect, useMemo } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { ErrorBoundary } from './ErrorBoundary'
import {
  CalendarDays, Users, Receipt, Shield, FileText, Image, MessageSquare,
  BarChart3, Sparkles, Wrench, Layout, Settings, LogOut, ChevronLeft,
  ChevronRight, CreditCard, AlertTriangle, UserCircle, Menu,
} from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../hooks/useAuth'

interface NavItem {
  to: string
  icon: typeof CalendarDays
  label: string
  section?: string
}

const NAV_ITEMS: NavItem[] = [
  { to: '/', icon: Layout, label: 'Dashboard', section: 'main' },
  { to: '/schedule', icon: CalendarDays, label: 'Schedule', section: 'main' },
  { to: '/patients', icon: Users, label: 'Patients', section: 'main' },
  { to: '/imaging', icon: Image, label: 'Imaging', section: 'clinical' },
  { to: '/ledger', icon: Receipt, label: 'Ledger', section: 'finance' },
  { to: '/insurance', icon: Shield, label: 'Insurance', section: 'finance' },
  { to: '/claims', icon: FileText, label: 'Claims', section: 'finance' },
  { to: '/payments', icon: CreditCard, label: 'Payments', section: 'finance' },
  { to: '/communications', icon: MessageSquare, label: 'Messages', section: 'comms' },
  { to: '/reports', icon: BarChart3, label: 'Reports', section: 'insights' },
  { to: '/ai-insights', icon: Sparkles, label: 'AI Insights', section: 'insights' },
  { to: '/ai-tools', icon: Wrench, label: 'AI Tools', section: 'insights' },
]

const BOTTOM_ITEMS: NavItem[] = [
  { to: '/imaging/alerts', icon: AlertTriangle, label: 'Alerts' },
  { to: '/portal-admin', icon: UserCircle, label: 'Portal' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

const ROLE_LABELS: Record<string, string> = {
  owner: 'Owner',
  doctor: 'Doctor',
  office_manager: 'Office Manager',
  dental_assistant: 'Dental Assistant',
  front_desk: 'Front Desk',
  bookkeeper: 'Bookkeeper',
}

const ROLE_BADGE_COLORS: Record<string, string> = {
  owner: 'bg-teal-100 text-teal-700',
  doctor: 'bg-blue-100 text-blue-700',
  office_manager: 'bg-violet-100 text-violet-700',
  dental_assistant: 'bg-amber-100 text-amber-700',
  front_desk: 'bg-emerald-100 text-emerald-700',
  bookkeeper: 'bg-gray-100 text-gray-700',
}

// Nav labels visible per role
const ROLE_NAV_ALLOWED: Record<string, string[]> = {
  dental_assistant: ['Dashboard', 'Schedule', 'Patients', 'Imaging', 'AI Insights', 'AI Tools'],
  front_desk: ['Dashboard', 'Schedule', 'Patients', 'Messages', 'Payments', 'Portal'],
  office_manager: ['Dashboard', 'Schedule', 'Patients', 'Imaging', 'Ledger', 'Insurance', 'Claims', 'Payments', 'Messages', 'Reports', 'AI Insights', 'Portal', 'Alerts'],
  // doctor and owner get everything — no filter needed
}

function filterNavForRole(items: NavItem[], role: string): NavItem[] {
  if (!role || role === 'owner' || role === 'doctor') return items
  const allowed = ROLE_NAV_ALLOWED[role]
  if (!allowed) return items
  return items.filter(item => allowed.includes(item.label))
}

function filterBottomForRole(items: NavItem[], role: string): NavItem[] {
  if (!role || role === 'owner' || role === 'doctor') return items
  const allowed = ROLE_NAV_ALLOWED[role]
  if (!allowed) return items
  return items.filter(item => allowed.includes(item.label) || item.label === 'Settings')
}

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [practiceName, setPracticeName] = useState('OrthoFlow')
  const [practiceLogo, setPracticeLogo] = useState('')
  const navigate = useNavigate()
  const { role } = useAuth()

  const filteredNav = useMemo(() => filterNavForRole(NAV_ITEMS, role), [role])
  const filteredBottom = useMemo(() => filterBottomForRole(BOTTOM_ITEMS, role), [role])

  useEffect(() => {
    api.getPractice().then(async res => {
      if (res.ok) {
        const data = await res.json()
        setPracticeName(data.name || 'OrthoFlow')
        setPracticeLogo(data.logo_url || '')
      }
    })
  }, [])

  function handleLogout() {
    localStorage.clear()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar — Desktop */}
      <aside
        className={`hidden lg:flex flex-col fixed top-0 left-0 h-full bg-white border-r border-gray-200 z-30 transition-all duration-200 ${
          collapsed ? 'w-16' : 'w-56'
        }`}
      >
        {/* Logo */}
        <div className={`h-14 flex items-center border-b border-gray-100 px-4 ${collapsed ? 'justify-center' : 'gap-2.5'}`}>
          {practiceLogo ? (
            <img src={practiceLogo} alt="" className="w-7 h-7 rounded-md object-contain flex-shrink-0" />
          ) : (
            <div className="w-7 h-7 bg-gradient-to-br from-teal-500 to-teal-700 rounded-md flex items-center justify-center flex-shrink-0">
              <span className="text-white text-xs font-bold">O</span>
            </div>
          )}
          {!collapsed && (
            <div className="flex flex-col min-w-0">
              <span className="text-sm font-bold text-gray-900 truncate">{practiceName}</span>
              {role && (
                <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full w-fit ${ROLE_BADGE_COLORS[role] || 'bg-gray-100 text-gray-600'}`}>
                  {ROLE_LABELS[role] || role}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Nav Items */}
        <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
          {filteredNav.map((item, i) => {
            // Section divider
            const prevSection = i > 0 ? filteredNav[i - 1].section : null
            const showDivider = item.section !== prevSection && i > 0

            return (
              <div key={item.to}>
                {showDivider && <div className="my-2 mx-2 border-t border-gray-100" />}
                <SidebarLink item={item} collapsed={collapsed} />
              </div>
            )
          })}
        </nav>

        {/* Bottom Items */}
        <div className="border-t border-gray-100 py-3 px-2 space-y-0.5">
          {filteredBottom.map(item => (
            <SidebarLink key={item.to} item={item} collapsed={collapsed} />
          ))}
          <button
            onClick={handleLogout}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-gray-500 hover:text-red-600 hover:bg-red-50 transition-colors ${
              collapsed ? 'justify-center' : ''
            }`}
          >
            <LogOut size={18} />
            {!collapsed && <span className="text-sm">Sign Out</span>}
          </button>
        </div>

        {/* Collapse Toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="h-10 flex items-center justify-center border-t border-gray-100 text-gray-400 hover:text-gray-600 hover:bg-gray-50 transition-colors"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </aside>

      {/* Mobile Sidebar Overlay */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-40">
          <div className="absolute inset-0 bg-black/20" onClick={() => setMobileOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-64 bg-white border-r border-gray-200 shadow-xl">
            <div className="h-14 flex items-center border-b border-gray-100 px-4 gap-2.5">
              <div className="w-7 h-7 bg-gradient-to-br from-teal-500 to-teal-700 rounded-md flex items-center justify-center">
                <span className="text-white text-xs font-bold">O</span>
              </div>
              <span className="text-sm font-bold text-gray-900">{practiceName}</span>
            </div>
            <nav className="py-3 px-2 space-y-0.5">
              {filteredNav.map(item => (
                <SidebarLink key={item.to} item={item} collapsed={false} onClick={() => setMobileOpen(false)} />
              ))}
              <div className="my-2 mx-2 border-t border-gray-100" />
              {filteredBottom.map(item => (
                <SidebarLink key={item.to} item={item} collapsed={false} onClick={() => setMobileOpen(false)} />
              ))}
            </nav>
          </aside>
        </div>
      )}

      {/* Main Content Area */}
      <div className={`flex-1 flex flex-col min-h-screen transition-all duration-200 ${collapsed ? 'lg:ml-16' : 'lg:ml-56'}`}>
        {/* Top Bar */}
        <header className="sticky top-0 z-20 h-14 bg-white/90 backdrop-blur-md border-b border-gray-100 flex items-center px-4 lg:px-6">
          {/* Mobile menu button */}
          <button
            onClick={() => setMobileOpen(true)}
            className="lg:hidden p-2 -ml-2 mr-2 text-gray-600 hover:text-gray-900"
            aria-label="Open menu"
          >
            <Menu size={20} />
          </button>

          <div className="flex-1" />

          {/* Right side — user */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleLogout}
              className="text-xs text-gray-500 hover:text-gray-700 transition-colors"
            >
              Sign Out
            </button>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-4 lg:p-6">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  )
}

function SidebarLink({ item, collapsed, onClick }: { item: NavItem; collapsed: boolean; onClick?: () => void }) {
  return (
    <NavLink
      to={item.to}
      end={item.to === '/'}
      onClick={onClick}
      className={({ isActive }) =>
        `flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors ${
          collapsed ? 'justify-center' : ''
        } ${
          isActive
            ? 'bg-teal-50 text-teal-700 font-medium'
            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
        }`
      }
    >
      <item.icon size={18} className="flex-shrink-0" />
      {!collapsed && <span className="text-sm truncate">{item.label}</span>}
    </NavLink>
  )
}
