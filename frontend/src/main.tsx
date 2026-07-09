import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './index.css'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import InvoiceDetail from './pages/InvoiceDetail'
import Invoices from './pages/Invoices'
import Analytics from './pages/Analytics'
import SettingsPage from './pages/Settings'
import Account from './pages/Account'
import Privacy from './pages/Privacy'
import Terms from './pages/Terms'
import Schedule from './pages/Schedule'
import Patients from './pages/Patients'
import PatientDetail from './pages/PatientDetail'
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

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('token')
  return token ? <>{children}</> : <Navigate to="/login" />
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/terms" element={<Terms />} />
        <Route path="/" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
        <Route path="/invoice/:id" element={<PrivateRoute><InvoiceDetail /></PrivateRoute>} />
        <Route path="/invoices" element={<PrivateRoute><Invoices /></PrivateRoute>} />
        <Route path="/analytics" element={<PrivateRoute><Analytics /></PrivateRoute>} />
        <Route path="/settings" element={<PrivateRoute><SettingsPage /></PrivateRoute>} />
        <Route path="/account" element={<PrivateRoute><Account /></PrivateRoute>} />
        <Route path="/schedule" element={<PrivateRoute><Schedule /></PrivateRoute>} />
        <Route path="/patients" element={<PrivateRoute><Patients /></PrivateRoute>} />
        <Route path="/patients/:id" element={<PrivateRoute><PatientDetail /></PrivateRoute>} />
        <Route path="/ledger" element={<PrivateRoute><Ledger /></PrivateRoute>} />
        <Route path="/insurance" element={<PrivateRoute><Insurance /></PrivateRoute>} />
        <Route path="/claims" element={<PrivateRoute><Claims /></PrivateRoute>} />
        <Route path="/payments" element={<PrivateRoute><Payments /></PrivateRoute>} />
        <Route path="/communications" element={<PrivateRoute><Communications /></PrivateRoute>} />
        <Route path="/messages" element={<PrivateRoute><MessageLog /></PrivateRoute>} />
        <Route path="/imaging" element={<PrivateRoute><Imaging /></PrivateRoute>} />
        <Route path="/imaging/alerts" element={<PrivateRoute><ImagingAlerts /></PrivateRoute>} />
        <Route path="/ai-insights" element={<PrivateRoute><AIInsights /></PrivateRoute>} />
        <Route path="/ai-tools" element={<PrivateRoute><AITools /></PrivateRoute>} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
