import { useRef } from 'react'

interface FormField {
  name: string
  label: string
  type: 'text' | 'textarea' | 'date' | 'tel' | 'email' | 'select' | 'checkbox' | 'checkbox_group' | 'yes_no' | 'signature' | 'section_header' | 'paragraph'
  required?: boolean
  options?: string[]
  placeholder?: string
  content?: string
}

interface FormFieldRendererProps {
  fields: FormField[]
  values: Record<string, string>
  onChange: (name: string, value: string) => void
  errors?: Record<string, string>
}

const inputBase = 'w-full px-4 py-2.5 min-h-[44px] bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-300 transition-colors'

function FieldLabel({ label, required }: { label: string; required?: boolean }) {
  return (
    <label className="block text-xs font-medium text-gray-700 mb-1.5">
      {label}
      {required && <span className="text-red-500 ml-0.5">*</span>}
    </label>
  )
}

function FieldError({ error }: { error?: string }) {
  if (!error) return null
  return <p className="text-xs text-red-500 mt-1">{error}</p>
}

function renderTextField(field: FormField, value: string, onChange: (name: string, value: string) => void, error?: string) {
  return (
    <div>
      <FieldLabel label={field.label} required={field.required} />
      <input
        type="text"
        name={field.name}
        value={value}
        onChange={e => onChange(field.name, e.target.value)}
        placeholder={field.placeholder}
        className={`${inputBase} ${error ? 'border-red-300 focus:ring-red-500/20 focus:border-red-300' : ''}`}
        aria-required={field.required}
        aria-invalid={!!error}
      />
      <FieldError error={error} />
    </div>
  )
}

function renderTextareaField(field: FormField, value: string, onChange: (name: string, value: string) => void, error?: string) {
  return (
    <div>
      <FieldLabel label={field.label} required={field.required} />
      <textarea
        name={field.name}
        value={value}
        onChange={e => onChange(field.name, e.target.value)}
        placeholder={field.placeholder}
        rows={4}
        className={`${inputBase} resize-none ${error ? 'border-red-300 focus:ring-red-500/20 focus:border-red-300' : ''}`}
        aria-required={field.required}
        aria-invalid={!!error}
      />
      <FieldError error={error} />
    </div>
  )
}

function renderDateField(field: FormField, value: string, onChange: (name: string, value: string) => void, error?: string) {
  return (
    <div>
      <FieldLabel label={field.label} required={field.required} />
      <input
        type="date"
        name={field.name}
        value={value}
        onChange={e => onChange(field.name, e.target.value)}
        className={`${inputBase} ${error ? 'border-red-300 focus:ring-red-500/20 focus:border-red-300' : ''}`}
        aria-required={field.required}
        aria-invalid={!!error}
      />
      <FieldError error={error} />
    </div>
  )
}

function renderTelField(field: FormField, value: string, onChange: (name: string, value: string) => void, error?: string) {
  return (
    <div>
      <FieldLabel label={field.label} required={field.required} />
      <input
        type="tel"
        name={field.name}
        value={value}
        onChange={e => onChange(field.name, e.target.value)}
        placeholder={field.placeholder || '(555) 123-4567'}
        className={`${inputBase} ${error ? 'border-red-300 focus:ring-red-500/20 focus:border-red-300' : ''}`}
        aria-required={field.required}
        aria-invalid={!!error}
      />
      <FieldError error={error} />
    </div>
  )
}

function renderEmailField(field: FormField, value: string, onChange: (name: string, value: string) => void, error?: string) {
  return (
    <div>
      <FieldLabel label={field.label} required={field.required} />
      <input
        type="email"
        name={field.name}
        value={value}
        onChange={e => onChange(field.name, e.target.value)}
        placeholder={field.placeholder || 'email@example.com'}
        className={`${inputBase} ${error ? 'border-red-300 focus:ring-red-500/20 focus:border-red-300' : ''}`}
        aria-required={field.required}
        aria-invalid={!!error}
      />
      <FieldError error={error} />
    </div>
  )
}

