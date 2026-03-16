import React, { useEffect, useState } from 'react';
import { ProcessingProgress, subscribeToVideoProgress } from '../services/websocket';
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react';

interface VideoProcessingProgressProps {
  videoId: string;
  onComplete?: () => void;
  onError?: (error: string) => void;
}

const stepLabels: Record<string, string> = {
  started: '🚀 Starting',
  cutting_silence: '✂️ Removing Silence',
  enhancing_audio: '🎵 Enhancing Audio',
  generating_thumbnail: '🖼️ Creating Thumbnail',
  generating_subtitles: '📝 Generating Subtitles',
  summarizing: '📄 Creating Summary',
  enhancing_video: '✨ Enhancing Video',
  completed: '✅ Complete',
  failed: '❌ Failed',
};

export const VideoProcessingProgress: React.FC<VideoProcessingProgressProps> = ({
  videoId,
  onComplete,
  onError,
}) => {
  const [progress, setProgress] = useState<ProcessingProgress | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [hasFailed, setHasFailed] = useState(false);

  useEffect(() => {
    console.log('Setting up WebSocket for video:', videoId);

    const cleanup = subscribeToVideoProgress(
      videoId,
      // On progress update
      (data) => {
        setProgress(data);
      },
      // On completion
      (data) => {
        setProgress(data);
        setIsComplete(true);
        if (onComplete) {
          setTimeout(() => onComplete(), 1000);
        }
      },
      // On error
      (data) => {
        setProgress(data);
        setHasFailed(true);
        if (onError) {
          onError(data.message);
        }
      }
    );

    return cleanup;
  }, [videoId, onComplete, onError]);

  if (!progress) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-8 h-8 animate-spin text-purple-600" />
        <span className="ml-3 text-gray-600">Initializing...</span>
      </div>
    );
  }

  const progressPercentage = Math.min(100, Math.max(0, progress.progress));

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-800 flex items-center">
          {hasFailed ? (
            <XCircle className="w-6 h-6 text-red-500 mr-2" />
          ) : isComplete ? (
            <CheckCircle2 className="w-6 h-6 text-green-500 mr-2" />
          ) : (
            <Loader2 className="w-6 h-6 animate-spin text-purple-600 mr-2" />
          )}
          Video Processing {isComplete ? 'Complete' : hasFailed ? 'Failed' : 'in Progress'}
        </h3>
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">{progress.message}</span>
          <span className="text-sm font-bold text-purple-600">{progressPercentage}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              hasFailed
                ? 'bg-red-500'
                : isComplete
                ? 'bg-green-500'
                : 'bg-gradient-to-r from-purple-500 to-pink-500'
            }`}
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
      </div>

      {/* Current Step Indicator */}
      <div className="space-y-2">
        <div className="flex flex-wrap gap-2">
          {Object.entries(stepLabels).map(([key, label]) => {
            const isCurrent = progress.step === key;
            const isPast = Object.keys(stepLabels).indexOf(key) < Object.keys(stepLabels).indexOf(progress.step);
            
            return (
              <div
                key={key}
                className={`
                  px-3 py-1 rounded-full text-xs font-medium transition-all
                  ${isCurrent ? 'bg-purple-600 text-white scale-110' : ''}
                  ${isPast ? 'bg-green-100 text-green-700' : ''}
                  ${!isCurrent && !isPast ? 'bg-gray-100 text-gray-500' : ''}
                `}
              >
                {label}
              </div>
            );
          })}
        </div>
      </div>

      {/* Status Message */}
      {isComplete && (
        <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-green-800 text-sm">
            ✨ Your video has been processed successfully! All enhancements have been applied.
          </p>
        </div>
      )}

      {hasFailed && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800 text-sm">
            ⚠️ {progress.message}
          </p>
        </div>
      )}

      {/* Timestamp */}
      <div className="mt-3 text-xs text-gray-400 text-right">
        Last updated: {new Date(progress.timestamp).toLocaleTimeString()}
      </div>
    </div>
  );
};

export default VideoProcessingProgress;
