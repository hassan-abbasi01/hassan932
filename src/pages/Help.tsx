import { useState, useEffect } from 'react';
import { 
  Search, 
  MessageCircle, 
  Book, 
  HelpCircle, 
  Send, 
  Phone, 
  Mail, 
  Clock,
  ChevronDown,
  ChevronRight,
  Bug,
  FileText,
  Video,
  Scissors,
  Type,
  Volume2,
  Sparkles,
  User,
  CheckCircle2,
  AlertCircle,
  Zap
} from 'lucide-react';
import toast from 'react-hot-toast';
import { ApiService } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

interface FAQ {
  id: string;
  question: string;
  answer: string;
  category: string;
}

interface Response {
  message: string;
  responder_type: 'admin' | 'user';
  responder_id: string;
  responder_name: string;
  timestamp: string;
}

interface SupportTicket {
  _id: string;
  subject: string;
  description: string;
  status: 'open' | 'pending' | 'closed';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  type: string;
  created_at: string;
  updated_at: string;
  responses: Response[];
  name: string;
  email: string;
}

const Help = () => {
  const { isAuthenticated, user } = useAuth();
  const [activeTab, setActiveTab] = useState('faq');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [expandedFAQ, setExpandedFAQ] = useState<string | null>(null);
  const [supportForm, setSupportForm] = useState({
    name: user?.firstName && user?.lastName ? `${user.firstName} ${user.lastName}` : '',
    email: user?.email || '',
    subject: '',
    description: '',
    priority: 'medium',
    type: 'bug'
  });
  const [isSubmittingTicket, setIsSubmittingTicket] = useState(false);
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<SupportTicket | null>(null);
  const [replyMessage, setReplyMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [showTicketList, setShowTicketList] = useState(true);

  useEffect(() => {
    if (activeTab === 'support' && isAuthenticated) {
      fetchTickets();
    }
  }, [activeTab, isAuthenticated]);

  const faqs: FAQ[] = [
    {
      id: '1',
      question: 'How do I upload a video to SnipX?',
      answer: 'To upload a video, go to the Editor page and either drag & drop your video file or click the "Select Video" button. We support MP4, MOV, AVI, and MKV formats up to 500MB.',
      category: 'upload'
    },
    {
      id: '2',
      question: 'What video formats are supported?',
      answer: 'SnipX supports MP4, MOV, AVI, MKV, and WMV formats. For best results, we recommend using MP4 format.',
      category: 'upload'
    },
    {
      id: '3',
      question: 'How does the automatic subtitle generation work?',
      answer: 'Our AI analyzes the audio in your video and generates accurate subtitles. You can choose from multiple languages including English, Urdu, Spanish, French, and German.',
      category: 'subtitles'
    },
    {
      id: '4',
      question: 'Can I edit the generated subtitles?',
      answer: 'Yes! After subtitles are generated, you can edit them directly in the editor. You can modify text, timing, and styling.',
      category: 'subtitles'
    },
    {
      id: '5',
      question: 'What is the silence cutting feature?',
      answer: 'The silence cutting feature automatically detects and removes silent parts from your video, making it more engaging and reducing file size.',
      category: 'editing'
    },
    {
      id: '6',
      question: 'How long does video processing take?',
      answer: 'Processing time depends on video length and selected features. Typically, it takes 1-3 minutes per minute of video content.',
      category: 'processing'
    },
    {
      id: '7',
      question: 'Is my video data secure?',
      answer: 'Yes, we use enterprise-grade encryption and secure cloud storage. Your videos are private and only accessible to you.',
      category: 'security'
    },
    {
      id: '8',
      question: 'Can I download my processed videos?',
      answer: 'Absolutely! Once processing is complete, you can download your enhanced video in various quality settings.',
      category: 'download'
    }
  ];

  const categories = [
    { id: 'all', label: 'All Categories' },
    { id: 'upload', label: 'Upload & Import' },
    { id: 'editing', label: 'Video Editing' },
    { id: 'subtitles', label: 'Subtitles' },
    { id: 'processing', label: 'Processing' },
    { id: 'download', label: 'Export & Download' },
    { id: 'security', label: 'Security' }
  ];

  const tutorials = [
    {
      id: '1',
      title: 'Getting Started with SnipX',
      description: 'Learn the basics of uploading and processing your first video',
      duration: '5 min',
      icon: <Video className="text-blue-500" size={24} />
    },
    {
      id: '2',
      title: 'Advanced Subtitle Editing',
      description: 'Master subtitle generation and customization features',
      duration: '8 min',
      icon: <Type className="text-green-500" size={24} />
    },
    {
      id: '3',
      title: 'Audio Enhancement Techniques',
      description: 'Improve your video audio quality with AI-powered tools',
      duration: '6 min',
      icon: <Volume2 className="text-purple-500" size={24} />
    },
    {
      id: '4',
      title: 'Automated Video Cutting',
      description: 'Use AI to automatically remove silences and improve pacing',
      duration: '7 min',
      icon: <Zap className="text-orange-500" size={24} />
    }
  ];

  // Filter FAQs based on search and category
  const filteredFAQs = faqs.filter(faq => {
    const matchesSearch = faq.question.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          faq.answer.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || faq.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const fetchTickets = async () => {
    try {
      const token = ApiService.getToken();
      if (!token) {
        console.log('No token found, skipping ticket fetch');
        return;
      }
      
      const response = await fetch(`${import.meta.env.VITE_API_URL}/support/tickets`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Fetched tickets:', data);
        setTickets(Array.isArray(data) ? data : []);
      } else {
        console.error('Failed to fetch tickets:', response.status);
      }
    } catch (error) {
      console.error('Error fetching tickets:', error);
    }
  };

  const fetchTicketDetails = async (ticketId: string) => {
    try {
      const token = ApiService.getToken();
      const response = await fetch(`${import.meta.env.VITE_API_URL}/support/tickets/${ticketId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Fetched ticket details:', data);
        setSelectedTicket(data);
      } else {
        console.error('Failed to fetch ticket details:', response.status);
        toast.error('Failed to load ticket details');
      }
    } catch (error) {
      console.error('Error fetching ticket details:', error);
      toast.error('Error loading ticket details');
    }
  };

  const handleTicketClick = (ticket: SupportTicket) => {
    setSelectedTicket(ticket);
    setShowTicketList(false);
    fetchTicketDetails(ticket._id);
  };

  const handleSendReply = async () => {
    if (!replyMessage.trim() || !selectedTicket) return;

    setSending(true);
    try {
      const token = ApiService.getToken();
      const response = await fetch(`${import.meta.env.VITE_API_URL}/support/tickets/${selectedTicket._id}/reply`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: replyMessage.trim() })
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Reply sent successfully:', data);
        toast.success('Reply sent successfully');
        setReplyMessage('');
        
        // Wait a moment for database to update, then refresh
        setTimeout(async () => {
          await fetchTicketDetails(selectedTicket._id);
          await fetchTickets();
        }, 300);
      } else {
        const errorData = await response.json().catch(() => ({}));
        console.error('Failed to send reply:', response.status, errorData);
        toast.error(errorData.error || 'Failed to send reply');
      }
    } catch (error) {
      console.error('Error sending reply:', error);
      toast.error('Failed to send reply');
    } finally {
      setSending(false);
    }
  };

  const handleSupportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!isAuthenticated) {
      toast.error('Please log in to submit a support ticket.');
      return;
    }
    
    setIsSubmittingTicket(true);

    try {
      // Submit as authenticated user
      await ApiService.submitSupportTicket(supportForm);
      toast.success('Support ticket submitted successfully! We\'ll get back to you within 24 hours.');
      console.log('Ticket saved to MongoDB via authenticated API');

      // Reset form
      setSupportForm({
        name: user?.firstName && user?.lastName ? `${user.firstName} ${user.lastName}` : '',
        email: user?.email || '',
        subject: '',
        description: '',
        priority: 'medium',
        type: 'bug'
      });
      
      // Wait a moment for database to update, then refresh tickets and show list
      setTimeout(async () => {
        await fetchTickets();
        setShowTicketList(true);
      }, 500);
    } catch (error) {
      console.error('Error submitting support ticket:', error);
      toast.error('Failed to submit support ticket. Please try again.');
    } finally {
      setIsSubmittingTicket(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const colors = {
      open: 'bg-green-100 text-green-800',
      pending: 'bg-yellow-100 text-yellow-800',
      closed: 'bg-gray-100 text-gray-800'
    };
    return colors[status as keyof typeof colors] || colors.open;
  };

  const getPriorityBadge = (priority: string) => {
    const colors = {
      urgent: 'bg-red-100 text-red-800',
      high: 'bg-orange-100 text-orange-800',
      medium: 'bg-blue-100 text-blue-800',
      low: 'bg-gray-100 text-gray-800'  
    };
    return colors[priority as keyof typeof colors] || colors.medium;
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-purple-50 py-8 relative overflow-hidden">
      {/* 3D Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Floating 3D Spheres */}
        <div className="absolute top-20 left-10 w-32 h-32 bg-gradient-to-br from-purple-400/20 to-pink-400/20 rounded-full blur-xl animate-float-3d transform-gpu" 
             style={{ transform: 'translateZ(0) rotateX(45deg) rotateY(45deg)' }} />
        <div className="absolute top-40 right-20 w-24 h-24 bg-gradient-to-br from-blue-400/20 to-cyan-400/20 rounded-full blur-lg animate-float-3d-delayed transform-gpu"
             style={{ transform: 'translateZ(0) rotateX(-30deg) rotateY(60deg)' }} />
        <div className="absolute bottom-32 left-1/4 w-40 h-40 bg-gradient-to-br from-green-400/15 to-teal-400/15 rounded-full blur-2xl animate-pulse-3d transform-gpu"
             style={{ transform: 'translateZ(0) rotateX(60deg) rotateY(-45deg)' }} />
        
        {/* 3D Geometric Shapes */}
        <div className="absolute top-1/3 right-1/4 w-16 h-16 bg-gradient-to-br from-orange-400/30 to-red-400/30 transform rotate-45 animate-spin-3d blur-sm" />
        <div className="absolute bottom-1/4 right-1/3 w-12 h-12 bg-gradient-to-br from-indigo-400/30 to-purple-400/30 transform rotate-12 animate-bounce-3d blur-sm" />
        
        {/* Floating Sparkles */}
        <div className="absolute top-1/4 left-1/3 animate-sparkle-3d">
          <Sparkles className="text-purple-400/40 w-6 h-6 transform-gpu" style={{ transform: 'rotateZ(45deg)' }} />
        </div>
        <div className="absolute top-2/3 right-1/2 animate-sparkle-3d-delayed">
          <Sparkles className="text-pink-400/40 w-4 h-4 transform-gpu" style={{ transform: 'rotateZ(-30deg)' }} />
        </div>
      </div>

      <div className="container mx-auto px-4 max-w-6xl relative z-10">
        {/* Header with 3D Effects */}
        <div className="text-center mb-8 animate-slide-up-3d">
          <div className="inline-flex items-center px-6 py-3 bg-white/80 backdrop-blur-md rounded-full shadow-lg border border-white/20 mb-6 transform hover:scale-105 transition-all duration-300 hover:shadow-xl">
            <HelpCircle className="text-purple-600 mr-3 animate-pulse" size={24} />
            <span className="text-purple-700 font-medium">Help & Support Center</span>
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4 bg-gradient-to-r from-purple-600 via-pink-600 to-blue-600 bg-clip-text text-transparent animate-text-shimmer">
            Help & Support
          </h1>
          <p className="text-xl text-gray-600 animate-fade-in-up-3d">
            Find answers, get help, and learn how to make the most of SnipX
          </p>
        </div>

        {/* Navigation Tabs with 3D Effects */}
        <div className="bg-white/90 backdrop-blur-md rounded-2xl shadow-xl mb-6 border border-white/20 animate-slide-in-3d">
          <nav className="flex space-x-8 px-6 overflow-x-auto">
            {[
              { id: 'faq', label: 'FAQ', icon: HelpCircle },
              { id: 'tutorials', label: 'Tutorials', icon: Book },
              { id: 'support', label: 'Support Ticket', icon: Bug }
            ].map((tab, index) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center py-4 px-2 border-b-2 font-medium text-sm transition-all duration-300 transform hover:scale-105 hover:-translate-y-1 ${
                  activeTab === tab.id
                    ? 'border-purple-500 text-purple-600 shadow-lg'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
                style={{ animationDelay: `${index * 100}ms` }}
              >
                <tab.icon size={16} className="mr-2 animate-pulse" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content with 3D Animations */}
        <div className="bg-white/90 backdrop-blur-md rounded-2xl shadow-xl p-6 border border-white/20 animate-content-reveal-3d">
          {activeTab === 'faq' && (
            <div className="space-y-6">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1 relative group">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 group-hover:text-purple-500 transition-colors" size={16} />
                  <input
                    type="text"
                    placeholder="Search FAQs..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent bg-white/80 backdrop-blur-sm transition-all duration-300 hover:shadow-lg"
                  />
                </div>
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white/80 backdrop-blur-sm transition-all duration-300 hover:shadow-lg"
                >
                  {categories.map(category => (
                    <option key={category.id} value={category.id}>
                      {category.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-4">
                {filteredFAQs.map((faq, index) => (
                  <div 
                    key={faq.id} 
                    className="border border-gray-200 rounded-xl bg-white/80 backdrop-blur-sm shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 hover:scale-[1.02] animate-slide-in-stagger-3d"
                    style={{ animationDelay: `${index * 100}ms` }}
                  >
                    <button
                      onClick={() => setExpandedFAQ(expandedFAQ === faq.id ? null : faq.id)}
                      className="w-full flex items-center justify-between p-6 text-left hover:bg-purple-50/50 rounded-xl transition-all duration-300"
                    >
                      <span className="font-medium text-gray-900 pr-4">{faq.question}</span>
                      <div className="transform transition-transform duration-300" style={{ transform: expandedFAQ === faq.id ? 'rotateZ(180deg)' : 'rotateZ(0deg)' }}>
                        <ChevronDown size={20} className="text-gray-500" />
                      </div>
                    </button>
                    {expandedFAQ === faq.id && (
                      <div className="px-6 pb-6 text-gray-600 animate-expand-3d">
                        {faq.answer}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {filteredFAQs.length === 0 && (
                <div className="text-center py-12 animate-fade-in-3d">
                  <HelpCircle className="mx-auto text-gray-400 mb-4 animate-bounce-3d" size={48} />
                  <p className="text-gray-500">No FAQs found matching your search.</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'tutorials' && (
            <div className="space-y-6">
              <h2 className="text-2xl font-semibold text-gray-900 animate-slide-in-3d">Video Tutorials</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {tutorials.map((tutorial, index) => (
                  <div 
                    key={tutorial.id} 
                    className="border border-gray-200 rounded-xl p-6 hover:shadow-xl transition-all duration-500 bg-white/80 backdrop-blur-sm transform hover:-translate-y-2 hover:scale-105 animate-card-float-3d"
                    style={{ animationDelay: `${index * 150}ms` }}
                  >
                    <div className="flex items-start">
                      <div className="flex-shrink-0 mr-4 transform hover:scale-110 transition-transform duration-300">
                        {tutorial.icon}
                      </div>
                      <div className="flex-1">
                        <h3 className="text-lg font-medium text-gray-900 mb-2 hover:text-purple-600 transition-colors">
                          {tutorial.title}
                        </h3>
                        <p className="text-gray-600 mb-3">{tutorial.description}</p>
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-500 flex items-center">
                            <Clock size={14} className="mr-1" />
                            {tutorial.duration}
                          </span>
                          <button className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-4 py-2 rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all duration-300 transform hover:scale-105 hover:shadow-lg">
                            Watch Tutorial
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-xl p-6 animate-slide-up-3d">
                <h3 className="text-lg font-medium text-purple-900 mb-2">Need More Help?</h3>
                <p className="text-purple-700 mb-4">
                  Can't find what you're looking for? Check out our comprehensive documentation or contact our support team.
                </p>
                <div className="flex space-x-4">
                  <button className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-6 py-3 rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all duration-300 transform hover:scale-105 hover:shadow-lg">
                    View Documentation
                  </button>
                  <button className="border-2 border-purple-600 text-purple-600 px-6 py-3 rounded-lg hover:bg-purple-50 transition-all duration-300 transform hover:scale-105">
                    Contact Support
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'support' && (
            <div className="space-y-6">
              {!isAuthenticated ? (
                <div className="bg-gradient-to-r from-blue-50 to-cyan-50 border border-blue-200 rounded-xl p-6 text-center animate-slide-up-3d">
                  <div className="flex justify-center mb-4">
                    <Bug className="h-12 w-12 text-blue-600 animate-bounce-3d" />
                  </div>
                  <h3 className="text-lg font-semibold text-blue-900 mb-2">
                    Login Required
                  </h3>
                  <p className="text-blue-700 mb-4">
                    Please log in to submit a support ticket. This helps us track your issues and provide better support.
                  </p>
                  <button
                    onClick={() => window.location.href = '/login'}
                    className="bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white px-6 py-3 rounded-lg font-medium transition-all duration-300 transform hover:scale-105 hover:shadow-lg"
                  >
                    Go to Login
                  </button>
                </div>
              ) : (
                <>
                  {/* Header with toggle buttons */}
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-2xl font-semibold text-gray-900">Support Tickets</h2>
                    <div className="flex gap-2">
                      {!showTicketList && (
                        <button
                          onClick={() => { setShowTicketList(true); setSelectedTicket(null); }}
                          className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                        >
                          ← Back to List
                        </button>
                      )}
                      {showTicketList && (
                        <button
                          onClick={() => setShowTicketList(false)}
                          className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                        >
                          + New Ticket
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Show Ticket List */}
                  {showTicketList ? (
                    <div className="space-y-4">
                      {tickets.length === 0 ? (
                        <div className="text-center py-12 bg-white/80 rounded-xl">
                          <MessageCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                          <p className="text-gray-500 mb-4">No tickets yet</p>
                          <button
                            onClick={() => setShowTicketList(false)}
                            className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                          >
                            Create Your First Ticket
                          </button>
                        </div>
                      ) : (
                        <div className="grid grid-cols-1 gap-4">
                          {tickets.map((ticket) => (
                            <div
                              key={ticket._id}
                              onClick={() => handleTicketClick(ticket)}
                              className="bg-white/80 rounded-xl p-6 border border-gray-200 hover:shadow-xl transition-all cursor-pointer transform hover:-translate-y-1"
                            >
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                                    {ticket.subject}
                                  </h3>
                                  <p className="text-gray-600 text-sm line-clamp-2 mb-3">
                                    {ticket.description}
                                  </p>
                                  <div className="flex flex-wrap gap-2">
                                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusBadge(ticket.status)}`}>
                                      {ticket.status}
                                    </span>
                                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getPriorityBadge(ticket.priority)}`}>
                                      {ticket.priority}
                                    </span>
                                    <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-xs flex items-center gap-1">
                                      <Clock className="w-3 h-3" />
                                      {formatDate(ticket.created_at)}
                                    </span>
                                    {ticket.responses && ticket.responses.length > 0 && (
                                      <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-xs flex items-center gap-1">
                                        <CheckCircle2 className="w-3 h-3" />
                                        {ticket.responses.length} {ticket.responses.length === 1 ? 'reply' : 'replies'}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : selectedTicket ? (
                    /* Show Conversation View */
                    <div className="bg-white/90 rounded-xl border border-gray-200 overflow-hidden">
                      {/* Ticket Header */}
                      <div className="p-6 border-b border-gray-200 bg-gray-50">
                        <h3 className="text-xl font-bold text-gray-900 mb-2">{selectedTicket.subject}</h3>
                        <div className="flex items-center gap-4 text-sm text-gray-600">
                          <div className="flex items-center gap-1">
                            <User className="w-4 h-4" />
                            {selectedTicket.name}
                          </div>
                          <div className="flex items-center gap-1">
                            <Clock className="w-4 h-4" />
                            {formatDate(selectedTicket.created_at)}
                          </div>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusBadge(selectedTicket.status)}`}>
                            {selectedTicket.status}
                          </span>
                        </div>
                      </div>

                      {/* Messages */}
                      <div className="p-6 space-y-4 max-h-[400px] overflow-y-auto">
                        {/* Initial Message */}
                        <div className="flex gap-3">
                          <div className="flex-shrink-0">
                            <div className="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center">
                              <User className="w-5 h-5 text-purple-600" />
                            </div>
                          </div>
                          <div className="flex-1">
                            <div className="bg-gray-100 rounded-lg p-4">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-semibold text-sm text-gray-900">You</span>
                                <span className="text-xs text-gray-500">{formatTime(selectedTicket.created_at)}</span>
                              </div>
                              <p className="text-gray-800">{selectedTicket.description}</p>
                            </div>
                          </div>
                        </div>

                        {/* Responses */}
                        {selectedTicket.responses && selectedTicket.responses.map((response, index) => (
                          <div
                            key={index}
                            className={`flex gap-3 ${response.responder_type === 'admin' ? 'flex-row-reverse' : ''}`}
                          >
                            <div className="flex-shrink-0">
                              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                                response.responder_type === 'admin' ? 'bg-purple-600' : 'bg-purple-100'
                              }`}>
                                <User className={`w-5 h-5 ${
                                  response.responder_type === 'admin' ? 'text-white' : 'text-purple-600'
                                }`} />
                              </div>
                            </div>
                            <div className="flex-1">
                              <div className={`rounded-lg p-4 ${
                                response.responder_type === 'admin' ? 'bg-purple-600 text-white' : 'bg-gray-100'
                              }`}>
                                <div className="flex items-center gap-2 mb-1">
                                  <span className="font-semibold text-sm">
                                    {response.responder_type === 'admin' ? 'Admin' : 'You'}
                                  </span>
                                  <span className={`text-xs ${
                                    response.responder_type === 'admin' ? 'text-purple-100' : 'text-gray-500'
                                  }`}>
                                    {formatTime(response.timestamp)}
                                  </span>
                                </div>
                                <p className={response.responder_type === 'admin' ? 'text-white' : 'text-gray-800'}>
                                  {response.message}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* Reply Input */}
                      {selectedTicket.status !== 'closed' && (
                        <div className="p-4 border-t border-gray-200 bg-gray-50">
                          <div className="flex gap-2">
                            <input
                              type="text"
                              value={replyMessage}
                              onChange={(e) => setReplyMessage(e.target.value)}
                              onKeyPress={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                  e.preventDefault();
                                  handleSendReply();
                                }
                              }}
                              placeholder="Type your reply..."
                              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                              disabled={sending}
                            />
                            <button
                              onClick={handleSendReply}
                              disabled={!replyMessage.trim() || sending}
                              className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                            >
                              {sending ? (
                                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                              ) : (
                                <>
                                  <Send className="w-4 h-4" />
                                  Send
                                </>
                              )}
                            </button>
                          </div>
                        </div>
                      )}
                      {selectedTicket.status === 'closed' && (
                        <div className="p-4 border-t border-gray-200 bg-yellow-50">
                          <div className="flex items-center gap-2 text-yellow-800">
                            <AlertCircle className="w-5 h-5" />
                            <span className="text-sm font-medium">This ticket is closed.</span>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    /* Show New Ticket Form */
                    <form onSubmit={handleSupportSubmit} className="space-y-6 animate-form-reveal-3d">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="animate-slide-in-left-3d">
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Full Name
                          </label>
                          <input
                            type="text"
                            value={supportForm.name}
                            onChange={(e) => setSupportForm({...supportForm, name: e.target.value})}
                            className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white/80 backdrop-blur-sm transition-all duration-300 hover:shadow-lg"
                            required
                          />
                        </div>

                        <div className="animate-slide-in-right-3d">
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Email Address
                          </label>
                          <input
                            type="email"
                            value={supportForm.email}
                            onChange={(e) => setSupportForm({...supportForm, email: e.target.value})}
                            className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white/80 backdrop-blur-sm transition-all duration-300 hover:shadow-lg"
                            required
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="animate-slide-in-left-3d" style={{ animationDelay: '200ms' }}>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Issue Type
                          </label>
                          <select
                            value={supportForm.type}
                            onChange={(e) => setSupportForm({...supportForm, type: e.target.value})}
                            className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white/80 backdrop-blur-sm transition-all duration-300 hover:shadow-lg"
                          >
                            <option value="bug">Bug Report</option>
                            <option value="feature">Feature Request</option>
                            <option value="question">Question</option>
                            <option value="account">Account Issue</option>
                            <option value="other">Other</option>
                          </select>
                        </div>

                        <div className="animate-slide-in-right-3d" style={{ animationDelay: '200ms' }}>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Priority
                          </label>
                          <select
                            value={supportForm.priority}
                            onChange={(e) => setSupportForm({...supportForm, priority: e.target.value})}
                            className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white/80 backdrop-blur-sm transition-all duration-300 hover:shadow-lg"
                          >
                            <option value="low">Low</option>
                            <option value="medium">Medium</option>
                            <option value="high">High</option>
                            <option value="urgent">Urgent</option>
                          </select>
                        </div>
                      </div>

                      <div className="animate-slide-up-3d" style={{ animationDelay: '300ms' }}>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Subject
                        </label>
                        <input
                          type="text"
                          value={supportForm.subject}
                          onChange={(e) => setSupportForm({...supportForm, subject: e.target.value})}
                          className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white/80 backdrop-blur-sm transition-all duration-300 hover:shadow-lg"
                          required
                        />
                      </div>

                      <div className="animate-slide-up-3d" style={{ animationDelay: '400ms' }}>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Description
                        </label>
                        <textarea
                          value={supportForm.description}
                          onChange={(e) => setSupportForm({...supportForm, description: e.target.value})}
                          rows={6}
                          className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white/80 backdrop-blur-sm transition-all duration-300 hover:shadow-lg resize-none"
                          placeholder="Please provide as much detail as possible about your issue..."
                          required
                        />
                      </div>

                      <div className="flex justify-end gap-3 animate-slide-up-3d" style={{ animationDelay: '500ms' }}>
                        <button
                          type="button"
                          onClick={() => setShowTicketList(true)}
                          className="px-6 py-3 bg-gray-200 text-gray-700 rounded-xl hover:bg-gray-300 transition-colors"
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          disabled={isSubmittingTicket}
                          className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-8 py-3 rounded-xl hover:from-purple-700 hover:to-pink-700 transition-all duration-300 flex items-center disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105 hover:shadow-lg"
                        >
                          <FileText size={16} className="mr-2" />
                          {isSubmittingTicket ? 'Submitting...' : 'Submit Ticket'}
                        </button>
                      </div>
                    </form>
                  )}
                </>
              )}

              <div className="bg-gradient-to-r from-gray-50 to-slate-50 border border-gray-200 rounded-xl p-6 animate-slide-up-3d">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-medium text-gray-900">Support Contact</h3>
                  <div className="flex items-center space-x-4 text-sm text-gray-600">
                    <div className="flex items-center">
                      <Mail size={16} className="mr-1" />
                      support@snipx.com
                    </div>
                    <div className="flex items-center">
                      <Phone size={16} className="mr-1" />
                      +1 (555) 123-4567
                    </div>
                  </div>
                </div>
                <h3 className="text-sm font-medium text-gray-900 mb-4">Response Times</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  {[
                    { priority: 'Urgent', time: '2-4 hours', color: 'red' },
                    { priority: 'High', time: '4-8 hours', color: 'orange' },
                    { priority: 'Medium', time: '12-24 hours', color: 'yellow' },
                    { priority: 'Low', time: '24-48 hours', color: 'green' }
                  ].map((item, index) => (
                    <div 
                      key={item.priority}
                      className="animate-bounce-in-3d"
                      style={{ animationDelay: `${index * 100}ms` }}
                    >
                      <span className={`font-medium text-${item.color}-600`}>{item.priority}:</span>
                      <p className="text-gray-600">{item.time}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Help;