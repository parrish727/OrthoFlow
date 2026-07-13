import { useState, useMemo } from 'react'
import { Search } from 'lucide-react'

interface HelpSection {
  id: string
  title: string
  items: string[]
}

const SECTIONS: HelpSection[] = [
  {
    id: 'getting-started',
    title: 'Getting Started',
    items: [
      'The sidebar on the left provides access to all modules — Schedule, Patients, Imaging, Finance, Messages, Reports, and AI Tools.',
      'Your role determines which sections are visible. Owners and Doctors see everything; DAs and Front Desk see a focused set.',
      'The Dashboard shows today\'s appointments, pending notes for review, and key practice metrics at a glance.',
      'Use the top-right Sign Out button or the sidebar Sign Out to end your session.',
    ],
  },
  {
    id: 'schedule',
    title: 'Schedule',
    items: [
      'Create Appointment: Click "+ New Appointment", search for a patient, select time/duration/chair/DA, and confirm.',
      'Drag Between Chairs: Grab any appointment card and drop it onto a different chair column to reassign.',
      'Assign DA: Drag a DA badge from the roster above the columns and drop it onto an appointment card.',
      'Reschedule: Expand a card, click "Reschedule", pick a new time, and click "Move".',
      'Mark No-Show: Expand a card and click "No Show" to flag missed appointments.',
      'Phase auto-advances when a Bonding or Deband appointment is marked completed.',
    ],
  },
  {
    id: 'patients',
    title: 'Patients',
    items: [
      'Create Patient: From the Patients page, click "+ New Patient" and fill in demographics.',
      'View/Edit Profile: Click any patient name to open their full record — demographics, insurance, treatment phase, and history.',
      'Treatment Phases: Patients progress through Consultation → Records → Bonding → Active → Finishing → Retention → Complete.',
      'Phase changes happen automatically when key appointments are completed, or can be manually adjusted from the patient profile.',
    ],
  },
  {
    id: 'tooth-chart',
    title: 'Tooth Chart',
    items: [
      'Select Tooth: Click any tooth on the interactive chart to open its detail panel.',
      'Set Bracket Type: Choose the bracket system (ceramic, metal, self-ligating) from the dropdown on the selected tooth.',
      'Mark Band: Toggle the "Band" option for molars that receive bands instead of brackets.',
      'Mark Extracted: Click the red X icon to flag a tooth as extracted — it appears with a red X overlay.',
      'Wire Info: Set the current archwire type and size in the wire section below the chart.',
    ],
  },
  {
    id: 'clinical-notes',
    title: 'Clinical Notes',
    items: [
      'DA types shorthand observations during the appointment (e.g., "pt compliant, chain UL3-3, NiTi 16x22").',
      'Click "Assist" to have AI structure the shorthand into a formatted clinical note.',
      'Review and edit the generated note before saving — you have full control over the final content.',
      'Doctors review today\'s notes from the Dashboard "Today\'s Notes" section and sign off.',
    ],
  },
  {
    id: 'imaging',
    title: 'Imaging',
    items: [
      'Upload Images: From the Imaging page or patient profile, click "Upload" and select photos or X-rays.',
      'View in Chart: All uploaded images appear in the patient\'s imaging timeline, organized by date.',
      'Overdue Alerts: The Alerts badge in the sidebar shows patients overdue for progress photos or X-rays.',
    ],
  },
  {
    id: 'insurance-claims',
    title: 'Insurance & Claims',
    items: [
      'Add Insurance Plan: In a patient\'s profile, go to the Insurance tab and enter carrier, group, subscriber details.',
      'Check Eligibility: Click "Verify Eligibility" to confirm coverage and remaining benefits.',
      'Create Claim: From the Claims page, click "+ New Claim", select the patient and procedures, then submit.',
      'Submit Claims: Batch-submit pending claims or submit individually from the claim detail view.',
      'Review Denied Claims: Denied claims show a "Review & Appeal" button — click to view denial reason and draft an appeal.',
    ],
  },
  {
    id: 'ledger-payments',
    title: 'Ledger & Payments',
    items: [
      'Post Charges: From the Ledger, click "+ Charge" to add procedure fees to a patient\'s account.',
      'Record Payments: Click "+ Payment" to log patient payments, insurance checks, or adjustments.',
      'View Balance: Each patient\'s running balance is visible in the Ledger and on their profile.',
      'Payment Postings: Bulk-post insurance payments by matching EOB lines to outstanding charges.',
    ],
  },
  {
    id: 'communications',
    title: 'Communications',
    items: [
      'Send Reminders: Select patients and send appointment reminders via email from the Messages page.',
      'Templates: Create reusable message templates for common communications (recall, welcome, balance due).',
      'Scheduled Messages: Set messages to send at a future date/time — useful for pre-appointment reminders.',
    ],
  },
  {
    id: 'reports',
    title: 'Reports',
    items: [
      'Select Date Range: Use the date picker at the top to define the reporting period.',
      'Production: View total charges posted, broken down by procedure type.',
      'Collections: Track payments received vs. production to see collection rate.',
      'Accounts Receivable: See outstanding balances by aging bucket (30/60/90+ days).',
      'Productivity: Compare provider production, chair utilization, and appointment volume.',
    ],
  },
  {
    id: 'insights-tools',
    title: 'Insights & Tools',
    items: [
      'Denial Analysis: AI reviews denial patterns and suggests coding or documentation improvements.',
      'Timeline Predictions: Get AI-estimated treatment completion dates based on current progress.',
      'Referral Letters: Generate professional referral letters pre-filled with patient and treatment details.',
      'Note Summarization: Summarize lengthy clinical histories into concise overviews for transfers or consultations.',
    ],
  },
  {
    id: 'team-management',
    title: 'Team Management',
    items: [
      'Invite Staff: Go to Team settings, click "Invite", enter their email and assign a role.',
      'Assign Roles: Choose from Owner, Doctor, Office Manager, Dental Assistant, Front Desk, or Bookkeeper.',
      'Role Visibility: Each role sees only the sidebar sections relevant to their responsibilities.',
    ],
  },
  {
    id: 'patient-portal',
    title: 'Patient Portal',
    items: [
      'Patients access the portal at /portal to view upcoming appointments and treatment status.',
      'Digital Forms: Patients fill out intake and consent forms online before their visit.',
      'Messaging: Patients can send secure messages to the office (responded to from the Communications page).',
    ],
  },
]

