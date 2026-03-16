import { useState } from 'react';
import { Mic, MicOff, Volume2 } from 'lucide-react';
import { useVoiceControl } from '../hooks/useVoiceControl';

const VoiceControlButton = () => {
  const { isListening, isSupported, transcript, toggleListening } = useVoiceControl();
  const [showTranscript, setShowTranscript] = useState(true);

  if (!isSupported) {
    return null; // Don't show button if voice control isn't supported
  }

  return (
    <>
      {/* Floating Voice Control Button - Positioned above keyboard shortcuts */}
      <div className="fixed bottom-44 right-6 z-50 flex flex-col items-end gap-3">
        {/* Transcript Display */}
        {isListening && transcript && showTranscript && (
          <div className="bg-white/95 backdrop-blur-sm border-2 border-teal-500 rounded-2xl shadow-2xl px-6 py-4 max-w-sm animate-slide-up">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <Volume2 className="w-4 h-4 text-teal-600 animate-pulse" />
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Listening...
                  </span>
                </div>
                <p className="text-sm text-gray-800 font-medium leading-relaxed">
                  "{transcript}"
                </p>
              </div>
              <button
                onClick={() => setShowTranscript(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
                aria-label="Hide transcript"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        )}

        {/* Voice Control Button */}
        <button
          onClick={toggleListening}
          className={`group relative w-16 h-16 rounded-full shadow-2xl transition-all duration-300 transform hover:scale-110 active:scale-95 ${
            isListening
              ? 'bg-gradient-to-br from-red-500 to-pink-600 animate-pulse-slow'
              : 'bg-gradient-to-br from-teal-500 to-cyan-600 hover:from-teal-600 hover:to-cyan-700'
          }`}
          aria-label={isListening ? 'Stop voice control' : 'Start voice control'}
          title={isListening ? 'Click to stop voice control' : 'Click to start voice control'}
        >
          {/* Ripple effect when listening */}
          {isListening && (
            <>
              <span className="absolute inset-0 rounded-full bg-red-400 opacity-75 animate-ping"></span>
              <span className="absolute inset-0 rounded-full bg-red-400 opacity-50 animate-pulse"></span>
            </>
          )}

          {/* Icon */}
          <div className="relative z-10 flex items-center justify-center w-full h-full">
            {isListening ? (
              <MicOff className="w-7 h-7 text-white drop-shadow-lg" />
            ) : (
              <Mic className="w-7 h-7 text-white drop-shadow-lg" />
            )}
          </div>

          {/* Tooltip */}
          <div className="absolute bottom-full right-0 mb-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none">
            <div className="bg-gray-900 text-white text-xs font-medium px-3 py-2 rounded-lg shadow-lg whitespace-nowrap">
              {isListening ? 'Stop Voice Control' : 'Start Voice Control'}
              <div className="absolute top-full right-4 w-0 h-0 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent border-t-gray-900"></div>
            </div>
          </div>
        </button>

        {/* Status indicator */}
        {isListening && (
          <div className="absolute -top-1 -right-1 w-5 h-5 bg-green-400 border-2 border-white rounded-full animate-pulse shadow-lg"></div>
        )}
      </div>

      {/* Keyboard shortcut hint - show once on first load */}
      <style>{`
        @keyframes slide-up {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        @keyframes pulse-slow {
          0%, 100% {
            transform: scale(1);
          }
          50% {
            transform: scale(1.05);
          }
        }
        
        .animate-slide-up {
          animation: slide-up 0.3s ease-out;
        }
        
        .animate-pulse-slow {
          animation: pulse-slow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
      `}</style>
    </>
  );
};

export default VoiceControlButton;
