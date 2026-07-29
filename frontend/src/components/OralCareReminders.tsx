import { Sparkles, Droplets, Clock, Apple, ShieldCheck } from 'lucide-react'

interface CareReminder {
  icon: typeof Sparkles
  title: string
  description: string
  frequency: string
  color: string
  bgColor: string
}

const CARE_REMINDERS: CareReminder[] = [
  {
    icon: Sparkles,
    title: 'Brush After Meals',
    description: 'Brush for 2 minutes after every meal. Use a soft-bristle brush and angle at 45° to the gum line. With braces, food gets trapped — brushing prevents cavities and white spots.',
    frequency: 'After every meal',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
  },
  {
    icon: Droplets,
    title: 'Floss Daily',
    description: 'Use a floss threader or orthodontic flosser to clean between brackets. Water flossers (Waterpik) are great for braces — they reach spots regular floss can\'t.',
    frequency: 'Once daily before bed',
    color: 'text-teal-600',
    bgColor: 'bg-teal-50',
  },
  {
    icon: Clock,
    title: 'Teeth Cleaning Every 6 Months',
    description: 'Schedule a professional cleaning with your general dentist every 6 months (or every 4 months during ortho treatment). This prevents tartar buildup that your toothbrush can\'t remove.',
    frequency: 'Every 4-6 months',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
  },
  {
    icon: Apple,
    title: 'Watch What You Eat',
    description: 'Avoid hard, sticky, and crunchy foods that can break brackets: no ice chewing, caramel, popcorn kernels, or hard candy. Cut apples and carrots into small pieces.',
    frequency: 'Every meal',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
  },
  {
    icon: ShieldCheck,
    title: 'Wear Your Elastics',
    description: 'If prescribed, wear rubber bands exactly as instructed — typically 22 hours/day. Remove only to eat and brush. Consistent wear moves treatment faster; skipping adds months.',
    frequency: 'As prescribed (22 hr/day)',
    color: 'text-rose-600',
    bgColor: 'bg-rose-50',
  },
]

interface OralCareRemindersProps {
  treatmentPhase?: string
}

export default function OralCareReminders({ treatmentPhase }: OralCareRemindersProps) {
  // Show elastics reminder only for active/finishing phases
  const reminders = CARE_REMINDERS.filter(r => {
    if (r.title === 'Wear Your Elastics') {
      return treatmentPhase === 'active' || treatmentPhase === 'finishing'
    }
    return true
  })

  return (
    <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
      <div className="px-4 sm:px-5 py-3.5 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-teal-500 to-blue-500 flex items-center justify-center">
            <Sparkles size={14} className="text-white" />
          </div>
          <div>
            <h3 className="font-medium text-gray-800 text-sm">Oral Care Tips</h3>
            <p className="text-[10px] text-gray-400">Recommendations for your best smile</p>
          </div>
        </div>
      </div>
      <div className="divide-y divide-gray-50">
        {reminders.map((reminder) => {
          const Icon = reminder.icon
          return (
            <div key={reminder.title} className="px-4 sm:px-5 py-3.5 hover:bg-gray-50/50 transition-colors">
              <div className="flex items-start gap-3">
                <div className={`w-9 h-9 rounded-lg ${reminder.bgColor} flex items-center justify-center flex-shrink-0 mt-0.5`}>
                  <Icon size={16} className={reminder.color} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <h4 className="text-sm font-medium text-gray-800">{reminder.title}</h4>
                    <span className="text-[10px] text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full whitespace-nowrap flex-shrink-0">
                      {reminder.frequency}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1 leading-relaxed">{reminder.description}</p>
                </div>
              </div>
            </div>
          )
        })}
      </div>
      <div className="px-4 sm:px-5 py-3 bg-gradient-to-r from-teal-50 to-blue-50 border-t border-gray-100">
        <p className="text-[10px] text-gray-500 text-center">
          💡 Tip: Ask your general dentist about fluoride treatments during cleanings — they help prevent white spots around brackets.
        </p>
      </div>
    </div>
  )
}
