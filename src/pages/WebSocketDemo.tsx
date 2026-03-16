import React, { useState } from 'react';
import { VideoProcessingProgress } from '../components/VideoProcessingProgress';
import { connectWebSocket, disconnectWebSocket } from '../services/websocket';
import { Play, Upload } from 'lucide-react';

/**
 * Demo page showing WebSocket real-time progress
 * This demonstrates how to integrate the VideoProcessingProgress component
 */
const WebSocketDemo: React.FC = () => {
  const [videoId, setVideoId] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [testVideoId, setTestVideoId] = useState('');

  const handleStartProcessing = async () => {
    if (!testVideoId) {
      alert('Please enter a video ID');
      return;
    }

    setVideoId(testVideoId);
    setIsProcessing(true);

    // Connect WebSocket
    connectWebSocket();

    // Start processing via API
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';
      const response = await fetch(`${API_URL}/videos/${testVideoId}/process`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          options: {
            generate_thumbnail: true,
            generate_subtitles: true,
            enhance_audio: true,
          },
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to start processing');
      }
    } catch (error) {
      console.error('Error starting processing:', error);
      alert('Failed to start processing. Make sure video ID is valid.');
      setIsProcessing(false);
    }
  };

  const handleComplete = () => {
    console.log('Processing completed!');
    setIsProcessing(false);
    disconnectWebSocket();
  };

  const handleError = (error: string) => {
    console.error('Processing failed:', error);
    alert(`Processing failed: ${error}`);
    setIsProcessing(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-50 p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-8 mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">
            🚀 WebSocket Real-Time Progress Demo
          </h1>
          <p className="text-gray-600">
            Watch video processing happen in real-time with live progress updates!
          </p>
        </div>

        {/* Input Section */}
        {!isProcessing && (
          <div className="bg-white rounded-lg shadow-lg p-8 mb-6">
            <h2 className="text-xl font-semibold mb-4">Start Processing</h2>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Video ID
              </label>
              <input
                type="text"
                value={testVideoId}
                onChange={(e) => setTestVideoId(e.target.value)}
                placeholder="Enter video ID to process"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
              <p className="mt-2 text-sm text-gray-500">
                Tip: Upload a video first from the Features page, then use its ID here
              </p>
            </div>

            <button
              onClick={handleStartProcessing}
              disabled={!testVideoId}
              className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              <Play className="w-5 h-5" />
              Start Processing
            </button>
          </div>
        )}

        {/* Progress Section */}
        {isProcessing && videoId && (
          <VideoProcessingProgress
            videoId={videoId}
            onComplete={handleComplete}
            onError={handleError}
          />
        )}

        {/* Info Section */}
        <div className="bg-white rounded-lg shadow-lg p-8">
          <h2 className="text-xl font-semibold mb-4">How It Works</h2>
          
          <div className="space-y-4 text-gray-700">
            <div className="flex items-start">
              <div className="flex-shrink-0 w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center text-purple-600 font-bold mr-3">
                1
              </div>
              <div>
                <h3 className="font-semibold">WebSocket Connection</h3>
                <p className="text-sm text-gray-600">
                  Frontend establishes real-time connection to backend server
                </p>
              </div>
            </div>

            <div className="flex items-start">
              <div className="flex-shrink-0 w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center text-purple-600 font-bold mr-3">
                2
              </div>
              <div>
                <h3 className="font-semibold">Subscribe to Video</h3>
                <p className="text-sm text-gray-600">
                  Client tells server which video ID to send updates for
                </p>
              </div>
            </div>

            <div className="flex items-start">
              <div className="flex-shrink-0 w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center text-purple-600 font-bold mr-3">
                3
              </div>
              <div>
                <h3 className="font-semibold">Live Progress Updates</h3>
                <p className="text-sm text-gray-600">
                  Backend emits progress events as each processing step completes
                </p>
              </div>
            </div>

            <div className="flex items-start">
              <div className="flex-shrink-0 w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center text-purple-600 font-bold mr-3">
                4
              </div>
              <div>
                <h3 className="font-semibold">UI Updates Automatically</h3>
                <p className="text-sm text-gray-600">
                  Progress bar and status update instantly without page refresh
                </p>
              </div>
            </div>
          </div>

          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h4 className="font-semibold text-blue-900 mb-2">💡 Integration Tip</h4>
            <p className="text-sm text-blue-800">
              Use the <code className="bg-blue-100 px-2 py-1 rounded">VideoProcessingProgress</code> component
              anywhere you process videos. Just pass the video ID and optional callbacks!
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WebSocketDemo;
