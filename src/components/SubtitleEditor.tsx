import { useState, useEffect } from 'react';
import { Download, Edit3, Save, X, Plus, Trash2, Play, Pause } from 'lucide-react';
import { ApiService } from '../services/api';
import toast from 'react-hot-toast';

interface SubtitleSegment {
  id: number;
  start: number;
  end: number;
  text: string;
  language: string;
  style: string;
}

interface SubtitleEditorProps {
  videoId: string;
  onClose: () => void;
  onSubtitlesUpdate?: (subtitles: SubtitleSegment[]) => void;
}

const SubtitleEditor = ({ videoId, onClose, onSubtitlesUpdate }: SubtitleEditorProps) => {
  const [subtitles, setSubtitles] = useState<SubtitleSegment[]>([]);
  const [selectedLanguage, setSelectedLanguage] = useState('en');
  const [selectedStyle, setSelectedStyle] = useState('clean');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editText, setEditText] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const languages = [
    { code: 'en', name: 'English', flag: '🇺🇸' },
    { code: 'ur', name: 'Urdu (اردو)', flag: '🇵🇰' },
    { code: 'ar', name: 'Arabic (العربية)', flag: '🇸🇦' },
    { code: 'hi', name: 'Hindi (हिंदी)', flag: '🇮🇳' },
    { code: 'es', name: 'Spanish', flag: '🇪🇸' },
    { code: 'fr', name: 'French', flag: '🇫🇷' },
    { code: 'de', name: 'German', flag: '🇩🇪' },
    { code: 'zh', name: 'Chinese (中文)', flag: '🇨🇳' },
    { code: 'ja', name: 'Japanese', flag: '🇯🇵' },
    { code: 'ko', name: 'Korean (한국어)', flag: '🇰🇷' },
    { code: 'pt', name: 'Portuguese', flag: '🇵🇹' },
    { code: 'ru', name: 'Russian (Русский)', flag: '🇷🇺' },
    { code: 'it', name: 'Italian', flag: '🇮🇹' },
    { code: 'tr', name: 'Turkish', flag: '🇹🇷' },
    { code: 'nl', name: 'Dutch', flag: '🇳🇱' }
  ];

  const styles = [
    { value: 'clean', name: 'Clean', description: 'Simple, readable text' },
    { value: 'casual', name: 'Casual', description: 'Conversational tone' },
    { value: 'formal', name: 'Formal', description: 'Professional language' },
    { value: 'creative', name: 'Creative', description: 'Expressive and engaging' }
  ];

  useEffect(() => {
    loadSubtitles();
  }, [videoId]);

  const loadSubtitles = async () => {
    try {
      setIsLoading(true);
      const subtitleData = await ApiService.getVideoSubtitles(videoId);
      setSubtitles(subtitleData);
      onSubtitlesUpdate?.(subtitleData);
    } catch (error) {
      console.error('Failed to load subtitles:', error);
      setSubtitles([]);
    } finally {
      setIsLoading(false);
    }
  };

  const generateSubtitles = async () => {
    try {
      setIsGenerating(true);
      await ApiService.generateSubtitles(videoId, {
        language: selectedLanguage,
        style: selectedStyle
      });
      
      toast.success(`Subtitles generated in ${languages.find(l => l.code === selectedLanguage)?.name}`);
      await loadSubtitles();
    } catch (error) {
      toast.error('Failed to generate subtitles');
      console.error('Generate subtitles error:', error);
    } finally {
      setIsGenerating(false);
    }
  };

  const downloadSubtitles = async (format: 'srt' | 'json' = 'srt') => {
    try {
      const blob = await ApiService.downloadSubtitles(videoId, selectedLanguage, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `subtitles_${selectedLanguage}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success(`Subtitles downloaded as ${format.toUpperCase()}`);
    } catch (error) {
      toast.error('Failed to download subtitles');
      console.error('Download error:', error);
    }
  };

  const startEditing = (subtitle: SubtitleSegment) => {
    setEditingId(subtitle.id);
    setEditText(subtitle.text);
  };

  const saveEdit = () => {
    if (editingId !== null) {
      setSubtitles(prev => prev.map(sub => 
        sub.id === editingId ? { ...sub, text: editText } : sub
      ));
      setEditingId(null);
      setEditText('');
      toast.success('Subtitle updated');
    }
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditText('');
  };

  const deleteSubtitle = (id: number) => {
    setSubtitles(prev => prev.filter(sub => sub.id !== id));
    toast.success('Subtitle deleted');
  };

  const addSubtitle = () => {
    const newId = Math.max(...subtitles.map(s => s.id), 0) + 1;
    const lastSubtitle = subtitles[subtitles.length - 1];
    const startTime = lastSubtitle ? lastSubtitle.end + 1 : 0;
    
    const newSubtitle: SubtitleSegment = {
      id: newId,
      start: startTime,
      end: startTime + 3,
      text: 'New subtitle text',
      language: selectedLanguage,
      style: selectedStyle
    };
    
    setSubtitles(prev => [...prev, newSubtitle]);
    startEditing(newSubtitle);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl h-5/6 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-bold text-gray-900">Subtitle Editor</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X size={24} />
          </button>
        </div>

        {/* Controls */}
        <div className="p-6 border-b bg-gray-50">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Language
              </label>
              <select
                value={selectedLanguage}
                onChange={(e) => setSelectedLanguage(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                {languages.map(lang => (
                  <option key={lang.code} value={lang.code}>
                    {lang.flag} {lang.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Style
              </label>
              <select
                value={selectedStyle}
                onChange={(e) => setSelectedStyle(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                {styles.map(style => (
                  <option key={style.value} value={style.value}>
                    {style.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={generateSubtitles}
                disabled={isGenerating}
                className="w-full bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700 transition-colors disabled:opacity-50 flex items-center justify-center"
              >
                {isGenerating ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                ) : (
                  <Play size={16} className="mr-2" />
                )}
                Generate
              </button>
            </div>

            <div className="flex items-end space-x-2">
              <button
                onClick={() => downloadSubtitles('srt')}
                className="flex-1 bg-green-600 text-white px-3 py-2 rounded-md hover:bg-green-700 transition-colors flex items-center justify-center text-sm"
              >
                <Download size={14} className="mr-1" />
                SRT
              </button>
              <button
                onClick={() => downloadSubtitles('json')}
                className="flex-1 bg-blue-600 text-white px-3 py-2 rounded-md hover:bg-blue-700 transition-colors flex items-center justify-center text-sm"
              >
                <Download size={14} className="mr-1" />
                JSON
              </button>
            </div>
          </div>

          <button
            onClick={addSubtitle}
            className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 transition-colors flex items-center"
          >
            <Plus size={16} className="mr-2" />
            Add Subtitle
          </button>
        </div>

        {/* Subtitle List */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
            </div>
          ) : subtitles.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500 mb-4">No subtitles found</p>
              <p className="text-sm text-gray-400">Generate subtitles to get started</p>
            </div>
          ) : (
            <div className="space-y-4">
              {subtitles.map((subtitle) => (
                <div key={subtitle.id} className="bg-gray-50 rounded-lg p-4 border">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-4 mb-2">
                        <span className="text-sm font-medium text-purple-600">
                          #{subtitle.id}
                        </span>
                        <span className="text-sm text-gray-500">
                          {formatTime(subtitle.start)} → {formatTime(subtitle.end)}
                        </span>
                        <span className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded">
                          {languages.find(l => l.code === subtitle.language)?.name || subtitle.language}
                        </span>
                      </div>
                      
                      {editingId === subtitle.id ? (
                        <div className="space-y-2">
                          <textarea
                            value={editText}
                            onChange={(e) => setEditText(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                            rows={2}
                          />
                          <div className="flex space-x-2">
                            <button
                              onClick={saveEdit}
                              className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700 transition-colors flex items-center"
                            >
                              <Save size={14} className="mr-1" />
                              Save
                            </button>
                            <button
                              onClick={cancelEdit}
                              className="bg-gray-600 text-white px-3 py-1 rounded text-sm hover:bg-gray-700 transition-colors"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <p className="text-gray-900 leading-relaxed">{subtitle.text}</p>
                      )}
                    </div>
                    
                    {editingId !== subtitle.id && (
                      <div className="flex space-x-2 ml-4">
                        <button
                          onClick={() => startEditing(subtitle)}
                          className="text-blue-600 hover:text-blue-800"
                        >
                          <Edit3 size={16} />
                        </button>
                        <button
                          onClick={() => deleteSubtitle(subtitle.id)}
                          className="text-red-600 hover:text-red-800"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SubtitleEditor;