export default function Help() {
  const [search, setSearch] = useState('')

  const filteredSections = useMemo(() => {
    if (!search.trim()) return SECTIONS
    const term = search.toLowerCase()
    return SECTIONS.filter(
      section =>
        section.title.toLowerCase().includes(term) ||
        section.items.some(item => item.toLowerCase().includes(term))
    )
  }, [search])

  return (
    <div className="max-w-3xl mx-auto">
      {/* Search */}
      <div className="relative mb-8">
        <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search help topics..."
          className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl text-sm bg-white focus:ring-2 focus:ring-teal-500/20 focus:border-teal-300 transition-colors"
        />
      </div>

      {/* Sections */}
      <div className="space-y-8">
        {filteredSections.length === 0 && (
          <p className="text-center text-gray-400 py-12">No sections match "{search}"</p>
        )}
        {filteredSections.map(section => (
          <section key={section.id} id={section.id} className="scroll-mt-20">
            <h2 className="text-lg font-semibold text-gray-900 mb-3 pb-2 border-b border-gray-100">
              {section.title}
            </h2>
            <ul className="space-y-2">
              {section.items.map((item, i) => (
                <li key={i} className="flex gap-2 text-sm text-gray-700 leading-relaxed">
                  <span className="text-teal-500 mt-1 flex-shrink-0">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  )
}
