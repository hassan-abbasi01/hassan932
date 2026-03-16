import { useEffect, useState } from 'react';
import { X, Keyboard, Command } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface Shortcut {
  key: string;
  description: string;
  action: () => void;
}

const KeyboardShortcuts = () => {
  const [showHelp, setShowHelp] = useState(false);
  const navigate = useNavigate();

  const shortcuts: Shortcut[] = [
    {
      key: 'Ctrl+U',
      description: 'Upload video',
      action: () => {
        navigate('/features');
        setTimeout(() => {
          document.getElementById('video-upload')?.click();
        }, 100);
      }
    },
    {
      key: 'Ctrl+E',
      description: 'Go to Editor',
      action: () => navigate('/editor')
    },
    {
      key: 'Ctrl+F',
      description: 'Go to Features',
      action: () => navigate('/features')
    },
    {
      key: 'Ctrl+H',
      description: 'Go to Home',
      action: () => navigate('/')
    },
    {
      key: 'Ctrl+K',
      description: 'Open Help & Support',
      action: () => navigate('/help')
    },
    {
      key: 'Ctrl+/',
      description: 'Toggle Live Chat',
      action: () => {
        // Will trigger chat toggle
        const event = new CustomEvent('toggleLiveChat');
        window.dispatchEvent(event);
      }
    },
    {
      key: '?',
      description: 'Show keyboard shortcuts',
      action: () => setShowHelp(true)
    },
    {
      key: 'Escape',
      description: 'Close dialogs',
      action: () => setShowHelp(false)
    }
  ];

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in input fields
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
        // Allow Escape to work in inputs
        if (e.key === 'Escape') {
          target.blur();
          setShowHelp(false);
        }
        return;
      }

      // Show help with ?
      if (e.key === '?' && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        setShowHelp(true);
        return;
      }

      // Close help with Escape
      if (e.key === 'Escape') {
        e.preventDefault();
        setShowHelp(false);
        return;
      }

      // Handle Ctrl/Cmd shortcuts
      if (e.ctrlKey || e.metaKey) {
        switch (e.key.toLowerCase()) {
          case 'u':
            e.preventDefault();
            shortcuts.find(s => s.key === 'Ctrl+U')?.action();
            break;
          case 'e':
            e.preventDefault();
            shortcuts.find(s => s.key === 'Ctrl+E')?.action();
            break;
          case 'f':
            e.preventDefault();
            shortcuts.find(s => s.key === 'Ctrl+F')?.action();
            break;
          case 'h':
            e.preventDefault();
            shortcuts.find(s => s.key === 'Ctrl+H')?.action();
            break;
          case 'k':
            e.preventDefault();
            shortcuts.find(s => s.key === 'Ctrl+K')?.action();
            break;
          case '/':
            e.preventDefault();
            shortcuts.find(s => s.key === 'Ctrl+/')?.action();
            break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [navigate]);

  if (!showHelp) {
    return (
      <button
        onClick={() => setShowHelp(true)}
        className="fixed bottom-24 right-6 bg-white text-gray-700 p-3 rounded-full shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-110 z-40 border-2 border-purple-200 group"
        aria-label="Show keyboard shortcuts"
        title="Keyboard Shortcuts (?)"
      >
        <Keyboard size={20} className="group-hover:text-purple-600 transition-colors" />
      </button>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden animate-scale-in">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-600 to-pink-600 text-white p-6 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="bg-white/20 p-2 rounded-lg">
              <Keyboard size={24} />
            </div>
            <div>
              <h2 className="text-2xl font-bold">Keyboard Shortcuts</h2>
              <p className="text-sm text-white/80">Navigate faster with shortcuts</p>
            </div>
          </div>
          <button
            onClick={() => setShowHelp(false)}
            className="hover:bg-white/20 p-2 rounded-lg transition-colors"
            aria-label="Close"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(80vh-120px)]">
          <div className="space-y-4">
            {/* Navigation Shortcuts */}
            <div>
              <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center">
                <Command size={18} className="mr-2 text-purple-600" />
                Navigation
              </h3>
              <div className="space-y-2">
                {shortcuts.filter(s => 
                  ['Ctrl+H', 'Ctrl+E', 'Ctrl+F', 'Ctrl+K'].includes(s.key)
                ).map((shortcut) => (
                  <div
                    key={shortcut.key}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <span className="text-gray-700">{shortcut.description}</span>
                    <kbd className="px-3 py-1 bg-white border-2 border-gray-300 rounded-lg text-sm font-mono text-gray-800 shadow-sm">
                      {shortcut.key}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>

            {/* Action Shortcuts */}
            <div>
              <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center">
                <Command size={18} className="mr-2 text-pink-600" />
                Actions
              </h3>
              <div className="space-y-2">
                {shortcuts.filter(s => 
                  ['Ctrl+U', 'Ctrl+/'].includes(s.key)
                ).map((shortcut) => (
                  <div
                    key={shortcut.key}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <span className="text-gray-700">{shortcut.description}</span>
                    <kbd className="px-3 py-1 bg-white border-2 border-gray-300 rounded-lg text-sm font-mono text-gray-800 shadow-sm">
                      {shortcut.key}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>

            {/* General Shortcuts */}
            <div>
              <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center">
                <Command size={18} className="mr-2 text-blue-600" />
                General
              </h3>
              <div className="space-y-2">
                {shortcuts.filter(s => 
                  ['?', 'Escape'].includes(s.key)
                ).map((shortcut) => (
                  <div
                    key={shortcut.key}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <span className="text-gray-700">{shortcut.description}</span>
                    <kbd className="px-3 py-1 bg-white border-2 border-gray-300 rounded-lg text-sm font-mono text-gray-800 shadow-sm">
                      {shortcut.key}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Tips */}
          <div className="mt-6 bg-gradient-to-r from-purple-50 to-pink-50 border-2 border-purple-200 rounded-xl p-4">
            <h4 className="font-bold text-purple-900 mb-2">💡 Pro Tips</h4>
            <ul className="text-sm text-purple-800 space-y-1">
              <li>• Press <kbd className="px-2 py-0.5 bg-white rounded text-xs border border-purple-300">?</kbd> anytime to open this help</li>
              <li>• Press <kbd className="px-2 py-0.5 bg-white rounded text-xs border border-purple-300">Esc</kbd> to close dialogs and modals</li>
              <li>• Use <kbd className="px-2 py-0.5 bg-white rounded text-xs border border-purple-300">Ctrl+/</kbd> to quickly access support</li>
              <li>• Shortcuts work on Mac too - use <kbd className="px-2 py-0.5 bg-white rounded text-xs border border-purple-300">Cmd</kbd> instead of Ctrl</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default KeyboardShortcuts;
