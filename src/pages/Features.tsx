import { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Captions,
  Film,
  Wand2,
  Image as ImageIcon,
  UploadCloud,
  Video,
  Download,
  Loader2,
  CheckCircle,
  AlertCircle,
  LogIn,
  Sparkles,
  Zap,
  Brain,
  Volume2,
  Eye,
  Star,
  Sliders,
  FileText,
  Copy,
  List
} from 'lucide-react';
import { ApiService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import VideoPlayer from '../components/VideoPlayer';
import TranscriptViewer from '../components/TranscriptViewer';
import toast from 'react-hot-toast';
import { connectWebSocket, disconnectWebSocket, subscribeToVideoProgress } from '../services/websocket';

// Helper function to format file size
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

interface ConsoleLog {
  timestamp: string;
  message: string;
  type?: 'info' | 'success' | 'error';
}

interface ProgressState {
  visible: boolean;
  percentage: number;
  status: string;
}

interface VideoData {
  id: string;
  filename: string;
  status: string;
  metadata?: {
    duration?: number;
    format?: string;
    resolution?: string;
    fps?: number;
  };
  outputs?: {
    processed_video?: string;
    thumbnail?: string;
    subtitles?: string;
    condensed_video?: string;
    summary?: {
      condensed_video_path?: string;
      text_summary?: string;
      original_duration?: number;
      condensed_duration?: number;
      segments_count?: number;
      summary_length?: string;
      summary_focus?: string;
    };
    ai_text_summary?: {
      text?: string;
      key_points?: string[];
      compression_ratio?: number;
      video_duration?: number;
    };
    enhancement_results?: {
      filler_words_removed?: number;
      noise_reduction_percentage?: number;
      duration_reduction_percentage?: number;
      original_duration?: string;
      enhanced_duration?: string;
      time_saved?: string;
    };
    audio_enhancement_metrics?: {
      original_duration_ms?: number;
      enhanced_duration_ms?: number;
      time_saved_ms?: number;
      time_saved_percentage?: number;
      filler_words_removed?: number;
    };
  };
}

const Features = () => {
  const { isAuthenticated, loginAsDemo } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<string>('enhancement');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [videoBlobUrl, setVideoBlobUrl] = useState<string | null>(null); // Store blob URL to prevent GC
  const [uploadedVideoId, setUploadedVideoId] = useState<string | null>(null);
  const [videoData, setVideoData] = useState<VideoData | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [consoleLogs, setConsoleLogs] = useState<ConsoleLog[]>([
    { timestamp: new Date().toLocaleTimeString(), message: '[System] SnipX Video Editor API Ready', type: 'info' }
  ]);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [isLoadingPreview, setIsLoadingPreview] = useState<boolean>(false);
  const [isLoadingThumbnails, setIsLoadingThumbnails] = useState<boolean>(false);
  const [thumbnailFrames, setThumbnailFrames] = useState<string[]>([]);
  const [selectedFrameIndex, setSelectedFrameIndex] = useState<number | null>(null);
  const [generatedThumbnail, setGeneratedThumbnail] = useState<string | null>(null);

  // State for form inputs
  const [pauseThreshold] = useState<number>(500);
  const [fillerWordsLevel, setFillerWordsLevel] = useState<string>('medium');
  const [removeFillers, setRemoveFillers] = useState<boolean>(true);
  const [detectRepeatedWords, setDetectRepeatedWords] = useState<boolean>(true);
  const [removeFillersFromVideo, setRemoveFillersFromVideo] = useState<boolean>(true);
  const [customFillerWords, setCustomFillerWords] = useState<string[]>(['', '', '', '', '']);
  const [useCustomFillers, setUseCustomFillers] = useState<boolean>(false);
  const [showProcessedVideo, setShowProcessedVideo] = useState<boolean>(false);
  const [transcriptKey, setTranscriptKey] = useState<number>(0);
  const [subtitleLanguage, setSubtitleLanguage] = useState<string>('en');
  const [subtitleStyle] = useState<string>('clean');
  const [summaryLength, setSummaryLength] = useState<string>('medium');
  const [summaryFocus, setSummaryFocus] = useState<string>('balanced');
  const [audioEnhancement, setAudioEnhancement] = useState<string>('moderate');  // Default to 'moderate' - safe filtering
  const [brightnessLevel, setBrightnessLevel] = useState<number>(100);
  const [contrastLevel, setContrastLevel] = useState<number>(100);
  const [thumbnailStyle] = useState<string>('modern');
  const [thumbnailText, setThumbnailText] = useState<string>('');
  const [aiColorEnhancement, setAiColorEnhancement] = useState<boolean>(false);
  
  // Thumbnail text customization options
  const [thumbnailFontSize, setThumbnailFontSize] = useState<number>(100);
  const [thumbnailTextColor, setThumbnailTextColor] = useState<string>('#FFFFFF');
  const [thumbnailOutlineColor, setThumbnailOutlineColor] = useState<string>('#FF6400');
  const [thumbnailPosition, setThumbnailPosition] = useState<string>('bottom');
  const [thumbnailFontStyle, setThumbnailFontStyle] = useState<string>('bold');
  const [thumbnailShadow, setThumbnailShadow] = useState<boolean>(true);
  const [thumbnailBackground, setThumbnailBackground] = useState<boolean>(true);
  const [thumbnailBackgroundColor, setThumbnailBackgroundColor] = useState<string>('#000000');

  // State for progress bars
  const [audioProgress, setAudioProgress] = useState<ProgressState>({ visible: false, percentage: 0, status: '' });
  const [subtitlesProgress, setSubtitlesProgress] = useState<ProgressState>({ visible: false, percentage: 0, status: '' });
  const [summarizationProgress, setSummarizationProgress] = useState<ProgressState>({ visible: false, percentage: 0, status: '' });
  const [summaryResult, setSummaryResult] = useState<{
    text: string;
    key_points?: string[];
    compression_ratio?: number;
    video_duration?: number;
    condensed_duration?: number;
  } | null>(null);
  const [enhancementProgress, setEnhancementProgress] = useState<ProgressState>({ visible: false, percentage: 0, status: '' });
  const [thumbnailProgress, setThumbnailProgress] = useState<ProgressState>({ visible: false, percentage: 0, status: '' });

  // State for live preview
  const [previewFilters, setPreviewFilters] = useState<string>('');
  const [generatedSubtitles, setGeneratedSubtitles] = useState<string>('');
  const [subtitleFile, setSubtitleFile] = useState<string | null>(null);
  const [subtitleData, setSubtitleData] = useState<any[]>([]);
  const [showConsole, setShowConsole] = useState<boolean>(false);

  const processingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const consoleRef = useRef<HTMLDivElement>(null);
  const statusCheckIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const featuresRef = useRef<HTMLDivElement>(null);
  const wsCleanupRef = useRef<(() => void) | null>(null);

  // Voice command listeners
  useEffect(() => {
    const handleVoiceUpload = () => {
      if (fileInputRef.current) {
        fileInputRef.current.click();
      }
    };

    const handleVoiceGenerateSubtitles = () => {
      if (uploadedVideoId) {
        handleGenerateSubtitles();
      } else {
        toast.error('Please upload a video first');
      }
    };

    const handleVoiceGenerateThumbnail = () => {
      if (uploadedVideoId) {
        handleGenerateThumbnail();
      } else {
        toast.error('Please upload a video first');
      }
    };

    const handleVoiceDownloadVideo = () => {
      if (uploadedVideoId && videoData?.outputs?.processed_video) {
        handleDownloadVideo();
      } else {
        toast.error('No processed video available to download');
      }
    };

    const handleVoiceDownloadThumbnail = () => {
      if (uploadedVideoId && videoData?.outputs?.thumbnail) {
        handleDownloadThumbnail();
      } else {
        toast.error('No thumbnail available to download');
      }
    };

    window.addEventListener('voice-upload-video', handleVoiceUpload);
    window.addEventListener('voice-generate-subtitles', handleVoiceGenerateSubtitles);
    window.addEventListener('voice-generate-thumbnail', handleVoiceGenerateThumbnail);
    window.addEventListener('voice-download-video', handleVoiceDownloadVideo);
    window.addEventListener('voice-download-thumbnail', handleVoiceDownloadThumbnail);

    return () => {
      window.removeEventListener('voice-upload-video', handleVoiceUpload);
      window.removeEventListener('voice-generate-subtitles', handleVoiceGenerateSubtitles);
      window.removeEventListener('voice-generate-thumbnail', handleVoiceGenerateThumbnail);
      window.removeEventListener('voice-download-video', handleVoiceDownloadVideo);
      window.removeEventListener('voice-download-thumbnail', handleVoiceDownloadThumbnail);
    };
  }, [uploadedVideoId, videoData]);

  // Connect WebSocket on mount (optional feature, won't break if it fails)
  useEffect(() => {
    try {
      connectWebSocket();
      logToConsole('WebSocket enabled for real-time updates', 'info');
    } catch (error) {
      logToConsole('WebSocket unavailable, using polling mode', 'info');
    }
    return () => {
      try {
        disconnectWebSocket();
      } catch (error) {
        // Silent cleanup
      }
    };
  }, []);

  // Cleanup blob URLs on unmount
  useEffect(() => {
    return () => {
      if (videoBlobUrl) {
        URL.revokeObjectURL(videoBlobUrl);
      }
    };
  }, [videoBlobUrl]);

  // Mouse tracking for 3D effects - DISABLED to prevent hanging
  useEffect(() => {
    // Disabled mouse tracking to prevent animation hanging
    // const handleMouseMove = (e: MouseEvent) => { ... }
    return () => {
      // Cleanup function remains for safety
    };
  }, []);

  // Auto-switch to processed video when available (e.g., after filler removal)
  useEffect(() => {
    if (videoData?.outputs?.processed_video && uploadedVideoId && isAuthenticated) {
      // Only switch if user wants to see processed video
      if (showProcessedVideo || videoData?.outputs?.enhancement_results?.filler_words_removed) {
        // Fetch video with proper headers and create blob URL
        const token = localStorage.getItem('token');
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5001';
        
        fetch(`${apiUrl}/videos/${uploadedVideoId}/download`, {
          headers: {
            'ngrok-skip-browser-warning': 'true',
            'Authorization': `Bearer ${token}`
          }
        })
        .then(res => res.blob())
        .then(blob => {
          // Revoke old blob URL
          if (videoBlobUrl) {
            URL.revokeObjectURL(videoBlobUrl);
          }
          
          const blobUrl = URL.createObjectURL(blob);
          setVideoBlobUrl(blobUrl);
          setVideoSrc(blobUrl);
          setShowProcessedVideo(true);
          logToConsole('Switched to processed video with enhancements', 'success');
        })
        .catch(err => {
          console.error('Failed to load processed video:', err);
        });
      }
    }
  }, [videoData, uploadedVideoId, isAuthenticated, showProcessedVideo]);

  // Handle URL parameters for direct tab navigation
  useEffect(() => {
    const searchParams = new URLSearchParams(location.search);
    const tabParam = searchParams.get('tab');
    
    if (tabParam) {
      // Map of valid tab names
      const validTabs = ['audio', 'subtitles', 'summarization', 'enhancement', 'thumbnail'];
      
      if (validTabs.includes(tabParam)) {
        setActiveTab(tabParam);
        logToConsole(`Navigated to ${tabParam} tab from external link`);
        
        // Scroll to middle of the page after content is rendered
        setTimeout(() => {
          const documentHeight = document.documentElement.scrollHeight;
          // Position at about 25% from top to show the AI Studio area
          const targetPosition = Math.max(0, documentHeight * 0.25);
          
          window.scrollTo({
            top: targetPosition,
            behavior: 'smooth'
          });
        }, 500);
        
        // Clear the URL parameter to keep URL clean
        const newUrl = new URL(window.location.href);
        newUrl.searchParams.delete('tab');
        navigate(newUrl.pathname, { replace: true });
      }
    }
  }, [location.search, navigate]);

  // Log to console function
  const logToConsole = useCallback((message: string, type: 'info' | 'success' | 'error' = 'info') => {
    setConsoleLogs(prevLogs => [
      ...prevLogs,
      { timestamp: new Date().toLocaleTimeString(), message, type }
    ]);
  }, []);

  // Scroll console to bottom
  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [consoleLogs]);

  // Update live preview filters when enhancement values change
  useEffect(() => {
    const brightness = brightnessLevel / 100;
    const contrast = contrastLevel / 100;
    
    // Apply AI-suggested saturation boost for live preview
    let saturation = 1.0;
    if (aiColorEnhancement) {
      // Simulate AI boost - in real scenario this would be calculated from video analysis
      saturation = 1.3; // Default AI boost for demonstration
    }
    
    const filterString = `brightness(${brightness}) contrast(${contrast}) saturate(${saturation})`;
    setPreviewFilters(filterString);
    
    if (videoRef.current) {
      videoRef.current.style.filter = filterString;
    }
  }, [brightnessLevel, contrastLevel, aiColorEnhancement]);

  // Demo video upload function (simulates upload without backend)
  const uploadVideoDemo = async (file: File) => {
    setIsUploading(true);
    setUploadProgress(0);
    logToConsole(`Starting demo upload: ${file.name} (${formatFileSize(file.size)})`);

    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          const newProgress = Math.min(prev + Math.random() * 15, 95);
          return newProgress;
        });
      }, 200);

      // Simulate upload delay
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      // Generate demo video ID
      const demoVideoId = 'demo-video-' + Date.now();
      setUploadedVideoId(demoVideoId);
      
      // Set demo video data
      setVideoData({
        id: demoVideoId,
        filename: file.name,
        status: 'uploaded',
        metadata: {
          duration: 120,
          format: 'mp4',
          resolution: '1920x1080',
          fps: 30
        },
        outputs: {}
      });
      
      logToConsole(`Demo upload successful! Video ID: ${demoVideoId}`, 'success');
      toast.success('Video uploaded successfully (Demo Mode)');
      
    } catch (error) {
      logToConsole(`Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
      toast.error('Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  // Real video upload function
  const uploadVideo = async (file: File) => {
    if (!isAuthenticated) {
      toast.error('Please login to upload videos');
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);
    logToConsole(`Starting upload: ${file.name} (${formatFileSize(file.size)})`);

    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          const newProgress = Math.min(prev + Math.random() * 15, 95);
          return newProgress;
        });
      }, 200);

      const response = await ApiService.uploadVideo(file);
      
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      if (response.video_id) {
        setUploadedVideoId(response.video_id);
        logToConsole(`Upload successful! Video ID: ${response.video_id}`, 'success');
        
        // Immediately fetch video data instead of relying on status check
        try {
          const videoData = await ApiService.getVideoStatus(response.video_id);
          setVideoData(videoData);
          logToConsole(`Video data loaded: ${videoData.filename}, FPS: ${videoData.metadata?.fps || 'N/A'}, Size: ${formatFileSize(videoData.size || 0)}`, 'success');
        } catch (err) {
          logToConsole(`Failed to load video data: ${err}`, 'error');
        }
        
        // Start checking video status for any processing updates
        startStatusCheck(response.video_id);
      }
    } catch (error) {
      logToConsole(`Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
      toast.error('Upload failed. Using demo mode instead.');
      
      // Fallback to demo mode
      await uploadVideoDemo(file);
    } finally {
      setIsUploading(false);
    }
  };

  // Check video processing status
  const startStatusCheck = (videoId: string) => {
    const checkStatus = async () => {
      try {
        const data = await ApiService.getVideoStatus(videoId);
        setVideoData(data);
        
        if (data.status === 'completed' || data.status === 'failed') {
          if (statusCheckIntervalRef.current) {
            clearInterval(statusCheckIntervalRef.current);
            statusCheckIntervalRef.current = null;
          }
          
          if (data.status === 'completed') {
            logToConsole('Video processing completed successfully!', 'success');
          } else {
            logToConsole(`Video processing failed: ${data.error || 'Unknown error'}`, 'error');
          }
        }
      } catch (error) {
        logToConsole(`Status check failed: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
      }
    };

    // Check immediately and then every 2 seconds
    checkStatus();
    statusCheckIntervalRef.current = setInterval(checkStatus, 2000);
  };

  // Demo processing function
  const processVideoDemo = async (
    _options: any,
    progressSetter: React.Dispatch<React.SetStateAction<ProgressState>>,
    successMessage: string
  ) => {
    progressSetter({ visible: true, percentage: 0, status: 'Starting processing...' });
    
    try {
      // Simulate progress updates
      let progress = 0;
      const progressInterval = setInterval(() => {
        progress += Math.random() * 10;
        if (progress >= 100) {
          clearInterval(progressInterval);
          progress = 100;
          progressSetter(prev => ({ ...prev, percentage: 100, status: successMessage }));
          logToConsole(successMessage + ' (Demo Mode)', 'success');
          
          // Update video data status
          if (videoData) {
            setVideoData(prev => prev ? { ...prev, status: 'completed' } : null);
          }
        } else {
          progressSetter(prev => ({ ...prev, percentage: progress, status: `${Math.round(progress)}% - Processing...` }));
        }
      }, 300);
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Processing failed';
      logToConsole(`Processing failed: ${errorMessage}`, 'error');
      progressSetter(prev => ({ ...prev, status: `Error: ${errorMessage}` }));
      toast.error(errorMessage);
    }
  };

  // Enhanced processing function with detailed options
  const processVideo = async (options: {
    cut_silence?: boolean;
    enhance_audio?: boolean;
    generate_thumbnail?: boolean;
    generate_subtitles?: boolean;
    summarize?: boolean;
    summary_length?: string;
    summary_focus?: string;
    stabilization?: string;
    audio_enhancement_type?: string;
    pause_threshold?: number;
    noise_reduction?: string;
    brightness?: number;
    contrast?: number;
    detect_and_remove_fillers?: boolean;
    detect_repeated_words?: boolean;
    cut_filler_segments?: boolean;
    filler_removal_level?: string;
    subtitle_language?: string;
    subtitle_style?: string;
  }, progressSetter: React.Dispatch<React.SetStateAction<ProgressState>>, successMessage: string) => {
    if (!uploadedVideoId) {
      toast.error('Please upload a video first');
      return;
    }

    if (!isAuthenticated) {
      // Use demo processing
      return processVideoDemo(options, progressSetter, successMessage);
    }

    progressSetter({ visible: true, percentage: 0, status: 'Starting processing...' });
    
    try {
      // Clean up any previous WebSocket subscription
      if (wsCleanupRef.current) {
        wsCleanupRef.current();
        wsCleanupRef.current = null;
      }

      // Track whether WebSocket is delivering updates
      let wsActive = false;
      let pollTimer: NodeJS.Timeout | null = null;
      let completed = false;

      // Helper: when processing finishes (called once)
      const handleDone = async (status: 'completed' | 'failed', message?: string) => {
        if (completed) return;
        completed = true;

        // Stop polling
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
        // Stop WebSocket
        if (wsCleanupRef.current) { wsCleanupRef.current(); wsCleanupRef.current = null; }

        if (status === 'failed') {
          progressSetter(prev => ({ ...prev, percentage: 0, status: `Error: ${message || 'Processing failed'}` }));
          logToConsole(`Processing failed: ${message || 'Unknown error'}`, 'error');
          toast.error(message || 'Processing failed');
          return;
        }

        progressSetter(prev => ({ ...prev, percentage: 100, status: successMessage }));
        logToConsole(successMessage, 'success');

        // Force transcript re-fetch by incrementing key
        setTranscriptKey(prev => prev + 1);

        // Fetch final video data with retry (DB may not be committed yet)
        for (let attempt = 0; attempt < 4; attempt++) {
          try {
            if (attempt > 0) await new Promise(r => setTimeout(r, 1000));
            const updatedData = await ApiService.getVideoStatus(uploadedVideoId!);
            console.log('[FRONTEND] Updated video data:', updatedData);
            setVideoData(updatedData);

            if (updatedData.outputs?.processed_video) {
              const token = localStorage.getItem('token');
              const processedUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:5001/api'}/videos/${uploadedVideoId}/download?token=${token}`;
              setVideoSrc(processedUrl);
              setShowProcessedVideo(true);
              logToConsole('Switched to processed video with enhancements', 'success');
              toast.success('Processing complete! Now showing enhanced video');
              break;
            }
          } catch (err) {
            console.error(`Fetch attempt ${attempt + 1} failed:`, err);
          }
        }
      };

      // 1. Subscribe to WebSocket for real-time progress
      wsCleanupRef.current = subscribeToVideoProgress(
        uploadedVideoId,
        // onProgress
        (data) => {
          wsActive = true;
          progressSetter({ visible: true, percentage: data.progress, status: data.message });
          logToConsole(`Progress: ${data.progress}% - ${data.message}`, 'info');
        },
        // onComplete
        (data) => {
          wsActive = true;
          handleDone('completed', data.message);
        },
        // onError
        (data) => {
          wsActive = true;
          handleDone('failed', data.message);
        }
      );

      // 2. Fire the processing request (returns immediately)
      await ApiService.processVideo(uploadedVideoId, options);
      logToConsole('Processing request sent to server', 'info');

      // 3. Polling fallback: if WebSocket doesn't fire within 3s, start polling
      setTimeout(() => {
        if (completed) return;
        if (!wsActive) {
          logToConsole('Using polling for progress updates', 'info');
        }
        // Poll regardless as a safety net
        pollTimer = setInterval(async () => {
          if (completed) { if (pollTimer) clearInterval(pollTimer); return; }
          try {
            const data = await ApiService.getVideoStatus(uploadedVideoId!);
            setVideoData(data);

            // If WebSocket is not active, estimate progress from status
            if (!wsActive) {
              if (data.status === 'processing') {
                progressSetter(prev => {
                  // Slowly increment but never reach 100 until truly done
                  const next = Math.min(prev.percentage + 2, 90);
                  return { visible: true, percentage: next, status: 'Processing audio... please wait' };
                });
              }
            }

            if (data.status === 'completed') {
              handleDone('completed');
            } else if (data.status === 'failed') {
              handleDone('failed', data.error || 'Processing failed');
            }
          } catch {
            // ignore intermittent fetch errors
          }
        }, 3000);
      }, 3000);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Processing failed';
      logToConsole(`Processing failed: ${errorMessage}`, 'error');
      progressSetter(prev => ({ ...prev, status: `Error: ${errorMessage}` }));
      toast.error(errorMessage);
    }
  };

  // Cleanup intervals and WebSocket on unmount
  useEffect(() => {
    return () => {
      if (processingIntervalRef.current) {
        clearInterval(processingIntervalRef.current);
      }
      if (statusCheckIntervalRef.current) {
        clearInterval(statusCheckIntervalRef.current);
      }
      if (wsCleanupRef.current) {
        wsCleanupRef.current();
        wsCleanupRef.current = null;
      }
    };
  }, []);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      const objectUrl = URL.createObjectURL(file);
      setVideoSrc(objectUrl);
      
      // Reset states
      setUploadedVideoId(null);
      setVideoData(null);
      setGeneratedThumbnail(null);
      setThumbnailFrames([]);
      setSelectedFrameIndex(null);
      setGeneratedSubtitles('');
      setSubtitleData([]);
      setSubtitleFile(null);
      
      // Reset enhancement values
      setBrightnessLevel(100);
      setContrastLevel(100);
      setPreviewFilters('');
      setAiColorEnhancement(false);
      
      // Upload the video (will use demo mode if not authenticated)
      if (isAuthenticated) {
        await uploadVideo(file);
      } else {
        await uploadVideoDemo(file);
      }
    }
  };

  // Effect to auto-generate thumbnail frames when video is loaded
  useEffect(() => {
    if (videoSrc && selectedFile && thumbnailFrames.length === 0) {
      // Small delay to ensure video element can load
      const timer = setTimeout(() => {
        simulateThumbnailFrameGeneration();
      }, 800);
      return () => clearTimeout(timer);
    }
  }, [videoSrc, selectedFile]);

  // Effect for cleaning up Object URL
  useEffect(() => {
    const currentVideoSrc = videoSrc;
    return () => {
      if (currentVideoSrc) {
        URL.revokeObjectURL(currentVideoSrc);
      }
    };
  }, [videoSrc]);

  const triggerFileUpload = () => {
    fileInputRef.current?.click();
  };

  const handleTabClick = (tabId: string) => {
    setActiveTab(tabId);
    logToConsole(`Switched to ${tabId.replace('-', ' ')} tab`);
    
    if (tabId === 'thumbnail' && selectedFile && thumbnailFrames.length === 0) {
      simulateThumbnailFrameGeneration();
    }
  };

  const simulateThumbnailFrameGeneration = () => {
    if (!selectedFile || !videoSrc) return;
    setIsLoadingThumbnails(true);
    logToConsole('Generating thumbnail frames from video...');
    
    // Create a video element to extract frames
    const video = document.createElement('video');
    video.src = videoSrc;
    video.crossOrigin = 'anonymous';
    
    video.addEventListener('loadedmetadata', () => {
      const duration = video.duration;
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      
      if (!ctx) {
        logToConsole('Failed to create canvas context', 'error');
        setIsLoadingThumbnails(false);
        return;
      }
      
      canvas.width = 192; // 2x size for better quality
      canvas.height = 128;
      
      const frames: string[] = [];
      const positions = [0.1, 0.25, 0.4, 0.55, 0.7, 0.85]; // Different positions in video
      let currentIndex = 0;
      
      const captureFrame = () => {
        if (currentIndex >= positions.length) {
          setThumbnailFrames(frames);
          setIsLoadingThumbnails(false);
          logToConsole(`Generated ${frames.length} thumbnail frames successfully!`, 'success');
          return;
        }
        
        const timestamp = duration * positions[currentIndex];
        video.currentTime = timestamp;
      };
      
      video.addEventListener('seeked', () => {
        try {
          // Draw the current video frame to canvas
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
          
          // Convert canvas to data URL
          const frameDataUrl = canvas.toDataURL('image/jpeg', 0.9);
          frames.push(frameDataUrl);
          
          logToConsole(`Extracted frame ${currentIndex + 1}/6 at ${Math.round(video.currentTime)}s`);
          currentIndex++;
          captureFrame();
        } catch (error) {
          logToConsole(`Failed to capture frame ${currentIndex + 1}: ${error}`, 'error');
          currentIndex++;
          captureFrame();
        }
      });
      
      // Start capturing frames
      captureFrame();
    });
    
    video.addEventListener('error', (e) => {
      logToConsole(`Video loading error: ${e}`, 'error');
      setIsLoadingThumbnails(false);
    });
  };

  // Enhanced processing functions
  const handleProcessAudio = () => {
    if (!uploadedVideoId) {
      toast.error('Please upload a video file first');
      return;
    }
    
    // Debug logging
    console.log('[FRONTEND] Current checkbox states:');
    console.log('[FRONTEND] removeFillers:', removeFillers);
    console.log('[FRONTEND] removeFillersFromVideo:', removeFillersFromVideo);
    console.log('[FRONTEND] detectRepeatedWords:', detectRepeatedWords);
    console.log('[FRONTEND] fillerWordsLevel:', fillerWordsLevel);
    console.log('[FRONTEND] ========================================');
    console.log('[FRONTEND] ⭐ NOISE REDUCTION:', audioEnhancement);
    console.log('[FRONTEND] ⭐ METHOD: Safe frequency filtering (NO aggressive processing)');
    console.log('[FRONTEND] ⭐ Light=60Hz HPF, Moderate=80Hz HPF+12kHz LPF, Strong=100Hz HPF+10kHz LPF+compression');
    console.log('[FRONTEND] ⭐ Voice frequencies (85-8000Hz) ALWAYS PRESERVED');
    console.log('[FRONTEND] ========================================');
    
    // Filter out empty custom filler words
    const validCustomFillers = customFillerWords.filter(word => word.trim() !== '');
    
    // CRITICAL: When filler removal is unchecked, ALL filler-related options must be false
    // Otherwise their default state values (true) leak through and cause unwanted processing
    const processingOptions = { 
      cut_silence: false,  // DISABLED - preserve all audio timing
      enhance_audio: true,
      pause_threshold: pauseThreshold,
      noise_reduction: audioEnhancement,  // Respect user's choice
      detect_and_remove_fillers: removeFillers,
      audio_enhancement_type: removeFillers ? fillerWordsLevel : 'medium',
      detect_repeated_words: removeFillers ? detectRepeatedWords : false,
      cut_filler_segments: removeFillers ? removeFillersFromVideo : false,
      filler_removal_level: removeFillers ? fillerWordsLevel : 'medium',
      custom_filler_words: removeFillers && useCustomFillers && validCustomFillers.length > 0 ? validCustomFillers : null,
      use_custom_fillers: removeFillers && useCustomFillers && validCustomFillers.length > 0
    };
    
    console.log('[FRONTEND] Sending processing options:', processingOptions);
    logToConsole(`Starting audio processing: Pause Threshold=${pauseThreshold}ms, Noise Reduction=${audioEnhancement}, Detect & Remove Fillers=${removeFillers}, Cut Video Segments=${removeFillersFromVideo}, Level=${fillerWordsLevel}`);
    
    processVideo(
      processingOptions,
      setAudioProgress,
      'Audio processing completed successfully'
    );
  };

  // FIXED: Enhanced subtitle generation with WebSocket support and fallback
  const handleGenerateSubtitles = async () => {
    if (!uploadedVideoId) {
      toast.error('Please upload a video file first');
      return;
    }
    logToConsole(`Starting subtitle generation: Lang=${subtitleLanguage}, Style=${subtitleStyle}`);
    
    // Start the processing
    setSubtitlesProgress({ visible: true, percentage: 0, status: 'Starting subtitle generation...' });
    
    // Clean up previous WebSocket subscription if any
    if (wsCleanupRef.current) {
      wsCleanupRef.current();
      wsCleanupRef.current = null;
    }
    
    // Flag to track if WebSocket is working
    let websocketWorking = false;
    let fallbackTimeout: NodeJS.Timeout | null = null;
    
    // Try to use WebSocket for real-time updates (optional feature)
    try {
      wsCleanupRef.current = subscribeToVideoProgress(
        uploadedVideoId,
        // On progress
        (data) => {
          websocketWorking = true;
          if (fallbackTimeout) {
            clearTimeout(fallbackTimeout);
            fallbackTimeout = null;
          }
          logToConsole(`WebSocket Progress: ${data.progress}% - ${data.message}`, 'info');
          setSubtitlesProgress({
            visible: true,
            percentage: data.progress,
            status: data.message
          });
        },
        // On complete
        async (data) => {
          websocketWorking = true;
          if (fallbackTimeout) {
            clearTimeout(fallbackTimeout);
            fallbackTimeout = null;
          }
          logToConsole(`WebSocket: Processing complete! ${data.message}`, 'success');
          
          // Fetch the real subtitles (retry up to 3 times with 1s delay to allow DB commit)
          const fetchWithRetry = async (retriesLeft: number): Promise<void> => {
            try {
              const subtitleApiData = await ApiService.getVideoSubtitles(uploadedVideoId);
              
              if (subtitleApiData && subtitleApiData.length > 0) {
                setSubtitleData(subtitleApiData);
                const srtContent = convertSubtitlesToSRT(subtitleApiData);
                setGeneratedSubtitles(srtContent);
                setSubtitleFile(`subtitles_${subtitleLanguage}.srt`);
                
                setSubtitlesProgress({ visible: false, percentage: 100, status: 'Completed' });
                logToConsole(`✅ Real subtitles loaded: ${subtitleApiData.length} segments in ${getLanguageName(subtitleLanguage)}`, 'success');
                toast.success(`Real subtitles loaded with ${subtitleApiData.length} segments!`);
              } else if (retriesLeft > 0) {
                logToConsole(`Subtitles not yet in DB, retrying in 1s... (${retriesLeft} left)`, 'info');
                await new Promise(r => setTimeout(r, 1000));
                await fetchWithRetry(retriesLeft - 1);
              } else {
                logToConsole('No subtitle data found after retries, using fallback', 'info');
                const sampleSubtitles = generateSampleSubtitles(subtitleLanguage);
                setGeneratedSubtitles(sampleSubtitles);
                setSubtitleFile(`subtitles_${subtitleLanguage}.srt`);
                setSubtitleData([]);
                setSubtitlesProgress({ visible: false, percentage: 100, status: 'Completed with fallback' });
                toast.success(`Sample subtitles generated in ${getLanguageName(subtitleLanguage)}`);
              }
            } catch (error) {
              if (retriesLeft > 0) {
                await new Promise(r => setTimeout(r, 1000));
                await fetchWithRetry(retriesLeft - 1);
              } else {
                logToConsole(`Error fetching subtitles: ${error}`, 'error');
                const sampleSubtitles = generateSampleSubtitles(subtitleLanguage);
                setGeneratedSubtitles(sampleSubtitles);
                setSubtitleFile(`subtitles_${subtitleLanguage}.srt`);
                setSubtitleData([]);
                setSubtitlesProgress({ visible: false, percentage: 100, status: 'Completed with fallback' });
                toast.success(`Sample subtitles generated in ${getLanguageName(subtitleLanguage)}`);
              }
            }
          };
          await fetchWithRetry(3);
        },
        // On error
        (data) => {
          logToConsole(`WebSocket Error: ${data.message}`, 'error');
          // Don't fail completely, let the polling fallback handle it
        }
      );
    } catch (error) {
      logToConsole(`WebSocket connection failed: ${error}. Using polling fallback.`, 'info');
      // WebSocket failed - will use polling fallback after it's defined
    }
    
    // Polling fallback function (works without WebSocket)
    // Defined here so it can be used by both setTimeout and catch block
    const startPollingFallback = async () => {
      if (isAuthenticated && uploadedVideoId) {
        let attempts = 0;
        const maxAttempts = 100; // 5 minutes (100 × 3s) - Whisper needs time
        
        const pollInterval = setInterval(async () => {
          try {
            attempts++;
            const elapsedSec = attempts * 3;
            const elapsedStr = elapsedSec >= 60 ? `${Math.floor(elapsedSec/60)}m ${elapsedSec%60}s` : `${elapsedSec}s`;
            logToConsole(`Polling for subtitles (${elapsedStr} elapsed)...`, 'info');
            
            setSubtitlesProgress(prev => ({ 
              ...prev, 
              percentage: Math.min(90, 10 + (attempts * 0.8)), 
              status: `Whisper is transcribing... (${elapsedStr} elapsed)` 
            }));

            // First check video status - if failed, stop polling
            try {
              const videoStatus = await ApiService.getVideoStatus(uploadedVideoId);
              if (videoStatus?.status === 'failed') {
                clearInterval(pollInterval);
                logToConsole('Processing failed on backend', 'error');
                toast.error('Subtitle generation failed on the server');
                setSubtitlesProgress({ visible: false, percentage: 0, status: '' });
                return;
              }
            } catch (_) { /* ignore status check errors */ }
            
            const subtitleApiData = await ApiService.getVideoSubtitles(uploadedVideoId);
            
            if (subtitleApiData && subtitleApiData.length > 0) {
              clearInterval(pollInterval);
              setSubtitleData(subtitleApiData);
              const srtContent = convertSubtitlesToSRT(subtitleApiData);
              setGeneratedSubtitles(srtContent);
              setSubtitleFile(`subtitles_${subtitleLanguage}.srt`);
              
              setSubtitlesProgress({ visible: false, percentage: 100, status: 'Completed' });
              logToConsole(`✅ Real subtitles loaded: ${subtitleApiData.length} segments`, 'success');
              toast.success(`Real subtitles loaded with ${subtitleApiData.length} segments!`);
            } else if (attempts >= maxAttempts) {
              clearInterval(pollInterval);
              const sampleSubtitles = generateSampleSubtitles(subtitleLanguage);
              setGeneratedSubtitles(sampleSubtitles);
              setSubtitleFile(`subtitles_${subtitleLanguage}.srt`);
              setSubtitleData([]);
              setSubtitlesProgress({ visible: false, percentage: 100, status: 'Completed with fallback' });
              toast.success(`Sample subtitles generated in ${getLanguageName(subtitleLanguage)}`);
            }
          } catch (error) {
            if (attempts >= maxAttempts) {
              clearInterval(pollInterval);
              logToConsole('Polling timeout, using fallback', 'info');
              const sampleSubtitles = generateSampleSubtitles(subtitleLanguage);
              setGeneratedSubtitles(sampleSubtitles);
              setSubtitleFile(`subtitles_${subtitleLanguage}.srt`);
              setSubtitleData([]);
              setSubtitlesProgress({ visible: false, percentage: 100, status: 'Completed with fallback' });
              toast.success(`Sample subtitles generated in ${getLanguageName(subtitleLanguage)}`);
            }
          }
        }, 3000);
      } else {
        // Demo mode - use sample subtitles immediately
        logToConsole('Demo mode: Using sample subtitles', 'info');
        const sampleSubtitles = generateSampleSubtitles(subtitleLanguage);
        setGeneratedSubtitles(sampleSubtitles);
        setSubtitleFile(`subtitles_${subtitleLanguage}.srt`);
        setSubtitleData([]);
        setSubtitlesProgress({ visible: false, percentage: 100, status: 'Demo completed' });
        toast.success(`Sample subtitles generated in ${getLanguageName(subtitleLanguage)}`);
      }
    };
    
    // Set a timeout - if WebSocket doesn't work within 5 seconds, use polling fallback
    fallbackTimeout = setTimeout(() => {
      if (!websocketWorking) {
        logToConsole('WebSocket not responding, using polling fallback', 'info');
        startPollingFallback();
      }
    }, 5000);
    
    try {
      // Start backend processing
      await processVideo(
        { 
          generate_subtitles: true,
          subtitle_language: subtitleLanguage,
          subtitle_style: subtitleStyle
        },
        setSubtitlesProgress,
        'Subtitles generation started'
      );
      
    } catch (error) {
      logToConsole(`Subtitle generation failed: ${error}`, 'error');
      toast.error('Subtitle generation failed');
      setSubtitlesProgress({ visible: false, percentage: 0, status: '' });
      if (wsCleanupRef.current) {
        wsCleanupRef.current();
        wsCleanupRef.current = null;
      }
    }
  };

  // Helper function to convert API subtitle data to SRT format
  const convertSubtitlesToSRT = (subtitleData: any[]): string => {
    return subtitleData.map((sub, index) => {
      const startTime = formatTimeForSRT(sub.start);
      const endTime = formatTimeForSRT(sub.end);
      return `${index + 1}\n${startTime} --> ${endTime}\n${sub.text}\n`;
    }).join('\n');
  };

  // Helper function to format time for SRT
  const formatTimeForSRT = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const milliseconds = Math.floor((seconds % 1) * 1000);
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')},${milliseconds.toString().padStart(3, '0')}`;
  };

  // Helper function to generate sample subtitles based on language
  const generateSampleSubtitles = (language: string): string => {
    const subtitleTemplates = {
      'en': `1
00:00:00,000 --> 00:00:05,000
Welcome to this video demonstration

2
00:00:05,000 --> 00:00:10,000
This is an example of English subtitles

3
00:00:10,000 --> 00:00:15,000
Generated automatically by SnipX AI`,
      
      'ur': `1
00:00:00,000 --> 00:00:05,000
اس ویڈیو ڈیمونسٹریشن میں خوش آمدید

2
00:00:05,000 --> 00:00:10,000
یہ اردو سب ٹائٹلز کی مثال ہے

3
00:00:10,000 --> 00:00:15,000
SnipX AI کے ذریعے خودکار طور پر تیار کیا گیا`,
      
      'ru-ur': `1
00:00:00,000 --> 00:00:05,000
Is video demonstration mein khush aamdeed

2
00:00:05,000 --> 00:00:10,000
Yeh Roman Urdu subtitles ki misaal hai

3
00:00:10,000 --> 00:00:15,000
SnipX AI ke zariye automatic tayyar kiya gaya`,
      
      'es': `1
00:00:00,000 --> 00:00:05,000
Bienvenido a esta demostración de video

2
00:00:05,000 --> 00:00:10,000
Este es un ejemplo de subtítulos en español

3
00:00:10,000 --> 00:00:15,000
Generado automáticamente por SnipX AI`,
      
      'fr': `1
00:00:00,000 --> 00:00:05,000
Bienvenue dans cette démonstration vidéo

2
00:00:05,000 --> 00:00:10,000
Ceci est un exemple de sous-titres français

3
00:00:10,000 --> 00:00:15,000
Généré automatiquement par SnipX AI`,
      
      'de': `1
00:00:00,000 --> 00:00:05,000
Willkommen zu dieser Video-Demonstration

2
00:00:05,000 --> 00:00:10,000
Dies ist ein Beispiel für deutsche Untertitel

3
00:00:10,000 --> 00:00:15,000
Automatisch generiert von SnipX AI`
    };
    
    return subtitleTemplates[language as keyof typeof subtitleTemplates] || subtitleTemplates['en'];
  };

  // Helper function to get language name
  const getLanguageName = (code: string): string => {
    const languages = {
      'en': 'English',
      'ur': 'Urdu',
      'es': 'Spanish',
      'fr': 'French',
      'de': 'German'
    };
    return languages[code as keyof typeof languages] || 'English';
  };

  const handleSummarizeVideo = () => {
    if (!uploadedVideoId) {
      toast.error('Please upload a video file first');
      return;
    }
    logToConsole(`Starting video summarization: Length=${summaryLength}, Focus=${summaryFocus}`);
    setIsLoadingPreview(true);
    setSummarizationProgress({ visible: true, percentage: 5, status: 'Sending to server...' });

    // Start polling immediately — backend now returns right away and processes in background
    let attempts = 0;
    const maxAttempts = 180; // wait up to 15 min (CPU Whisper is slow)
    let pollInterval: ReturnType<typeof setInterval> | null = null;
    let pollingStarted = false;

    const startPolling = () => {
      if (pollingStarted) return; // guard against double-start
      pollingStarted = true;
      setSummarizationProgress({ visible: true, percentage: 15, status: 'Analyzing video scenes...' });
      pollInterval = setInterval(async () => {
        attempts++;
        try {
          const updated = await ApiService.getVideoStatus(uploadedVideoId!);
          const hasSummary = updated?.outputs?.summary &&
            (updated.outputs.summary as any)?.condensed_duration !== undefined;

          if (hasSummary) {
            clearInterval(pollInterval!);
            setVideoData(updated);
            setSummarizationProgress({ visible: true, percentage: 100, status: 'Summarization complete!' });
            toast.success('Video summarized successfully! Download your condensed video.');
            logToConsole(`✅ Summary done: ${Math.round((updated?.outputs?.summary as any)?.condensed_duration ?? 0)}s condensed`, 'success');
            setIsLoadingPreview(false);
            
            // Fetch AI text summary
            if (uploadedVideoId && isAuthenticated) {
              try {
                const data = await ApiService.getVideoSummary(uploadedVideoId);
                if (data?.summary && data.summary.text) {
                  setSummaryResult(data.summary);
                  logToConsole(`AI text summary generated: ${data.summary.text.length} chars`, 'success');
                }
              } catch (err) {
                console.error('[Features] Error fetching text summary:', err);
              }
            }
          } else if (updated?.status === 'failed' || attempts >= maxAttempts) {
            clearInterval(pollInterval!);
            setSummarizationProgress({ visible: true, percentage: 0, status: 'Processing timed out or failed' });
            toast.error('Summarization failed or timed out');
            setIsLoadingPreview(false);
          } else {
            // Show realistic step labels based on how long it's been running
            const pct = Math.min(90, 15 + attempts * 1.5);
            const stepLabel = attempts < 10 ? 'Detecting key moments...'
              : attempts < 25 ? 'Transcribing audio...'
              : attempts < 40 ? 'Selecting best segments...'
              : 'Creating condensed video...';
            setSummarizationProgress({ visible: true, percentage: pct, status: stepLabel });
          }
        } catch {
          // ignore transient fetch errors
        }
      }, 5000);
    };

    ApiService.processVideo(uploadedVideoId, {
      summarize: true,
      summary_length: summaryLength,
      summary_focus: summaryFocus
    }).then(() => {
      startPolling();
    }).catch((err) => {
      const msg = err instanceof Error ? err.message : 'Processing failed';
      setSummarizationProgress({ visible: true, percentage: 0, status: `Error: ${msg}` });
      toast.error(msg);
      logToConsole(`Summarization failed: ${msg}`, 'error');
      setIsLoadingPreview(false);
    });

    // Also start polling right away in case processVideo call takes time
    setTimeout(startPolling, 1000);
  };

  // FIXED: Enhanced video processing with live preview updates
  const handleEnhanceVideo = () => {
    if (!uploadedVideoId) {
      toast.error('Please upload a video file first');
      return;
    }
    
    logToConsole(`Starting video enhancement: AI Color=${aiColorEnhancement}, Bright=${brightnessLevel}%, Contrast=${contrastLevel}%`);
    setIsLoadingPreview(true);
    
    // Create comprehensive enhancement options
    const enhancementOptions = {
      brightness: brightnessLevel,
      contrast: contrastLevel,
      ai_color_enhancement: aiColorEnhancement,
      saturation: 100  // Default, will be overridden by AI if enabled
    };
    
    processVideo(
      enhancementOptions,
      setEnhancementProgress,
      'Video enhancement completed successfully'
    ).finally(() => setIsLoadingPreview(false));
  };

  const handleGenerateThumbnail = async () => {
    if (!uploadedVideoId) {
      toast.error('Please upload a video file first');
      return;
    }
    if (selectedFrameIndex === null) {
      toast.error('Please select a frame first');
      return;
    }
    logToConsole(`Starting thumbnail generation: Style=${thumbnailStyle}, Text="${thumbnailText}", Frame=${selectedFrameIndex + 1}`);
    
    // Debug logging - ALL OPTIONS
    console.log('==================== THUMBNAIL OPTIONS DEBUG ====================');
    console.log('[THUMBNAIL DEBUG] thumbnailText value:', thumbnailText);
    console.log('[THUMBNAIL DEBUG] thumbnailText type:', typeof thumbnailText);
    console.log('[THUMBNAIL DEBUG] thumbnailText length:', thumbnailText?.length);
    console.log('[THUMBNAIL DEBUG] Will send:', thumbnailText || null);
    console.log('[THUMBNAIL DEBUG] Font Size:', thumbnailFontSize);
    console.log('[THUMBNAIL DEBUG] Text Color:', thumbnailTextColor);
    console.log('[THUMBNAIL DEBUG] Outline Color:', thumbnailOutlineColor);
    console.log('[THUMBNAIL DEBUG] Position:', thumbnailPosition);
    console.log('[THUMBNAIL DEBUG] Font Style:', thumbnailFontStyle);
    console.log('[THUMBNAIL DEBUG] Shadow:', thumbnailShadow);
    console.log('[THUMBNAIL DEBUG] Background:', thumbnailBackground);
    console.log('[THUMBNAIL DEBUG] Background Color:', thumbnailBackgroundColor);
    console.log('================================================================');
    
    setGeneratedThumbnail(null);
    
    try {
      const requestOptions = { 
        generate_thumbnail: true,
        thumbnail_text: thumbnailText || null,
        thumbnail_frame_index: selectedFrameIndex,
        // Text customization options
        thumbnail_font_size: thumbnailFontSize,
        thumbnail_text_color: thumbnailTextColor,
        thumbnail_outline_color: thumbnailOutlineColor,
        thumbnail_position: thumbnailPosition,
        thumbnail_font_style: thumbnailFontStyle,
        thumbnail_shadow: thumbnailShadow,
        thumbnail_background: thumbnailBackground,
        thumbnail_background_color: thumbnailBackgroundColor
      };
      
      console.log('[THUMBNAIL DEBUG] Full request options:', JSON.stringify(requestOptions, null, 2));
      
      await processVideo(
        requestOptions,
        setThumbnailProgress,
        'Thumbnail generated successfully'
      );
      
      // Wait a bit for backend to process, then get the real thumbnail URL
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      if (isAuthenticated && uploadedVideoId) {
        // Get the real thumbnail URL from backend with cache busting
        // Always use index 0 — backend generates up to 5 thumbnails (0-4) by AI quality scoring.
        // selectedFrameIndex is a frame hint sent to the backend, not the result array index.
        const timestamp = Date.now();
        const thumbnailUrl = `${ApiService.getVideoThumbnailUrl(uploadedVideoId, 0)}&t=${timestamp}`;
        setGeneratedThumbnail(thumbnailUrl);
        logToConsole(`Thumbnail ready: ${thumbnailUrl}`, 'success');
      } else {
        // Demo mode - use the selected frame itself
        setGeneratedThumbnail(thumbnailFrames[selectedFrameIndex]);
        logToConsole('Demo mode: Using selected frame as thumbnail', 'info');
      }
    } catch (error) {
      logToConsole(`Thumbnail generation error: ${error}`, 'error');
      toast.error('Failed to generate thumbnail');
    }
  };

  // FIXED: Proper download functionality
  const handleDownloadVideo = async () => {
    if (!uploadedVideoId) {
      toast.error('No video available for download');
      return;
    }

    try {
      logToConsole('Starting video download...', 'info');
      
      // Use ApiService for automatic API URL detection and fallback
      const blob = await ApiService.downloadVideo(uploadedVideoId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `enhanced_${selectedFile?.name || videoData?.filename || 'video.mp4'}`;
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      logToConsole('Video download started successfully!', 'success');
      toast.success('Enhanced video download started!');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Download failed';
      logToConsole(`Download failed: ${errorMessage}`, 'error');
      toast.error(errorMessage);
    }
  };

  // Download subtitle file
  const handleDownloadSubtitles = () => {
    if (!generatedSubtitles) {
      toast.error('No subtitles available for download');
      return;
    }

    try {
      const blob = new Blob([generatedSubtitles], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = subtitleFile || `subtitles_${subtitleLanguage}.srt`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      logToConsole(`Subtitles downloaded: ${getLanguageName(subtitleLanguage)}`, 'success');
      toast.success('Subtitles downloaded successfully!');
    } catch (error) {
      logToConsole('Subtitle download failed', 'error');
      toast.error('Failed to download subtitles');
    }
  };

  const handleDownloadThumbnail = async () => {
    if (!generatedThumbnail) {
      toast.error('No thumbnail to download');
      return;
    }
    
    try {
      logToConsole('Downloading thumbnail...');

      // If it's already a data URL (demo mode), download directly
      if (generatedThumbnail.startsWith('data:')) {
        const link = document.createElement('a');
        link.href = generatedThumbnail;
        link.download = `thumbnail-${Date.now()}.jpg`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        toast.success('Thumbnail downloaded!');
        return;
      }

      // Fetch the already-displayed thumbnail URL (has token baked in as query param)
      const response = await fetch(generatedThumbnail);
      
      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }
      
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `thumbnail-${Date.now()}.jpg`;
      document.body.appendChild(link);
      link.click();
      
      setTimeout(() => {
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      }, 100);
      
      logToConsole('Thumbnail downloaded successfully!', 'success');
      toast.success('Thumbnail downloaded!');
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Download failed';
      logToConsole(`Thumbnail download failed: ${errorMsg}`, 'error');
      toast.error('Failed to download thumbnail');
    }
  };

  const renderProgressBar = (progressState: ProgressState) => {
    if (!progressState.visible) return null;
    return (
      <div className="mt-6 bg-white/80 backdrop-blur-md rounded-2xl p-6 border border-white/20 shadow-lg animate-slide-up-3d">
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-medium text-gray-700">{progressState.status.includes(' - ') ? progressState.status.split(' - ').slice(1).join(' - ') : progressState.status || 'Processing...'}</p>
          <span className="text-sm font-bold text-purple-600">{Math.round(progressState.percentage)}%</span>
        </div>
        <div className="bg-gray-200 rounded-full h-3 overflow-hidden shadow-inner">
          <div
            className="bg-gradient-to-r from-purple-500 via-pink-500 to-blue-500 h-3 rounded-full transition-all duration-500 shadow-lg"
            style={{ 
              width: `${progressState.percentage}%`,
              animation: 'progress-glow 2s ease-in-out infinite'
            }}
          />
        </div>
      </div>
    );
  };

  const tabs = [
    { id: 'audio', name: 'Audio Enhancement', icon: Volume2, color: 'purple', gradient: 'from-purple-500 to-indigo-600' },
    { id: 'subtitles', name: 'Subtitling', icon: Captions, color: 'teal', gradient: 'from-teal-500 to-cyan-600' },
    { id: 'summarization', name: 'Summarization', icon: Film, color: 'orange', gradient: 'from-orange-500 to-red-600' },
    { id: 'enhancement', name: 'Enhancement', icon: Wand2, color: 'green', gradient: 'from-green-500 to-emerald-600' },
    { id: 'thumbnail', name: 'Thumbnail', icon: ImageIcon, color: 'red', gradient: 'from-red-500 to-pink-600' },
  ];

  // Show login prompt if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-purple-50 py-8 relative overflow-hidden">
        {/* Optimized Background Elements - Fixed hanging animations */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          {/* Simplified floating orbs with optimized animations */}
          <div 
            className="absolute w-96 h-96 rounded-full opacity-10"
            style={{
              background: 'radial-gradient(circle, rgba(139, 92, 246, 0.3) 0%, transparent 70%)',
              top: '10%',
              left: '10%',
              animation: 'gentle-float 8s ease-in-out infinite',
              willChange: 'transform'
            }}
          />
          
          <div 
            className="absolute w-80 h-80 rounded-full opacity-8"
            style={{
              background: 'radial-gradient(circle, rgba(236, 72, 153, 0.3) 0%, transparent 70%)',
              top: '60%',
              right: '10%',
              animation: 'gentle-float 10s ease-in-out infinite reverse',
              animationDelay: '2s',
              willChange: 'transform'
            }}
          />

          {/* Simple geometric shapes with reduced animation complexity */}
          <div 
            className="absolute w-24 h-24 opacity-15"
            style={{
              top: '20%',
              right: '20%',
              background: 'linear-gradient(45deg, rgba(59, 130, 246, 0.4), rgba(147, 51, 234, 0.4))',
              clipPath: 'polygon(50% 0%, 0% 100%, 100% 100%)',
              animation: 'gentle-spin 15s linear infinite',
              willChange: 'transform'
            }}
          />

          {/* Simplified floating sparkles */}
          <div className="absolute top-1/4 left-1/3" style={{ animation: 'gentle-bounce 3s ease-in-out infinite' }}>
            <Sparkles className="text-purple-400/20 w-4 h-4" />
          </div>
          <div className="absolute top-2/3 right-1/2" style={{ animation: 'gentle-bounce 4s ease-in-out infinite', animationDelay: '1s' }}>
            <Sparkles className="text-pink-400/20 w-3 h-3" />
          </div>
        </div>

        <div className="max-w-4xl mx-auto px-4 relative z-10">
          <div className="text-center bg-white/90 backdrop-blur-md rounded-3xl shadow-2xl p-12 border border-white/20 animate-slide-up-3d">
            <div className="mb-8">
              <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-purple-100 to-pink-100 rounded-full mb-6 shadow-lg">
                <LogIn className="text-purple-600 animate-pulse-3d" size={40} />
              </div>
              <h2 className="text-4xl font-bold text-gray-900 mb-4 bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
                Login Required
              </h2>
              <p className="text-xl text-gray-600 mb-8 max-w-md mx-auto leading-relaxed">
                Please login to access the full video editing features, or try our demo mode with limited functionality.
              </p>
            </div>
            
            <div className="flex flex-col sm:flex-row gap-6 justify-center">
              <button
                onClick={loginAsDemo}
                className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white px-8 py-4 rounded-2xl font-semibold transition-all duration-300 transform hover:scale-105 hover:shadow-xl flex items-center justify-center"
              >
                <Zap className="mr-3" size={20} />
                Try Demo Mode
              </button>
              <a
                href="/login"
                className="bg-white/80 backdrop-blur-sm hover:bg-white/90 text-gray-800 px-8 py-4 rounded-2xl font-semibold transition-all duration-300 border-2 border-gray-200 hover:border-purple-300 transform hover:scale-105 hover:shadow-xl flex items-center justify-center"
              >
                <LogIn className="mr-3" size={20} />
                Login / Signup
              </a>
            </div>
            
            <p className="text-sm text-gray-500 mt-6 bg-blue-50 border border-blue-200 rounded-xl p-4">
              <Brain className="inline mr-2" size={16} />
              Demo mode allows you to test features with sample data
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={featuresRef}
      className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-purple-50 py-8 relative overflow-hidden"
    >
      {/* Optimized Background Elements - Fixed hanging animations */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Simplified floating orbs with optimized animations */}
        <div 
          className="absolute w-96 h-96 rounded-full opacity-10"
          style={{
            background: 'radial-gradient(circle, rgba(139, 92, 246, 0.3) 0%, transparent 70%)',
            top: '10%',
            left: '10%',
            animation: 'gentle-float 8s ease-in-out infinite',
            willChange: 'transform'
          }}
        />
        
        <div 
          className="absolute w-80 h-80 rounded-full opacity-8"
          style={{
            background: 'radial-gradient(circle, rgba(236, 72, 153, 0.3) 0%, transparent 70%)',
            top: '60%',
            right: '10%',
            animation: 'gentle-float 10s ease-in-out infinite reverse',
            animationDelay: '2s',
            willChange: 'transform'
          }}
        />

        {/* Simple geometric shapes with reduced animation complexity */}
        <div 
          className="absolute w-24 h-24 opacity-15"
          style={{
            top: '20%',
            right: '20%',
            background: 'linear-gradient(45deg, rgba(59, 130, 246, 0.4), rgba(147, 51, 234, 0.4))',
            clipPath: 'polygon(50% 0%, 0% 100%, 100% 100%)',
            animation: 'gentle-spin 15s linear infinite',
            willChange: 'transform'
          }}
        />

        {/* Simplified floating sparkles */}
        <div className="absolute top-1/4 left-1/3" style={{ animation: 'gentle-bounce 3s ease-in-out infinite' }}>
          <Sparkles className="text-purple-400/20 w-4 h-4" />
        </div>
        <div className="absolute top-2/3 right-1/2" style={{ animation: 'gentle-bounce 4s ease-in-out infinite', animationDelay: '1s' }}>
          <Sparkles className="text-pink-400/20 w-3 h-3" />
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Enhanced Header */}
        <div className="text-center mb-12 animate-slide-up-3d">
          <div className="inline-flex items-center px-6 py-3 bg-white/80 backdrop-blur-md rounded-full shadow-lg border border-white/20 mb-6 transform hover:scale-105 transition-all duration-300 hover:shadow-xl">
            <Brain className="text-purple-600 mr-3 animate-pulse" size={24} />
            <span className="text-purple-700 font-medium">AI-Powered Video Editor</span>
            <Sparkles className="text-pink-600 ml-3 animate-bounce" size={20} />
          </div>
          <h1 className="text-5xl font-bold text-gray-900 mb-4 bg-gradient-to-r from-purple-600 via-pink-600 to-blue-600 bg-clip-text text-transparent animate-text-shimmer">
            Professional Video Editing
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto animate-fade-in-up-3d">
            Upload your video and let AI do the magic with advanced processing capabilities
          </p>
        </div>

        <div 
          className="editor-container p-8 bg-white/90 backdrop-blur-md rounded-3xl shadow-2xl border border-white/20 animate-slide-up-3d"
        >
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="text-3xl font-bold text-gray-900 flex items-center">
                <Wand2 className="mr-3 text-purple-600 animate-pulse" size={32} />
                AI Video Studio
              </h2>
              <p className="text-gray-600 mt-2">Transform your videos with cutting-edge AI technology</p>
            </div>
            {!isAuthenticated && (
              <div className="bg-gradient-to-r from-yellow-100 to-orange-100 border-2 border-yellow-300 rounded-2xl px-6 py-3 shadow-lg">
                <span className="text-sm text-yellow-800 font-bold flex items-center">
                  <Star className="mr-2" size={16} />
                  Demo Mode
                </span>
              </div>
            )}
          </div>

          {/* Enhanced Tabs */}
          <div className="border-b border-gray-200 mb-8">
            <nav className="-mb-px flex space-x-2 overflow-x-auto bg-gray-50/50 rounded-2xl p-2">
              {tabs.map((tab, index) => (
                <button
                  key={tab.id}
                  onClick={() => handleTabClick(tab.id)}
                  className={`tab-button whitespace-nowrap py-4 px-6 rounded-xl font-semibold text-sm flex items-center transition-all duration-300 transform hover:scale-105 hover:-translate-y-1 ${
                    activeTab === tab.id
                      ? `bg-gradient-to-r ${tab.gradient} text-white shadow-lg`
                      : 'text-gray-600 hover:text-gray-800 hover:bg-white/80'
                  }`}
                  style={{ 
                    animationDelay: `${index * 100}ms`,
                  }}
                >
                  <tab.icon className="mr-3 h-5 w-5" />
                  {tab.name}
                </button>
              ))}
            </nav>
          </div>

          {/* Enhanced File Upload Area */}
          <div
            id="file-upload-area"
            className="file-upload-area border-dashed border-3 border-purple-300 hover:border-purple-500 hover:bg-purple-50/50 py-16 px-8 text-center cursor-pointer mb-8 rounded-2xl transition-all duration-300 bg-gradient-to-br from-white/80 to-purple-50/50 backdrop-blur-sm shadow-lg transform hover:scale-105 hover:shadow-xl"
            onClick={triggerFileUpload}
          >
            <div className="mb-6">
              <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-purple-100 to-pink-100 rounded-full mb-4 shadow-lg animate-bounce-3d">
                <UploadCloud className="text-purple-600 animate-pulse" size={40} />
              </div>
            </div>
            <h3 className="text-2xl font-bold mb-3 text-gray-900">Drag & Drop Your Video</h3>
            <p className="text-gray-600 font-medium mb-6">or click to browse files</p>
            <input
              type="file"
              id="video-upload"
              accept="video/*"
              className="hidden"
              ref={fileInputRef}
              onChange={handleFileSelect}
            />
            <div className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white px-8 py-4 rounded-2xl font-semibold transition-all duration-300 transform hover:scale-105 hover:shadow-lg inline-block">
              Select Video File
            </div>
            <p className="text-sm text-gray-500 mt-4 bg-white/60 rounded-full px-4 py-2 inline-block">
              Supports MP4, MOV, AVI up to 500MB
            </p>
          </div>

          {/* Enhanced Upload Progress */}
          {isUploading && (
            <div className="mb-8 bg-gradient-to-r from-blue-50 to-cyan-50 border-2 border-blue-200 rounded-2xl p-6 shadow-lg animate-slide-up-3d">
              <div className="flex items-center justify-between mb-4">
                <span className="text-lg font-bold text-blue-800 flex items-center">
                  <Loader2 className="animate-spin mr-3" size={24} />
                  Uploading video...
                </span>
                <span className="text-lg font-bold text-blue-800">{Math.round(uploadProgress)}%</span>
              </div>
              <div className="w-full bg-blue-200 rounded-full h-4 overflow-hidden shadow-inner">
                <div 
                  className="bg-gradient-to-r from-blue-500 to-cyan-500 h-4 rounded-full transition-all duration-300 shadow-lg"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Enhanced Selected File Info */}
          {selectedFile && (
            <div 
              id="filename-display" 
              className="mb-8 bg-gradient-to-r from-gray-50 to-purple-50 border-2 border-gray-200 rounded-2xl p-6 shadow-lg animate-slide-in-3d"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className="bg-gradient-to-br from-purple-100 to-pink-100 rounded-2xl p-4 mr-4 shadow-lg">
                    <Video className="text-purple-600" size={24} />
                  </div>
                  <div>
                    <p className="text-lg font-bold text-gray-900">{selectedFile.name}</p>
                    <p className="text-sm text-gray-600">{formatFileSize(selectedFile.size)}</p>
                  </div>
                </div>
                {videoData && (
                  <div className="flex items-center bg-white/80 rounded-full px-4 py-2 shadow-md">
                    {videoData.status === 'completed' && <CheckCircle className="text-green-500 mr-2 animate-pulse" size={20} />}
                    {videoData.status === 'failed' && <AlertCircle className="text-red-500 mr-2 animate-pulse" size={20} />}
                    {videoData.status === 'processing' && <Loader2 className="animate-spin text-blue-500 mr-2" size={20} />}
                    <span className="text-sm font-bold capitalize">{videoData.status}</span>
                  </div>
                )}
              </div>
              {videoData?.metadata && (
                <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
                  {videoData.metadata.duration && (
                    <div className="bg-white/60 rounded-xl p-3 text-center">
                      <div className="text-lg font-bold text-purple-600">{Math.round(videoData.metadata.duration)}s</div>
                      <div className="text-xs text-gray-600">Duration</div>
                    </div>
                  )}
                  {videoData.metadata.resolution && (
                    <div className="bg-white/60 rounded-xl p-3 text-center">
                      <div className="text-lg font-bold text-blue-600">{videoData.metadata.resolution}</div>
                      <div className="text-xs text-gray-600">Resolution</div>
                    </div>
                  )}
                  {videoData.metadata.fps && (
                    <div className="bg-white/60 rounded-xl p-3 text-center">
                      <div className="text-lg font-bold text-green-600">{videoData.metadata.fps}</div>
                      <div className="text-xs text-gray-600">FPS</div>
                    </div>
                  )}
                  {videoData.metadata.format && (
                    <div className="bg-white/60 rounded-xl p-3 text-center">
                      <div className="text-lg font-bold text-orange-600">{videoData.metadata.format}</div>
                      <div className="text-xs text-gray-600">Format</div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Enhanced Tab Contents */}
          <div className="mt-8">
            {/* Audio Enhancement Tab */}
            <div id="audio-tab" className={`tab-content ${activeTab === 'audio' ? 'block' : 'hidden'}`}>
              <div className="bg-white/80 backdrop-blur-md rounded-2xl p-8 shadow-xl border border-white/20 animate-content-reveal-3d">
                <h3 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
                  <Volume2 className="mr-3 text-purple-600 animate-pulse" size={28} />
                  Audio Enhancement
                </h3>
                
                {/* Two Column Layout */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Left Column - Noise Reduction */}
                  <div className="bg-gradient-to-br from-purple-50 to-indigo-50 border-2 border-purple-200 rounded-xl p-5">
                    <div className="flex items-center mb-3">
                      <Volume2 className="h-5 w-5 text-purple-600 mr-2" />
                      <h4 className="text-sm font-bold text-gray-800">Background Noise Reduction</h4>
                    </div>
                    <select 
                      id="noise-reduction" 
                      value={audioEnhancement} 
                      onChange={(e) => setAudioEnhancement(e.target.value)} 
                      className="block w-full px-3 py-2 border-2 border-purple-200 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white text-sm font-medium mb-2"
                    >
                      <option value="none">None</option>
                      <option value="light">Light</option>
                      <option value="moderate">Moderate</option>
                      <option value="strong">Strong</option>
                    </select>
                    <p className="text-xs text-gray-500">AI-powered noise filtering</p>
                  </div>

                  {/* Right Column - Filler Word Removal */}
                  <div className="bg-gradient-to-br from-blue-50 to-cyan-50 border-2 border-blue-200 rounded-xl p-5">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center">
                        <Zap className="h-5 w-5 text-blue-600 mr-2" />
                        <h4 className="text-sm font-bold text-gray-800">Filler Word Removal</h4>
                      </div>
                      <input
                        type="checkbox"
                        checked={removeFillers}
                        onChange={(e) => setRemoveFillers(e.target.checked)}
                        className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      />
                    </div>
                    
                    {removeFillers && (
                      <div className="space-y-2 animate-slide-down">
                        <select
                          value={fillerWordsLevel}
                          onChange={(e) => setFillerWordsLevel(e.target.value)}
                          className="block w-full px-3 py-2 border border-blue-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 bg-white"
                        >
                          <option value="conservative">Conservative</option>
                          <option value="medium">Medium</option>
                          <option value="aggressive">Aggressive</option>
                        </select>
                        
                        <label className="flex items-center cursor-pointer text-xs">
                          <input
                            type="checkbox"
                            checked={useCustomFillers}
                            onChange={(e) => setUseCustomFillers(e.target.checked)}
                            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 mr-2"
                          />
                          <span className="text-gray-600 font-semibold">Use custom filler words</span>
                        </label>
                        
                        {useCustomFillers && (
                          <div className="space-y-1 p-2 bg-white rounded border border-blue-200">
                            <p className="text-xs text-gray-600 font-semibold mb-1">Enter up to 5 custom filler words:</p>
                            {[0, 1, 2, 3, 4].map((index) => (
                              <input
                                key={index}
                                type="text"
                                placeholder={`Word ${index + 1}`}
                                value={customFillerWords[index]}
                                onChange={(e) => {
                                  const newWords = [...customFillerWords];
                                  newWords[index] = e.target.value;
                                  setCustomFillerWords(newWords);
                                }}
                                className="w-full px-2 py-1 border border-blue-200 rounded text-xs focus:ring-1 focus:ring-blue-500"
                              />
                            ))}
                          </div>
                        )}
                        
                        <label className="flex items-center cursor-pointer text-xs">
                          <input
                            type="checkbox"
                            checked={detectRepeatedWords}
                            onChange={(e) => setDetectRepeatedWords(e.target.checked)}
                            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 mr-2"
                          />
                          <span className="text-gray-600">Detect repeated words</span>
                        </label>
                        
                        <label className="flex items-center cursor-pointer text-xs">
                          <input
                            type="checkbox"
                            checked={removeFillersFromVideo}
                            onChange={(e) => setRemoveFillersFromVideo(e.target.checked)}
                            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 mr-2"
                          />
                          <span className="text-gray-600">Cut video segments</span>
                        </label>
                      </div>
                    )}
                    {!removeFillers && (
                      <p className="text-xs text-gray-400 italic">Enable to remove um, uh, like, etc.</p>
                    )}
                  </div>
                </div>
                
                
                <div className="mt-6 flex flex-col sm:flex-row gap-4">
                  <button 
                    onClick={handleProcessAudio} 
                    className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white px-8 py-4 rounded-2xl text-lg font-bold transition-all duration-300 flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105 hover:shadow-xl" 
                    disabled={!uploadedVideoId || isUploading}
                  >
                    <Volume2 className="mr-3 h-6 w-6" />
                    Enhance Audio
                  </button>
                  
                  <div className="flex items-center text-sm text-gray-600 bg-blue-50 rounded-xl px-4 py-2 border border-blue-200">
                    <CheckCircle className="mr-2 text-blue-600" size={16} />
                    <span>Processing will maintain video quality while improving audio clarity</span>
                  </div>
                </div>
                
                {renderProgressBar(audioProgress)}
                
                {/* Results Display */}
                {audioProgress.percentage === 100 && (
                  <div className="mt-8 bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-200 rounded-2xl p-6 shadow-lg animate-slide-up-3d">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <CheckCircle className="text-green-500 mr-3 animate-pulse" size={24} />
                        <div>
                          <span className="text-lg font-bold text-green-800">Audio Enhancement Complete!</span>
                          <p className="text-sm text-green-700">Your video now has clean, fluent audio</p>
                        </div>
                      </div>
                      <button 
                        onClick={handleDownloadVideo}
                        className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white px-6 py-3 rounded-xl text-sm font-bold transition-all duration-300 flex items-center transform hover:scale-105 hover:shadow-lg"
                      >
                        <Download className="mr-2 h-4 w-4" />
                        Download Enhanced Video
                      </button>
                    </div>
                    
                    <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div className="bg-white/60 rounded-xl p-3 text-center">
                        <div className="text-lg font-bold text-green-600">
                          {videoData?.outputs?.enhancement_results?.duration_reduction_percentage 
                            ? `${videoData.outputs.enhancement_results.duration_reduction_percentage.toFixed(1)}%`
                            : videoData?.outputs?.audio_enhancement_metrics?.time_saved_percentage
                              ? `${videoData.outputs.audio_enhancement_metrics.time_saved_percentage.toFixed(1)}%`
                              : '0%'}
                        </div>
                        <div className="text-xs text-gray-600">Shorter Duration</div>
                      </div>
                      <div className="bg-white/60 rounded-xl p-3 text-center">
                        <div className="text-lg font-bold text-blue-600">
                          {videoData?.outputs?.enhancement_results?.noise_reduction_percentage 
                            ? `${videoData.outputs.enhancement_results.noise_reduction_percentage}%`
                            : audioEnhancement === 'strong' ? '95%' 
                              : audioEnhancement === 'moderate' ? '75%' 
                                : audioEnhancement === 'light' ? '50%' : '0%'}
                        </div>
                        <div className="text-xs text-gray-600">Noise Reduced</div>
                      </div>
                      <div className="bg-white/60 rounded-xl p-3 text-center">
                        <div className="text-lg font-bold text-purple-600">
                          {videoData?.outputs?.enhancement_results?.filler_words_removed 
                            ?? videoData?.outputs?.audio_enhancement_metrics?.filler_words_removed 
                            ?? 0}
                        </div>
                        <div className="text-xs text-gray-600">Fillers Removed</div>
                      </div>
                      <div className="bg-white/60 rounded-xl p-3 text-center">
                        <div className="text-lg font-bold text-orange-600">
                          {videoData?.outputs?.enhancement_results?.filler_words_removed 
                            ?? videoData?.outputs?.audio_enhancement_metrics?.filler_words_removed 
                            ?? 0}
                        </div>
                        <div className="text-xs text-gray-600">Total Removed</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Subtitling Tab */}
            <div id="subtitles-tab" className={`tab-content ${activeTab === 'subtitles' ? 'block' : 'hidden'}`}>
              <div className="bg-white/80 backdrop-blur-md rounded-2xl p-8 shadow-xl border border-white/20 animate-content-reveal-3d">
                <h3 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
                  <Captions className="mr-3 text-teal-600 animate-pulse" size={28} />
                  Subtitling Settings
                </h3>
                
                <div className="space-y-4">
                  <label htmlFor="subtitle-language" className="block text-sm font-bold text-gray-700">Language</label>
                  <select 
                    id="subtitle-language" 
                    value={subtitleLanguage} 
                    onChange={(e) => setSubtitleLanguage(e.target.value)} 
                    className="block w-full px-4 py-3 border-2 border-teal-200 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500 bg-white/80 backdrop-blur-sm text-sm font-medium"
                  >
                    <option value="en">🇺🇸 English</option>
                    <option value="ur">🇵🇰 Urdu (اردو)</option>
                    <option value="es">🇪🇸 Spanish (Español)</option>
                    <option value="fr">🇫🇷 French (Français)</option>
                    <option value="de">🇩🇪 German (Deutsch)</option>
                  </select>
                </div>

                {/* Enhanced Subtitle Preview */}
                {generatedSubtitles && (
                  <div className="mt-8 bg-gradient-to-br from-teal-50 to-cyan-50 border-2 border-teal-200 rounded-2xl p-6 shadow-lg animate-slide-up-3d">
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="text-lg font-bold text-teal-900 flex items-center">
                        <Eye className="mr-2" size={20} />
                        Generated Subtitles ({getLanguageName(subtitleLanguage)})
                      </h4>
                      <button 
                        onClick={handleDownloadSubtitles}
                        className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white px-6 py-3 rounded-xl text-sm font-bold transition-all duration-300 flex items-center transform hover:scale-105 hover:shadow-lg"
                      >
                        <Download className="mr-2 h-4 w-4" />
                        Download SRT
                      </button>
                    </div>
                    <div className="bg-white/80 backdrop-blur-sm border border-teal-200 rounded-xl p-4 max-h-48 overflow-y-auto shadow-inner">
                      <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono leading-relaxed">{generatedSubtitles}</pre>
                    </div>
                  </div>
                )}

                <div className="mt-8 flex space-x-4">
                  <button 
                    onClick={handleGenerateSubtitles} 
                    className="bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-700 hover:to-cyan-700 text-white px-8 py-4 rounded-2xl text-lg font-bold transition-all duration-300 flex items-center disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105 hover:shadow-xl" 
                    disabled={!uploadedVideoId || isUploading}
                  >
                    <Captions className="mr-3 h-6 w-6" />
                    Generate Subtitles
                  </button>
                  
                  {/* Debug test button for subtitle loading */}
                  {process.env.NODE_ENV === 'development' && isAuthenticated && uploadedVideoId && (
                    <button 
                      onClick={async () => {
                        try {
                          console.log('[Features] 🧪 Testing subtitle API for videoId:', uploadedVideoId);
                          const testData = await ApiService.getVideoSubtitles(uploadedVideoId);
                          console.log('[Features] 🧪 Test API response:', testData);
                          if (testData && testData.length > 0) {
                            setSubtitleData(testData);
                            logToConsole(`🧪 Test: Loaded ${testData.length} subtitle segments`, 'success');
                          } else {
                            logToConsole(`🧪 Test: No subtitle data found`, 'info');
                          }
                        } catch (error) {
                          console.error('[Features] 🧪 Test error:', error);
                          logToConsole(`🧪 Test: API error - ${error}`, 'error');
                        }
                      }}
                      className="bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-600 hover:to-indigo-600 text-white px-6 py-4 rounded-2xl text-sm font-bold transform hover:scale-105 hover:shadow-lg transition-all duration-300"
                    >
                      🧪 Test Subtitles
                    </button>
                  )}
                </div>
                {renderProgressBar(subtitlesProgress)}
              </div>
            </div>

            {/* Summarization Tab */}
            <div id="summarization-tab" className={`tab-content ${activeTab === 'summarization' ? 'block' : 'hidden'}`}>
              <div className="bg-white/80 backdrop-blur-md rounded-2xl p-8 shadow-xl border border-white/20 animate-content-reveal-3d">
                <h3 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
                  <Film className="mr-3 text-orange-600 animate-pulse" size={28} />
                  Video Summarization
                </h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div className="space-y-4">
                    <label htmlFor="summary-length" className="block text-sm font-bold text-gray-700">Summary Length</label>
                    <select 
                      id="summary-length" 
                      value={summaryLength} 
                      onChange={(e) => setSummaryLength(e.target.value)} 
                      className="block w-full px-4 py-3 border-2 border-orange-200 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 bg-white/80 backdrop-blur-sm text-sm font-medium"
                    >
                      <option value="short">Short (15% of original)</option>
                      <option value="medium">Medium (30% of original)</option>
                      <option value="long">Long (50% of original)</option>
                    </select>
                  </div>
                  
                  <div className="space-y-4">
                    <label htmlFor="summary-focus" className="block text-sm font-bold text-gray-700">Focus</label>
                    <select 
                      id="summary-focus" 
                      value={summaryFocus} 
                      onChange={(e) => setSummaryFocus(e.target.value)} 
                      className="block w-full px-4 py-3 border-2 border-orange-200 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 bg-white/80 backdrop-blur-sm text-sm font-medium"
                    >
                      <option value="balanced">Balanced (Visual + Audio)</option>
                      <option value="action">Action & Motion</option>
                      <option value="speech">Speech & Dialogue</option>
                    </select>
                  </div>
                </div>
                
                <div className="mt-8 flex flex-wrap gap-4 items-center">
                  <button 
                    onClick={handleSummarizeVideo} 
                    className="bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-700 hover:to-red-700 text-white px-8 py-4 rounded-2xl text-lg font-bold transition-all duration-300 flex items-center disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105 hover:shadow-xl" 
                    disabled={!uploadedVideoId || isUploading}
                  >
                    <Film className="mr-3 h-6 w-6" />
                    Summarize Video
                  </button>

                  {/* Download button — shown after summarization completes */}
                  {uploadedVideoId && videoData?.outputs?.condensed_video && (
                    <button
                      onClick={async () => {
                        try {
                          const token = localStorage.getItem('token');
                          const url = `${import.meta.env.VITE_API_URL || 'http://localhost:5001/api'}/videos/${uploadedVideoId}/download/summarized`;
                          toast.loading('Preparing download...');
                          const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
                          if (!res.ok) throw new Error(`Server returned ${res.status}`);
                          const blob = await res.blob();
                          const a = document.createElement('a');
                          a.href = URL.createObjectURL(blob);
                          a.download = `summarized_video.mp4`;
                          document.body.appendChild(a);
                          a.click();
                          a.remove();
                          toast.dismiss();
                          toast.success('Download started!');
                        } catch (e) {
                          toast.dismiss();
                          toast.error('Download failed: ' + (e instanceof Error ? e.message : e));
                        }
                      }}
                      className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white px-8 py-4 rounded-2xl text-lg font-bold transition-all duration-300 flex items-center transform hover:scale-105 hover:shadow-xl"
                    >
                      <svg className="mr-3 h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                      Download Summary
                    </button>
                  )}
                </div>

                {/* Summarization Result Stats */}
                {videoData?.outputs?.summary && videoData.outputs.summary.condensed_duration !== undefined && (
                  <div className="mt-6 bg-gradient-to-r from-orange-50 to-red-50 border-2 border-orange-200 rounded-xl p-5">
                    <h4 className="text-base font-bold text-orange-800 mb-4 flex items-center">
                      <Film className="mr-2 h-5 w-5" />
                      Summarization Results
                    </h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="bg-white rounded-lg p-3 text-center shadow-sm">
                        <div className="text-2xl font-bold text-gray-800">
                          {Math.round(videoData.outputs.summary.original_duration ?? 0)}s
                        </div>
                        <div className="text-xs text-gray-500 mt-1">Original Duration</div>
                      </div>
                      <div className="bg-white rounded-lg p-3 text-center shadow-sm">
                        <div className="text-2xl font-bold text-orange-600">
                          {Math.round(videoData.outputs.summary.condensed_duration ?? 0)}s
                        </div>
                        <div className="text-xs text-gray-500 mt-1">Condensed Duration</div>
                      </div>
                      <div className="bg-white rounded-lg p-3 text-center shadow-sm">
                        <div className="text-2xl font-bold text-green-600">
                          {videoData.outputs.summary.original_duration
                            ? Math.round((1 - (videoData.outputs.summary.condensed_duration ?? 0) / videoData.outputs.summary.original_duration) * 100)
                            : 0}%
                        </div>
                        <div className="text-xs text-gray-500 mt-1">Reduced</div>
                      </div>
                      <div className="bg-white rounded-lg p-3 text-center shadow-sm">
                        <div className="text-2xl font-bold text-blue-600">
                          {videoData.outputs.summary.segments_count ?? 0}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">Key Moments</div>
                      </div>
                    </div>
                    <p className="mt-3 text-xs text-orange-700">
                      ✅ Condensed video ready — click <strong>Download Summary</strong> to save it.
                    </p>
                  </div>
                )}

                {/* AI Text Summary Card */}
                {summaryResult && summaryResult.text && (
                  <div className="mt-6">
                    <div className="bg-gradient-to-br from-orange-50 to-amber-50 border-2 border-orange-200 rounded-2xl p-6 shadow-lg">
                      <div className="flex items-center justify-between mb-4">
                        <h4 className="text-lg font-bold text-gray-900 flex items-center">
                          <FileText className="mr-2 text-orange-600" size={20} />
                          Video Summary
                        </h4>
                        <div className="flex items-center gap-3 text-xs text-gray-500">
                          {summaryResult.condensed_duration && summaryResult.video_duration && (
                            <span className="bg-orange-100 text-orange-700 px-2 py-1 rounded-full font-medium">
                              {Math.round(summaryResult.video_duration)}s → {Math.round(summaryResult.condensed_duration)}s
                            </span>
                          )}
                          {summaryResult.video_duration && (
                            <span className="bg-amber-100 text-amber-700 px-2 py-1 rounded-full font-medium">
                              {Math.round(summaryResult.video_duration)}s video
                            </span>
                          )}
                        </div>
                      </div>
                      
                      <div className="text-gray-700 leading-relaxed mb-4 whitespace-pre-wrap max-h-64 overflow-y-auto pr-2">
                        {summaryResult.text.length > 2000 
                          ? summaryResult.text.slice(0, 2000) + '...'
                          : summaryResult.text}
                      </div>
                      
                      {summaryResult.key_points && summaryResult.key_points.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-orange-200">
                          <h5 className="text-sm font-bold text-gray-800 mb-2 flex items-center">
                            <List className="mr-1.5 text-orange-500" size={14} />
                            Key Points:
                          </h5>
                          <ul className="space-y-1">
                            {summaryResult.key_points.map((point: string, idx: number) => (
                              <li key={idx} className="flex items-start text-sm text-gray-600">
                                <span className="text-orange-500 mr-2 mt-0.5">•</span>
                                {point}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      
                      <div className="mt-4 flex gap-2">
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(
                              summaryResult.text + 
                              (summaryResult.key_points?.length 
                                ? '\n\nKey Points:\n' + summaryResult.key_points.map((p: string) => `• ${p}`).join('\n') 
                                : '')
                            );
                            toast.success('Summary copied to clipboard!');
                          }}
                          className="bg-orange-100 hover:bg-orange-200 text-orange-700 px-4 py-2 rounded-xl text-sm font-medium transition-colors flex items-center"
                        >
                          <Copy className="mr-1.5 h-4 w-4" />
                          Copy Summary
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {renderProgressBar(summarizationProgress)}
              </div>
            </div>

            {/* Enhancement Tab */}
            <div id="enhancement-tab" className={`tab-content ${activeTab === 'enhancement' ? 'block' : 'hidden'}`}>
              <div className="bg-white/80 backdrop-blur-md rounded-2xl p-8 shadow-xl border border-white/20 animate-content-reveal-3d">
                <h3 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
                  <Wand2 className="mr-3 text-green-600 animate-pulse" size={28} />
                  Video Enhancement
                </h3>
                
                {/* Two Column Layout */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Left Column - AI Color Enhancement */}
                  <div className="bg-gradient-to-br from-purple-50 to-pink-50 border-2 border-purple-200 rounded-xl p-5">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center">
                        <Wand2 className="h-5 w-5 text-purple-600 mr-2" />
                        <h4 className="text-sm font-bold text-gray-800">AI Color Enhancement</h4>
                        <span className="ml-2 bg-purple-600 text-white text-xs px-2 py-0.5 rounded-full">NEW</span>
                      </div>
                      <input 
                        type="checkbox" 
                        checked={aiColorEnhancement}
                        onChange={(e) => setAiColorEnhancement(e.target.checked)}
                        className="w-5 h-5 text-purple-600 border-gray-300 rounded focus:ring-purple-500"
                      />
                    </div>
                    {aiColorEnhancement && (
                      <div className="bg-white/60 rounded-lg p-2 border border-purple-200 animate-slide-down">
                        <p className="text-xs text-purple-800">
                          ✨ AI auto-adjusts colors optimally
                        </p>
                      </div>
                    )}
                    {!aiColorEnhancement && (
                      <p className="text-xs text-gray-400 italic">Enable for automatic optimization</p>
                    )}
                  </div>

                  {/* Right Column - Manual Adjustments */}
                  <div className="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-200 rounded-xl p-5">
                    <div className="flex items-center mb-3">
                      <Sliders className="h-5 w-5 text-green-600 mr-2" />
                      <h4 className="text-sm font-bold text-gray-800">Manual Adjustments</h4>
                    </div>
                    
                    {/* Brightness */}
                    <div className="mb-3">
                      <label className="text-xs text-gray-600 mb-1 block">Brightness</label>
                      <div className="flex items-center gap-2">
                        <input 
                          type="range" 
                          min="0" 
                          max="200" 
                          value={brightnessLevel} 
                          onChange={(e) => setBrightnessLevel(Number(e.target.value))} 
                          className="flex-1 h-2 bg-green-200 rounded-lg appearance-none cursor-pointer accent-green-600" 
                        />
                        <span className="text-sm font-bold text-green-600 w-12 text-right">{brightnessLevel}%</span>
                      </div>
                    </div>
                    
                    {/* Contrast */}
                    <div>
                      <label className="text-xs text-gray-600 mb-1 block">Contrast</label>
                      <div className="flex items-center gap-2">
                        <input 
                          type="range" 
                          min="0" 
                          max="200" 
                          value={contrastLevel} 
                          onChange={(e) => setContrastLevel(Number(e.target.value))} 
                          className="flex-1 h-2 bg-green-200 rounded-lg appearance-none cursor-pointer accent-green-600" 
                        />
                        <span className="text-sm font-bold text-green-600 w-12 text-right">{contrastLevel}%</span>
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Enhancement Preview */}
                {videoData && videoData.status === 'completed' && (
                  <div className="mt-8 bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-200 rounded-2xl p-6 shadow-lg animate-slide-up-3d">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <CheckCircle className="text-green-500 mr-3 animate-pulse" size={24} />
                        <span className="text-lg font-bold text-green-800">Enhanced video is ready!</span>
                      </div>
                      <button 
                        onClick={handleDownloadVideo}
                        className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white px-6 py-3 rounded-xl text-sm font-bold transition-all duration-300 flex items-center transform hover:scale-105 hover:shadow-lg"
                      >
                        <Download className="mr-2 h-4 w-4" />
                        Download Enhanced Video
                      </button>
                    </div>
                  </div>
                )}
                
                <div className="mt-8">
                  <button 
                    onClick={handleEnhanceVideo} 
                    className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white px-8 py-4 rounded-2xl text-lg font-bold transition-all duration-300 flex items-center disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105 hover:shadow-xl" 
                    disabled={!uploadedVideoId || isUploading}
                  >
                    <Wand2 className="mr-3 h-6 w-6" />
                    Enhance Video
                  </button>
                </div>
                {renderProgressBar(enhancementProgress)}
              </div>
            </div>

            {/* Thumbnail Tab */}
            <div id="thumbnail-tab" className={`tab-content ${activeTab === 'thumbnail' ? 'block' : 'hidden'}`}>
              <div className="bg-white/80 backdrop-blur-md rounded-2xl p-8 shadow-xl border border-white/20 animate-content-reveal-3d">
                <h3 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
                  <ImageIcon className="mr-3 text-red-600 animate-pulse" size={28} />
                  Thumbnail Generation
                </h3>
                
                <div className="space-y-6">
                  <div className="space-y-4">
                    <label htmlFor="thumbnail-text" className="block text-sm font-bold text-gray-700">Add Text Overlay (Optional)</label>
                    <input 
                      type="text" 
                      id="thumbnail-text" 
                      value={thumbnailText} 
                      onChange={(e) => setThumbnailText(e.target.value)} 
                      className="block w-full px-4 py-3 border-2 border-red-200 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500 bg-white/80 backdrop-blur-sm text-sm font-medium" 
                      placeholder="Leave empty for AI generated text" 
                    />
                  </div>
                  
                  <div className="space-y-4">
                    <label className="block text-sm font-bold text-gray-700">Select Frame</label>
                    <div className="flex space-x-4 overflow-x-auto py-4 bg-gradient-to-r from-red-50 to-pink-50 p-4 rounded-2xl border-2 border-red-200 shadow-inner">
                      {isLoadingThumbnails ? (
                        <div className="flex items-center justify-center w-full h-20 text-red-600">
                          <Loader2 className="animate-spin mr-3 h-6 w-6" /> 
                          <span className="font-medium">Loading frames...</span>
                        </div>
                      ) : thumbnailFrames.length > 0 ? (
                        thumbnailFrames.map((frameSrc, index) => (
                          <div
                            key={index}
                            onClick={() => {
                              setSelectedFrameIndex(index);
                              logToConsole(`Selected frame ${index + 1} for thumbnail generation`);
                            }}
                            className={`w-32 h-20 bg-gray-200 rounded-xl cursor-pointer ring-offset-4 ring-offset-red-50 hover:ring-4 hover:ring-red-400 flex-shrink-0 overflow-hidden transition-all duration-300 transform hover:scale-110 hover:shadow-lg ${selectedFrameIndex === index ? 'ring-4 ring-red-500 scale-105' : ''}`}
                          >
                            <img src={frameSrc} alt={`Frame ${index + 1}`} className="w-full h-full object-cover" />
                          </div>
                        ))
                      ) : (
                        <div className="w-full h-20 flex items-center justify-center text-gray-500 text-sm font-medium">
                          {selectedFile ? 'No frames generated yet.' : 'Upload a video to generate frames.'}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
                
                <div className="mt-8">
                  <button 
                    onClick={handleGenerateThumbnail} 
                    className="bg-gradient-to-r from-red-600 to-pink-600 hover:from-red-700 hover:to-pink-700 text-white px-8 py-4 rounded-2xl text-lg font-bold transition-all duration-300 flex items-center disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105 hover:shadow-xl" 
                    disabled={!uploadedVideoId || selectedFrameIndex === null || isUploading}
                  >
                    <ImageIcon className="mr-3 h-6 w-6" />
                    Generate Thumbnail
                  </button>
                </div>
                {renderProgressBar(thumbnailProgress)}
                
                {generatedThumbnail && (
                  <div id="thumbnail-result" className="mt-8 bg-gradient-to-br from-red-50 to-pink-50 border-2 border-red-200 rounded-2xl p-6 shadow-lg animate-slide-up-3d">
                    <h4 className="text-lg font-bold text-red-900 mb-4 flex items-center">
                      <Star className="mr-2" size={20} />
                      Generated Thumbnail
                    </h4>
                    <div className="w-full max-w-md bg-white rounded-2xl overflow-hidden border-2 border-red-200 shadow-xl transform hover:scale-105 transition-all duration-300">
                      <img id="generated-thumbnail" src={generatedThumbnail} alt="Generated Thumbnail" className="w-full h-auto block" />
                    </div>
                    
                    {/* Edit Thumbnail Controls */}
                    <div className="mt-6 bg-white rounded-xl p-6 border-2 border-red-200">
                      <h5 className="text-md font-bold text-gray-900 mb-4">Edit Thumbnail Text</h5>
                      
                      {/* Edit Text */}
                      <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-2">Text</label>
                        <input
                          type="text"
                          value={thumbnailText}
                          onChange={(e) => setThumbnailText(e.target.value)}
                          className="block w-full px-4 py-2 border-2 border-red-200 rounded-lg focus:ring-2 focus:ring-red-500"
                          placeholder="Edit thumbnail text"
                        />
                      </div>
                      
                      {/* Font Size */}
                      <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Font Size: {thumbnailFontSize}px
                        </label>
                        <input
                          type="range"
                          min="50"
                          max="200"
                          value={thumbnailFontSize}
                          onChange={(e) => setThumbnailFontSize(Number(e.target.value))}
                          className="w-full h-2 bg-red-200 rounded-lg appearance-none cursor-pointer accent-red-600"
                        />
                      </div>
                      
                      {/* Position */}
                      <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-2">Position</label>
                        <select
                          value={thumbnailPosition}
                          onChange={(e) => setThumbnailPosition(e.target.value)}
                          className="block w-full px-4 py-2 border-2 border-red-200 rounded-lg focus:ring-2 focus:ring-red-500"
                        >
                          <option value="top">Top</option>
                          <option value="center">Center</option>
                          <option value="bottom">Bottom</option>
                        </select>
                      </div>
                      
                      {/* Colors */}
                      <div className="grid grid-cols-2 gap-4 mb-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Text Color</label>
                          <input
                            type="color"
                            value={thumbnailTextColor}
                            onChange={(e) => setThumbnailTextColor(e.target.value)}
                            className="w-full h-10 rounded-lg cursor-pointer border-2 border-red-200"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Outline Color</label>
                          <input
                            type="color"
                            value={thumbnailOutlineColor}
                            onChange={(e) => setThumbnailOutlineColor(e.target.value)}
                            className="w-full h-10 rounded-lg cursor-pointer border-2 border-red-200"
                          />
                        </div>
                      </div>
                      
                      {/* Background Color (only shown when background is enabled) */}
                      {thumbnailBackground && (
                        <div className="mb-4">
                          <label className="block text-sm font-medium text-gray-700 mb-2">Background Color</label>
                          <input
                            type="color"
                            value={thumbnailBackgroundColor}
                            onChange={(e) => setThumbnailBackgroundColor(e.target.value)}
                            className="w-full h-10 rounded-lg cursor-pointer border-2 border-red-200"
                          />
                        </div>
                      )}
                      
                      {/* Font Style */}
                      <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-2">Font Style</label>
                        <select
                          value={thumbnailFontStyle}
                          onChange={(e) => setThumbnailFontStyle(e.target.value)}
                          className="block w-full px-4 py-2 border-2 border-red-200 rounded-lg focus:ring-2 focus:ring-red-500"
                        >
                          <option value="bold">Bold</option>
                          <option value="regular">Regular</option>
                          <option value="italic">Italic</option>
                          <option value="bold-italic">Bold Italic</option>
                          <option value="light">Light</option>
                        </select>
                      </div>
                      
                      {/* Toggles */}
                      <div className="flex gap-4 mb-4">
                        <label className="flex items-center space-x-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={thumbnailShadow}
                            onChange={(e) => setThumbnailShadow(e.target.checked)}
                            className="w-4 h-4 text-red-600 border-red-300 rounded focus:ring-red-500"
                          />
                          <span className="text-sm font-medium text-gray-700">Shadow</span>
                        </label>
                        <label className="flex items-center space-x-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={thumbnailBackground}
                            onChange={(e) => setThumbnailBackground(e.target.checked)}
                            className="w-4 h-4 text-red-600 border-red-300 rounded focus:ring-red-500"
                          />
                          <span className="text-sm font-medium text-gray-700">Background</span>
                        </label>
                      </div>
                      
                      {/* Regenerate Button */}
                      <button
                        onClick={handleGenerateThumbnail}
                        className="w-full bg-gradient-to-r from-red-600 to-pink-600 hover:from-red-700 hover:to-pink-700 text-white px-6 py-3 rounded-xl text-sm font-bold transition-all duration-300 flex items-center justify-center transform hover:scale-105 hover:shadow-lg"
                        disabled={!uploadedVideoId || selectedFrameIndex === null}
                      >
                        <ImageIcon className="mr-2 h-4 w-4" />
                        Regenerate Thumbnail
                      </button>
                    </div>
                    
                    <div className="mt-6">
                      <button 
                        onClick={handleDownloadThumbnail} 
                        className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white px-6 py-3 rounded-xl text-sm font-bold transition-all duration-300 flex items-center transform hover:scale-105 hover:shadow-lg"
                      >
                        <Download className="mr-2 h-4 w-4" />
                        Download Thumbnail
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Enhanced Video Preview Section */}
          <div className="mt-12">
            <h3 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
              <Eye className="mr-3 text-blue-600 animate-pulse" size={28} />
              Live Preview
            </h3>
            
            <div 
              className="video-preview flex items-center justify-center bg-gradient-to-br from-gray-900 to-black relative rounded-2xl overflow-hidden shadow-2xl aspect-video border-4 border-white/20"
            >
              {!videoSrc ? (
                <div id="video-placeholder" className="text-center text-gray-400 p-12">
                  <div className="mb-8">
                    <Video className="mx-auto mb-6 animate-float-3d" size={80} />
                    <Sparkles className="mx-auto text-purple-400 animate-sparkle-3d" size={40} />
                  </div>
                  <p className="text-2xl font-bold mb-2">AI Video Preview</p>
                  <p className="text-lg">Upload a video to see the magic happen</p>
                </div>
              ) : (
                <div className="w-full h-full relative bg-black" style={{ filter: previewFilters }}>
                  <VideoPlayer
                    videoUrl={videoSrc}
                    videoId={isAuthenticated ? (uploadedVideoId ?? undefined) : undefined}
                    subtitles={subtitleData.length > 0 ? subtitleData : undefined}
                    onTimeUpdate={(_time) => {
                      // Optional: handle time updates if needed
                    }}
                  />
                  {aiColorEnhancement && (
                    <div className="absolute top-4 left-4 bg-purple-600/90 backdrop-blur-sm text-white px-4 py-2 rounded-full flex items-center space-x-2 shadow-lg animate-pulse">
                      <Sparkles size={16} />
                      <span className="text-sm font-bold">AI Enhanced Preview</span>
                    </div>
                  )}
                  {showProcessedVideo && videoData?.outputs?.processed_video && (
                    <div className="absolute top-4 left-4 bg-green-600/90 backdrop-blur-sm text-white px-4 py-2 rounded-full flex items-center space-x-2 shadow-lg">
                      <CheckCircle size={16} />
                      <span className="text-sm font-bold">Processed Video (Fillers Removed)</span>
                    </div>
                  )}
                </div>
              )}
              {isLoadingPreview && (
                <div id="preview-loading" className="absolute inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50">
                  <div className="text-center">
                    <Loader2 className="animate-spin h-16 w-16 text-purple-400 mb-4" />
                    <p className="text-white text-xl font-bold">AI Processing...</p>
                  </div>
                </div>
              )}
            </div>
            
            {/* Enhanced Live Preview Controls */}
            {videoSrc && (
              <div className="mt-6 space-y-6">
                {/* Transcript Viewer with Auto-Transcription - Only show in audio tab */}
                {uploadedVideoId && isAuthenticated && activeTab === 'audio' && (
                  <TranscriptViewer
                    key={transcriptKey}
                    videoId={uploadedVideoId}
                    onSeek={(time) => {
                      const videoElement = document.querySelector('video') as HTMLVideoElement;
                      if (videoElement) {
                        videoElement.currentTime = time;
                        videoElement.play();
                      }
                    }}
                    onRemoveFillers={() => {
                      console.log('[FRONTEND] Remove fillers clicked from transcript');
                      handleProcessAudio();
                    }}
                  />
                )}

                {/* Original vs Processed Video Toggle - Only show in audio tab */}
                {videoData?.outputs?.processed_video && uploadedVideoId && isAuthenticated && activeTab === 'audio' && (
                  <div className="bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-200 rounded-2xl p-6 shadow-lg">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4">
                        <Film className="h-6 w-6 text-green-600" />
                        <span className="text-lg font-bold text-green-900">
                          Video Version
                        </span>
                      </div>
                      <button
                        onClick={async () => {
                          const token = localStorage.getItem('token');
                          const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:5001';
                          
                          try {
                            // Revoke old blob URL if exists
                            if (videoBlobUrl) {
                              URL.revokeObjectURL(videoBlobUrl);
                              setVideoBlobUrl(null);
                            }
                            
                            if (showProcessedVideo) {
                              // Switch to original - use /download/original endpoint
                              if (selectedFile) {
                                const blobUrl = URL.createObjectURL(selectedFile);
                                setVideoBlobUrl(blobUrl);
                                setVideoSrc(blobUrl);
                              } else {
                                console.log('[VIDEO] Fetching original video...');
                                const response = await fetch(`${apiUrl}/videos/${uploadedVideoId}/download/original`, {
                                  headers: {
                                    'ngrok-skip-browser-warning': 'true',
                                    'Authorization': `Bearer ${token}`
                                  }
                                });
                                
                                if (!response.ok) {
                                  throw new Error(`Failed to fetch: ${response.status} ${response.statusText}`);
                                }
                                
                                const contentType = response.headers.get('content-type');
                                console.log('[VIDEO] Content-Type:', contentType);
                                
                                const blob = await response.blob();
                                console.log('[VIDEO] Blob size:', blob.size, 'type:', blob.type);
                                
                                const blobUrl = URL.createObjectURL(blob);
                                setVideoBlobUrl(blobUrl);
                                setVideoSrc(blobUrl);
                              }
                              setShowProcessedVideo(false);
                              toast.success('Switched to original video');
                            } else {
                              // Switch to processed - use /download endpoint
                              console.log('[VIDEO] Fetching processed video...');
                              const response = await fetch(`${apiUrl}/videos/${uploadedVideoId}/download`, {
                                headers: {
                                  'ngrok-skip-browser-warning': 'true',
                                  'Authorization': `Bearer ${token}`
                                }
                              });
                              
                              if (!response.ok) {
                                throw new Error(`Failed to fetch: ${response.status} ${response.statusText}`);
                              }
                              
                              const contentType = response.headers.get('content-type');
                              console.log('[VIDEO] Content-Type:', contentType);
                              
                              const blob = await response.blob();
                              console.log('[VIDEO] Blob size:', blob.size, 'type:', blob.type);
                              
                              const blobUrl = URL.createObjectURL(blob);
                              setVideoBlobUrl(blobUrl);
                              setVideoSrc(blobUrl);
                              setShowProcessedVideo(true);
                              toast.success('Switched to processed video (fillers removed)');
                            }
                          } catch (error: any) {
                            console.error('[VIDEO] Error loading video:', error);
                            toast.error('Failed to load video: ' + error.message);
                          }
                        }}
                        className={`px-6 py-3 rounded-lg font-bold text-white transition-all ${
                          showProcessedVideo
                            ? 'bg-blue-600 hover:bg-blue-700'
                            : 'bg-green-600 hover:bg-green-700'
                        }`}
                      >
                        {showProcessedVideo ? 'View Original' : 'View Processed (Fillers Removed)'}
                      </button>
                    </div>
                    <p className="text-sm text-green-600 mt-2">
                      {showProcessedVideo 
                        ? '✅ Now showing enhanced video with fillers removed'
                        : '📹 Now showing original uploaded video'}
                    </p>
                  </div>
                )}
                
                {/* Subtitle Controls */}
                {(subtitleData.length > 0 || generatedSubtitles) && (
                  <div className="bg-gradient-to-r from-blue-50 to-cyan-50 border-2 border-blue-200 rounded-2xl p-6 shadow-lg animate-slide-in-3d">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4">
                        <Captions className="h-6 w-6 text-blue-600 animate-pulse" />
                        <span className="text-lg font-bold text-blue-900">
                          {subtitleData.length > 0 
                            ? `Live Subtitles Active (${subtitleData.length} segments)`
                            : `Subtitles Generated (${generatedSubtitles ? 'SRT format' : 'Processing...'})`
                          }
                        </span>
                      </div>
                      <div className="text-sm font-medium text-blue-700 bg-blue-100 rounded-full px-4 py-2">
                        {subtitleData.length > 0 
                          ? 'Real-time Whisper AI transcription'
                          : 'Use CC button in player controls'
                        }
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Enhanced API Console - Collapsible */}
          <div className="mt-12">
            <button 
              onClick={() => setShowConsole(!showConsole)}
              className="w-full text-left text-xl font-bold text-gray-900 mb-4 flex items-center justify-between bg-gradient-to-r from-gray-100 to-gray-50 hover:from-gray-200 hover:to-gray-100 px-6 py-4 rounded-2xl transition-all duration-300 border border-gray-200 shadow-md hover:shadow-lg"
            >
              <span className="flex items-center">
                <Zap className="mr-3 text-green-600 animate-pulse" size={24} />
                API Console
              </span>
              <span className={`transform transition-transform duration-300 ${showConsole ? 'rotate-180' : ''}`}>
                ▼
              </span>
            </button>
            {showConsole && (
              <div 
                id="api-console" 
                ref={consoleRef} 
                className="api-console text-sm bg-gradient-to-br from-gray-900 to-black text-green-400 font-mono p-6 rounded-2xl h-64 overflow-y-auto border-2 border-gray-700 scroll-smooth shadow-2xl backdrop-blur-md animate-slide-down"
              >
                {consoleLogs.map((log, index) => (
                  <div key={index} className="console-line whitespace-pre-wrap break-words mb-2 last:mb-0 animate-message-slide-3d" style={{ animationDelay: `${index * 50}ms` }}>
                    <span className="text-gray-500 mr-3 select-none">[{log.timestamp}]</span>
                    <span className={
                      log.type === 'success' ? 'text-green-400 font-bold' : 
                      log.type === 'error' ? 'text-red-400 font-bold' : 
                      log.message.startsWith('[System]') ? 'text-blue-400 font-bold' : 'text-green-400'
                    }>{log.message}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Optimized Custom Styles - Fixed hanging animations */}
      <style>{`
        /* Performance optimized animations */
        @keyframes progress-glow {
          0%, 100% { box-shadow: 0 0 10px rgba(139, 92, 246, 0.4); }
          50% { box-shadow: 0 0 15px rgba(139, 92, 246, 0.6); }
        }
        
        @keyframes gentle-float {
          0%, 100% { 
            transform: translateY(0px); 
            opacity: 0.8;
          }
          50% { 
            transform: translateY(-8px); 
            opacity: 1;
          }
        }
        
        @keyframes gentle-spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        
        @keyframes gentle-bounce {
          0%, 100% { 
            transform: translateY(0px); 
            opacity: 0.6;
          }
          50% { 
            transform: translateY(-4px); 
            opacity: 8;
          }
        }
        
        /* Hardware acceleration for smooth performance */
        .animate-spin, .animate-pulse, .animate-bounce {
          will-change: transform, opacity;
          transform: translateZ(0);
        }
        
        /* Ensure text clarity */
        * {
          text-rendering: optimizeLegibility;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
          backface-visibility: hidden;
        }
        
        /* Optimize transitions */
        .transition-all {
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        /* Reduce motion for accessibility */
        @media (prefers-reduced-motion: reduce) {
          *, *::before, *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
          }
        }
      `}</style>
    </div>
  );
};

export default Features;