import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Send, User, Clock, CheckCircle2 } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';

interface SupportTicket {
  _id: string;
  user_id: string;
  name: string;
  email: string;
  subject: string;
  description: string;
  status: string;
  priority: string;
  type: string;
  created_at: string;
  updated_at: string;
  responses: Response[];
}

interface Response {
  message: string;
  responder_type: 'admin' | 'user';
  responder_name?: string;
  timestamp: string;
}

export default function AdminSupport() {
  const navigate = useNavigate();
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<SupportTicket | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);

  useEffect(() => {
    fetchTickets();
  }, []);

  const fetchTickets = async () => {
    const token = localStorage.getItem('admin_token');
    try {
      const response = await fetch(`${API_URL}/support/all`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      console.log('Admin fetched tickets:', data);
      if (data.success) {
        setTickets(data.tickets || []);
      } else {
        console.error('Failed to fetch tickets:', data);
      }
    } catch (error) {
      console.error('Error fetching tickets:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTicketDetails = async (ticketId: string) => {
    const token = localStorage.getItem('admin_token');
    try {
      const response = await fetch(`${API_URL}/support/ticket/${ticketId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      console.log('Admin fetched ticket details:', data);
      if (data.success) {
        setSelectedTicket(data.ticket);
      } else {
        console.error('Failed to fetch ticket details:', data);
        alert('Failed to load ticket details');
      }
    } catch (error) {
      console.error('Error fetching ticket details:', error);
      alert('Error loading ticket details');
    }
  };

  const handleTicketClick = (ticket: SupportTicket) => {
    fetchTicketDetails(ticket._id);
  };

  const handleSendReply = async () => {
    if (!message.trim() || !selectedTicket || sending) return;
    
    setSending(true);
    const token = localStorage.getItem('admin_token');
    
    try {
      const response = await fetch(`${API_URL}/support/ticket/${selectedTicket._id}/reply`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: message.trim() })
      });

      const data = await response.json();
      console.log('Admin reply response:', data);
      
      if (data.success) {
        setMessage('');
        // Wait a moment for database to update, then refresh
        setTimeout(async () => {
          await fetchTicketDetails(selectedTicket._id);
          await fetchTickets();
        }, 300);
      } else {
        console.error('Failed to send reply:', data);
        alert(data.error || 'Failed to send reply');
      }
    } catch (error) {
      console.error('Error sending reply:', error);
      alert('Error sending reply');
    } finally {
      setSending(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendReply();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-purple-50">
      <div className="bg-white/90 backdrop-blur-xl border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/admin/dashboard')} className="p-2 text-gray-600 hover:text-gray-900">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Support Center</h1>
              <p className="text-sm text-gray-600 mt-1">{tickets.length} support tickets</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Tickets List */}
          <div className="lg:col-span-1 bg-white/90 rounded-2xl border border-gray-200">
            <div className="p-4 border-b border-gray-200">
              <h2 className="font-semibold text-gray-900">Recent Tickets</h2>
            </div>
            <div className="divide-y divide-gray-200 max-h-[calc(100vh-300px)] overflow-y-auto">
              {loading ? (
                <div className="p-8 flex justify-center">
                  <div className="w-8 h-8 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin"></div>
                </div>
              ) : tickets.length === 0 ? (
                <div className="p-8 text-center text-gray-600">No tickets yet</div>
              ) : (
                tickets.map(ticket => (
                  <div 
                    key={ticket._id} 
                    onClick={() => handleTicketClick(ticket)}
                    className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors ${
                      selectedTicket?._id === ticket._id ? 'bg-purple-50 border-l-4 border-l-purple-600' : ''
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 bg-purple-500/20 rounded-full flex items-center justify-center flex-shrink-0">
                        <User className="w-5 h-5 text-purple-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{ticket.subject}</p>
                        <p className="text-xs text-gray-600 mt-1 truncate">{ticket.name || ticket.email}</p>
                        <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {new Date(ticket.created_at).toLocaleDateString()}
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                          <span className={`inline-block px-2 py-0.5 text-xs rounded-full ${
                            ticket.status === 'open' ? 'bg-green-500/20 text-green-600' :
                            ticket.status === 'pending' ? 'bg-yellow-500/20 text-yellow-600' :
                            'bg-gray-200 text-gray-600'
                          }`}>
                            {ticket.status}
                          </span>
                          <span className={`inline-block px-2 py-0.5 text-xs rounded-full ${
                            ticket.priority === 'urgent' ? 'bg-red-500/20 text-red-600' :
                            ticket.priority === 'high' ? 'bg-orange-500/20 text-orange-600' :
                            'bg-blue-500/20 text-blue-600'
                          }`}>
                            {ticket.priority}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Chat Area */}
          <div className="lg:col-span-2 bg-white/90 rounded-2xl border border-gray-200 flex flex-col h-[calc(100vh-250px)]">
            {selectedTicket ? (
              <>
                <div className="p-4 border-b border-gray-200">
                  <div className="flex items-start justify-between">
                    <div>
                      <h2 className="font-semibold text-gray-900">{selectedTicket.subject}</h2>
                      <p className="text-sm text-gray-600 mt-1">
                        {selectedTicket.name} ({selectedTicket.email})
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        Created: {new Date(selectedTicket.created_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      <span className="text-sm text-gray-600">Online</span>
                    </div>
                  </div>
                </div>
                
                {/* Messages */}
                <div className="flex-1 p-6 overflow-y-auto space-y-4">
                  {/* Initial Ticket Message */}
                  <div className="flex gap-3">
                    <div className="w-8 h-8 bg-purple-500/20 rounded-full flex items-center justify-center flex-shrink-0">
                      <User className="w-4 h-4 text-purple-600" />
                    </div>
                    <div className="flex-1">
                      <div className="bg-gray-100 rounded-2xl rounded-tl-none p-4">
                        <p className="text-sm text-gray-900">{selectedTicket.description}</p>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(selectedTicket.created_at).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>

                  {/* Responses */}
                  {selectedTicket.responses && Array.isArray(selectedTicket.responses) && selectedTicket.responses.length > 0 ? (
                    selectedTicket.responses.map((response, idx) => (
                    <div key={idx} className={`flex gap-3 ${response.responder_type === 'admin' ? 'flex-row-reverse' : ''}`}>
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                        response.responder_type === 'admin' 
                          ? 'bg-purple-600' 
                          : 'bg-purple-500/20'
                      }`}>
                        {response.responder_type === 'admin' ? (
                          <CheckCircle2 className="w-4 h-4 text-white" />
                        ) : (
                          <User className="w-4 h-4 text-purple-600" />
                        )}
                      </div>
                      <div className="flex-1">
                        <div className={`rounded-2xl p-4 ${
                          response.responder_type === 'admin'
                            ? 'bg-purple-600 text-white rounded-tr-none'
                            : 'bg-gray-100 text-gray-900 rounded-tl-none'
                        }`}>
                          <p className="text-sm">{response.message}</p>
                        </div>
                        <p className={`text-xs text-gray-500 mt-1 ${
                          response.responder_type === 'admin' ? 'text-right' : ''
                        }`}>
                          {response.responder_name || (response.responder_type === 'admin' ? 'Admin' : 'User')} • {' '}
                          {new Date(response.timestamp).toLocaleTimeString()}
                        </p>
                      </div>
                    </div>
                  ))
                  ) : null}
                </div>

                {/* Reply Input */}
                <div className="p-4 border-t border-gray-200">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder="Type your reply..."
                      className="flex-1 px-4 py-2 bg-gray-100 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-600 focus:border-purple-600 focus:outline-none"
                      disabled={sending}
                    />
                    <button
                      onClick={handleSendReply}
                      disabled={!message.trim() || sending}
                      className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {sending ? (
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                      ) : (
                        <Send className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">Press Enter to send, Shift+Enter for new line</p>
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center text-gray-600 py-12">
                  <User className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                  <p className="text-lg font-medium">Select a ticket to view conversation</p>
                  <p className="text-sm mt-2">Click on a ticket from the list to start responding</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
