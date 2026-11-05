import React, { useState, useEffect } from 'react';
import AudioRecorderForm from './components/AudioRecorderForm';
import Studio from './components/Studio';
import { fetchLexicon, fetchCategories } from './services/api';
import {
  BookOpen,
  Mic,
  Search,
  Volume2,
  Sparkles,
  Layers,
  Database,
  ExternalLink,
  Play,
  Pause,
  Filter,
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('record'); // 'record' | 'explore'
  const [recordingMode, setRecordingMode] = useState('studio');
  const [lexicon, setLexicon] = useState([]);
  const [categories, setCategories] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [activePlayingUrl, setActivePlayingUrl] = useState(null);
  const [audioInstance, setAudioInstance] = useState(null);

  useEffect(() => {
    loadCategories();
    loadLexicon();
  }, []);

  async function loadCategories() {
    try {
      const data = await fetchCategories();
      setCategories(data);
    } catch (e) {
      console.warn('Failed to load categories', e);
    }
  }

  async function loadLexicon(query = '', catId = '') {
    try {
      setIsLoading(true);
      const params = {};
      if (query) params.q = query;
      if (catId) params.category_id = catId;
      const res = await fetchLexicon(params);
      setLexicon(res.data || []);
    } catch (e) {
      console.error('Failed to load lexicon', e);
    } finally {
      setIsLoading(false);
    }
  }

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadLexicon(searchQuery, selectedCategory);
  };

  const handlePlayAudio = (url) => {
    if (!url) return;

    if (activePlayingUrl === url && audioInstance) {
      audioInstance.pause();
      setActivePlayingUrl(null);
      return;
    }

    if (audioInstance) {
      audioInstance.pause();
    }

    const newAudio = new Audio(url);
    newAudio.play();
    setActivePlayingUrl(url);
    setAudioInstance(newAudio);

    newAudio.onended = () => {
      setActivePlayingUrl(null);
    };
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="sticky top-0 z-50 bg-slate-900/90 backdrop-blur-md border-b border-slate-800">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-2xl">🇬🇭</span>
            <div>
              <h1 className="text-base font-extrabold tracking-tight text-white flex items-center gap-1.5">
                Larteh Lingo
                <span className="text-[10px] tracking-widest uppercase font-semibold text-larteh-400 bg-larteh-500/10 border border-larteh-500/20 px-1.5 py-0.5 rounded">
                  Gua Engine
                </span>
              </h1>
              <p className="text-[11px] text-slate-400">Open-Source West African Language Preservation</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center space-x-1 sm:space-x-2 bg-slate-950 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setActiveTab('record')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeTab === 'record'
                  ? 'bg-larteh-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Mic className="w-3.5 h-3.5" />
              <span>Record</span>
            </button>
            <button
              onClick={() => {
                setActiveTab('explore');
                loadLexicon(searchQuery, selectedCategory);
              }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeTab === 'explore'
                  ? 'bg-forest-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span>Lexicon ({lexicon.length})</span>
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-6 sm:py-8">
        {activeTab === 'record' ? (
          <div>
            <div className="mb-5 flex flex-wrap justify-center gap-3" aria-label="Recording mode">
              <button
                type="button"
                aria-pressed={recordingMode === 'studio'}
                onClick={() => setRecordingMode('studio')}
                className={`rounded-lg px-5 py-3 text-base font-semibold focus:outline-none focus:ring-2 focus:ring-larteh-400 ${
                  recordingMode === 'studio'
                    ? 'bg-larteh-600 text-white'
                    : 'border border-slate-600 bg-slate-900 text-slate-200'
                }`}
              >
                Studio prompts
              </button>
              <button
                type="button"
                aria-pressed={recordingMode === 'manual'}
                onClick={() => setRecordingMode('manual')}
                className={`rounded-lg px-5 py-3 text-base font-semibold focus:outline-none focus:ring-2 focus:ring-larteh-400 ${
                  recordingMode === 'manual'
                    ? 'bg-larteh-600 text-white'
                    : 'border border-slate-600 bg-slate-900 text-slate-200'
                }`}
              >
                Manual entry
              </button>
            </div>
            {recordingMode === 'studio' ? (
              <Studio />
            ) : (
              <AudioRecorderForm
                onEntryCreated={(newEntry) => {
                  setLexicon((prev) => [newEntry, ...prev]);
                }}
              />
            )}
          </div>
        ) : (
          /* Lexicon Explorer View */
          <div className="space-y-6">
            {/* Filter & Search Bar */}
            <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
                <input
                  type="text"
                  placeholder="Search Larteh spelling, phonetics, or English..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-forest-500"
                />
              </div>

              <select
                value={selectedCategory}
                onChange={(e) => {
                  setSelectedCategory(e.target.value);
                  loadLexicon(searchQuery, e.target.value);
                }}
                className="px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-sm text-slate-200 focus:outline-none focus:border-forest-500"
              >
                <option value="">All Categories</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>

              <button
                type="submit"
                className="px-5 py-2.5 rounded-xl bg-forest-600 hover:bg-forest-500 text-white font-semibold text-sm transition"
              >
                Search
              </button>
            </form>

            {/* Entries Grid */}
            {isLoading ? (
              <div className="text-center py-16 text-slate-400">Loading entries...</div>
            ) : lexicon.length === 0 ? (
              <div className="text-center py-16 border border-dashed border-slate-800 rounded-2xl">
                <Layers className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400 text-sm">No lexicon entries found.</p>
                <button
                  onClick={() => setActiveTab('record')}
                  className="mt-3 text-xs text-larteh-400 hover:underline font-semibold"
                >
                  Record the first word →
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {lexicon.map((item) => (
                  <div
                    key={item.id}
                    className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition flex flex-col justify-between shadow-sm"
                  >
                    <div>
                      <div className="flex items-start justify-between mb-2">
                        <span className="text-xs uppercase font-semibold text-larteh-400 bg-larteh-500/10 border border-larteh-500/20 px-2 py-0.5 rounded-md">
                          {item.grammatical_type?.replace('_', ' ')}
                        </span>
                        {item.category_name && (
                          <span className="text-[11px] text-slate-400">{item.category_name}</span>
                        )}
                      </div>

                      <h3 className="text-xl font-bold text-white tracking-tight mb-0.5">
                        {item.larteh_text}
                      </h3>
                      <div className="text-xs font-mono text-slate-400 mb-2">
                        {item.phonetic_script}
                      </div>
                      <p className="text-sm text-slate-200 font-medium">{item.english_translation}</p>

                      {item.cultural_notes && (
                        <p className="mt-3 text-xs text-slate-400 border-t border-slate-800/80 pt-2 italic">
                          "{item.cultural_notes}"
                        </p>
                      )}
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                      <span>Speaker: {item.speaker_name || 'Dad'}</span>
                      {item.audio_url ? (
                        <button
                          onClick={() => handlePlayAudio(item.audio_url)}
                          className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-slate-800 hover:bg-forest-600/30 text-emerald-400 hover:text-white transition"
                        >
                          {activePlayingUrl === item.audio_url ? (
                            <>
                              <Pause className="w-3.5 h-3.5" /> Playing
                            </>
                          ) : (
                            <>
                              <Play className="w-3.5 h-3.5" /> Listen
                            </>
                          )}
                        </button>
                      ) : (
                        <span className="text-slate-600 text-[11px]">No Audio</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-6 text-center text-xs text-slate-500">
        <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <span>Larteh (Gua) Language Preservation Project • Open Access</span>
          <div className="flex items-center space-x-4">
            <span className="text-slate-400">Flask + PostgreSQL + React PWA</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