function renderSelectField(field: FormField, value: string, onChange: (name: string, value: string) => void, error?: string) {
  return (
    <div>
      <FieldLabel label={field.label} required={field.required} />
      <select
        name={field.name}
        value={value}
        onChange={e => onChange(field.name, e.target.value)}
        className={`${inputBase} appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2220%22%20height%3D%2220%22%20fill%3D%22none%22%20stroke%3D%22%236b7280%22%20stroke-width%3D%222%22%3E%3Cpath%20d%3D%22m6%208%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')] bg-[length:20px] bg-[right_12px_center] bg-no-repeat pr-10 ${error ? 'border-red-300 focus:ring-red-500/20 focus:border-red-300' : ''}`}
        aria-required={field.required}
        aria-invalid={!!error}
      >
        <option value="">{field.placeholder || 'Select an option'}</option>
        {field.options?.map(opt => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
      <FieldError error={error} />
    </div>
  )
}

function renderCheckboxField(field: FormField, value: string, onChange: (name: string, value: string) => void, error?: string) {
  const checked = value === 'true'
  return (
    <div>
      <label className="flex items-center gap-3 min-h-[44px] cursor-pointer group">
        <input
          type="checkbox"
          name={field.name}
          checked={checked}
          onChange={e => onChange(field.name, e.target.checked ? 'true' : '')}
          className="w-5 h-5 rounded-md border-gray-300 text-teal-600 focus:ring-teal-500/20 focus:ring-2 cursor-pointer"
          aria-required={field.required}
          aria-invalid={!!error}
        />
        <span className="text-sm text-gray-700 group-hover:text-gray-900">
          {field.label}
          {field.required && <span className="text-red-500 ml-0.5">*</span>}
        </span>
      </label>
      <FieldError error={error} />
    </div>
  )
}

function renderCheckboxGroupField(field: FormField, value: string, onChange: (name: string, value: string) => void, error?: string) {
  const selected = value ? value.split(',').map(v => v.trim()) : []

  function toggleOption(option: string) {
    const updated = selected.includes(option)
      ? selected.filter(s => s !== option)
      : [...selected, option]
    onChange(field.name, updated.join(', '))
  }

  return (
    <div>
      <FieldLabel label={field.label} required={field.required} />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-1" role="group" aria-label={field.label}>
        {field.options?.map(opt => (
          <label key={opt} className="flex items-center gap-3 min-h-[44px] px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl cursor-pointer hover:bg-gray-100 transition-colors">
            <input
              type="checkbox"
              checked={selected.includes(opt)}
              onChange={() => toggleOption(opt)}
              className="w-5 h-5 rounded-md border-gray-300 text-teal-600 focus:ring-teal-500/20 focus:ring-2 cursor-pointer"
            />
            <span className="text-sm text-gray-700">{opt}</span>
          </label>
        ))}
      </div>
      <FieldError error={error} />
    </div>
  )
}

function renderYesNoField(field: FormField, value: string, onChange: (name: string, value: string) => void, error?: string) {
  return (
    <div>
      <FieldLabel label={field.label} required={field.required} />
      <div className="flex items-center gap-4 mt-1" role="radiogroup" aria-label={field.label}>
        <label className="flex items-center gap-2 min-h-[44px] cursor-pointer group">
          <span
            className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors ${
              value === 'yes' ? 'border-teal-600 bg-teal-600' : 'border-gray-300 group-hover:border-gray-400'
            }`}
            aria-hidden="true"
          >
            {value === 'yes' && <span className="w-2 h-2 bg-white rounded-full" />}
          </span>
          <input
            type="radio"
            name={field.name}
            value="yes"
            checked={value === 'yes'}
            onChange={() => onChange(field.name, 'yes')}
            className="sr-only"
            aria-required={field.required}
          />
          <span className="text-sm text-gray-700 font-medium">Yes</span>
        </label>
        <label className="flex items-center gap-2 min-h-[44px] cursor-pointer group">
          <span
            className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors ${
              value === 'no' ? 'border-teal-600 bg-teal-600' : 'border-gray-300 group-hover:border-gray-400'
            }`}
            aria-hidden="true"
          >
            {value === 'no' && <span className="w-2 h-2 bg-white rounded-full" />}
          </span>
          <input
            type="radio"
            name={field.name}
            value="no"
            checked={value === 'no'}
            onChange={() => onChange(field.name, 'no')}
            className="sr-only"
          />
          <span className="text-sm text-gray-700 font-medium">No</span>
        </label>
      </div>
      <FieldError error={error} />
    </div>
  )
}

function renderSignatureField(field: FormField, value: string, onChange: (name: string, value: string) => void, error?: string) {
  return (
    <div>
      <FieldLabel label={field.label} required={field.required} />
      <p className="text-xs text-gray-500 mb-2">
        By typing your name below, you acknowledge that this constitutes a legal electronic signature.
      </p>
      <input
        type="text"
        name={field.name}
        value={value}
        onChange={e => onChange(field.name, e.target.value)}
        placeholder="Type your full name as signature"
        className={`${inputBase} font-['Georgia',_'Times_New_Roman',_serif] italic text-base border-b-2 border-t-0 border-l-0 border-r-0 rounded-none bg-transparent px-0 focus:ring-0 focus:border-teal-500 ${error ? 'border-red-300' : 'border-gray-400'}`}
        aria-required={field.required}
        aria-invalid={!!error}
      />
      <FieldError error={error} />
    </div>
  )
}

function renderSectionHeader(field: FormField) {
  return (
    <div className="pt-4 pb-1 border-b border-gray-200">
      <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wide">{field.label}</h3>
    </div>
  )
}

function renderParagraph(field: FormField) {
  return (
    <div className="py-2">
      <p className="text-xs text-gray-500 leading-relaxed whitespace-pre-wrap">
        {field.content || field.label}
      </p>
    </div>
  )
}

export default function FormFieldRenderer({ fields, values, onChange, errors }: FormFieldRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  function renderField(field: FormField) {
    const value = values[field.name] || ''
    const error = errors?.[field.name]

    switch (field.type) {
      case 'text':
        return renderTextField(field, value, onChange, error)
      case 'textarea':
        return renderTextareaField(field, value, onChange, error)
      case 'date':
        return renderDateField(field, value, onChange, error)
      case 'tel':
        return renderTelField(field, value, onChange, error)
      case 'email':
        return renderEmailField(field, value, onChange, error)
      case 'select':
        return renderSelectField(field, value, onChange, error)
      case 'checkbox':
        return renderCheckboxField(field, value, onChange, error)
      case 'checkbox_group':
        return renderCheckboxGroupField(field, value, onChange, error)
      case 'yes_no':
        return renderYesNoField(field, value, onChange, error)
      case 'signature':
        return renderSignatureField(field, value, onChange, error)
      case 'section_header':
        return renderSectionHeader(field)
      case 'paragraph':
        return renderParagraph(field)
      default:
        return null
    }
  }

  return (
    <div ref={containerRef} className="space-y-4">
      {fields.map(field => (
        <div key={field.name} data-field={field.name}>
          {renderField(field)}
        </div>
      ))}
    </div>
  )
}

export type { FormField, FormFieldRendererProps }
