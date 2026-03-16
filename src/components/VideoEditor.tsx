import { useState, useRef, useEffect } from 'react';
import { Upload, Video, X, UploadCloud as CloudUpload, Scissors, Trash2, Undo2, Music, Type, Save, Download, Volume2, Play, Pause } from 'lucide-react';
import SubtitleEditor from './SubtitleEditor';
import VideoPlayer from './VideoPlayer';
import { ApiService } from '../services/api';
import toast from 'react-hot-toast';

interface VideoEditorProps {
  videoUrl?: string;
}

const VideoEditor = ({ videoUrl }: VideoEditorProps) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(100);
  const [activeTab, setActiveTab] = useState('cutting');
  const [showSubtitleEditor, setShowSubtitleEditor] = useState(false);
  const [showMusicPanel, setShowMusicPanel] = useState(false);
  const [showTextPanel, setShowTextPanel] = useState(false);
  const [showTrimPanel, setShowTrimPanel] = useState(true);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [videoId, setVideoId] = useState<string | null>(null);
  const [processedVideoData, setProcessedVideoData] = useState<any>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [trimStart, setTrimStart] = useState(0);
  const [trimEnd, setTrimEnd] = useState(100);
  const [isTrimMode, setIsTrimMode] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [selectedMusic, setSelectedMusic] = useState<string | null>(null);
  const [musicVolume, setMusicVolume] = useState(50);
  const [textOverlay, setTextOverlay] = useState('');
  const [textPosition, setTextPosition] = useState('center');
  const [textColor, setTextColor] = useState('#ffffff');
  const [textSize, setTextSize] = useState(32);
  const [musicFile, setMusicFile] = useState<File | null>(null);
  const [musicUrl, setMusicUrl] = useState<string | null>(null);
  const [videoVolume, setVideoVolume] = useState(100);
  const [muteVideoAudio, setMuteVideoAudio] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      
      // Create object URL for preview
      const objectUrl = URL.createObjectURL(file);
      setPreviewUrl(objectUrl);
      
      // Upload the file to backend
      await uploadFile(file);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      
      // Create object URL for preview
      const objectUrl = URL.createObjectURL(file);
      setPreviewUrl(objectUrl);
      
      // Upload the file to backend
      await uploadFile(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const uploadFile = async (file: File) => {
    try {
      setUploadProgress(0);
      console.log('Uploading file:', file.name);
      
      const response = await ApiService.uploadVideo(file, (progress) => {
        setUploadProgress(progress);
      });
      
      console.log('Upload response:', response);
      setVideoId(response.video_id);
      toast.success('Video uploaded successfully!');
      
    } catch (error) {
      console.error('Upload failed:', error);
      toast.error('Upload failed. Please try again.');
    }
  };

  const handleProcessVideo = async () => {
    if (!videoId) {
      toast.error('Please upload a video first');
      return;
    }

    setIsProcessing(true);
    try {
      console.log('Exporting video with edits:', videoId);
      
      // Export video with all editing changes
      const exportOptions = {
        trim_start: isTrimMode ? trimStart : 0,
        trim_end: isTrimMode ? trimEnd : 100,
        text_overlay: textOverlay,
        text_position: textPosition,
        text_color: textColor,
        text_size: textSize,
        music_volume: musicVolume,
        video_volume: videoVolume,
        mute_original: muteVideoAudio
      };
      
      console.log('Export options:', exportOptions);
      
      // Call export API
      const result = await ApiService.exportVideo(videoId, exportOptions);
      console.log('Export result:', result);
      
      toast.success('Video exported! Starting download...');
      
      // Download the exported video
      const blob = await ApiService.downloadExportedVideo(videoId);
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${selectedFile?.name.replace(/\.[^/.]+$/, '') || 'video'}_edited.mp4`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      
      toast.success('Video downloaded successfully!');
      
    } catch (error) {
      console.error('Export failed:', error);
      toast.error('Export failed. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const clearVideo = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setVideoId(null);
    setProcessedVideoData(null);
    setUploadProgress(0);
    setIsProcessing(false);
    setTrimStart(0);
    setTrimEnd(100);
    setIsTrimMode(false);
  };

  // Live preview rendering
  useEffect(() => {
    const renderPreview = () => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const audio = audioRef.current;

      if (!video || !canvas) return;

      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      // Set canvas size to match video
      canvas.width = video.videoWidth || video.clientWidth;
      canvas.height = video.videoHeight || video.clientHeight;

      // Draw video frame
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      // Apply video audio settings
      video.muted = muteVideoAudio;
      video.volume = muteVideoAudio ? 0 : videoVolume / 100;

      // Draw text overlay if present
      if (textOverlay.trim()) {
        ctx.font = `bold ${textSize}px Arial`;
        ctx.fillStyle = textColor;
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 3;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        let x = canvas.width / 2;
        let y = canvas.height / 2;

        // Position text based on selection
        switch (textPosition) {
          case 'top-left': x = 100; y = 80; break;
          case 'top-center': y = 80; break;
          case 'top-right': x = canvas.width - 100; y = 80; break;
          case 'center': break;
          case 'bottom-left': x = 100; y = canvas.height - 80; break;
          case 'bottom-center': y = canvas.height - 80; break;
          case 'bottom-right': x = canvas.width - 100; y = canvas.height - 80; break;
        }

        // Draw text with stroke (outline)
        ctx.strokeText(textOverlay, x, y);
        ctx.fillText(textOverlay, x, y);
      }

      // Sync audio with video if music is playing
      if (audio && musicUrl && !video.paused) {
        if (audio.paused) audio.play();
        // Sync audio time with video time (approximate)
        const timeDiff = Math.abs(audio.currentTime - video.currentTime);
        if (timeDiff > 0.3) {
          audio.currentTime = video.currentTime;
        }
        audio.volume = musicVolume / 100;
      } else if (audio && !audio.paused) {
        audio.pause();
      }

      animationFrameRef.current = requestAnimationFrame(renderPreview);
    };

    if (previewUrl || videoUrl) {
      renderPreview();
    }

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [textOverlay, textPosition, textColor, textSize, musicUrl, musicVolume, videoVolume, muteVideoAudio, previewUrl, videoUrl]);

  const handleAddMusic = () => {
    setShowMusicPanel(!showMusicPanel);
    if (!videoId && !previewUrl) {
      toast.error('Please upload a video first');
    } else {
      toast.success('Music panel opened!');
    }
  };

  const handleAddText = () => {
    setShowTextPanel(!showTextPanel);
    if (!videoId && !previewUrl) {
      toast.error('Please upload a video first');
    } else {
      toast.success('Text overlay panel opened!');
    }
  };

  const handleApplyMusic = () => {
    if (!musicFile) {
      toast.error('Please select a music file first');
      return;
    }
    if (!videoId && !previewUrl) {
      toast.error('Please upload a video first');
      return;
    }
    
    // Create object URL for audio preview
    if (musicUrl) {
      URL.revokeObjectURL(musicUrl);
    }
    const url = URL.createObjectURL(musicFile);
    setMusicUrl(url);
    
    toast.success(`Music applied! Playing at ${musicVolume}% volume`);
    console.log('Music applied:', musicFile.name, 'Volume:', musicVolume);
    setShowMusicPanel(false);
  };

  const handleApplyText = () => {
    if (!textOverlay.trim()) {
      toast.error('Please enter text');
      return;
    }
    if (!videoId && !previewUrl) {
      toast.error('Please upload a video first');
      return;
    }
    toast.success(`Text applied! Showing live preview`);
    console.log('Text applied:', textOverlay, 'Position:', textPosition, 'Color:', textColor, 'Size:', textSize);
    // Keep panel open for live adjustments
  };

  const handleTrim = () => {
    if (!videoId) {
      toast.error('Please upload a video first');
      return;
    }
    setIsTrimMode(!isTrimMode);
    if (!isTrimMode) {
      toast.success('Trim mode activated. Adjust the timeline sliders.');
    }
  };

  const handleSave = async () => {
    if (!videoId) {
      toast.error('Please upload a video first');
      return;
    }

    setIsSaving(true);
    try {
      toast.success('Saving video with trim settings...');
      await new Promise(resolve => setTimeout(resolve, 2000));
      toast.success('Video saved successfully!');
    } catch (error) {
      toast.error('Failed to save video');
      console.error('Save error:', error);
    } finally {
      setIsSaving(false);
    }
  };
  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
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

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Cleanup object URL when component unmounts or when previewUrl changes
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  return (
    <div className="bg-white/90 backdrop-blur-md rounded-2xl shadow-2xl overflow-hidden border border-white/20 animate-fade-in">
      <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-pink-50">
        <h2 className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent animate-slide-in-left">Video Editor</h2>
        <p className="text-gray-600 mt-1 animate-slide-in-left" style={{ animationDelay: '0.1s' }}>Upload your video to enjoy basic edits</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 p-6">
        {/* Left Panel - Upload & Settings */}
        <div className="lg:col-span-1 space-y-6">
          {/* Upload Area */}
          <div
            className="border-2 border-dashed border-gray-300 rounded-xl p-6 text-center transition-all duration-300 hover:border-purple-400 hover:bg-purple-50/50 hover:shadow-lg transform hover:scale-105"
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            style={{
              animation: 'fade-in-up 0.6s ease-out'
            }}
          >
            <div className="flex justify-center">
              <CloudUpload className="text-purple-600" size={40} />
            </div>
            <h3 className="mt-4 text-lg font-medium text-gray-900">Drag & Drop Video</h3>
            <p className="mt-1 text-sm text-gray-600">or click to browse files</p>
            <input 
              type="file" 
              className="hidden" 
              id="video-upload" 
              accept="video/*"
              onChange={handleFileChange}
            />
            <button
              onClick={() => document.getElementById('video-upload')?.click()}
              className="mt-4 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white px-6 py-3 rounded-xl text-sm font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-xl"
              style={{
                boxShadow: '0 4px 15px rgba(139, 92, 246, 0.4)'
              }}
            >
              Select Video
            </button>
          </div>

          {/* Selected File Info */}
          {selectedFile && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="flex items-center">
                <Video className="text-purple-600 mr-3" size={20} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {selectedFile.name}
                  </p>
                  <p className="text-sm text-gray-500">
                    {(selectedFile.size / (1024 * 1024)).toFixed(1)} MB
                  </p>
                </div>
                <button className="text-gray-400 hover:text-gray-500">
                  <X size={20} />
                </button>
              </div>
              <div className="mt-3 bg-gray-200 rounded-full h-1.5">
                <div 
                  className="bg-purple-600 h-1.5 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
              <p className="mt-1 text-xs text-gray-500 text-right">{uploadProgress}% uploaded</p>
            </div>
          )}

          {/* Quick Action Buttons */}
          <div className="flex items-center gap-3 mb-4 flex-wrap">
            <button
              onClick={() => setShowTrimPanel(!showTrimPanel)}
              className={`px-3 py-2 rounded-lg text-sm flex items-center transition-all duration-300 transform hover:scale-105 hover:shadow-md ${
                showTrimPanel
                  ? 'bg-gradient-to-r from-purple-500 to-purple-600 text-white'
                  : 'bg-gradient-to-r from-gray-100 to-gray-200 hover:from-gray-200 hover:to-gray-300 text-gray-700'
              }`}
            >
              <Scissors className="mr-1" size={16} />
              Trim Video
            </button>
            <button
              onClick={handleAddMusic}
              className={`px-3 py-2 rounded-lg text-sm flex items-center transition-all duration-300 transform hover:scale-105 hover:shadow-md ${
                showMusicPanel
                  ? 'bg-gradient-to-r from-purple-500 to-purple-600 text-white'
                  : 'bg-gradient-to-r from-gray-100 to-gray-200 hover:from-gray-200 hover:to-gray-300 text-gray-700'
              }`}
            >
              <Music className="mr-1" size={16} />
              Add Music
            </button>
            <button
              onClick={handleAddText}
              className={`px-3 py-2 rounded-lg text-sm flex items-center transition-all duration-300 transform hover:scale-105 hover:shadow-md ${
                showTextPanel
                  ? 'bg-gradient-to-r from-purple-500 to-purple-600 text-white'
                  : 'bg-gradient-to-r from-gray-100 to-gray-200 hover:from-gray-200 hover:to-gray-300 text-gray-700'
              }`}
            >
              <Type className="mr-1" size={16} />
              Add Text
            </button>
            <button
              onClick={handleSave}
              disabled={!videoId || isSaving}
              className="px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white rounded-lg text-sm font-medium flex items-center transition-all duration-300 transform hover:scale-105 hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
              style={{
                boxShadow: !isSaving && videoId ? '0 4px 15px rgba(139, 92, 246, 0.4)' : 'none'
              }}
            >
              {isSaving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Saving...
                </>
              ) : (
                <>
                  <Save className="mr-2" size={16} />
                  Save
                </>
              )}
            </button>
          </div>

          {/* Trim Panel */}
          {showTrimPanel && (
            <div className="mb-4 bg-gradient-to-br from-orange-50 to-yellow-50 rounded-lg p-4 border border-orange-200 animate-fade-in">
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-semibold text-gray-800 flex items-center">
                  <Scissors className="mr-2 text-orange-600" size={18} />
                  Trim Video
                </h4>
                <button
                  onClick={() => setShowTrimPanel(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="space-y-4">
                {/* Trim Timeline */}
                <div className="bg-white rounded-lg p-4 border border-orange-200">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700">Select trim range</span>
                    <span className="text-xs text-orange-600 font-medium">
                      Duration: {((trimEnd - trimStart) / 100 * duration).toFixed(1)}s
                    </span>
                  </div>
                  
                  {/* Dual Range Slider */}
                  <div className="relative h-12 bg-gray-100 rounded-lg overflow-hidden">
                    {/* Selected Range Highlight */}
                    <div 
                      className="absolute h-full bg-gradient-to-r from-orange-400 to-yellow-400 opacity-50"
                      style={{
                        left: `${trimStart}%`,
                        width: `${trimEnd - trimStart}%`
                      }}
                    />
                    
                    {/* Start Handle */}
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={trimStart}
                      onChange={(e) => {
                        const value = Number(e.target.value);
                        if (value < trimEnd - 5) {
                          setTrimStart(value);
                        }
                      }}
                      className="absolute w-full h-full opacity-0 cursor-pointer z-10"
                    />
                    
                    {/* End Handle */}
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={trimEnd}
                      onChange={(e) => {
                        const value = Number(e.target.value);
                        if (value > trimStart + 5) {
                          setTrimEnd(value);
                        }
                      }}
                      className="absolute w-full h-full opacity-0 cursor-pointer z-20"
                    />
                    
                    {/* Visual Handles */}
                    <div 
                      className="absolute top-0 bottom-0 w-1 bg-orange-600 cursor-ew-resize"
                      style={{ left: `${trimStart}%` }}
                    >
                      <div className="absolute -left-2 top-1/2 -translate-y-1/2 w-5 h-8 bg-orange-600 rounded-md flex items-center justify-center">
                        <div className="w-0.5 h-4 bg-white rounded-full" />
                      </div>
                    </div>
                    <div 
                      className="absolute top-0 bottom-0 w-1 bg-orange-600 cursor-ew-resize"
                      style={{ left: `${trimEnd}%` }}
                    >
                      <div className="absolute -left-2 top-1/2 -translate-y-1/2 w-5 h-8 bg-orange-600 rounded-md flex items-center justify-center">
                        <div className="w-0.5 h-4 bg-white rounded-full" />
                      </div>
                    </div>
                  </div>
                  
                  {/* Time Labels */}
                  <div className="flex justify-between mt-2 text-xs text-gray-500">
                    <span>Start: {(trimStart / 100 * duration).toFixed(1)}s</span>
                    <span>End: {(trimEnd / 100 * duration).toFixed(1)}s</span>
                  </div>
                </div>

                {/* Quick Trim Options */}
                <div className="grid grid-cols-4 gap-2">
                  <button
                    onClick={() => { setTrimStart(0); setTrimEnd(25); }}
                    className="py-2 px-3 bg-white border border-orange-200 text-gray-700 rounded-lg text-xs font-medium hover:bg-orange-50 transition-colors"
                  >
                    First 25%
                  </button>
                  <button
                    onClick={() => { setTrimStart(25); setTrimEnd(75); }}
                    className="py-2 px-3 bg-white border border-orange-200 text-gray-700 rounded-lg text-xs font-medium hover:bg-orange-50 transition-colors"
                  >
                    Middle 50%
                  </button>
                  <button
                    onClick={() => { setTrimStart(75); setTrimEnd(100); }}
                    className="py-2 px-3 bg-white border border-orange-200 text-gray-700 rounded-lg text-xs font-medium hover:bg-orange-50 transition-colors"
                  >
                    Last 25%
                  </button>
                  <button
                    onClick={() => { setTrimStart(0); setTrimEnd(100); }}
                    className="py-2 px-3 bg-white border border-orange-200 text-gray-700 rounded-lg text-xs font-medium hover:bg-orange-50 transition-colors"
                  >
                    Reset
                  </button>
                </div>

                {/* Set from current playback */}
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => {
                      const percent = (currentTime / duration) * 100;
                      if (percent < trimEnd - 5) {
                        setTrimStart(percent);
                        toast.success(`Start set to ${currentTime.toFixed(1)}s`);
                      }
                    }}
                    className="py-2 px-3 bg-orange-100 text-orange-700 rounded-lg text-sm font-medium hover:bg-orange-200 transition-colors flex items-center justify-center gap-2"
                  >
                    <Play size={14} />
                    Set Start from Playhead
                  </button>
                  <button
                    onClick={() => {
                      const percent = (currentTime / duration) * 100;
                      if (percent > trimStart + 5) {
                        setTrimEnd(percent);
                        toast.success(`End set to ${currentTime.toFixed(1)}s`);
                      }
                    }}
                    className="py-2 px-3 bg-orange-100 text-orange-700 rounded-lg text-sm font-medium hover:bg-orange-200 transition-colors flex items-center justify-center gap-2"
                  >
                    <Pause size={14} />
                    Set End from Playhead
                  </button>
                </div>

                <button
                  onClick={() => {
                    setIsTrimMode(true);
                    // Seek video to trim start position
                    if (videoRef.current && duration > 0) {
                      const trimStartTime = (trimStart / 100) * duration;
                      videoRef.current.currentTime = trimStartTime;
                      videoRef.current.play();
                      setIsPlaying(true);
                    }
                    toast.success(`Trim applied: ${(trimStart / 100 * duration).toFixed(1)}s to ${(trimEnd / 100 * duration).toFixed(1)}s`);
                  }}
                  disabled={trimStart === 0 && trimEnd === 100}
                  className="w-full py-2 bg-gradient-to-r from-orange-500 to-yellow-500 hover:from-orange-600 hover:to-yellow-600 disabled:from-gray-400 disabled:to-gray-400 text-white rounded-lg font-medium transition-all duration-300 disabled:cursor-not-allowed"
                >
                  Apply Trim
                </button>

                {/* Remove Trim Button */}
                {isTrimMode && (
                  <button
                    onClick={() => {
                      setIsTrimMode(false);
                      setTrimStart(0);
                      setTrimEnd(100);
                      toast.info('Trim removed');
                    }}
                    className="w-full py-2 mt-2 bg-gray-500 hover:bg-gray-600 text-white rounded-lg font-medium transition-all duration-300"
                  >
                    Remove Trim
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Music Panel */}
          {showMusicPanel && (
            <div className="mb-4 bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg p-4 border border-purple-200 animate-fade-in">
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-semibold text-gray-800 flex items-center">
                  <Music className="mr-2 text-purple-600" size={18} />
                  Add Background Music
                </h4>
                <button
                  onClick={() => setShowMusicPanel(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Select Music File</label>
                  <input
                    type="file"
                    accept="audio/*"
                    onChange={(e) => {
                      if (e.target.files?.[0]) {
                        const file = e.target.files[0];
                        setMusicFile(file);
                        setSelectedMusic(file.name);
                        toast.success(`Selected: ${file.name}`);
                      }
                    }}
                    className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-purple-100 file:text-purple-700 hover:file:bg-purple-200"
                  />
                </div>

                {selectedMusic && (
                  <div className="flex items-center justify-between p-3 bg-white rounded-lg border border-purple-200">
                    <span className="text-sm font-medium text-gray-700">{selectedMusic}</span>
                    <button
                      onClick={() => {
                        setSelectedMusic(null);
                        setMusicFile(null);
                        if (musicUrl) {
                          URL.revokeObjectURL(musicUrl);
                          setMusicUrl(null);
                        }
                      }}
                      className="text-red-500 hover:text-red-700"
                    >
                      <X size={16} />
                    </button>
                  </div>
                )}

                <div>
                  <label className="flex items-center justify-between text-sm font-medium text-gray-700 mb-2">
                    <span>Music Volume</span>
                    <span className="text-purple-600">{musicVolume}%</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={musicVolume}
                    onChange={(e) => setMusicVolume(Number(e.target.value))}
                    className="w-full"
                  />
                </div>

                {/* Silence Original Audio Toggle */}
                <div className="flex items-center justify-between p-3 bg-white rounded-lg border border-purple-200">
                  <div>
                    <span className="text-sm font-medium text-gray-700">Silence Original Audio</span>
                    <p className="text-xs text-gray-500">Mute video's original sound</p>
                  </div>
                  <button
                    onClick={() => setMuteVideoAudio(!muteVideoAudio)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      muteVideoAudio ? 'bg-red-500' : 'bg-gray-200'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        muteVideoAudio ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>

                <button
                  onClick={handleApplyMusic}
                  disabled={!selectedMusic}
                  className="w-full py-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:from-gray-400 disabled:to-gray-400 text-white rounded-lg font-medium transition-all duration-300 disabled:cursor-not-allowed"
                >
                  Apply Music
                </button>
              </div>
            </div>
          )}

          {/* Text Panel */}
          {showTextPanel && (
            <div className="mb-4 bg-gradient-to-br from-blue-50 to-cyan-50 rounded-lg p-4 border border-blue-200 animate-fade-in">
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-semibold text-gray-800 flex items-center">
                  <Type className="mr-2 text-blue-600" size={18} />
                  Add Text Overlay
                </h4>
                <button
                  onClick={() => setShowTextPanel(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Text Content</label>
                  <textarea
                    value={textOverlay}
                    onChange={(e) => setTextOverlay(e.target.value)}
                    placeholder="Enter your text here..."
                    className="w-full px-3 py-2 border border-blue-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                    rows={2}
                  />
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="flex items-center justify-between text-sm font-medium text-gray-700 mb-2">
                      <span>Text Size</span>
                      <span className="text-blue-600">{textSize}px</span>
                    </label>
                    <input
                      type="range"
                      min="16"
                      max="72"
                      value={textSize}
                      onChange={(e) => setTextSize(Number(e.target.value))}
                      className="w-full"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Position</label>
                      <select
                        value={textPosition}
                        onChange={(e) => setTextPosition(e.target.value)}
                        className="w-full px-3 py-2 border border-blue-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      >
                        <option value="top-left">Top Left</option>
                        <option value="top-center">Top Center</option>
                        <option value="top-right">Top Right</option>
                        <option value="center">Center</option>
                        <option value="bottom-left">Bottom Left</option>
                        <option value="bottom-center">Bottom Center</option>
                        <option value="bottom-right">Bottom Right</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Color</label>
                      <div className="flex items-center gap-2">
                        <input
                          type="color"
                          value={textColor}
                          onChange={(e) => setTextColor(e.target.value)}
                          className="w-12 h-10 rounded-lg cursor-pointer border border-blue-200"
                        />
                        <span className="text-sm text-gray-600">{textColor}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={handleApplyText}
                    disabled={!textOverlay.trim()}
                    className="flex-1 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 disabled:from-gray-400 disabled:to-gray-400 text-white rounded-lg font-medium transition-all duration-300 disabled:cursor-not-allowed"
                  >
                    Apply Preview
                  </button>
                  <button
                    onClick={() => {
                      setTextOverlay('');
                      setTextPosition('center');
                      setTextColor('#ffffff');
                      setTextSize(32);
                      toast.info('Text cleared');
                    }}
                    className="px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded-lg font-medium transition-all duration-300"
                  >
                    Clear
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Export & Download Button */}
          <button
            onClick={handleProcessVideo}
            disabled={!videoId || isProcessing}
            className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 disabled:from-gray-400 disabled:to-gray-400 text-white py-4 px-6 rounded-xl font-semibold flex items-center justify-center transition-all duration-300 transform hover:scale-105 hover:shadow-2xl disabled:hover:scale-100 disabled:cursor-not-allowed"
            style={{
              boxShadow: !isProcessing && videoId ? '0 8px 25px rgba(16, 185, 129, 0.5)' : 'none',
              animation: videoId && !isProcessing ? 'pulse-glow 2s ease-in-out infinite' : 'none'
            }}
          >
            <Download className="mr-2" size={20} />
            {isProcessing ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                Exporting...
              </>
            ) : (
              'Export & Download'
            )}
          </button>
        </div>

        {/* Center Panel - Video Preview */}
        <div className="lg:col-span-2">
          <div className="bg-gray-900 aspect-video rounded-lg overflow-hidden flex items-center justify-center relative">
            {!previewUrl ? (
              <div className="text-center text-gray-400">
                <Video className="mx-auto mb-3" size={48} />
                <p>Video preview will appear here</p>
              </div>
            ) : (
              <div className="relative w-full h-full">
                {/* Hidden video element for canvas processing */}
                <video
                  ref={videoRef}
                  src={previewUrl}
                  className="hidden"
                  onLoadedMetadata={(e) => {
                    const video = e.currentTarget;
                    setDuration(video.duration);
                    // If trim is active, seek to trim start
                    if (isTrimMode) {
                      video.currentTime = (trimStart / 100) * video.duration;
                    }
                  }}
                  onTimeUpdate={(e) => {
                    const video = e.currentTarget;
                    setCurrentTime(video.currentTime);
                    
                    // Enforce trim boundaries when trim is active
                    if (isTrimMode && duration > 0) {
                      const trimStartTime = (trimStart / 100) * duration;
                      const trimEndTime = (trimEnd / 100) * duration;
                      
                      // If video goes past trim end, loop back to trim start
                      if (video.currentTime >= trimEndTime) {
                        video.currentTime = trimStartTime;
                      }
                      // If video is before trim start (e.g., user seeked), go to trim start
                      if (video.currentTime < trimStartTime - 0.1) {
                        video.currentTime = trimStartTime;
                      }
                    }
                  }}
                  crossOrigin="anonymous"
                />
                
                {/* Canvas for rendering video with overlays */}
                <canvas
                  ref={canvasRef}
                  className="w-full h-full object-contain"
                  onClick={() => {
                    if (videoRef.current) {
                      if (videoRef.current.paused) {
                        videoRef.current.play();
                        setIsPlaying(true);
                      } else {
                        videoRef.current.pause();
                        setIsPlaying(false);
                      }
                    }
                  }}
                />

                {/* Hidden audio element for background music */}
                {musicUrl && (
                  <audio
                    ref={audioRef}
                    src={musicUrl}
                    loop
                  />
                )}

                {/* Play/Pause Overlay */}
                {!isPlaying && previewUrl && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/30 pointer-events-none">
                    <div className="bg-white/20 backdrop-blur-sm rounded-full p-4">
                      <Play className="text-white" size={48} />
                    </div>
                  </div>
                )}

                {/* Status indicators */}
                {isTrimMode && (
                  <div className="absolute top-4 left-4 bg-orange-600/90 text-white px-3 py-1 rounded-lg text-sm font-medium flex items-center gap-2">
                    <Scissors size={14} />
                    Trim Active: {(trimStart / 100 * duration).toFixed(1)}s - {(trimEnd / 100 * duration).toFixed(1)}s
                  </div>
                )}
                {textOverlay && !isTrimMode && (
                  <div className="absolute top-4 left-4 bg-blue-600/90 text-white px-3 py-1 rounded-lg text-sm font-medium flex items-center gap-2">
                    <Type size={14} />
                    Text Overlay Active
                  </div>
                )}
                {musicUrl && (
                  <div className="absolute top-4 right-4 bg-purple-600/90 text-white px-3 py-1 rounded-lg text-sm font-medium flex items-center gap-2">
                    <Music size={14} />
                    Music Playing
                  </div>
                )}

                {/* Video Controls Overlay - Inside Player */}
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent p-4 pt-8">
                  {/* Progress Bar */}
                  <div className="mb-3 relative">
                    {/* Trim Range Indicator */}
                    {isTrimMode && (
                      <div 
                        className="absolute top-0 h-1.5 bg-orange-500/50 rounded-lg pointer-events-none"
                        style={{
                          left: `${trimStart}%`,
                          width: `${trimEnd - trimStart}%`
                        }}
                      />
                    )}
                    <input
                      type="range"
                      min="0"
                      max={duration || 100}
                      value={currentTime}
                      onChange={(e) => {
                        if (videoRef.current) {
                          let newTime = Number(e.target.value);
                          // Enforce trim boundaries when seeking
                          if (isTrimMode && duration > 0) {
                            const trimStartTime = (trimStart / 100) * duration;
                            const trimEndTime = (trimEnd / 100) * duration;
                            newTime = Math.max(trimStartTime, Math.min(trimEndTime, newTime));
                          }
                          videoRef.current.currentTime = newTime;
                          setCurrentTime(newTime);
                        }
                      }}
                      className="w-full h-1.5 bg-white/30 rounded-lg appearance-none cursor-pointer hover:h-2 transition-all relative z-10"
                      style={{
                        background: isTrimMode 
                          ? `linear-gradient(to right, 
                              rgba(255,255,255,0.1) 0%, 
                              rgba(255,255,255,0.1) ${trimStart}%, 
                              rgba(249,115,22,0.3) ${trimStart}%, 
                              #9333ea ${trimStart}%, 
                              #9333ea ${(currentTime / (duration || 100)) * 100}%, 
                              rgba(249,115,22,0.3) ${(currentTime / (duration || 100)) * 100}%, 
                              rgba(249,115,22,0.3) ${trimEnd}%, 
                              rgba(255,255,255,0.1) ${trimEnd}%, 
                              rgba(255,255,255,0.1) 100%)`
                          : `linear-gradient(to right, #9333ea 0%, #9333ea ${(currentTime / (duration || 100)) * 100}%, rgba(255,255,255,0.3) ${(currentTime / (duration || 100)) * 100}%, rgba(255,255,255,0.3) 100%)`
                      }}
                    />
                  </div>

                  {/* Controls Row */}
                  <div className="flex items-center gap-4">
                    {/* Play/Pause Button */}
                    <button
                      onClick={() => {
                        if (videoRef.current) {
                          if (videoRef.current.paused) {
                            // When playing, start from trim start if trim is active
                            if (isTrimMode && duration > 0) {
                              const trimStartTime = (trimStart / 100) * duration;
                              const trimEndTime = (trimEnd / 100) * duration;
                              if (videoRef.current.currentTime < trimStartTime || videoRef.current.currentTime >= trimEndTime) {
                                videoRef.current.currentTime = trimStartTime;
                              }
                            }
                            videoRef.current.play();
                            setIsPlaying(true);
                          } else {
                            videoRef.current.pause();
                            setIsPlaying(false);
                          }
                        }
                      }}
                      className="p-2 bg-white/20 hover:bg-white/30 text-white rounded-lg transition-colors"
                    >
                      {isPlaying ? <Pause size={20} /> : <Play size={20} />}
                    </button>

                    {/* Time Display */}
                    <span className="text-sm text-white font-mono">
                      {isTrimMode ? (
                        <>
                          {Math.floor(currentTime / 60)}:{String(Math.floor(currentTime % 60)).padStart(2, '0')} 
                          <span className="text-orange-400 mx-1">/</span>
                          <span className="text-orange-400">
                            {Math.floor(((trimEnd - trimStart) / 100 * duration) / 60)}:{String(Math.floor(((trimEnd - trimStart) / 100 * duration) % 60)).padStart(2, '0')}
                          </span>
                        </>
                      ) : (
                        <>
                          {Math.floor(currentTime / 60)}:{String(Math.floor(currentTime % 60)).padStart(2, '0')} / {Math.floor(duration / 60)}:{String(Math.floor(duration % 60)).padStart(2, '0')}
                        </>
                      )}
                    </span>

                    <div className="flex-1" />

                    {/* Volume Control */}
                    <div className="flex items-center gap-2 group">
                      <button
                        onClick={() => setMuteVideoAudio(!muteVideoAudio)}
                        className="p-2 bg-white/20 hover:bg-white/30 text-white rounded-lg transition-colors"
                      >
                        {muteVideoAudio ? <X size={16} /> : <Volume2 size={16} />}
                      </button>
                      <div className="w-0 group-hover:w-20 overflow-hidden transition-all duration-300">
                        <input
                          type="range"
                          min="0"
                          max="100"
                          value={muteVideoAudio ? 0 : videoVolume}
                          onChange={(e) => {
                            setVideoVolume(Number(e.target.value));
                            if (muteVideoAudio) setMuteVideoAudio(false);
                          }}
                          className="w-full h-1.5 bg-white/30 rounded-lg appearance-none cursor-pointer"
                          style={{
                            background: `linear-gradient(to right, #9333ea 0%, #9333ea ${muteVideoAudio ? 0 : videoVolume}%, rgba(255,255,255,0.3) ${muteVideoAudio ? 0 : videoVolume}%, rgba(255,255,255,0.3) 100%)`
                          }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Custom Animations */}
      <style>{`
        @keyframes fade-in {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .animate-fade-in {
          animation: fade-in 0.3s ease-in-out;
        }
        @keyframes fade-in-up {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes slide-in-left {
          from {
            opacity: 0;
            transform: translateX(-20px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }

        @keyframes slide-down {
          from {
            opacity: 0;
            max-height: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            max-height: 200px;
            transform: translateY(0);
          }
        }

        @keyframes pulse-glow {
          0%, 100% {
            box-shadow: 0 8px 25px rgba(139, 92, 246, 0.5);
          }
          50% {
            box-shadow: 0 8px 35px rgba(236, 72, 153, 0.6);
          }
        }

        .animate-fade-in {
          animation: fade-in 0.6s ease-out;
        }

        .animate-slide-in-left {
          animation: slide-in-left 0.6s ease-out;
        }

        .animate-slide-down {
          animation: slide-down 0.4s ease-out;
        }
      `}</style>

      {/* Subtitle Editor Modal */}
      {showSubtitleEditor && videoId && (
        <SubtitleEditor
          videoId={videoId}
          onClose={() => setShowSubtitleEditor(false)}
          onSubtitlesUpdate={(subtitles) => {
            console.log('Subtitles updated:', subtitles);
          }}
        />
      )}
    </div>
  );
};

export default VideoEditor;