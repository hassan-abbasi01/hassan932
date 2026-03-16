import { useState, useRef, useEffect } from 'react';
import { MessageCircle, X, Send, Minimize2, User, Bot } from 'lucide-react';

interface ChatMessage {
  id: string;
  message: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

const LiveChat = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      message: 'Hello! 👋 Welcome to SnipX. How can I help you today?',
      sender: 'bot',
      timestamp: new Date()
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Listen for toggle event from keyboard shortcut
  useEffect(() => {
    const handleToggle = () => {
      setIsOpen(prev => !prev);
      if (!isOpen) {
        setIsMinimized(false);
      }
    };

    window.addEventListener('toggleLiveChat', handleToggle);
    return () => window.removeEventListener('toggleLiveChat', handleToggle);
  }, [isOpen]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    // Add user message
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      message: inputMessage,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsTyping(true);

    // Simulate bot response
    setTimeout(() => {
      const botResponse = generateBotResponse(inputMessage);
      const botMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        message: botResponse,
        sender: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, botMessage]);
      setIsTyping(false);
    }, 1000 + Math.random() * 1000);
  };

  const generateBotResponse = (userInput: string): string => {
    const input = userInput.toLowerCase();
    
    if (input.includes('upload') || input.includes('video')) {
      return "To upload a video, go to the Features page and drag & drop your video file or click 'Select Video'. We support MP4, MOV, AVI formats up to 500MB! 🎬";
    } else if (input.includes('subtitle') || input.includes('caption')) {
      return "Our AI can generate subtitles in multiple languages including English, Urdu, Spanish, and more! Just upload your video and select the Subtitles tab. ✨";
    } else if (input.includes('thumbnail') || input.includes('thumb')) {
      return "Our AI Thumbnail Generator creates eye-catching thumbnails for your videos! Upload your video, go to the Thumbnail tab, select a frame, and let AI enhance it with branding. Perfect for YouTube! 🖼️";
    } else if (input.includes('summar') || input.includes('summary')) {
      return "Our AI Video Summarization analyzes your video content and generates concise summaries! Great for creating descriptions, understanding content, or generating quick overviews. Just enable it in the processing options! 📝";
    } else if (input.includes('audio') && (input.includes('enhance') || input.includes('improve') || input.includes('quality'))) {
      return "Our Audio Enhancement removes silence, reduces noise, and improves audio quality automatically! It can remove filler words, normalize volume, and make your audio crystal clear. Enable it in the Audio tab! 🎵";
    } else if (input.includes('silence') || input.includes('cut') || input.includes('pause')) {
      return "The Silence Cutting feature automatically detects and removes silent parts from your video, making it more engaging and reducing file size. Perfect for tutorials and vlogs! ✂️";
    } else if (input.includes('price') || input.includes('cost') || input.includes('plan')) {
      return "We offer flexible pricing plans starting from free! Check out our pricing page for detailed information about our features. 💰";
    } else if (input.includes('help') || input.includes('support')) {
      return "I'm here to help! You can also visit our Help & Support page for FAQs, tutorials, and to submit a support ticket. 🎯";
    } else if (input.includes('thank') || input.includes('thanks')) {
      return "You're welcome! Feel free to ask if you need anything else. Happy editing! 😊";
    } else if (input.includes('hi') || input.includes('hello') || input.includes('hey')) {
      return "Hello! Great to hear from you! How can I assist you with SnipX today? 👋";
    } else if (input.includes('enhance') || input.includes('quality') || input.includes('color')) {
      return "Our AI Color Enhancement automatically adjusts saturation, brightness, and contrast for professional-quality videos! Try it in the Enhancement tab. 🎨";
    } else if (input.includes('urdu') || input.includes('language')) {
      return "Yes! We have excellent Urdu subtitle support using the latest Whisper AI model. It provides highly accurate transcription for Urdu content. We also support English, Spanish, French, German, and more! 🇵🇰";
    } else if (input.includes('feature') || input.includes('what can')) {
      return "SnipX offers: 🎬 Video Upload, ✨ AI Subtitles (Urdu included!), 🎨 Color Enhancement, 🖼️ Thumbnail Generation, 📝 Video Summarization, 🎵 Audio Enhancement, ✂️ Silence Cutting. Ask me about any specific feature!";
    } else if (input.includes('how') && input.includes('work')) {
      return "SnipX uses advanced AI to process your videos! Upload a video, choose features you want (subtitles, enhancement, thumbnails), and our AI does the rest. Processing usually takes 1-3 minutes per minute of video. 🚀";
    } else {
      return "Thanks for your message! For detailed assistance, please visit our Help & Support page or email us at support@snipx.com. Our team typically responds within 24 hours. 📧";
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 bg-gradient-to-r from-purple-600 to-pink-600 text-white p-4 rounded-full shadow-2xl hover:shadow-purple-500/50 transition-all duration-300 transform hover:scale-110 z-50 animate-bounce-slow"
        aria-label="Open live chat"
      >
        <MessageCircle size={28} />
        <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center animate-pulse">
          1
        </span>
      </button>
    );
  }

  return (
    <div 
      className={`fixed bottom-6 right-6 bg-white rounded-2xl shadow-2xl z-50 transition-all duration-300 ${
        isMinimized ? 'h-16 w-80' : 'h-[600px] w-96'
      } flex flex-col`}
      style={{ maxHeight: 'calc(100vh - 100px)' }}
    >
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-pink-600 text-white p-4 rounded-t-2xl flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="bg-white/20 p-2 rounded-full">
            <Bot size={20} />
          </div>
          <div>
            <h3 className="font-bold text-lg">SnipX Assistant</h3>
            <p className="text-xs text-white/80">Online • Typically replies instantly</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setIsMinimized(!isMinimized)}
            className="hover:bg-white/20 p-2 rounded-lg transition-colors"
            aria-label="Minimize chat"
          >
            <Minimize2 size={18} />
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="hover:bg-white/20 p-2 rounded-lg transition-colors"
            aria-label="Close chat"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {!isMinimized && (
        <>
          {/* Messages Container */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex items-start space-x-2 ${
                  msg.sender === 'user' ? 'flex-row-reverse space-x-reverse' : ''
                }`}
              >
                <div
                  className={`p-2 rounded-full ${
                    msg.sender === 'user'
                      ? 'bg-purple-600 text-white'
                      : 'bg-white border-2 border-purple-200'
                  }`}
                >
                  {msg.sender === 'user' ? (
                    <User size={16} />
                  ) : (
                    <Bot size={16} className="text-purple-600" />
                  )}
                </div>
                <div
                  className={`max-w-[70%] p-3 rounded-2xl ${
                    msg.sender === 'user'
                      ? 'bg-purple-600 text-white rounded-tr-none'
                      : 'bg-white border border-gray-200 rounded-tl-none'
                  }`}
                >
                  <p className="text-sm">{msg.message}</p>
                  <p
                    className={`text-xs mt-1 ${
                      msg.sender === 'user' ? 'text-purple-200' : 'text-gray-500'
                    }`}
                  >
                    {msg.timestamp.toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </p>
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="flex items-start space-x-2">
                <div className="p-2 rounded-full bg-white border-2 border-purple-200">
                  <Bot size={16} className="text-purple-600" />
                </div>
                <div className="bg-white border border-gray-200 p-3 rounded-2xl rounded-tl-none">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: '0.2s' }}
                    ></div>
                    <div
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: '0.4s' }}
                    ></div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-4 border-t border-gray-200 bg-white rounded-b-2xl">
            <div className="flex items-center space-x-2">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your message..."
                className="flex-1 px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-purple-500 transition-colors"
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputMessage.trim()}
                className="bg-gradient-to-r from-purple-600 to-pink-600 text-white p-3 rounded-xl hover:shadow-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105"
                aria-label="Send message"
              >
                <Send size={20} />
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-2 text-center">
              Press Enter to send • Shift + Enter for new line
            </p>
          </div>
        </>
      )}
    </div>
  );
};

export default LiveChat;
