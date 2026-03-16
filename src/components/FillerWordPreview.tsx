import { useState, useEffect } from 'react';
import { AlertCircle, Eye, EyeOff, RefreshCw, Download, X } from 'lucide-react';
import { ApiService } from '../services/api';
import toast from 'react-hot-toast';

interface FillerWord {
  word: string;
  start: number;
  end: number;
  type: 'filler' | 'repeated' | 'phrase';
  confidence?: number;
}

interface FillerWordPreviewProps {
  videoId: string;
  detectionLevel?: 'conservative' | 'medium' | 'aggressive';
  detectRepeated?: boolean;
  onClose?: () => void;
}

const FillerWordPreview = ({ 
  videoId, 
  detectionLevel = 'medium',
  detectRepeated = true,
  onClose 
}: FillerWordPreviewProps) => {
  const [fillerWords, setFillerWords] = useState<FillerWord[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [transcript, setTranscript] = useState<string>('');
  const [showOnlyFillers, setShowOnlyFillers] = useState(false);
  const [totalDuration, setTotalDuration] = useState(0);
  const [timeSaved, setTimeSaved] = useState(0);

  useEffect(() => {
    detectFillerWords();
  }, [videoId, detectionLevel, detectRepeated]);

  const detectFillerWords = async () => {
    try {
      setIsLoading(true);
      console.log('[FILLER PREVIEW] Starting detection for video:', videoId);
      console.log('[FILLER PREVIEW] Detection level:', detectionLevel);
      console.log('[FILLER PREVIEW] Detect repeated:', detectRepeated);
      
      // Call backend API to detect filler words
      const response = await ApiService.detectFillerWords(videoId, {
        detection_level: detectionLevel,
        detect_repeated: detectRepeated
      });
      
      console.log('[FILLER PREVIEW] Response received:', response);
      console.log('[FILLER PREVIEW] Filler words count:', response.filler_words?.length || 0);
      
      setFillerWords(response.filler_words || []);
      setTranscript(response.transcript || '');
      setTotalDuration(response.total_duration || 0);
      
      // Calculate time saved
      const totalFillerTime = (response.filler_words || []).reduce(
        (sum: number, fw: FillerWord) => sum + (fw.end - fw.start), 
        0
      );
      setTimeSaved(totalFillerTime);
      
      if (!response.filler_words || response.filler_words.length === 0) {
        toast.success('No filler words detected in this video!');
      } else {
        toast.success(`Detected ${response.filler_words.length} filler words`);
      }
      
    } catch (error: any) {
      console.error('[FILLER PREVIEW] Error:', error);
      console.error('[FILLER PREVIEW] Error details:', error.response?.data || error.message);
      toast.error(error.response?.data?.error || 'Failed to detect filler words. Check console for details.');
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);
    return `${mins}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
  };

  const getFillerTypeColor = (type: string) => {
    switch (type) {
      case 'filler': return 'bg-red-100 text-red-700 border-red-300';
      case 'repeated': return 'bg-orange-100 text-orange-700 border-orange-300';
      case 'phrase': return 'bg-yellow-100 text-yellow-700 border-yellow-300';
      default: return 'bg-gray-100 text-gray-700 border-gray-300';
    }
  };

  const getFillerTypeIcon = (type: string) => {
    switch (type) {
      case 'filler': return '🗣️';
      case 'repeated': return '🔁';
      case 'phrase': return '💬';
      default: return '⚠️';
    }
  };

  const downloadFillerReport = () => {
    const report = {
      video_id: videoId,
      detection_level: detectionLevel,
      total_fillers: fillerWords.length,
      time_saved: timeSaved,
      percentage_saved: ((timeSaved / totalDuration) * 100).toFixed(2),
      filler_words: fillerWords.map(fw => ({
        word: fw.word,
        type: fw.type,
        timestamp: `${formatTime(fw.start)} - ${formatTime(fw.end)}`,
        duration: `${((fw.end - fw.start) * 1000).toFixed(0)}ms`
      }))
    };
    
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `filler-words-report-${videoId}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Filler word report downloaded');
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold flex items-center gap-2">
                <AlertCircle className="h-6 w-6" />
                Filler Word Preview
              </h2>
              <p className="text-purple-100 text-sm mt-1">
                AI-detected filler words and repeated words in your video
              </p>
            </div>
            {onClose && (
              <button
                onClick={onClose}
                className="p-2 hover:bg-white/20 rounded-lg transition-colors"
              >
                <X className="h-6 w-6" />
              </button>
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="bg-gradient-to-r from-gray-50 to-purple-50 p-4 border-b border-gray-200">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl p-3 shadow-sm">
              <div className="text-2xl font-bold text-red-600">
                {fillerWords.filter(fw => fw.type === 'filler').length}
              </div>
              <div className="text-xs text-gray-600">Filler Words</div>
            </div>
            <div className="bg-white rounded-xl p-3 shadow-sm">
              <div className="text-2xl font-bold text-orange-600">
                {fillerWords.filter(fw => fw.type === 'repeated').length}
              </div>
              <div className="text-xs text-gray-600">Repeated Words</div>
            </div>
            <div className="bg-white rounded-xl p-3 shadow-sm">
              <div className="text-2xl font-bold text-green-600">
                {timeSaved.toFixed(1)}s
              </div>
              <div className="text-xs text-gray-600">Time Saved</div>
            </div>
            <div className="bg-white rounded-xl p-3 shadow-sm">
              <div className="text-2xl font-bold text-blue-600">
                {((timeSaved / totalDuration) * 100).toFixed(1)}%
              </div>
              <div className="text-xs text-gray-600">Reduction</div>
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="p-4 bg-gray-50 border-b border-gray-200 flex flex-wrap gap-2">
          <button
            onClick={() => setShowOnlyFillers(!showOnlyFillers)}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium"
          >
            {showOnlyFillers ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
            {showOnlyFillers ? 'Show All' : 'Show Only Fillers'}
          </button>
          <button
            onClick={detectFillerWords}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm font-medium disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={downloadFillerReport}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm font-medium"
          >
            <Download className="h-4 w-4" />
            Download Report
          </button>
        </div>

        {/* Filler Words List */}
        <div className="flex-1 overflow-y-auto p-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <RefreshCw className="h-12 w-12 text-purple-600 animate-spin mx-auto mb-4" />
                <p className="text-gray-600 font-medium">Detecting filler words...</p>
                <p className="text-sm text-gray-500 mt-1">Using Whisper AI for accurate detection</p>
              </div>
            </div>
          ) : fillerWords.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="text-6xl mb-4">🎉</div>
                <p className="text-gray-600 font-medium">No filler words detected!</p>
                <p className="text-sm text-gray-500 mt-1">Your audio is clean and fluent</p>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              {fillerWords.map((fw, index) => (
                <div
                  key={index}
                  className={`flex items-center justify-between p-3 rounded-lg border-2 ${getFillerTypeColor(fw.type)} transition-all hover:scale-[1.02]`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{getFillerTypeIcon(fw.type)}</span>
                    <div>
                      <div className="font-bold text-lg">"{fw.word}"</div>
                      <div className="text-xs opacity-75">
                        {formatTime(fw.start)} → {formatTime(fw.end)} ({((fw.end - fw.start) * 1000).toFixed(0)}ms)
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs font-semibold uppercase opacity-75">{fw.type}</div>
                    {fw.confidence && (
                      <div className="text-xs opacity-60">{(fw.confidence * 100).toFixed(0)}% confidence</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-gray-50 p-4 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">
              Detection Level: <span className="font-semibold text-purple-600">{detectionLevel}</span>
              {detectRepeated && <span className="ml-2">| Repeated words: ✓</span>}
            </div>
            <div className="text-sm font-medium text-gray-700">
              Total: {fillerWords.length} items to remove
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FillerWordPreview;
