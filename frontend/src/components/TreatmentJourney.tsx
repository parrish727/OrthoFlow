import { motion } from 'framer-motion'
import { CheckCircle2, Circle, ArrowRight, Sparkles } from 'lucide-react'

interface TreatmentJourneyProps {
  currentPhase: string
  phaseOrder: number
  totalPhases: number
  completedAppointments: number
  totalAppointments: number
}

const PHASES = [
  { key: 'consultation', label: 'Consultation' },
  { key: 'records', label: 'Records' },
  { key: 'bonding', label: 'Bonding' },
  { key: 'active', label: 'Active Treatment' },
  { key: 'finishing', label: 'Finishing' },
  { key: 'retention', label: 'Retention' },
  { key: 'complete', label: 'Complete' },
] as const

type PhaseStatus = 'completed' | 'current' | 'future'

function getPhaseStatus(phaseIndex: number, currentOrder: number): PhaseStatus {
  const phasePosition = phaseIndex + 1
  if (phasePosition < currentOrder) return 'completed'
  if (phasePosition === currentOrder) return 'current'
  return 'future'
}

function PhaseNode({
  label,
  status,
  index,
}: {
  label: string
  status: PhaseStatus
  index: number
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.6 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: index * 0.12, duration: 0.4, ease: 'easeOut' }}
      className="flex flex-col items-center gap-1.5 md:gap-2"
    >
      {/* Circle indicator */}
      <div className="relative">
        {status === 'completed' && (
          <CheckCircle2 className="h-8 w-8 text-teal-500 fill-teal-500" />
        )}
        {status === 'current' && (
          <div className="relative flex items-center justify-center">
            <motion.div
              animate={{ scale: [1, 1.3, 1] }}
              transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
              className="absolute h-10 w-10 rounded-full bg-blue-400/20"
            />
            <div className="h-10 w-10 rounded-full bg-gradient-to-br from-blue-500 to-teal-500 flex items-center justify-center shadow-lg shadow-blue-500/30">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
          </div>
        )}
        {status === 'future' && (
          <Circle className="h-8 w-8 text-gray-300" />
        )}
      </div>

      {/* Phase label */}
      <span
        className={`text-xs font-medium text-center leading-tight max-w-[80px] ${
          status === 'completed'
            ? 'text-teal-600'
            : status === 'current'
              ? 'text-blue-600 font-semibold'
              : 'text-gray-400'
        }`}
      >
        {label}
      </span>
    </motion.div>
  )
}

function Connector({ status }: { status: PhaseStatus }) {
  const isCompleted = status === 'completed'

  return (
    <div className="flex items-center flex-1 min-w-[16px] md:min-w-[24px]">
      <div
        className={`h-0.5 w-full ${
          isCompleted
            ? 'bg-teal-400'
            : 'border-t-2 border-dashed border-gray-300'
        }`}
      />
    </div>
  )
}

function VerticalConnector({ status }: { status: PhaseStatus }) {
  const isCompleted = status === 'completed'

  return (
    <div className="flex justify-center py-1">
      <div
        className={`w-0.5 h-6 ${
          isCompleted
            ? 'bg-teal-400'
            : 'border-l-2 border-dashed border-gray-300'
        }`}
      />
    </div>
  )
}

function VerticalPhaseNode({
  label,
  status,
  index,
}: {
  label: string
  status: PhaseStatus
  index: number
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.12, duration: 0.4, ease: 'easeOut' }}
      className="flex items-center gap-3"
    >
      {/* Circle indicator */}
      <div className="relative flex-shrink-0">
        {status === 'completed' && (
          <CheckCircle2 className="h-7 w-7 text-teal-500 fill-teal-500" />
        )}
        {status === 'current' && (
          <div className="relative flex items-center justify-center">
            <motion.div
              animate={{ scale: [1, 1.3, 1] }}
              transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
              className="absolute h-9 w-9 rounded-full bg-blue-400/20"
            />
            <div className="h-9 w-9 rounded-full bg-gradient-to-br from-blue-500 to-teal-500 flex items-center justify-center shadow-lg shadow-blue-500/30">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
          </div>
        )}
        {status === 'future' && (
          <Circle className="h-7 w-7 text-gray-300" />
        )}
      </div>

      {/* Phase label */}
      <span
        className={`text-sm font-medium ${
          status === 'completed'
            ? 'text-teal-600'
            : status === 'current'
              ? 'text-blue-600 font-semibold text-base'
              : 'text-gray-400'
        }`}
      >
        {label}
      </span>
    </motion.div>
  )
}

export default function TreatmentJourney({
  currentPhase,
  phaseOrder,
  totalPhases,
  completedAppointments,
  totalAppointments,
}: TreatmentJourneyProps) {
  const progressPercent = Math.round(((phaseOrder - 1) / (totalPhases - 1)) * 100)
  const currentLabel =
    PHASES.find((p) => p.key === currentPhase)?.label ?? currentPhase

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="w-full space-y-6"
    >
      {/* Desktop horizontal stepper */}
      <div className="hidden md:flex items-center justify-between px-4">
        {PHASES.map((phase, i) => {
          const status = getPhaseStatus(i, phaseOrder)
          return (
            <div key={phase.key} className="flex items-center flex-1 last:flex-none">
              <PhaseNode label={phase.label} status={status} index={i} />
              {i < PHASES.length - 1 && (
                <Connector status={getPhaseStatus(i, phaseOrder)} />
              )}
            </div>
          )
        })}
      </div>

      {/* Mobile vertical stepper */}
      <div className="md:hidden flex flex-col px-2">
        {PHASES.map((phase, i) => {
          const status = getPhaseStatus(i, phaseOrder)
          return (
            <div key={phase.key}>
              <VerticalPhaseNode label={phase.label} status={status} index={i} />
              {i < PHASES.length - 1 && (
                <VerticalConnector status={getPhaseStatus(i, phaseOrder)} />
              )}
            </div>
          )
        })}
      </div>

      {/* Current phase details card */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8, duration: 0.4 }}
        className="bg-gradient-to-br from-blue-50 to-teal-50 border border-blue-100 rounded-2xl p-5 shadow-sm"
      >
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="h-5 w-5 text-blue-500" />
          <h3 className="text-sm font-semibold text-gray-700">
            You are here: {currentLabel}
          </h3>
        </div>

        {/* Progress bar */}
        <div className="mb-3">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>Treatment Progress</span>
            <span>{progressPercent}%</span>
          </div>
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${progressPercent}%` }}
              transition={{ delay: 1, duration: 0.8, ease: 'easeOut' }}
              className="h-full bg-gradient-to-r from-teal-400 to-blue-500 rounded-full"
            />
          </div>
        </div>

        {/* Appointment count and next steps */}
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">
            Appointments: {completedAppointments} / {totalAppointments} completed
          </span>
          <div className="flex items-center gap-1 text-blue-600 font-medium">
            <span>Phase {phaseOrder} of {totalPhases}</span>
            <ArrowRight className="h-4 w-4" />
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}
