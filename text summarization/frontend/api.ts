import { z } from 'zod';

// Support both local and remote API with automatic fallback
const REMOTE_API_URL = import.meta.env.VITE_API_URL;
const LOCAL_API_URL = 'http://localhost:5001/api';

// Start with remote if available, otherwise local
let API_URL = REMOTE_API_URL || LOCAL_API_URL;
let useRemote = !!REMOTE_API_URL;

// Export getter for current API URL (always fresh)
export const getCurrentApiUrl = () => API_URL;

// Interface for subtitle data
export interface SubtitleData {
  id: number;
  start: number;
  end: number;
  text: string;
  language: string;
  style: string;
}

// Validation schemas
const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8)
});

const registerSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  firstName: z.string().min(2),
  lastName: z.string().min(2)
});

const videoOptionsSchema = z.object({
  cut_silence: z.boolean().optional(),
  enhance_audio: z.boolean().optional(),
  generate_thumbnail: z.boolean().optional(),
  generate_subtitles: z.boolean().optional(),
  summarize: z.boolean().optional(),
  summary_length: z.string().optional(),
  summary_focus: z.string().optional(),
  // Enhancement specific options
  stabilization: z.string().optional(),
  audio_enhancement_type: z.string().optional(),
  pause_threshold: z.number().optional(),
  noise_reduction: z.string().optional(),
  brightness: z.number().optional(),
  contrast: z.number().optional(),
  // Filler word removal options
  detect_and_remove_fillers: z.boolean().optional(),
  detect_repeated_words: z.boolean().optional(),
  cut_filler_segments: z.boolean().optional(),
  filler_removal_level: z.string().optional(),
  // Subtitle specific options
  subtitle_language: z.string().optional(),
  subtitle_style: z.string().optional(),
  // Thumbnail specific options
  thumbnail_text: z.string().nullable().optional(),
  thumbnail_frame_index: z.number().nullable().optional(),
  thumbnail_font_size: z.number().optional(),
  thumbnail_text_color: z.string().optional(),
  thumbnail_outline_color: z.string().optional(),
  thumbnail_position: z.string().optional(),
  thumbnail_font_style: z.string().optional(),
  thumbnail_shadow: z.boolean().optional(),
  thumbnail_background: z.boolean().optional(),
  thumbnail_background_color: z.string().optional(),
});

export class ApiService {
  private static token: string | null = null;

  static setToken(token: string) {
    this.token = token;
    localStorage.setItem('token', token);
  }

  static getToken(): string | null {
    if (!this.token) {
      this.token = localStorage.getItem('token');
    }
    return this.token;
  }

  static clearToken() {
    this.token = null;
    localStorage.removeItem('token');
  }

  // Get current API URL (for debugging)
  static getCurrentApiUrl(): string {
    return API_URL;
  }

  // Try to switch to fallback API
  private static switchToFallback() {
    if (useRemote && REMOTE_API_URL) {
      console.warn('🔄 Remote API failed, switching to local...');
      API_URL = LOCAL_API_URL;
      useRemote = false;
    } else if (!useRemote && REMOTE_API_URL) {
      console.warn('🔄 Local API failed, switching to remote...');
      API_URL = REMOTE_API_URL;
      useRemote = true;
    }
  }

