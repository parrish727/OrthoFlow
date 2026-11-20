import { Server } from 'lucide-react'

/** Plain-language answer to "where is our patient data?" Shown in setup and Settings. */
export default function DataLocationPanel() {
  return (
    <div data-testid="data-location-panel" className="bg-white rounded-2xl border border-gray-200/80 p-5 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 bg-teal-50 rounded-xl flex items-center justify-center flex-shrink-0">
          <Server size={18} className="text-teal-600" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-800">Where your patient data lives</h3>
          <ul className="text-xs text-gray-600 mt-2 space-y-1.5 list-disc pl-4 max-w-xl">
            <li><b>Hosted by OrthoFlow.</b> Your data is stored on Melanin Technologies Inc. local infrastructure in the United States, not in your office and not on a shared public cloud.</li>
            <li><b>Kept separate.</b> Your practice's records are isolated from every other practice, encrypted, and every access is logged.</li>
            <li><b>Yours to export.</b> Ask us for a full export at any time.</li>
            <li><b>Edge device / practice local server.</b> Nothing is installed in your office today. An optional on-site device for imaging capture is not yet available.</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
