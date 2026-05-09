import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

export default function Terms() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center gap-4">
          <button onClick={() => navigate(-1)} className="w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded-lg flex items-center justify-center transition-colors">
            <ArrowLeft size={16} className="text-gray-600" />
          </button>
          <h1 className="text-lg font-semibold text-gray-900">Terms of Service</h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        <div className="bg-white rounded-2xl border border-gray-200/80 p-8 shadow-sm prose prose-sm prose-gray max-w-none">
          <p className="text-xs text-gray-500">Effective Date: May 8, 2026</p>

          <h2>1. Acceptance of Terms</h2>
          <p>By accessing or using OrthoFlow AI ("Service"), you agree to be bound by these Terms of Service. If you do not agree, do not use the Service.</p>

          <h2>2. Description of Service</h2>
          <p>OrthoFlow AI is an accounts payable automation platform that processes vendor invoices using artificial intelligence, routes them for approval, and integrates with third-party financial services (QuickBooks, Plaid) on behalf of orthodontic and dental practices.</p>

          <h2>3. Account Registration</h2>
          <ul>
            <li>You must provide accurate and complete information when creating an account</li>
            <li>You are responsible for maintaining the security of your account credentials</li>
            <li>You must notify us immediately of any unauthorized access</li>
            <li>One account per practice; team members are added by the account owner</li>
          </ul>

          <h2>4. Acceptable Use</h2>
          <p>You agree not to:</p>
          <ul>
            <li>Upload malicious files, viruses, or harmful content</li>
            <li>Attempt to access other users' data or accounts</li>
            <li>Use the Service for any illegal purpose</li>
            <li>Reverse engineer, decompile, or disassemble the Service</li>
            <li>Exceed reasonable usage limits or abuse API endpoints</li>
          </ul>

          <h2>5. Data Ownership</h2>
          <ul>
            <li>You retain ownership of all data you upload to the Service</li>
            <li>We do not claim ownership of your invoices, financial data, or practice information</li>
            <li>You grant us a limited license to process your data solely to provide the Service</li>
            <li>Upon account termination, your data will be deleted per our retention policy</li>
          </ul>

          <h2>6. Third-Party Integrations</h2>
          <p>The Service integrates with third-party providers (Plaid, QuickBooks/Intuit). Your use of these integrations is subject to their respective terms of service. We are not responsible for third-party service availability or changes.</p>

          <h2>7. Payment Terms</h2>
          <ul>
            <li>Subscription fees are billed monthly in advance</li>
            <li>Prices may change with 30 days written notice</li>
            <li>Refunds are not provided for partial months</li>
            <li>Failure to pay may result in service suspension</li>
          </ul>

          <h2>8. Service Availability</h2>
          <p>We strive for high availability but do not guarantee uninterrupted service. Scheduled maintenance will be communicated in advance. We are not liable for downtime caused by factors outside our control.</p>

          <h2>9. Limitation of Liability</h2>
          <p>To the maximum extent permitted by law, OrthoFlow AI shall not be liable for any indirect, incidental, special, or consequential damages arising from your use of the Service, including but not limited to lost profits, data loss, or business interruption.</p>

          <h2>10. Indemnification</h2>
          <p>You agree to indemnify and hold harmless OrthoFlow AI from any claims, damages, or expenses arising from your use of the Service or violation of these Terms.</p>

          <h2>11. Termination</h2>
          <ul>
            <li>You may cancel your account at any time through Settings</li>
            <li>We may suspend or terminate accounts that violate these Terms</li>
            <li>Upon termination, your data will be retained for 90 days then permanently deleted</li>
          </ul>

          <h2>12. Changes to Terms</h2>
          <p>We may modify these Terms at any time. Material changes will be communicated via email at least 30 days before taking effect. Continued use after changes constitutes acceptance.</p>

          <h2>13. Governing Law</h2>
          <p>These Terms are governed by the laws of the State of North Carolina, without regard to conflict of law principles.</p>

          <h2>14. Contact</h2>
          <p>For questions: <strong>legal@orthoflowsolutions.com</strong></p>
        </div>
      </main>
    </div>
  )
}
