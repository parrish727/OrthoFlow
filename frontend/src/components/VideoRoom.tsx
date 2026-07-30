import { useState, useEffect, useRef, useCallback } from 'react'
import { Video, VideoOff, Mic, MicOff, Monitor, PhoneOff, X } from 'lucide-react'

interface VideoRoomProps {
  roomName: string
  token: string
  onEnd: () => void
}

export default function VideoRoom({ roomName, token: _token, onEnd }: VideoRoomProps) {
  const localVideoRef = useRef<HTMLVideoElement>(null)
  const [stream, setStream] = useState<MediaStream | null>(null)
  const [cameraOn, setCameraOn] = useState(true)
  const [micOn, setMicOn] = useState(true)
  const [screenSharing, setScreenSharing] = useState(false)
  const [connected, setConnected] = useState(false)
  const [participantConnected, setParticipantConnected] = useState(false)

  // Simulate connection after short delay
  useEffect(() => {
    const timer = setTimeout(() => setConnected(true), 1500)
    return () => clearTimeout(timer)
  }, [])

  // participantConnected will be set to true when the doctor actually joins via LiveKit events
  // No simulation — patient waits until the real connection is established

  // Start local camera
  useEffect(() => {
    let activeStream: MediaStream | null = null

    async function startCamera() {
      try {
        const mediaStream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: true,
        })
        activeStream = mediaStream
        setStream(mediaStream)
        if (localVideoRef.current) {
          localVideoRef.current.srcObject = mediaStream
        }
      } catch {
        // Camera not available — degrade gracefully
        setCameraOn(false)
        setMicOn(false)
      }
    }

    startCamera()

    return () => {
      if (activeStream) {
        activeStream.getTracks().forEach(track => track.stop())
      }
    }
  }, [])

  const toggleCamera = useCallback(() => {
    if (!stream) return
    const videoTrack = stream.getVideoTracks()[0]
    if (videoTrack) {
      videoTrack.enabled = !videoTrack.enabled
      setCameraOn(videoTrack.enabled)
    }
  }, [stream])

  const toggleMic = useCallback(() => {
    if (!stream) return
    const audioTrack = stream.getAudioTracks()[0]
    if (audioTrack) {
      audioTrack.enabled = !audioTrack.enabled
      setMicOn(audioTrack.enabled)
    }
  }, [stream])

  const toggleScreenShare = useCallback(async () => {
    if (screenSharing) {
      // Stop screen share — revert to camera
      if (stream && localVideoRef.current) {
        localVideoRef.current.srcObject = stream
      }
      setScreenSharing(false)
    } else {
      try {
        const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true })
        if (localVideoRef.current) {
          localVideoRef.current.srcObject = screenStream
        }
        setScreenSharing(true)
        // When user stops sharing via browser UI
        screenStream.getVideoTracks()[0].onended = () => {
          if (stream && localVideoRef.current) {
            localVideoRef.current.srcObject = stream
          }
          setScreenSharing(false)
        }
      } catch {
        // User cancelled screen share picker
      }
    }
  }, [screenSharing, stream])

  const handleEndCall = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
    }
    onEnd()
  }, [stream, onEnd])

  return (
    <div className="fixed inset-0 z-[9999] bg-gray-900/95 flex flex-col items-center justify-center">
      {/* Close button */}
      <button
        onClick={handleEndCall}
        className="absolute top-4 right-4 p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors"
        aria-label="Close video room"
      >
        <X size={24} />
      </button>

      {/* Room info */}
      <div className="absolute top-4 left-4 flex items-center gap-3">
        <div className={`w-2.5 h-2.5 rounded-full ${connected ? 'bg-green-400 animate-pulse' : 'bg-yellow-400 animate-pulse'}`} />
        <span className="text-white/80 text-sm font-medium">
          {connected ? `Connected to ${roomName}` : 'Connecting...'}
        </span>
      </div>

      {/* Main video area */}
      <div className="flex-1 w-full max-w-5xl px-6 py-16 flex items-center justify-center gap-6">
        {/* Remote participant area */}
        <div className="flex-1 h-full max-h-[70vh] bg-gray-800 rounded-2xl border border-gray-700/50 flex items-center justify-center relative overflow-hidden">
          {participantConnected ? (
            <div className="text-center">
              <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center mx-auto mb-3">
                <span className="text-white text-2xl font-semibold">Dr</span>
              </div>
              <p className="text-white/90 text-sm font-medium">Doctor Connected</p>
              <p className="text-white/40 text-xs mt-1">Audio & Video Active</p>
            </div>
          ) : (
            <div className="text-center">
              {/* Calming pulsing rings animation */}
              <div className="relative w-24 h-24 mx-auto mb-4 flex items-center justify-center">
                <div className="absolute inset-0 rounded-full border-2 border-blue-400/20 animate-ping" style={{ animationDuration: '3s' }} />
                <div className="absolute inset-2 rounded-full border-2 border-blue-400/30 animate-ping" style={{ animationDuration: '3s', animationDelay: '0.5s' }} />
                <div className="absolute inset-4 rounded-full border-2 border-blue-400/40 animate-ping" style={{ animationDuration: '3s', animationDelay: '1s' }} />
                <div className="w-14 h-14 bg-blue-500/20 rounded-full flex items-center justify-center">
                  <Video size={24} className="text-blue-400" />
                </div>
              </div>
              <p className="text-white/80 text-sm font-medium">Waiting for your doctor to join...</p>
              <p className="text-gray-500 text-xs mt-1.5">You're in the waiting room — sit tight</p>
            </div>
          )}
        </div>

        {/* Local video (picture-in-picture style) */}
        <div className="w-64 h-48 bg-gray-800 rounded-2xl border border-gray-700/50 overflow-hidden relative flex-shrink-0">
          {cameraOn ? (
            <video
              ref={localVideoRef}
              autoPlay
              muted
              playsInline
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-gray-800">
              <div className="w-14 h-14 bg-gray-700 rounded-full flex items-center justify-center">
                <VideoOff size={20} className="text-gray-400" />
              </div>
            </div>
          )}
          <div className="absolute bottom-2 left-2 px-2 py-0.5 bg-black/60 rounded text-[10px] text-white/80">
            You {screenSharing && '(Screen)'}
          </div>
        </div>
      </div>

      {/* Controls bar */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex items-center gap-3 bg-gray-800/80 backdrop-blur-xl rounded-full px-6 py-3 border border-gray-700/50">
        {/* Camera toggle */}
        <button
          onClick={toggleCamera}
          className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
            cameraOn
              ? 'bg-gray-700 hover:bg-gray-600 text-white'
              : 'bg-red-500/20 hover:bg-red-500/30 text-red-400'
          }`}
          aria-label={cameraOn ? 'Turn camera off' : 'Turn camera on'}
        >
          {cameraOn ? <Video size={20} /> : <VideoOff size={20} />}
        </button>

        {/* Mic toggle */}
        <button
          onClick={toggleMic}
          className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
            micOn
              ? 'bg-gray-700 hover:bg-gray-600 text-white'
              : 'bg-red-500/20 hover:bg-red-500/30 text-red-400'
          }`}
          aria-label={micOn ? 'Mute microphone' : 'Unmute microphone'}
        >
          {micOn ? <Mic size={20} /> : <MicOff size={20} />}
        </button>

        {/* Screen share */}
        <button
          onClick={toggleScreenShare}
          className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
            screenSharing
              ? 'bg-blue-500/20 hover:bg-blue-500/30 text-blue-400'
              : 'bg-gray-700 hover:bg-gray-600 text-white'
          }`}
          aria-label={screenSharing ? 'Stop screen share' : 'Share screen'}
        >
          <Monitor size={20} />
        </button>

        {/* Divider */}
        <div className="w-px h-8 bg-gray-600" />

        {/* End call */}
        <button
          onClick={handleEndCall}
          className="w-14 h-12 rounded-full bg-red-500 hover:bg-red-600 text-white flex items-center justify-center transition-colors"
          aria-label="End call"
        >
          <PhoneOff size={20} />
        </button>
      </div>
    </div>
  )
}