  private static async request(endpoint: string, options: RequestInit = {}) {
    const token = this.getToken();
    const isForm = options.body instanceof FormData;

    const headers: HeadersInit = {
      // Only set JSON content-type when not sending FormData
      ...(isForm ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      // Add ngrok bypass header to avoid browser warning page
      'ngrok-skip-browser-warning': 'true',
      ...options.headers
    };

    try {
      console.log(`API Request: ${API_URL}${endpoint}`);
      const res = await fetch(`${API_URL}${endpoint}`, {
        ...options,
        headers
      });

      console.log(`API Response: ${res.status} ${res.statusText}`);

      if (!res.ok) {
        // Try to parse JSON error, fallback to text
        let msg = `HTTP ${res.status}`;
        try {
          const payload = await res.json();
          console.error('API Error payload:', payload);
          msg = payload.message || payload.error || msg;
        } catch {
          const text = await res.text();
          console.error('API Error text:', text);
          msg = text || msg;
        }
        throw new Error(msg);
      }

      // Handle no-content responses
      if (res.status === 204) {
        return null;
      }

      const data = await res.json();
      console.log('API Response data:', data);
      return data;
    } catch (err) {
      console.error('API request failed:', endpoint, err);
      
      // If request failed and we have both URLs configured, try fallback
      if (REMOTE_API_URL && LOCAL_API_URL && err instanceof TypeError) {
        console.log('🔄 Network error detected, attempting fallback...');
        this.switchToFallback();
        
        // Retry once with fallback URL
        try {
          console.log(`🔄 Retrying with fallback: ${API_URL}${endpoint}`);
          const retryRes = await fetch(`${API_URL}${endpoint}`, {
            ...options,
            headers
          });
          
          if (!retryRes.ok) {
            let msg = `HTTP ${retryRes.status}`;
            try {
              const payload = await retryRes.json();
              msg = payload.message || payload.error || msg;
            } catch {
              const text = await retryRes.text();
              msg = text || msg;
            }
            throw new Error(msg);
          }
          
          if (retryRes.status === 204) {
            return null;
          }
          
          const retryData = await retryRes.json();
          console.log('✅ Fallback successful:', retryData);
          return retryData;
        } catch (retryErr) {
          console.error('❌ Fallback also failed:', retryErr);
          throw retryErr;
        }
      }
      
      throw err;
    }
  }

  static async login(email: string, password: string) {
    const validated = loginSchema.parse({ email, password });
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify(validated)
    });
    this.setToken(data.token);
    return data;
  }

  static async register(data: {
    email: string;
    password: string;
    firstName: string;
    lastName: string;
  }) {
    const validated = registerSchema.parse(data);
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(validated)
    });
  }

  static async uploadVideo(
    file: File, 
    onProgress?: (progress: number) => void,
    onServerProgress?: (status: string, progress: number) => void
  ) {
    const formData = new FormData();
    formData.append('video', file);
    
    // Use XMLHttpRequest for real upload progress tracking
    if (onProgress || onServerProgress) {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        
        // Track upload progress (network transfer)
        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable && onProgress) {
            const percentComplete = (e.loaded / e.total) * 100;
            onProgress(Math.round(percentComplete));
          }
        });
        
        // Handle completion
        xhr.addEventListener('load', () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              const response = JSON.parse(xhr.responseText);
              if (onProgress) {
                onProgress(100);
              }
              resolve(response);
            } catch (error) {
              reject(new Error('Invalid response format'));
            }
          } else {
            reject(new Error(`Upload failed with status ${xhr.status}`));
          }
        });
        
        // Handle errors
        xhr.addEventListener('error', () => {
          reject(new Error('Upload failed'));
        });
        
        xhr.addEventListener('abort', () => {
          reject(new Error('Upload aborted'));
        });
        
        // Setup request
        const token = this.getToken();
        xhr.open('POST', `${API_URL}/upload`);
        if (token) {
          xhr.setRequestHeader('Authorization', `Bearer ${token}`);
        }
        
        // Send the request
        xhr.send(formData);
      });
    }
    
    // Fallback to regular request without progress
    return this.request('/upload', {
      method: 'POST',
      body: formData
    });
  }

  static async processVideo(videoId: string, options: {
    cut_silence?: boolean;
    enhance_audio?: boolean;
    generate_thumbnail?: boolean;
    generate_subtitles?: boolean;
    summarize?: boolean;
    summary_length?: string;
    summary_focus?: string;
    // Enhancement specific options
    stabilization?: string;
    audio_enhancement_type?: string;
    pause_threshold?: number;
    noise_reduction?: string;
    brightness?: number;
    contrast?: number;
    // Filler word removal options
    detect_and_remove_fillers?: boolean;
    detect_repeated_words?: boolean;
    cut_filler_segments?: boolean;
    filler_removal_level?: string;
    // Subtitle specific options
    subtitle_language?: string;
    subtitle_style?: string;
    // Thumbnail specific options
    thumbnail_text?: string | null;
    thumbnail_frame_index?: number | null;
    thumbnail_font_size?: number;
    thumbnail_text_color?: string;
    thumbnail_outline_color?: string;
    thumbnail_position?: string;
    thumbnail_font_style?: string;
    thumbnail_shadow?: boolean;
    thumbnail_background?: boolean;
  }) {
    const validated = videoOptionsSchema.parse(options);
    return this.request(`/videos/${videoId}/process`, {
      method: 'POST',
      body: JSON.stringify({ options: validated })
    });
  }

  static async getVideoStatus(videoId: string) {
    return this.request(`/videos/${videoId}`);
  }

  static async getVideo(videoId: string) {
    return this.getVideoStatus(videoId);
  }

  static async getUserVideos() {
    return this.request('/videos');
  }

  static async deleteVideo(videoId: string) {
    return this.request(`/videos/${videoId}`, {
      method: 'DELETE'
    });
  }

  static async getVideoSummary(videoId: string): Promise<{
    summary: {
      text: string;
      key_points?: string[];
      length?: string;
      focus?: string;
      transcript_length?: number;
      summary_length?: number;
      compression_ratio?: number;
      video_duration?: number;
      error?: string;
    } | null;
  }> {
    return this.request(`/videos/${videoId}/summary`);
  }

  // Enhanced subtitle generation with Whisper
  static async generateAdvancedSubtitles(videoId: string, options: {
    language: string;
    style: string;
    format?: 'srt' | 'json' | 'both';
  }) {
    return this.request(`/videos/${videoId}/subtitles/advanced`, {
      method: 'POST',
      body: JSON.stringify(options)
    });
  }

  // Real-time thumbnail generation
  static async generateThumbnails(videoId: string, options: {
    count?: number;
    timestamps?: number[];
    style?: 'auto' | 'manual';
  } = {}) {
    return this.request(`/videos/${videoId}/thumbnails/generate`, {
      method: 'POST',
      body: JSON.stringify(options)
    });
  }

  // Real-time audio enhancement
  static async enhanceAudio(videoId: string, options: {
    type?: 'clear' | 'music' | 'full';
    noiseReduction?: boolean;
    volumeBoost?: number;
    equalization?: boolean;
  } = {}) {
    return this.request(`/videos/${videoId}/audio/enhance`, {
      method: 'POST',
      body: JSON.stringify(options)
    });
  }

  // Get processing status with real-time updates
  static async getProcessingStatus(videoId: string) {
    return this.request(`/videos/${videoId}/status`);
  }

  // Get subtitle data in JSON format for live preview
  static async getSubtitleData(videoId: string, language: string) {
    return this.request(`/videos/${videoId}/subtitles/${language}/json`);
  }

  // Get video subtitles for player
  static async getVideoSubtitles(videoId: string): Promise<SubtitleData[]> {
    try {
      const response = await this.request(`/videos/${videoId}/subtitles`);
      console.log('[ApiService] getVideoSubtitles response:', response);
      
      // Handle different response formats
      if (Array.isArray(response)) {
        return response;
      } else if (response?.segments && Array.isArray(response.segments)) {
        return response.segments;
      } else if (response?.subtitles?.segments && Array.isArray(response.subtitles.segments)) {
        return response.subtitles.segments;
      } else {
        console.log('[ApiService] No valid subtitle segments found');
        return [];
      }
    } catch (error) {
      console.error('[ApiService] Error fetching subtitles:', error);
      return [];
    }
  }

  // Generate subtitles for a video
  static async generateSubtitles(videoId: string, options: {
    language: string;
    style: string;
  }) {
    return this.request(`/videos/${videoId}/subtitles/generate`, {
      method: 'POST',
      body: JSON.stringify(options)
    });
  }

  // Profile management
  static async getUserProfile() {
    return this.request('/profile');
  }

  static async updateUserProfile(data: {
    firstName?: string;
    lastName?: string;
    email?: string;
    preferences?: Record<string, any>;
  }) {
    return this.request('/profile', {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  // Admin endpoints
  static async getAdminStats() {
    return this.request('/admin/stats');
  }

  static async getAllUsers() {
    return this.request('/admin/users');
  }

  static async getAllVideos() {
    return this.request('/admin/videos');
  }

  static async updateUserStatus(userId: string, status: string) {
    return this.request(`/admin/users/${userId}/status`, {
      method: 'PUT',
      body: JSON.stringify({ status })
    });
  }

  // Support ticket
  static async submitSupportTicket(data: {
    name: string;
    email: string;
    subject: string;
    description: string;
    priority: string;
    type: string;
  }) {
    return this.request('/support/tickets', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  // Export video with edits (trim, text overlay, audio settings)
  static async exportVideo(videoId: string, options: {
    trim_start?: number;
    trim_end?: number;
    text_overlay?: string;
    text_position?: string;
    text_color?: string;
    text_size?: number;
    music_volume?: number;
    video_volume?: number;
    mute_original?: boolean;
  }) {
    return this.request(`/videos/${videoId}/export`, {
      method: 'POST',
      body: JSON.stringify(options)
    });
  }

  // Merge multiple videos
  static async mergeVideos(videoIds: string[]) {
    if (!videoIds || videoIds.length < 2) {
      throw new Error('At least 2 videos are required for merging');
    }
    return this.request('/videos/merge', {
      method: 'POST',
      body: JSON.stringify({ video_ids: videoIds })
    });
  }

  // Download exported video
  static async downloadExportedVideo(videoId: string): Promise<Blob> {
    const token = this.getToken();
    const response = await fetch(`${API_URL}/videos/${videoId}/download-export`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        'ngrok-skip-browser-warning': 'true'
      }
    });

    if (!response.ok) {
      throw new Error('Download failed');
    }

    return response.blob();
  }

  // Download processed video with automatic fallback
  static async downloadVideo(videoId: string): Promise<Blob> {
    const token = this.getToken();
    
    // Try current API_URL first
    try {
      console.log(`Downloading from: ${API_URL}/videos/${videoId}/download`);
      const response = await fetch(`${API_URL}/videos/${videoId}/download`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          'ngrok-skip-browser-warning': 'true'
        }
      });

      if (response.ok) {
        return response.blob();
      }
      
      console.warn(`Download failed with status ${response.status}, trying fallback...`);
    } catch (error) {
      console.warn('Download error, trying fallback:', error);
    }
    
    // Try fallback URL
    const fallbackUrl = useRemote ? LOCAL_API_URL : (REMOTE_API_URL || API_URL);
    if (fallbackUrl !== API_URL) {
      console.log(`Downloading from fallback: ${fallbackUrl}/videos/${videoId}/download`);
      const response = await fetch(`${fallbackUrl}/videos/${videoId}/download`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          'ngrok-skip-browser-warning': 'true'
        }
      });

      if (!response.ok) {
        throw new Error('Download failed on both URLs');
      }

      return response.blob();
    }
    
    throw new Error('Download failed');
  }

  // Download thumbnail
  static async downloadThumbnail(videoId: string): Promise<Blob> {
    const token = this.getToken();
    const response = await fetch(`${API_URL}/videos/${videoId}/thumbnail/download`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        'ngrok-skip-browser-warning': 'true'
      }
    });

    if (!response.ok) {
      throw new Error('Thumbnail download failed');
    }

    return response.blob();
  }

  // Download subtitle file
  static async downloadSubtitles(videoId: string, language: string, format: 'srt' | 'json' = 'srt'): Promise<Blob> {
    const token = this.getToken();
    const response = await fetch(`${API_URL}/videos/${videoId}/subtitles/${language}/download?format=${format}`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        'ngrok-skip-browser-warning': 'true'
      }
    });

    if (!response.ok) {
      throw new Error('Subtitle download failed');
    }

    return response.blob();
  }

  // Delete user account
  static async deleteAccount() {
    return this.request('/auth/delete-account', {
      method: 'DELETE'
    });
  }

  // Get video thumbnail URL
  static getVideoThumbnailUrl(videoId: string, index?: number): string {
    const token = this.getToken();
    const indexParam = index !== undefined ? `index=${index}` : '';
    const tokenParam = token ? `token=${encodeURIComponent(token)}` : '';
    const separator = indexParam && tokenParam ? '&' : '';
    const queryString = indexParam || tokenParam ? `?${indexParam}${separator}${tokenParam}` : '';
    return `${API_URL}/videos/${videoId}/thumbnail${queryString}`;
  }

  // Get all thumbnails for a video
  static async getVideoThumbnails(videoId: string) {
    return this.request(`/videos/${videoId}/thumbnails`);
  }

  // Detect filler words in video
  static async detectFillerWords(videoId: string, options: {
    detection_level?: 'conservative' | 'medium' | 'aggressive';
    detect_repeated?: boolean;
  }) {
    return this.request(`/videos/${videoId}/detect-fillers`, {
      method: 'POST',
      body: JSON.stringify(options)
    });
  }

  // Get available dubbing languages
  static async getDubbingLanguages(videoId: string) {
    return this.request(`/videos/${videoId}/dubbing-languages`);
  }

  // Dub video to another language
  static async dubVideo(videoId: string, options: {
    targetLanguage: string;
    sourceLanguage?: string;
    mixOriginal?: boolean;
  }) {
    return this.request(`/videos/${videoId}/dub`, {
      method: 'POST',
      body: JSON.stringify(options)
    });
  }
}