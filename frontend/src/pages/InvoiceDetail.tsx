import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, CheckCircle, XCircle, HelpCircle, FileText, Download, Eye } from 'lucide-react'
import { api } from '../lib/api'
import Tooltip from '../components/Tooltip'

interface InvoiceDetail {
  id: string
  vendor_name: string
  invoice_number: string | null
  invoice_date: string | null
  due_date: string | null
  total_amount: number
  status: string
  confidence_score: number | null
  coded_json: string | null
  created_at: string
}

interface LineItem {
  description: string
  quantity: number | null
  unit_price: number | null
  total: number
  category: string
}

export default function InvoiceDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [invoice, setInvoice] = useState<InvoiceDetail | null>(null)
  const [lineItems, setLineItems] = useState<LineItem[]>([])
  const [acting, setActing] = useState(false)

  useEffect(() => {
    if (!id) return
    api.getInvoice(id).then(async res => {
      if (res.ok) {
        const data = await res.json()
        setInvoice(data)
        if (data.coded_json) {
          try {
            const coded = JSON.parse(data.coded_json)
            setLineItems(coded.line_items || [])
          } catch { /* ignore */ }
        }
      }
    })
  }, [id])

  async function handleAction(action: 'approve' | 'reject') {
    if (!id) return
    setActing(true)
    const res = action === 'approve' ? await api.approveInvoice(id) : await api.rejectInvoice(id)
    if (res.ok) {
      const data = await res.json()
      setInvoice(prev => prev ? { ...prev, status: data.status } : null)
    }
    setActing(false)
  }

  if (!invoice) {
    return <div className="min-h-screen flex items-center justify-center bg-[#f5f5f7] text-gray-400 text-sm">Loading...</div>
  }

  const canAct = ['coded', 'review'].includes(invoice.status)

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-4">
          <button onClick={() => navigate('/')} className="w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded-lg flex items-center justify-center transition-colors">
            <ArrowLeft size={16} className="text-gray-600" />
          </button>
          <div>
            <h1 className="text-base font-semibold text-gray-900">{invoice.vendor_name}</h1>
            <p className="text-xs text-gray-500">Invoice {invoice.invoice_number || '—'}</p>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/* Summary */}
        <div className="bg-white rounded-2xl border border-gray-200/80 p-6 shadow-sm mb-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <div className="flex items-center gap-1.5 mb-1">
                <p className="text-xs text-gray-500">Amount Due</p>
                <Tooltip content="Total amount on this invoice"><HelpCircle size={11} className="text-gray-300" /></Tooltip>
              </div>
              <p className="text-2xl font-semibold text-gray-900">${invoice.total_amount.toLocaleString()}</p>
            </div>
            <div>
              <div className="flex items-center gap-1.5 mb-1">
                <p className="text-xs text-gray-500">Status</p>
                <Tooltip content="Current stage in the approval workflow"><HelpCircle size={11} className="text-gray-300" /></Tooltip>
              </div>
              <p className="text-lg font-medium capitalize text-gray-800">{invoice.status}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Invoice Date</p>
              <p className="text-lg font-medium text-gray-800">{invoice.invoice_date ? new Date(invoice.invoice_date).toLocaleDateString() : '—'}</p>
            </div>
            <div>
              <div className="flex items-center gap-1.5 mb-1">
                <p className="text-xs text-gray-500">AI Confidence</p>
                <Tooltip content="How confident the AI is in its classification. Above 90% is high confidence."><HelpCircle size={11} className="text-gray-300" /></Tooltip>
              </div>
              <p className="text-lg font-medium text-gray-800">
                {invoice.confidence_score ? `${Math.round(invoice.confidence_score * 100)}%` : '—'}
              </p>
            </div>
          </div>
        </div>

        {/* Original Document */}
        <div className="bg-white rounded-2xl border border-gray-200/80 p-6 shadow-sm mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                <FileText size={18} className="text-gray-500" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-800">Original Document</p>
                <p className="text-xs text-gray-400">Uploaded invoice file</p>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={async () => {
                  const res = await fetch(`https://api.orthoflowsolutions.com/api/v1/invoices/${id}/document`, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } })
                  if (res.ok) { const data = await res.json(); window.open(data.url, '_blank') }
                }}
                className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg border border-blue-200 transition-colors"
              >
                <Eye size={14} /> View
              </button>
              <button
                onClick={async () => {
                  const res = await fetch(`https://api.orthoflowsolutions.com/api/v1/invoices/${id}/document`, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } })
                  if (res.ok) { const data = await res.json(); const a = document.createElement('a'); a.href = data.url; a.download = data.filename; a.click() }
                }}
                className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium text-gray-600 bg-gray-50 hover:bg-gray-100 rounded-lg border border-gray-200 transition-colors"
              >
                <Download size={14} /> Download
              </button>
            </div>
          </div>
        </div>

        {/* Line Items */}
        {lineItems.length > 0 && (
          <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden mb-6">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
              <h2 className="font-medium text-gray-800 text-sm">Line Items</h2>
              <Tooltip content="These items were automatically extracted and classified by AI. Review for accuracy before approving.">
                <HelpCircle size={13} className="text-gray-400 cursor-help" />
              </Tooltip>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50/50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500">Description</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500">
                      <div className="flex items-center gap-1">
                        Category
                        <Tooltip content="AI-assigned expense category (supplies, lab, equipment, etc.)"><HelpCircle size={10} className="text-gray-300" /></Tooltip>
                      </div>
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500">Qty</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500">Unit Price</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {lineItems.map((item, i) => (
                    <tr key={i} className="hover:bg-gray-50/50 transition-colors">
                      <td className="px-6 py-3.5 text-sm text-gray-800">{item.description}</td>
                      <td className="px-6 py-3.5">
                        <span className="inline-block px-2.5 py-1 bg-blue-50 text-blue-700 text-xs rounded-full font-medium capitalize">
                          {item.category}
                        </span>
                      </td>
                      <td className="px-6 py-3.5 text-sm text-gray-600 text-right">{item.quantity || '—'}</td>
                      <td className="px-6 py-3.5 text-sm text-gray-600 text-right">{item.unit_price ? `$${item.unit_price}` : '—'}</td>
                      <td className="px-6 py-3.5 text-sm font-medium text-gray-800 text-right">${item.total.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Actions */}
        {canAct && (
          <div className="bg-white rounded-2xl border border-gray-200/80 p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <h3 className="font-medium text-gray-800 text-sm">Take Action</h3>
              <Tooltip content="Approve to sync this invoice to QuickBooks, or reject to discard it.">
                <HelpCircle size={13} className="text-gray-400 cursor-help" />
              </Tooltip>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => handleAction('approve')}
                disabled={acting}
                className="flex items-center gap-2 px-6 py-3 bg-emerald-500 hover:bg-emerald-600 text-white font-medium rounded-xl transition-colors disabled:opacity-50 text-sm shadow-sm"
              >
                <CheckCircle size={16} /> Approve & Sync
              </button>
              <button
                onClick={() => handleAction('reject')}
                disabled={acting}
                className="flex items-center gap-2 px-6 py-3 bg-white hover:bg-gray-50 text-red-600 font-medium rounded-xl transition-colors disabled:opacity-50 text-sm border border-gray-200"
              >
                <XCircle size={16} /> Reject
              </button>
            </div>
          </div>
        )}

        {invoice.status === 'approved' && (
          <div className="flex items-center gap-3 p-5 bg-emerald-50 border border-emerald-200 rounded-2xl">
            <CheckCircle className="text-emerald-600 flex-shrink-0" size={20} />
            <div>
              <p className="text-emerald-800 font-medium text-sm">Invoice Approved</p>
              <p className="text-emerald-600 text-xs mt-0.5">This invoice will sync to QuickBooks automatically.</p>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
