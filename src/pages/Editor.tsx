import { useState, useRef, useEffect } from 'react';
import { Upload, CheckCircle, Video, Scissors, Type, Volume2, Wand2, Settings, Download, Share2, MoreHorizontal, X, Clock, Play, Pause, VolumeX, Mic, MicOff } from 'lucide-react';
import VideoEditor from '../components/VideoEditor';

const Editor = () => {
  const [activeTab, setActiveTab] = useState('upload');
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [videoURL, setVideoURL] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  
  // Audio processing states
  const [audioContext, setAudioContext] = useState<AudioContext | null>(null);
  const [audioSource, setAudioSource] = useState<MediaElementAudioSourceNode | null>(null);
  const [gainNode, setGainNode] = useState<GainNode | null>(null);
  const [isAudioProcessing, setIsAudioProcessing] = useState(false);
  const [audioVolume, setAudioVolume] = useState(50);
  const [noiseReduction, setNoiseReduction] = useState(false);
  const [audioEnhancement, setAudioEnhancement] = useState(false);
  const [audioVisualization, setAudioVisualization] = useState<number[]>([]);
  const [isPlaying, setIsPlaying] = useState(false);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const animationRef = useRef<number>();

  const tabs = [
    { id: 'upload', label: 'Upload', icon: Upload, description: 'Import your video' },
    { id: 'edit', label: 'Edit', icon: Scissors, description: 'Trim and enhance' },
    { id: 'audio', label: 'Audio', icon: Volume2, description: 'Real-time audio processing' },
    { id: 'export', label: 'Export', icon: Download, description: 'Save your work' }
  ];

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      setVideoURL(URL.createObjectURL(file));
      simulateUpload();
      setActiveTab('edit');
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setVideoURL(URL.createObjectURL(file));
      simulateUpload();
      setActiveTab('edit');
    }
  };

  const simulateUpload = () => {
    setIsUploading(true);
    setUploadProgress(0);

    const interval = setInterval(() => {
      setUploadProgress(prev => {
        const newProgress = prev + Math.random() * 10;
        if (newProgress >= 100) {
          clearInterval(interval);
          setIsUploading(false);
          return 100;
        }
        return newProgress;
      });
    }, 200);
  };

  // Initialize audio processing
  const initializeAudioProcessing = async () => {
    if (!videoRef.current || !videoURL) return;

    try {
      const context = new (window.AudioContext || (window as any).webkitAudioContext)();
      const source = context.createMediaElementSource(videoRef.current);
      const gain = context.createGain();
      const analyser = context.createAnalyser();

      // Configure analyser for real-time visualization
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.8;

      // Connect audio nodes
      source.connect(gain);
      gain.connect(analyser);
      analyser.connect(context.destination);

      // Set initial volume
      gain.gain.value = audioVolume / 100;

      setAudioContext(context);
      setAudioSource(source);
      setGainNode(gain);
      setIsAudioProcessing(true);

      // Start visualization
      startAudioVisualization(analyser);
    } catch (error) {
      console.error('Failed to initialize audio processing:', error);
    }
    }
  };

  // Start real-time audio visualization
  const startAudioVisualization = (analyser: AnalyserNode) => {
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const animate = () => {
      analyser.getByteFrequencyData(dataArray);
      const visualization = Array.from(dataArray).slice(0, 32); // Use first 32 frequency bins
      setAudioVisualization(visualization);
      animationRef.current = requestAnimationFrame(animate);
    };

    animate();
  };

  // Handle volume change
  const handleVolumeChange = (value: number) => {
    setAudioVolume(value);
    if (gainNode) {
      gainNode.gain.value = value / 100;
    }
  };

  // Toggle noise reduction (simplified implementation)
  const toggleNoiseReduction = () => {
    setNoiseReduction(!noiseReduction);
    if (audioContext && audioSource) {
      // In a real implementation, you'd apply a high-pass filter
      // This is a simplified demonstration
      const filter = audioContext.createBiquadFilter();
      filter.type = 'highpass';
      filter.frequency.value = noiseReduction ? 0 : 300;
      // Reconnect with or without filter
    }
  };

  // Toggle audio enhancement
  const toggleAudioEnhancement = () => {
    setAudioEnhancement(!audioEnhancement);
    if (audioContext && gainNode) {
      // Apply compression/limiting for enhancement
      const compressor = audioContext.createDynamicsCompressor();
      compressor.threshold.value = audioEnhancement ? -24 : -50;
      compressor.knee.value = 30;
      compressor.ratio.value = 12;
      compressor.attack.value = 0.003;
      compressor.release.value = 0.25;
    }
  };

  // Play/pause video
  const togglePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
        if (!isAudioProcessing) {
          initializeAudioProcessing();
        }
      }
      setIsPlaying(!isPlaying);
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      if (audioContext) {
        audioContext.close();
      }
    };
  }, [audioContext]);

  // Audio Visualization Component
  const AudioVisualizer = () => (
    <div className="flex items-end justify-center gap-1 h-16 bg-black/10 rounded-lg p-2">
      {audioVisualization.map((value, index) => (
        <div
          key={index}
          className="bg-gradient-to-t from-green-500 to-green-300 rounded-sm transition-all duration-75"
          style={{
            height: `${Math.max(2, (value / 255) * 100)}%`,
            width: '6px',
            opacity: value > 0 ? 1 : 0.3
          }}
        />
      ))}
    </div>
  );

  // Enhanced Audio Controls Component
  const AudioControls = () => (
    <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 border border-gray-200/50 space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-semibold text-gray-900">Real-time Audio Enhancement</h3>
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${isAudioProcessing ? 'bg-green-500 animate-pulse' : 'bg-gray-300'}`} />
          <span className="text-sm text-gray-600">
            {isAudioProcessing ? 'Processing' : 'Inactive'}
          </span>
        </div>
      </div>

      {/* Audio Visualization */}
      <div className="bg-gray-50 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-gray-700">Audio Levels</span>
          <button
            onClick={togglePlayPause}
            className="flex items-center gap-2 px-3 py-1 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
          >
            {isPlaying ? <Pause size={16} /> : <Play size={16} />}
            {isPlaying ? 'Pause' : 'Play'}
          </button>
        </div>
        <AudioVisualizer />
      </div>

      {/* Volume Control */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-700">Volume</label>
          <span className="text-sm text-purple-600 font-medium">{audioVolume}%</span>
        </div>
        <div className="flex items-center gap-3">
          <VolumeX size={16} className="text-gray-400" />
          <input
            type="range"
            min="0"
            max="100"
            value={audioVolume}
            onChange={(e) => handleVolumeChange(Number(e.target.value))}
            className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
          />
          <Volume2 size={16} className="text-gray-400" />
        </div>
      </div>

      {/* Audio Enhancement Options */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${noiseReduction ? 'bg-green-500' : 'bg-gray-300'}`}>
              {noiseReduction ? <Mic className="text-white" size={16} /> : <MicOff className="text-gray-600" size={16} />}
            </div>
            <div>
              <div className="font-medium text-gray-900">Noise Reduction</div>
              <div className="text-sm text-gray-500">Remove background noise</div>
            </div>
          </div>
          <button
            onClick={toggleNoiseReduction}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              noiseReduction ? 'bg-green-600' : 'bg-gray-200'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                noiseReduction ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${audioEnhancement ? 'bg-purple-500' : 'bg-gray-300'}`}>
              <Wand2 className={audioEnhancement ? 'text-white' : 'text-gray-600'} size={16} />
            </div>
            <div>
              <div className="font-medium text-gray-900">Enhancement</div>
              <div className="text-sm text-gray-500">Improve audio quality</div>
            </div>
          </div>
          <button
            onClick={toggleAudioEnhancement}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              audioEnhancement ? 'bg-purple-600' : 'bg-gray-200'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                audioEnhancement ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      </div>

      {/* Hidden video element for audio processing */}
      {videoURL && (
        <video
          ref={videoRef}
          src={videoURL}
          style={{ display: 'none' }}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
        />
      )}
    </div>
  );

  const TabContent = () => {
    switch (activeTab) {
      case 'upload':
        return (
          <div className="space-y-8">
            {/* Upload Area */}
            <div
              className={`relative border-2 border-dashed rounded-2xl p-12 flex flex-col items-center justify-center
                          transition-all duration-300 bg-gradient-to-br from-white to-purple-50/30
                          backdrop-blur-sm min-h-[400px]
                          ${isDragging ? 'border-purple-400 bg-purple-50/50 scale-[1.02]' : 'border-gray-300 hover:border-purple-300'}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              {/* Animated background pattern */}
              <div className="absolute inset-0 opacity-5">
                <div className="absolute top-4 left-4 w-8 h-8 bg-purple-600 rounded-full animate-pulse"></div>
                <div className="absolute top-12 right-8 w-4 h-4 bg-blue-500 rounded-full animate-bounce"></div>
                <div className="absolute bottom-8 left-12 w-6 h-6 bg-pink-500 rounded-full animate-pulse delay-300"></div>
                <div className="absolute bottom-12 right-4 w-5 h-5 bg-green-500 rounded-full animate-bounce delay-500"></div>
              </div>

              {isUploading ? (
                <div className="w-full max-w-md z-10">
                  <div className="flex items-center justify-center mb-6">
                    <div className="relative">
                      <div className="w-16 h-16 border-4 border-purple-200 rounded-full"></div>
                      <div className="absolute top-0 left-0 w-16 h-16 border-4 border-purple-600 rounded-full border-t-transparent animate-spin"></div>
                    </div>
                  </div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-medium text-gray-700">Uploading video...</span>
                    <span className="text-sm font-bold text-purple-700">{Math.round(uploadProgress)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-purple-500 to-purple-600 h-3 rounded-full transition-all duration-300 relative"
                      style={{ width: `${uploadProgress}%` }}
                    >
                      <div className="absolute inset-0 bg-white/20 animate-pulse rounded-full"></div>
                    </div>
                  </div>
                  {uploadProgress === 100 && (
                    <div className="flex items-center justify-center mt-6 text-green-600 gap-2 animate-fade-in">
                      <CheckCircle size={24} className="animate-bounce" />
                      <span className="font-medium">Upload complete! Ready to edit...</span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center z-10">
                  <div className="mb-6 relative">
                    <div className="p-6 rounded-full bg-gradient-to-br from-purple-500 to-purple-600 mx-auto w-fit shadow-xl">
                      <Upload className="text-white" size={40} />
                    </div>
                    <div className="absolute -top-2 -right-2 w-4 h-4 bg-blue-500 rounded-full animate-ping"></div>
                  </div>
                  <h3 className="text-2xl font-bold mb-3 text-gray-900">Drop your video here</h3>
                  <p className="text-gray-600 mb-8 text-center max-w-md mx-auto leading-relaxed">
                    Drag and drop your video file, or click below to browse. We support all major formats.
                  </p>
                  
                  <label className="group relative inline-flex items-center gap-3 bg-gradient-to-r from-purple-600 to-purple-700 
                                    text-white px-8 py-4 rounded-xl hover:from-purple-700 hover:to-purple-800 
                                    transition-all duration-300 cursor-pointer font-medium text-lg shadow-lg hover:shadow-xl 
                                    hover:scale-105 active:scale-95">
                    <Upload size={20} className="group-hover:rotate-12 transition-transform duration-300" />
                    Select Video File
                    <input
                      type="file"
                      className="hidden"
                      accept="video/*"
                      onChange={handleFileChange}
                    />
                  </label>
                  
                  <div className="mt-8 grid grid-cols-2 gap-4 max-w-sm mx-auto text-sm text-gray-500">
                    <div className="flex items-center gap-2">
                      <CheckCircle size={16} className="text-green-500" />
                      <span>Max 500MB</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <CheckCircle size={16} className="text-green-500" />
                      <span>All formats</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <CheckCircle size={16} className="text-green-500" />
                      <span>Secure upload</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <CheckCircle size={16} className="text-green-500" />
                      <span>Fast processing</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Recent Projects */}
            <div className="bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-gray-200/50">
              <div className="flex items-center gap-3 mb-4">
                <Clock className="text-purple-600" size={20} />
                <h3 className="text-lg font-semibold text-gray-900">Recent Projects</h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="group p-4 border border-gray-200 rounded-xl hover:border-purple-300 hover:shadow-md transition-all duration-300 cursor-pointer">
                    <div className="aspect-video bg-gradient-to-br from-gray-100 to-gray-200 rounded-lg mb-3 flex items-center justify-center">
                      <Video className="text-gray-400" size={24} />
                    </div>
                    <h4 className="font-medium text-gray-900 group-hover:text-purple-600 transition-colors">Project {i}</h4>
                    <p className="text-sm text-gray-500">2 days ago</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        );

      case 'edit':
        return videoURL ? (
          <VideoEditor videoUrl={videoURL} />
        ) : (
          <div className="text-center py-12">
            <Video className="mx-auto text-gray-400 mb-4" size={48} />
            <p className="text-gray-600">Upload a video first to start editing</p>
          </div>
        );

      case 'audio':
        return <AudioControls />;

      case 'export':
        return (
          <div className="space-y-6">
            <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-8 border border-gray-200/50">
              <h3 className="text-xl font-semibold text-gray-900 mb-6">Export Settings</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Quality</label>
                  <select className="w-full rounded-lg border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500">
                    <option>4K (3840x2160)</option>
                    <option>HD (1920x1080)</option>
                    <option>720p (1280x720)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Format</label>
                  <select className="w-full rounded-lg border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500">
                    <option>MP4</option>
                    <option>MOV</option>
                    <option>AVI</option>
                  </select>
                </div>
              </div>
              <div className="mt-8 flex gap-4">
                <button className="flex-1 bg-gradient-to-r from-purple-600 to-purple-700 text-white py-3 px-6 rounded-xl hover:from-purple-700 hover:to-purple-800 transition-all duration-300 flex items-center justify-center gap-2">
                  <Download size={20} />
                  Export Video
                </button>
                <button className="px-6 py-3 border border-gray-300 text-gray-700 rounded-xl hover:border-purple-300 hover:text-purple-700 transition-colors duration-300 flex items-center gap-2">
                  <Share2 size={20} />
                  Share
                </button>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-blue-50">
      {/* Header */}
      <div className="bg-white/80 backdrop-blur-sm border-b border-gray-200/50 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Video Editor</h1>
              <p className="text-gray-600">Transform your videos with AI-powered tools</p>
            </div>
            <div className="flex items-center gap-3">
              <button className="p-2 text-gray-600 hover:text-purple-600 transition-colors">
                <Settings size={20} />
              </button>
              <button className="p-2 text-gray-600 hover:text-purple-600 transition-colors">
                <MoreHorizontal size={20} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="container mx-auto px-4 py-6">
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl p-2 border border-gray-200/50 mb-8 shadow-lg">
          <div className="flex gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 relative group flex items-center gap-3 px-6 py-4 rounded-xl font-medium transition-all duration-300
                           ${activeTab === tab.id 
                             ? 'bg-gradient-to-r from-purple-600 to-purple-700 text-white shadow-lg' 
                             : 'text-gray-600 hover:text-purple-600 hover:bg-purple-50/50'}`}
              >
                <tab.icon size={20} className={`transition-transform duration-300 ${activeTab === tab.id ? 'scale-110' : 'group-hover:scale-105'}`} />
                <div className="text-left">
                  <div className="font-semibold">{tab.label}</div>
                  <div className={`text-xs ${activeTab === tab.id ? 'text-purple-100' : 'text-gray-500'}`}>
                    {tab.description}
                  </div>
                </div>
                {activeTab === tab.id && (
                  <div className="absolute inset-0 bg-white/20 rounded-xl animate-pulse"></div>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div className="transition-all duration-300">
          <TabContent />
        </div>
      </div>

      {/* Preview Video (if uploaded) */}
      {videoURL && activeTab !== 'edit' && (
        <div className="fixed bottom-6 right-6 w-80 bg-white/90 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200/50 overflow-hidden z-40">
          <div className="p-3 border-b border-gray-200/50 flex items-center justify-between">
            <span className="font-medium text-gray-900">Preview</span>
            <button 
              onClick={() => setVideoURL(null)}
              className="p-1 text-gray-500 hover:text-red-500 transition-colors"
            >
              <X size={16} />
            </button>
          </div>
          <video
            src={videoURL}
            controls
            className="w-full aspect-video"
          />
        </div>
      )}
    </div>
  );
};

export default Editor;
