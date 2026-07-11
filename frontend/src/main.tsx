import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './index.css'

// Layout
import AppLayout from './components/AppLayout'

// Public pages
import Login from './pages/Login'
import Privacy from './pages/Privacy'
import Terms from './pages/Terms'
import PatientPortal from './pages/PatientPortal'

// App pages (inside layout)
import Dashboard from './pages/Dashboard'
import Schedule from './pages/Schedule'
import Patients from './pages/Patients'
import PatientDetail from './pages/PatientDetail'
import Invoices from './pages/Invoices'
import InvoiceDetail from './pages/InvoiceDetail'
import Analytics from './pages/Analytics'
import SettingsPage from './pages/Settings'
import Account from './pages/Account'
import Ledger from './pages/Ledger'
import Insurance from './pages/Insurance'
import Claims from './pages/Claims'
import Payments from './pages/Payments'
import Communications from './pages/Communications'
import MessageLog from './pages/MessageLog'
import Imaging from './pages/Imaging'
import ImagingAlerts from './pages/ImagingAlerts'
import AIInsights from './pages/AIInsights'
import AITools from './pages/AITools'
import Reports from './pages/Reports'
import Migration from './pages/Migration'
import PortalAdmin from './pages/PortalAdmin'
import Team from './pages/Team'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('token')
  return token ? <>{children}</> : <Navigate to="/login" />
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        {/* Public routes (no layout) */}
        <Route path="/login" element={<Login />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/terms" element={<Terms />} />
        <Route path="/portal" element={<PatientPortal />} />

        {/* App routes (inside shared layout with sidebar) */}
        <Route element={<PrivateRoute><AppLayout /></PrivateRoute>}>
          <Route index element={<Dashboard />} />
          <Route path="/schedule" element={<Schedule />} />
          <Route path="/patients" element={<Patients />} />
          <Route path="/patients/:id" element={<PatientDetail />} />
          <Route path="/invoices" element={<Invoices />} />
          <Route path="/invoice/:id" element={<InvoiceDetail />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/account" element={<Account />} />
          <Route path="/ledger" element={<Ledger />} />
          <Route path="/insurance" element={<Insurance />} />
          <Route path="/claims" element={<Claims />} />
          <Route path="/payments" element={<Payments />} />
          <Route path="/communications" element={<Communications />} />
          <Route path="/messages" element={<MessageLog />} />
          <Route path="/imaging" element={<Imaging />} />
          <Route path="/imaging/alerts" element={<ImagingAlerts />} />
          <Route path="/insights" element={<AIInsights />} />
          <Route path="/tools" element={<AITools />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/migration" element={<Migration />} />
          <Route path="/portal-admin" element={<PortalAdmin />} />
          <Route path="/team" element={<Team />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
