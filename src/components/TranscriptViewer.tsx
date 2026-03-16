import React, { useEffect, useState } from 'react';
import { toast } from 'react-hot-toast';

interface TranscriptWord {
  text: string;
  start: number;
  end: number;
  is_filler: boolean;
  is_repeated: boolean;
}

interface TranscriptData {
  text: string;
  words: TranscriptWord[];
  filler_count: number;
  repeated_count: number;
  total_words: number;
  duration: number;
}

interface TranscriptViewerProps {
  videoId: string;
  onSeek?: (time: number) => void;
  onRemoveFillers?: () => void;
}

const TranscriptViewer: React.FC<TranscriptViewerProps> = ({ videoId, onSeek, onRemoveFillers }) => {
  const [transcript, setTranscript] = useState<TranscriptData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTranscript();
  }, [videoId]);

  // Auto-refresh transcript periodically when it has 0 words (processing may update it)
  useEffect(() => {
    if (transcript && transcript.total_words === 0) {
      const timer = setInterval(() => {
        console.log('[TRANSCRIPT] Auto-refreshing (0 words detected)...');
        fetchTranscript();
      }, 8000);
      return () => clearInterval(timer);
    }
  }, [transcript]);

  const fetchTranscript = async () => {
    try {
      setLoading(true);
      setError(null);

      const token = localStorage.getItem('token');
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5001';
      const response = await fetch(
        `${apiUrl}/videos/${videoId}/transcript`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'ngrok-skip-browser-warning': 'true',
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        const contentType = response.headers.get('content-type');
        if (response.status === 404) {
          setError('Transcript not yet generated. Please wait...');
          setTimeout(fetchTranscript, 5000);
          return;
        }
        // Check if response is HTML (error page)
        if (contentType && contentType.includes('text/html')) {
          throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }
        throw new Error('Failed to load transcript');
      }

      const data = await response.json();
      setTranscript(data);
      console.log('[TRANSCRIPT] Loaded:', data);
    } catch (err: any) {
      console.error('[TRANSCRIPT] Error:', err);
      setError(err.message || 'Failed to load transcript');
    } finally {
      setLoading(false);
    }
  };

  const handleWordClick = (word: TranscriptWord) => {
    if (onSeek) {
      onSeek(word.start);
      console.log(`[TRANSCRIPT] Seeking to ${word.start}s`);
    }
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="flex items-center justify-center space-x-2">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-purple-500"></div>
          <span className="text-gray-400">Generating transcript...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <button
            onClick={fetchTranscript}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!transcript) {
    return null;
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-semibold text-white">
          Transcript
        </h3>
        <div className="flex items-center space-x-4">
          <div className="text-sm text-gray-400">
            <span className="text-red-400 font-semibold">{transcript.filler_count}</span> fillers
            {transcript.repeated_count > 0 && (
              <>
                {' · '}
                <span className="text-orange-400 font-semibold">{transcript.repeated_count}</span> repeated
              </>
            )}
            {' · '}
            <span className="text-gray-300">{transcript.total_words}</span> total words
          </div>
          {onRemoveFillers && (transcript.filler_count > 0 || transcript.repeated_count > 0) && (
            <button
              onClick={onRemoveFillers}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center space-x-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              <span>Remove {transcript.filler_count + transcript.repeated_count} Fillers</span>
            </button>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center space-x-4 mb-4 text-xs">
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-red-500 rounded"></div>
          <span className="text-gray-400">Filler Word</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-orange-500 rounded"></div>
          <span className="text-gray-400">Repeated Word</span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="w-3 h-3 bg-gray-600 rounded"></div>
          <span className="text-gray-400">Normal Word</span>
        </div>
      </div>

      {/* Transcript with clickable words */}
      <div className="bg-gray-900 rounded-lg p-4 max-h-96 overflow-y-auto">
        <div className="text-base leading-relaxed">
          {transcript.words.map((word, index) => {
            let bgColor = 'bg-transparent';
            let textColor = 'text-gray-200';
            let hoverColor = 'hover:bg-gray-700';
            
            if (word.is_filler) {
              bgColor = 'bg-red-500 bg-opacity-20';
              textColor = 'text-red-300';
              hoverColor = 'hover:bg-red-500 hover:bg-opacity-30';
            } else if (word.is_repeated) {
              bgColor = 'bg-orange-500 bg-opacity-20';
              textColor = 'text-orange-300';
              hoverColor = 'hover:bg-orange-500 hover:bg-opacity-30';
            }

            return (
              <span
                key={index}
                onClick={() => handleWordClick(word)}
                className={`${bgColor} ${textColor} ${hoverColor} px-1 py-0.5 rounded cursor-pointer transition-all inline-block mr-1 mb-1`}
                title={`${formatTime(word.start)} - ${formatTime(word.end)}${word.is_filler ? ' (Filler)' : ''}${word.is_repeated ? ' (Repeated)' : ''}`}
              >
                {word.text}
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default TranscriptViewer;
