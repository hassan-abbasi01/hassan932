/**
 * WebSocket Service for Real-time Communication
 * Handles Socket.IO connection and video processing progress updates
 */

import { io, Socket } from 'socket.io-client';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';
const WS_URL = API_URL.replace('/api', ''); // Remove /api for WebSocket base URL

let socket: Socket | null = null;

export interface ProcessingProgress {
  video_id: string;
  step: string;
  progress: number;
  message: string;
  timestamp: string;
}

export const connectWebSocket = (): Socket => {
  if (socket?.connected) {
    console.log('WebSocket already connected');
    return socket;
  }

  console.log('Connecting to WebSocket at:', WS_URL);
  
  socket = io(WS_URL, {
    autoConnect: true,
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 5,
    transports: ['websocket', 'polling'], // Try WebSocket first, fallback to polling
  });

  socket.on('connect', () => {
    console.log('✅ WebSocket connected:', socket?.id);
  });

  socket.on('disconnect', (reason) => {
    console.log('❌ WebSocket disconnected:', reason);
  });

  socket.on('connect_error', (error) => {
    console.error('WebSocket connection error:', error);
  });

  socket.on('connection_response', (data) => {
    console.log('Connection response:', data);
  });

  return socket;
};

export const disconnectWebSocket = () => {
  if (socket) {
    console.log('Disconnecting WebSocket...');
    socket.disconnect();
    socket = null;
  }
};

/**
 * Subscribe to video processing progress updates
 */
export const subscribeToVideoProgress = (
  videoId: string,
  onProgress: (data: ProcessingProgress) => void,
  onComplete?: (data: ProcessingProgress) => void,
  onError?: (data: ProcessingProgress) => void
) => {
  if (!socket) {
    socket = connectWebSocket();
  }

  // Tell server we want updates for this video
  socket.emit('subscribe_video_progress', { video_id: videoId });
  console.log(`📡 Subscribed to video ${videoId} progress`);

  // Listen for progress updates
  const progressHandler = (data: ProcessingProgress) => {
    if (data.video_id === videoId) {
      console.log(`📊 Progress: ${data.progress}% - ${data.message}`);
      onProgress(data);
      
      // Check if completed
      if (data.step === 'completed' && onComplete) {
        onComplete(data);
      }
      
      // Check if failed
      if (data.step === 'failed' && onError) {
        onError(data);
      }
    }
  };

  socket.on('processing_progress', progressHandler);

  // Return cleanup function
  return () => {
    if (socket) {
      socket.off('processing_progress', progressHandler);
      console.log(`📡 Unsubscribed from video ${videoId} progress`);
    }
  };
};

/**
 * Unsubscribe from all progress updates
 */
export const unsubscribeFromVideoProgress = () => {
  if (socket) {
    socket.off('processing_progress');
  }
};

/**
 * Get current socket instance
 */
export const getSocket = (): Socket | null => {
  return socket;
};

export { socket };
