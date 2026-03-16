import { useState, useRef, useEffect } from 'react';
import { Play, Pause, Volume2, VolumeX, Maximize, Settings, Captions as ClosedCaptioning } from 'lucide-react';
import { ApiService } from '../services/api';

interface SubtitleData {
  id: number;
  start: number;
  end: number;
  text: string;
  language: string;
  style: string;
}

interface VideoPlayerProps {
  videoUrl: string;
  videoId?: string;
  subtitles?: SubtitleData[];
  onTimeUpdate?: (currentTime: number) => void;
}

const VideoPlayer = ({ videoUrl, videoId, subtitles, onTimeUpdate }: VideoPlayerProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [showControls, setShowControls] = useState(true);
  const [showSubtitles, setShowSubtitles] = useState(true);
  const [currentSubtitle, setCurrentSubtitle] = useState<SubtitleData | null>(null);
  const [loadedSubtitles, setLoadedSubtitles] = useState<SubtitleData[]>([]);
  const controlsTimeoutRef = useRef<NodeJS.Timeout>();

  // Load subtitles when videoId or provided subtitles change
  useEffect(() => {
    console.log('[VideoPlayer] useEffect triggered:', { videoId, subtitles: !!subtitles });
    if (videoId && !subtitles) {
      console.log('[VideoPlayer] Loading subtitles for videoId:', videoId);
      loadSubtitles();
    } else if (subtitles && Array.isArray(subtitles) && subtitles.length > 0) {
      console.log('[VideoPlayer] Using provided subtitles:', subtitles.length);
      
      // Transform provided subtitles to ensure proper format
      const formattedSubtitles = subtitles.map((segment: any, index: number) => ({
        id: segment.id || index,
        start: typeof segment.start === 'number' ? segment.start : parseFloat(segment.start) || 0,
        end: typeof segment.end === 'number' ? segment.end : parseFloat(segment.end) || 0,
        text: segment.text || '',
        language: segment.language || 'en',
        style: segment.style || 'default'
      }));
      
      console.log('[VideoPlayer] Formatted provided subtitles:', formattedSubtitles.slice(0, 3));
      setLoadedSubtitles(formattedSubtitles);
      setShowSubtitles(true); // Auto-enable subtitles when provided
    } else {
      console.log('[VideoPlayer] No videoId or subtitles provided');
      setLoadedSubtitles([]);
    }
  }, [videoId, subtitles]);

  // Update current subtitle based on time
  useEffect(() => {
    if (loadedSubtitles.length > 0 && showSubtitles) {
      const subtitle = loadedSubtitles.find(
        sub => currentTime >= sub.start && currentTime <= sub.end
      );
      
      if (subtitle !== currentSubtitle) {
        setCurrentSubtitle(subtitle || null);
        if (subtitle) {
          console.log('[VideoPlayer] 📺 Current subtitle:', {
            time: currentTime,
            start: subtitle.start,
            end: subtitle.end,
            text: subtitle.text.substring(0, 50) + '...'
          });
        }
      }
    } else {
      if (currentSubtitle) {
        setCurrentSubtitle(null);
      }
    }
  }, [currentTime, loadedSubtitles, showSubtitles]);

  const loadSubtitles = async () => {
    if (!videoId) {
      console.log('[VideoPlayer] loadSubtitles: No videoId provided');
      return;
    }
    
    try {
      console.log('[VideoPlayer] Loading subtitles for video:', videoId);
      const subtitleSegments = await ApiService.getVideoSubtitles(videoId);
      console.log('[VideoPlayer] Received subtitle segments:', subtitleSegments);
      
      if (Array.isArray(subtitleSegments) && subtitleSegments.length > 0) {
        // Transform segments to ensure proper format
        const formattedSubtitles = subtitleSegments.map((segment: any, index: number) => ({
          id: segment.id || index,
          start: typeof segment.start === 'number' ? segment.start : parseFloat(segment.start) || 0,
          end: typeof segment.end === 'number' ? segment.end : parseFloat(segment.end) || 0,
          text: segment.text || '',
          language: segment.language || 'en',
          style: segment.style || 'default'
        }));
        
        console.log('[VideoPlayer] Formatted subtitles:', formattedSubtitles.length, 'segments');
        console.log('[VideoPlayer] First 3 segments:', formattedSubtitles.slice(0, 3));
        
        setLoadedSubtitles(formattedSubtitles);
        setShowSubtitles(true); // Auto-enable subtitles when loaded
        
      } else {
        console.log('[VideoPlayer] No subtitle segments received');
        setLoadedSubtitles([]);
      }
    } catch (error) {
      console.error('[VideoPlayer] Failed to load subtitles:', error);
      setLoadedSubtitles([]);
    }
  };

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play().catch(() => {
          // Silently ignore - video may still be loading
        });
      }
      setIsPlaying(!isPlaying);
    }
  };

  const toggleMute = () => {
    if (videoRef.current) {
      videoRef.current.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (videoRef.current) {
      videoRef.current.volume = newVolume;
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      const time = videoRef.current.currentTime;
      setCurrentTime(time);
      onTimeUpdate?.(time);
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (videoRef.current) {
      videoRef.current.currentTime = time;
    }
  };

  const toggleFullscreen = () => {
    if (videoRef.current) {
      if (document.fullscreenElement) {
        document.exitFullscreen();
      } else {
        videoRef.current.requestFullscreen();
      }
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handleMouseMove = () => {
    setShowControls(true);
    if (controlsTimeoutRef.current) {
      clearTimeout(controlsTimeoutRef.current);
    }
    controlsTimeoutRef.current = setTimeout(() => {
      if (isPlaying) {
        setShowControls(false);
      }
    }, 3000);
  };

  const handleMouseLeave = () => {
    if (isPlaying) {
      setShowControls(false);
    }
  };

  return (
    <div 
      className="relative bg-black rounded-lg overflow-hidden group w-full h-full"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <video
        ref={videoRef}
        src={videoUrl}
        className="w-full h-full object-contain bg-black"
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onClick={togglePlay}
      />

      {/* Subtitles Overlay */}
      {showSubtitles && currentSubtitle && (
        <div className="absolute bottom-16 left-1/2 transform -translate-x-1/2 z-30 pointer-events-none px-4 w-full max-w-4xl">
          <div className="bg-black bg-opacity-90 text-white px-6 py-3 rounded-lg text-center shadow-lg border border-gray-600 mx-auto max-w-2xl">
            <p className="text-base md:text-lg font-medium leading-relaxed tracking-wide break-words">
              {currentSubtitle.text}
            </p>
          </div>
        </div>
      )}

      {/* Debug Subtitle Info */}
      {process.env.NODE_ENV === 'development' && (
        <div className="absolute top-4 right-4 bg-black bg-opacity-75 text-white p-3 rounded-lg text-xs max-w-xs z-50">
          <div>📺 Subtitles: {loadedSubtitles.length} loaded</div>
          <div>⏰ Time: {currentTime.toFixed(2)}s</div>
          <div>🎬 Current: {currentSubtitle ? currentSubtitle.text.substring(0, 30) + '...' : 'None'}</div>
          <div>👁️ Visible: {showSubtitles ? 'Yes' : 'No'}</div>
          {loadedSubtitles.length > 0 && !showSubtitles && (
            <div className="text-yellow-400 mt-1">⚠️ Click CC to show subtitles</div>
          )}
        </div>
      )}

      {/* Force Show Subtitles Button (Debug) */}
      {loadedSubtitles.length > 0 && process.env.NODE_ENV === 'development' && (
        <div className="absolute top-4 left-4 z-40">
          <button
            onClick={() => {
              // Force show first subtitle for testing
              setCurrentSubtitle(loadedSubtitles[0]);
              console.log('[VideoPlayer] 🧪 Force showing first subtitle:', loadedSubtitles[0]);
            }}
            className="bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded text-xs"
          >
            🧪 Test Subtitle
          </button>
        </div>
      )}

      {/* Video Controls */}
      <div 
        className={`absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black via-black/50 to-transparent p-4 transition-opacity duration-300 z-40 ${
          showControls ? 'opacity-100' : 'opacity-0'
        }`}
      >
        {/* Progress Bar */}
        <div className="mb-4">
          <input
            type="range"
            min="0"
            max={duration || 0}
            value={currentTime}
            onChange={handleSeek}
            className="w-full h-1 bg-gray-600 rounded-lg appearance-none cursor-pointer slider"
            style={{
              background: `linear-gradient(to right, #8b5cf6 0%, #8b5cf6 ${(currentTime / duration) * 100}%, #4b5563 ${(currentTime / duration) * 100}%, #4b5563 100%)`
            }}
          />
          <div className="flex justify-between text-xs text-gray-300 mt-1">
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>

        {/* Control Buttons */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            {/* Play/Pause */}
            <button
              onClick={togglePlay}
              className="text-white hover:text-purple-400 transition-colors"
            >
              {isPlaying ? <Pause size={24} /> : <Play size={24} />}
            </button>

            {/* Volume */}
            <div className="flex items-center space-x-2">
              <button
                onClick={toggleMute}
                className="text-white hover:text-purple-400 transition-colors"
              >
                {isMuted ? <VolumeX size={20} /> : <Volume2 size={20} />}
              </button>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={volume}
                onChange={handleVolumeChange}
                className="w-16 h-1 bg-gray-600 rounded-lg appearance-none cursor-pointer"
              />
            </div>

            {/* Time Display */}
            <div className="text-white text-sm">
              {formatTime(currentTime)} / {formatTime(duration)}
            </div>
          </div>

          <div className="flex items-center space-x-4">
            {/* Subtitles Toggle */}
            {loadedSubtitles.length > 0 && (
              <button
                onClick={() => setShowSubtitles(!showSubtitles)}
                className={`transition-colors flex items-center space-x-1 px-2 py-1 rounded ${
                  showSubtitles 
                    ? 'text-purple-400 bg-purple-400/20' 
                    : 'text-white hover:text-purple-400 hover:bg-white/10'
                }`}
                title={`${showSubtitles ? 'Hide' : 'Show'} Subtitles (${loadedSubtitles.length} segments)`}
              >
                <ClosedCaptioning size={20} />
                <span className="text-xs font-medium">CC</span>
              </button>
            )}

            {/* Settings */}
            <button className="text-white hover:text-purple-400 transition-colors">
              <Settings size={20} />
            </button>

            {/* Fullscreen */}
            <button
              onClick={toggleFullscreen}
              className="text-white hover:text-purple-400 transition-colors"
            >
              <Maximize size={20} />
            </button>
          </div>
        </div>
      </div>

      {/* Loading Overlay */}
      {!duration && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
        </div>
      )}
    </div>
  );
};

export default VideoPlayer;