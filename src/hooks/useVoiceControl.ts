import { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';

interface VoiceCommand {
  patterns: string[];
  action: () => void;
  description: string;
}

interface UseVoiceControlOptions {
  onCommand?: (command: string) => void;
  language?: string;
  continuous?: boolean;
}

export const useVoiceControl = (options: UseVoiceControlOptions = {}) => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isSupported, setIsSupported] = useState(false);
  const recognitionRef = useRef<any>(null);
  const navigate = useNavigate();

  // Initialize speech recognition
  useEffect(() => {
    if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      
      recognitionRef.current.continuous = false; // Changed to false - listen for one command at a time
      recognitionRef.current.interimResults = true;
      recognitionRef.current.lang = options.language || 'en-US';
      recognitionRef.current.maxAlternatives = 3;
      
      setIsSupported(true);
    } else {
      console.warn('Speech recognition not supported in this browser');
      setIsSupported(false);
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, [options.continuous, options.language]);

  // Voice feedback function
  const speak = useCallback((text: string) => {
    if ('speechSynthesis' in window) {
      // Cancel any ongoing speech
      window.speechSynthesis.cancel();
      
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'en-US';
      utterance.rate = 1.1;
      utterance.pitch = 1.0;
      utterance.volume = 0.9;
      
      window.speechSynthesis.speak(utterance);
    }
  }, []);

  // Define all voice commands
  const getCommands = useCallback((): VoiceCommand[] => [
    // Navigation commands
    {
      patterns: ['go home', 'home page', 'take me home', 'navigate home'],
      action: () => {
        navigate('/');
        speak('Going to home page');
      },
      description: 'Navigate to home page'
    },
    {
      patterns: ['go to features', 'features page', 'open features', 'show features'],
      action: () => {
        navigate('/features');
        speak('Opening features page');
      },
      description: 'Navigate to features page'
    },
    {
      patterns: ['go to technologies', 'technologies page', 'open technologies', 'show technologies', 'tech page'],
      action: () => {
        navigate('/technologies');
        speak('Opening technologies page');
      },
      description: 'Navigate to technologies page'
    },
    {
      patterns: ['go to editor', 'editor page', 'open editor', 'video editor', 'show editor'],
      action: () => {
        navigate('/editor');
        speak('Opening video editor');
      },
      description: 'Navigate to editor page'
    },
    {
      patterns: ['go to help', 'help page', 'open help', 'need help', 'support'],
      action: () => {
        navigate('/help');
        speak('Opening help and support');
      },
      description: 'Navigate to help page'
    },
    {
      patterns: ['go to profile', 'profile page', 'my profile', 'open profile', 'account settings'],
      action: () => {
        navigate('/profile');
        speak('Opening your profile');
      },
      description: 'Navigate to profile page'
    },
    {
      patterns: ['sign out', 'log out', 'logout', 'sign me out'],
      action: () => {
        localStorage.removeItem('token');
        navigate('/login');
        speak('Signing you out');
      },
      description: 'Sign out'
    },
    
    // Action commands (these will be triggered by custom events)
    {
      patterns: ['upload video', 'upload file', 'select video', 'choose video', 'open upload', 'upload menu'],
      action: () => {
        window.dispatchEvent(new CustomEvent('voice-upload-video'));
        speak('Please select a video file');
      },
      description: 'Upload a video'
    },
    {
      patterns: ['process video', 'start processing', 'enhance video', 'improve video'],
      action: () => {
        window.dispatchEvent(new CustomEvent('voice-process-video'));
        speak('Processing video');
      },
      description: 'Process uploaded video'
    },
    {
      patterns: ['generate subtitles', 'create subtitles', 'add subtitles', 'make subtitles'],
      action: () => {
        window.dispatchEvent(new CustomEvent('voice-generate-subtitles'));
        speak('Generating subtitles');
      },
      description: 'Generate subtitles'
    },
    {
      patterns: ['generate thumbnail', 'create thumbnail', 'make thumbnail'],
      action: () => {
        window.dispatchEvent(new CustomEvent('voice-generate-thumbnail'));
        speak('Generating thumbnail');
      },
      description: 'Generate thumbnail'
    },
    {
      patterns: ['download video', 'save video', 'export video'],
      action: () => {
        window.dispatchEvent(new CustomEvent('voice-download-video'));
        speak('Downloading video');
      },
      description: 'Download processed video'
    },
    {
      patterns: ['play video', 'start video', 'play', 'resume'],
      action: () => {
        window.dispatchEvent(new CustomEvent('voice-play-video'));
        speak('Playing video');
      },
      description: 'Play video'
    },
    {
      patterns: ['pause video', 'stop video', 'pause'],
      action: () => {
        window.dispatchEvent(new CustomEvent('voice-pause-video'));
        speak('Pausing video');
      },
      description: 'Pause video'
    },
    {
      patterns: ['open live chat', 'show chat', 'start chat', 'help chat', 'chat support'],
      action: () => {
        const event = new CustomEvent('toggleLiveChat');
        window.dispatchEvent(event);
        speak('Opening live chat');
      },
      description: 'Open live chat'
    },
    {
      patterns: ['download thumbnail', 'save thumbnail'],
      action: () => {
        window.dispatchEvent(new CustomEvent('voice-download-thumbnail'));
        speak('Downloading thumbnail');
      },
      description: 'Download thumbnail'
    },
    {
      patterns: ['scroll down', 'page down', 'go down'],
      action: () => {
        window.scrollBy({ top: 400, behavior: 'smooth' });
        speak('Scrolling down');
      },
      description: 'Scroll down'
    },
    {
      patterns: ['scroll up', 'page up', 'go up'],
      action: () => {
        window.scrollBy({ top: -400, behavior: 'smooth' });
        speak('Scrolling up');
      },
      description: 'Scroll up'
    },
    {
      patterns: ['scroll to top', 'go to top', 'top of page'],
      action: () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
        speak('Going to top');
      },
      description: 'Scroll to top'
    },
    {
      patterns: ['scroll to bottom', 'go to bottom', 'bottom of page'],
      action: () => {
        window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
        speak('Going to bottom');
      },
      description: 'Scroll to bottom'
    },
    
    // Help commands
    {
      patterns: ['what can you do', 'help me', 'show commands', 'list commands', 'what commands', 'available commands'],
      action: () => {
        speak('I can help you navigate to home, features, editor, technologies, and help pages. Upload videos, generate subtitles and thumbnails, download files, control video playback, open live chat, and scroll pages. Try saying go to editor, upload video, or play video.');
        toast.success('🎤 Voice Commands: Go home, Go to editor, Upload video, Generate subtitles, Play video, Open chat, and more!', {
          duration: 6000,
          icon: '🎤'
        });
      },
      description: 'Show available commands'
    },
    {
      patterns: ['stop listening', 'stop', 'pause', 'turn off'],
      action: () => {
        // Don't speak when stopping - just stop silently
        setIsListening(false);
      },
      description: 'Stop voice recognition'
    }
  ], [navigate, speak]);

  // Process voice command
  const processCommand = useCallback((command: string) => {
    const normalizedCommand = command.toLowerCase().trim();
    const commands = getCommands();
    
    // Find matching command
    const matchedCommand = commands.find(cmd => 
      cmd.patterns.some(pattern => normalizedCommand.includes(pattern))
    );

    if (matchedCommand) {
      console.log('[Voice] Executing command:', normalizedCommand);
      matchedCommand.action();
      
      if (options.onCommand) {
        options.onCommand(normalizedCommand);
      }
      
      return true;
    }
    
    return false;
  }, [getCommands, options]);

  // Setup recognition handlers
  useEffect(() => {
    if (!recognitionRef.current) return;

    recognitionRef.current.onresult = (event: any) => {
      const results = event.results;
      const lastResult = results[results.length - 1];
      
      if (lastResult.isFinal) {
        const transcript = lastResult[0].transcript;
        console.log('[Voice] Final transcript:', transcript);
        setTranscript(transcript);
        
        const commandExecuted = processCommand(transcript);
        
        if (!commandExecuted) {
          console.log('[Voice] No matching command found');
          toast.error('Command not recognized. Try "help me" to see available commands.', {
            icon: '🎤'
          });
        }
        
        // Auto-stop after processing one command (whether successful or not)
        setTimeout(() => {
          setIsListening(false);
        }, 1000);
        
      } else {
        // Show interim results
        const interimTranscript = lastResult[0].transcript;
        setTranscript(interimTranscript);
      }
    };

    recognitionRef.current.onerror = (event: any) => {
      console.error('[Voice] Recognition error:', event.error);
      
      if (event.error === 'no-speech') {
        toast.error('No speech detected. Please try again.', { icon: '🎤' });
      } else if (event.error === 'not-allowed') {
        toast.error('Microphone access denied. Please allow microphone access.', { icon: '🎤' });
        setIsListening(false);
      } else {
        toast.error(`Voice recognition error: ${event.error}`, { icon: '⚠️' });
      }
    };

    recognitionRef.current.onend = () => {
      console.log('[Voice] Recognition ended');
      // Don't auto-restart - let user click button again for next command
      if (isListening) {
        setIsListening(false);
      }
    };

    recognitionRef.current.onstart = () => {
      console.log('[Voice] Recognition started');
      setTranscript('');
    };
  }, [isListening, processCommand]);

  // Start listening
  const startListening = useCallback(() => {
    if (!recognitionRef.current || !isSupported) {
      toast.error('Voice control not supported in your browser', { icon: '❌' });
      return;
    }

    try {
      recognitionRef.current.start();
      setIsListening(true);
      speak('Voice control activated');
      toast.success('Voice control activated! Say "help me" to see commands.', {
        icon: '🎤',
        duration: 3000
      });
    } catch (error) {
      console.error('[Voice] Start error:', error);
      toast.error('Could not start voice control', { icon: '❌' });
    }
  }, [isSupported, speak]);

  // Stop listening
  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
      setTranscript('');
      // Removed speak call - stop silently
    }
  }, []);

  // Toggle listening
  const toggleListening = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  return {
    isListening,
    isSupported,
    transcript,
    startListening,
    stopListening,
    toggleListening,
    speak
  };
};
