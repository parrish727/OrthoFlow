import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

export default function Privacy() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center gap-4">
          <button onClick={() => navigate(-1)} className="w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded-lg flex items-center justify-center transition-colors">
            <ArrowLeft size={16} className="text-gray-600" />
          </button>
          <h1 className="text-lg font-semibold text-gray-900">Privacy Policy</h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        <div className="bg-white rounded-2xl border border-gray-200/80 p-8 shadow-sm prose prose-sm prose-gray max-w-none">
          <p className="text-xs text-gray-500">Effective Date: May 8, 2026 | Last Updated: May 8, 2026</p>

          <h2>1. Introduction</h2>
          <p>OrthoFlow AI ("OrthoFlow," "we," "us," or "our") is an accounts payable automation platform for orthodontic and dental practices. This Privacy Policy describes how we collect, use, store, and protect information when you use our application.</p>

          <h2>2. Information We Collect</h2>
          <h3>Information You Provide</h3>
          <ul>
            <li><strong>Account information:</strong> Name, email address, practice name, phone number</li>
            <li><strong>Practice information:</strong> NPI number, address, team member details</li>
            <li><strong>Invoice data:</strong> Vendor invoices uploaded to the platform</li>
          </ul>
          <h3>Information Collected Through Third-Party Services</h3>
          <ul>
            <li><strong>Plaid:</strong> When you connect your bank account, Plaid provides us with your account name, masked account number, and routing number for payment initiation. We do not store full account numbers.</li>
            <li><strong>QuickBooks:</strong> Authorization tokens to sync invoice data to your QuickBooks account.</li>
          </ul>

          <h2>3. How We Use Your Information</h2>
          <p>We use information solely to:</p>
          <ul>
            <li>Process and classify vendor invoices using AI</li>
            <li>Route invoices for approval within your practice</li>
            <li>Initiate ACH payments to vendors on your behalf (when authorized)</li>
            <li>Sync approved invoices to your QuickBooks account</li>
            <li>Send notifications about invoice status</li>
          </ul>
          <p>We do <strong>not</strong> sell your data, use it for advertising, or share it with other customers.</p>

          <h2>4. Data Sharing</h2>
          <p>We share data only with:</p>
          <ul>
            <li><strong>Plaid</strong> — bank account linking and payment initiation</li>
            <li><strong>QuickBooks (Intuit)</strong> — invoice sync</li>
            <li><strong>Twilio</strong> (if SMS enabled) — SMS notifications</li>
          </ul>

          <h2>5. Data Storage and Security</h2>
          <ul>
            <li>All data encrypted at rest (AES-256) and in transit (TLS 1.2+)</li>
            <li>Sensitive credentials encrypted at the application level</li>
            <li>Multi-factor authentication for system access</li>
            <li>Immutable audit trail on all data access</li>
            <li>Practice data isolated from all other customers</li>
          </ul>

          <h2>6. Data Retention</h2>
          <ul>
            <li><strong>Active accounts:</strong> Data retained for duration of subscription</li>
            <li><strong>Cancelled accounts:</strong> Data deleted within 90 days</li>
            <li><strong>Plaid tokens:</strong> Revoked immediately upon disconnection</li>
            <li><strong>Invoices:</strong> Retained per your configured policy (default: 7 years)</li>
          </ul>

          <h2>7. Your Rights</h2>
          <p>You have the right to:</p>
          <ul>
            <li>Access your data at any time</li>
            <li>Correct inaccurate information</li>
            <li>Delete your account and all associated data</li>
            <li>Disconnect third-party integrations at any time</li>
            <li>Opt out of SMS notifications</li>
            <li>Export your data upon request</li>
          </ul>

          <h2>8. Consent</h2>
          <p>By creating an account, you consent to data collection as described here. Additional consent is obtained for bank account linking, payment initiation, and SMS notifications. You may withdraw consent at any time.</p>

          <h2>9. HIPAA Compliance</h2>
          <p>OrthoFlow maintains compliance with the HIPAA Security Rule including administrative, physical, and technical safeguards. A Business Associate Agreement (BAA) is available upon request.</p>

          <h2>10. Changes to This Policy</h2>
          <p>We will notify you of material changes at least 30 days before they take effect.</p>

          <h2>11. Contact</h2>
          <p>For questions: <strong>privacy@orthoflowsolutions.com</strong></p>
        </div>
      </main>
    </div>
  )
}
