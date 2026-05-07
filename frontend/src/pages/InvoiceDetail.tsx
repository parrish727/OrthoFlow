import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, CheckCircle, XCircle, FileText } from 'lucide-react'
import { api } from '../lib/api'

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
    return <div className="min-h-screen flex items-center justify-center text-gray-400">Loading...</div>
  }

  const canAct = ['coded', 'review'].includes(invoice.status)

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center gap-4">
          <button onClick={() => navigate('/')} className="text-gray-500 hover:text-gray-700">
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-lg font-bold text-gray-900">{invoice.vendor_name}</h1>
            <p className="text-sm text-gray-500">Invoice {invoice.invoice_number || '—'}</p>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* Summary Card */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <p className="text-sm text-gray-500">Amount</p>
              <p className="text-2xl font-bold text-gray-900">${invoice.total_amount.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Status</p>
              <p className="text-lg font-semibold capitalize">{invoice.status}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Invoice Date</p>
              <p className="text-lg font-medium">{invoice.invoice_date ? new Date(invoice.invoice_date).toLocaleDateString() : '—'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">AI Confidence</p>
              <p className="text-lg font-medium">
                {invoice.confidence_score ? `${Math.round(invoice.confidence_score * 100)}%` : '—'}
              </p>
            </div>
          </div>
        </div>

        {/* Line Items */}
        {lineItems.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mb-6">
            <div className="px-6 py-4 border-b border-gray-100">
              <h2 className="font-semibold text-gray-800">Line Items (AI Classified)</h2>
            </div>
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Qty</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Unit Price</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {lineItems.map((item, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-6 py-3 text-sm text-gray-800">{item.description}</td>
                    <td className="px-6 py-3">
                      <span className="inline-block px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded-full font-medium capitalize">
                        {item.category}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-sm text-gray-600 text-right">{item.quantity || '—'}</td>
                    <td className="px-6 py-3 text-sm text-gray-600 text-right">{item.unit_price ? `$${item.unit_price}` : '—'}</td>
                    <td className="px-6 py-3 text-sm font-medium text-gray-800 text-right">${item.total.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Actions */}
        {canAct && (
          <div className="flex gap-4">
            <button
              onClick={() => handleAction('approve')}
              disabled={acting}
              className="flex items-center gap-2 px-6 py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition-colors disabled:opacity-50"
            >
              <CheckCircle size={18} /> Approve
            </button>
            <button
              onClick={() => handleAction('reject')}
              disabled={acting}
              className="flex items-center gap-2 px-6 py-3 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-lg transition-colors disabled:opacity-50"
            >
              <XCircle size={18} /> Reject
            </button>
          </div>
        )}

        {invoice.status === 'approved' && (
          <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-xl">
            <CheckCircle className="text-green-600" size={24} />
            <p className="text-green-800 font-medium">This invoice has been approved and will sync to QuickBooks.</p>
          </div>
        )}
      </main>
    </div>
  )
}
