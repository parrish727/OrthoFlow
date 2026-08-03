import { useState, useEffect, useRef, useCallback } from 'react'
import { Video, VideoOff, Mic, MicOff, Monitor, PhoneOff, X, User } from 'lucide-react'
import {
  Room,
  RoomEvent,
  Track,
  RemoteParticipant,
  RemoteTrack,
  RemoteTrackPublication,
  LocalTrack,
  createLocalTracks,
  ConnectionState,
} from 'livekit-client'

interface VideoRoomProps {
  roomName: string
  token: string
  onEnd: () => void
  role?: 'staff' | 'patient'
  patientName?: string
  visitId?: string
}

const LIVEKIT_URL = import.meta.env.VITE_LIVEKIT_URL || 'wss://livekit.orthoflowsolutions.com'

export default function VideoRoom({ roomName, token, onEnd, role = 'staff', patientName, visitId }: VideoRoomProps) {
  const localVideoRef = useRef<HTMLVideoElement>(null)
  const remoteVideoRef = useRef<HTMLVideoElement>(null)
  const remoteAudioRef = useRef<HTMLAudioElement>(null)
  const roomRef = useRef<Room | null>(null)
  const localTracksRef = useRef<LocalTrack[]>([])

  const [cameraOn, setCameraOn] = useState(true)
  const [micOn, setMicOn] = useState(true)
  const [screenSharing, setScreenSharing] = useState(false)
  const [connectionState, setConnectionState] = useState<ConnectionState>(ConnectionState.Disconnected)
  const [participantConnected, setParticipantConnected] = useState(false)
  const [participantName, setParticipantName] = useState('')
  const [remoteVideoEnabled, setRemoteVideoEnabled] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [visitEnded, setVisitEnded] = useState(false)
  const [endingVisit, setEndingVisit] = useState(false)

  // Connect to LiveKit room
  useEffect(() => {
    const room = new Room({
      adaptiveStream: true,
      dynacast: true,
    })
    roomRef.current = room

    // Track connection state
    room.on(RoomEvent.ConnectionStateChanged, (state: ConnectionState) => {
      setConnectionState(state)
    })

    // Handle remote participant joining
    room.on(RoomEvent.ParticipantConnected, (participant: RemoteParticipant) => {
      setParticipantConnected(true)
      setParticipantName(participant.identity || '')
    })

    // Handle remote participant leaving
    room.on(RoomEvent.ParticipantDisconnected, () => {
      setParticipantConnected(false)
      setParticipantName('')
      setRemoteVideoEnabled(false)
      if (remoteVideoRef.current) {
        remoteVideoRef.current.srcObject = null
      }
    })

    // Handle remote track subscribed
    room.on(
      RoomEvent.TrackSubscribed,
      (track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant) => {
        setParticipantConnected(true)
        setParticipantName(participant.identity || '')

        if (track.kind === Track.Kind.Video) {
          setRemoteVideoEnabled(true)
          const element = track.attach()
          if (remoteVideoRef.current) {
            // Replace existing content
            remoteVideoRef.current.srcObject = null
            remoteVideoRef.current.parentElement?.querySelectorAll('video[data-lk-remote]').forEach(el => el.remove())
            element.setAttribute('data-lk-remote', 'true')
            element.className = 'w-full h-full object-cover'
            remoteVideoRef.current.parentElement?.appendChild(element)
          }
        } else if (track.kind === Track.Kind.Audio) {
          const element = track.attach()
          element.setAttribute('data-lk-remote-audio', 'true')
          document.body.appendChild(element)
        }
      }
    )

    // Handle remote track unsubscribed
    room.on(
      RoomEvent.TrackUnsubscribed,
      (track: RemoteTrack) => {
        track.detach().forEach(el => el.remove())
        if (track.kind === Track.Kind.Video) {
          setRemoteVideoEnabled(false)
        }
      }
    )

    // Handle track muted/unmuted
    room.on(RoomEvent.TrackMuted, (publication: RemoteTrackPublication) => {
      if (publication.kind === Track.Kind.Video) {
        setRemoteVideoEnabled(false)
      }
    })

    room.on(RoomEvent.TrackUnmuted, (publication: RemoteTrackPublication) => {
      if (publication.kind === Track.Kind.Video) {
        setRemoteVideoEnabled(true)
      }
    })

    // Handle room disconnection (e.g., staff ended the visit and room was deleted)
    room.on(RoomEvent.Disconnected, () => {
      setVisitEnded(true)
      // Auto-close after a brief message
      setTimeout(() => onEnd(), 3000)
    })

    // Connect
    async function connect() {
      try {
        // Create local tracks first
        const tracks = await createLocalTracks({
          audio: true,
          video: true,
        })
        localTracksRef.current = tracks

        // Attach local video to preview
        const videoTrack = tracks.find(t => t.kind === Track.Kind.Video)
        if (videoTrack && localVideoRef.current) {
          const el = videoTrack.attach(localVideoRef.current)
          el.style.transform = 'scaleX(-1)' // Mirror local video
        }

        // Connect to room and publish tracks
        await room.connect(LIVEKIT_URL, token)
        await Promise.all(tracks.map(track => room.localParticipant.publishTrack(track)))

        // Check if remote participant already in room
        room.remoteParticipants.forEach((participant: RemoteParticipant) => {
          setParticipantConnected(true)
          setParticipantName(participant.identity || '')
          // Subscribe to existing tracks
          participant.trackPublications.forEach(publication => {
            if (publication.track && publication.isSubscribed) {
              const track = publication.track as RemoteTrack
              if (track.kind === Track.Kind.Video) {
                setRemoteVideoEnabled(true)
                const element = track.attach()
                element.setAttribute('data-lk-remote', 'true')
                element.className = 'w-full h-full object-cover'
                remoteVideoRef.current?.parentElement?.appendChild(element)
              } else if (track.kind === Track.Kind.Audio) {
                const element = track.attach()
                element.setAttribute('data-lk-remote-audio', 'true')
                document.body.appendChild(element)
              }
            }
          })
        })
      } catch (err) {
        console.error('Failed to connect to video room:', err)
        setError(err instanceof Error ? err.message : 'Failed to connect to video room')
        // Fallback: still show local camera preview
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true })
          if (localVideoRef.current) {
            localVideoRef.current.srcObject = stream
          }
        } catch {
          setCameraOn(false)
          setMicOn(false)
        }
      }
    }

    connect()

    return () => {
      // Cleanup
      localTracksRef.current.forEach(track => {
        track.stop()
        track.detach()
      })
      room.disconnect()
      // Remove any attached remote audio elements
      document.querySelectorAll('[data-lk-remote-audio]').forEach(el => el.remove())
    }
  }, [token])

  const toggleCamera = useCallback(async () => {
    const room = roomRef.current
    if (!room || room.state !== ConnectionState.Connected) {
      // Fallback for local-only mode
      const videoTrack = localTracksRef.current.find(t => t.kind === Track.Kind.Video)
      if (videoTrack) {
        if (cameraOn) {
          videoTrack.stop()
        } else {
          await videoTrack.restartTrack()
        }
        setCameraOn(!cameraOn)
      }
      return
    }

    const publication = room.localParticipant.getTrackPublication(Track.Source.Camera)
    if (publication?.track) {
      if (cameraOn) {
        await room.localParticipant.setCameraEnabled(false)
      } else {
        await room.localParticipant.setCameraEnabled(true)
      }
      setCameraOn(!cameraOn)
    }
  }, [cameraOn])

  const toggleMic = useCallback(async () => {
    const room = roomRef.current
    if (!room || room.state !== ConnectionState.Connected) {
      const audioTrack = localTracksRef.current.find(t => t.kind === Track.Kind.Audio)
      if (audioTrack) {
        if (micOn) {
          audioTrack.stop()
        } else {
          await audioTrack.restartTrack()
        }
        setMicOn(!micOn)
      }
      return
    }

    if (micOn) {
      await room.localParticipant.setMicrophoneEnabled(false)
    } else {
      await room.localParticipant.setMicrophoneEnabled(true)
    }
    setMicOn(!micOn)
  }, [micOn])

  const toggleScreenShare = useCallback(async () => {
    const room = roomRef.current
    if (!room || room.state !== ConnectionState.Connected) return

    if (screenSharing) {
      await room.localParticipant.setScreenShareEnabled(false)
      setScreenSharing(false)
    } else {
      try {
        await room.localParticipant.setScreenShareEnabled(true)
        setScreenSharing(true)
      } catch {
        // User cancelled screen share picker
      }
    }
  }, [screenSharing])

  const handleEndCall = useCallback(async () => {
    // For staff: formally end the visit via backend (deletes LiveKit room, notifies patient)
    if (role === 'staff' && visitId) {
      setEndingVisit(true)
      try {
        const token = localStorage.getItem('token')
        const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
        await fetch(`${baseUrl}/api/v1/virtual-visits/${visitId}/end`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        })
      } catch {
        // Best-effort — still disconnect locally
      }
      setEndingVisit(false)
    }

    const room = roomRef.current
    if (room) {
      localTracksRef.current.forEach(track => {
        track.stop()
        track.detach()
      })
      await room.disconnect()
    }
    // Remove remote audio elements
    document.querySelectorAll('[data-lk-remote-audio]').forEach(el => el.remove())
    onEnd()
  }, [onEnd, role, visitId])

  // Role-specific content
  const isStaff = role === 'staff'
  const waitingLabel = isStaff
    ? `Waiting for ${patientName || 'patient'} to join...`
    : 'Waiting for your doctor to join...'
  const waitingSubLabel = isStaff
    ? 'The patient has been notified. They\'ll appear here when they enter the waiting room.'
    : 'You\'re in the waiting room — sit tight'
  const connectedLabel = isStaff
    ? `${participantName || patientName || 'Patient'} Connected`
    : `${participantName || 'Doctor'} Connected`
  const connectedInitial = isStaff ? (participantName?.[0] || patientName?.[0] || 'P') : 'Dr'
  const connectedGradient = isStaff
    ? 'from-teal-500 to-teal-600'
    : 'from-blue-500 to-blue-600'
  const selfLabel = isStaff ? 'You (Provider)' : 'You'
  const roomStatus = isStaff ? 'Virtual Visit Room Open' : `Connected to ${roomName}`
  const isConnected = connectionState === ConnectionState.Connected

  return (
    <div className="fixed inset-0 z-[9999] bg-gray-900/95 flex flex-col items-center justify-center">
      {/* Close button */}
      <button
        onClick={handleEndCall}
        className="absolute top-4 right-4 p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors"
        aria-label="End visit"
      >
        <X size={24} />
      </button>

      {/* Room info */}
      <div className="absolute top-4 left-4 flex items-center gap-3">
        <div className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-green-400 animate-pulse' : connectionState === ConnectionState.Connecting ? 'bg-yellow-400 animate-pulse' : 'bg-red-400'}`} />
        <span className="text-white/80 text-sm font-medium">
          {isConnected ? roomStatus : connectionState === ConnectionState.Connecting ? 'Connecting...' : error ? 'Connection failed' : 'Connecting...'}
        </span>
        {isStaff && isConnected && !participantConnected && (
          <span className="ml-2 px-2 py-0.5 bg-amber-500/20 text-amber-300 text-xs rounded-full font-medium">
            Patient notified
          </span>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div className="absolute top-14 left-4 right-4 max-w-md mx-auto px-4 py-2 bg-red-500/20 border border-red-500/30 rounded-lg text-red-300 text-xs text-center">
          {error} — Showing local camera preview
        </div>
      )}

      {/* Main video area */}
      <div className="flex-1 w-full max-w-5xl px-6 py-16 flex items-center justify-center gap-6">
        {/* Remote participant area */}
        <div className="flex-1 h-full max-h-[70vh] bg-gray-800 rounded-2xl border border-gray-700/50 flex items-center justify-center relative overflow-hidden">
          {/* Hidden ref for remote video attachment */}
          <video ref={remoteVideoRef} className="hidden" />
          <audio ref={remoteAudioRef} className="hidden" />

          {participantConnected && remoteVideoEnabled ? (
            // Remote video is rendered via attached elements
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="absolute bottom-3 left-3 px-2 py-1 bg-black/60 rounded text-xs text-white/90">
                {connectedLabel}
              </div>
            </div>
          ) : participantConnected ? (
            <div className="text-center">
              <div className={`w-20 h-20 bg-gradient-to-br ${connectedGradient} rounded-full flex items-center justify-center mx-auto mb-3`}>
                <span className="text-white text-2xl font-semibold">{connectedInitial}</span>
              </div>
              <p className="text-white/90 text-sm font-medium">{connectedLabel}</p>
              <p className="text-white/40 text-xs mt-1">Camera off — Audio connected</p>
            </div>
          ) : (
            <div className="text-center">
              {/* Waiting animation */}
              <div className="relative w-24 h-24 mx-auto mb-4 flex items-center justify-center">
                <div className="absolute inset-0 rounded-full border-2 border-teal-400/20 animate-ping" style={{ animationDuration: '3s' }} />
                <div className="absolute inset-2 rounded-full border-2 border-teal-400/30 animate-ping" style={{ animationDuration: '3s', animationDelay: '0.5s' }} />
                <div className="absolute inset-4 rounded-full border-2 border-teal-400/40 animate-ping" style={{ animationDuration: '3s', animationDelay: '1s' }} />
                <div className={`w-14 h-14 ${isStaff ? 'bg-teal-500/20' : 'bg-blue-500/20'} rounded-full flex items-center justify-center`}>
                  {isStaff ? <User size={24} className="text-teal-400" /> : <Video size={24} className="text-blue-400" />}
                </div>
              </div>
              <p className="text-white/80 text-sm font-medium">{waitingLabel}</p>
              <p className="text-gray-500 text-xs mt-1.5">{waitingSubLabel}</p>
            </div>
          )}
        </div>

        {/* Local video (picture-in-picture) */}
        <div className="w-64 h-48 bg-gray-800 rounded-2xl border border-gray-700/50 overflow-hidden relative flex-shrink-0">
          {cameraOn ? (
            <video
              ref={localVideoRef}
              autoPlay
              muted
              playsInline
              className="w-full h-full object-cover"
              style={{ transform: 'scaleX(-1)' }}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-gray-800">
              <div className="w-14 h-14 bg-gray-700 rounded-full flex items-center justify-center">
                <VideoOff size={20} className="text-gray-400" />
              </div>
            </div>
          )}
          <div className="absolute bottom-2 left-2 px-2 py-0.5 bg-black/60 rounded text-[10px] text-white/80">
            {selfLabel} {screenSharing && '(Screen)'}
          </div>
        </div>
      </div>

      {/* Controls bar */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex items-center gap-3 bg-gray-800/80 backdrop-blur-xl rounded-full px-6 py-3 border border-gray-700/50">
        <button
          onClick={toggleCamera}
          className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
            cameraOn ? 'bg-gray-700 hover:bg-gray-600 text-white' : 'bg-red-500/20 hover:bg-red-500/30 text-red-400'
          }`}
          aria-label={cameraOn ? 'Turn camera off' : 'Turn camera on'}
        >
          {cameraOn ? <Video size={20} /> : <VideoOff size={20} />}
        </button>

        <button
          onClick={toggleMic}
          className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
            micOn ? 'bg-gray-700 hover:bg-gray-600 text-white' : 'bg-red-500/20 hover:bg-red-500/30 text-red-400'
          }`}
          aria-label={micOn ? 'Mute microphone' : 'Unmute microphone'}
        >
          {micOn ? <Mic size={20} /> : <MicOff size={20} />}
        </button>

        <button
          onClick={toggleScreenShare}
          className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
            screenSharing ? 'bg-blue-500/20 hover:bg-blue-500/30 text-blue-400' : 'bg-gray-700 hover:bg-gray-600 text-white'
          }`}
          aria-label={screenSharing ? 'Stop screen share' : 'Share screen'}
        >
          <Monitor size={20} />
        </button>

        <div className="w-px h-8 bg-gray-600" />

        <button
          onClick={handleEndCall}
          className="w-14 h-12 rounded-full bg-red-500 hover:bg-red-600 text-white flex items-center justify-center transition-colors"
          aria-label="End call"
        >
          <PhoneOff size={20} />
        </button>

        {/* End Visit button — staff only */}
        {role === 'staff' && visitId && (
          <button
            onClick={handleEndCall}
            disabled={endingVisit}
            className="ml-2 px-4 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-full text-xs font-semibold transition-colors disabled:opacity-50"
          >
            {endingVisit ? 'Ending...' : 'End Visit'}
          </button>
        )}
      </div>

      {/* Visit Ended Overlay (shown to patient when staff ends the visit) */}
      {visitEnded && (
        <div className="absolute inset-0 z-[10000] bg-gray-900/95 flex flex-col items-center justify-center">
          <div className="w-16 h-16 bg-teal-500/20 rounded-full flex items-center justify-center mb-4">
            <PhoneOff size={28} className="text-teal-400" />
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">Visit Ended</h2>
          <p className="text-sm text-gray-400">Your provider has ended the virtual visit. Thank you!</p>
          <p className="text-xs text-gray-500 mt-4">Closing automatically...</p>
        </div>
      )}
    </div>
  )
}
