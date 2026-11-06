import React, { useState } from 'react';
import AudioRecorderForm from './components/AudioRecorderForm';
import Studio from './components/Studio';
import { fetchLexicon, fetchCategories } from './services/api';
import {
  BookOpen,
  Mic,
  Search,
  Layers,
  Play,
  Pause,
  ShieldCheck,
  ArrowUpRight,
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
  const [recordingConsentAccepted, setRecordingConsentAccepted] = useState(false);
  const [recordingConsentChecked, setRecordingConsentChecked] = useState(false);

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
    <div className="flex min-h-screen flex-col bg-[#07120f] font-sans text-slate-100">
      <header className="sticky top-0 z-50 border-b border-white/10 bg-[#07120f]/90 backdrop-blur-xl">
        <div className="mx-auto flex h-[76px] max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <a href="/" className="flex items-center gap-3 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-300">
            <span className="grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-emerald-400 to-emerald-700 text-2xl shadow-lg shadow-emerald-950/60">
              🇬🇭
            </span>
            <div>
              <h1 className="flex items-center gap-2 text-base font-extrabold tracking-tight text-white">
                Larteh Lingo
                <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-2 py-0.5 text-[9px] font-bold uppercase tracking-[0.18em] text-emerald-200">
                  Language archive
                </span>
              </h1>
              <p className="mt-0.5 text-xs text-slate-400">Preserving the voice of Larteh</p>
            </div>
          </a>

          <nav aria-label="Main navigation" className="flex items-center gap-1 rounded-2xl border border-white/10 bg-white/[0.04] p-1.5">
            <button
              type="button"
              onClick={() => setActiveTab('record')}
              className={`flex min-h-11 items-center gap-2 rounded-xl px-3 text-sm font-semibold transition sm:px-4 ${
                activeTab === 'record'
                  ? 'bg-emerald-400 text-emerald-950 shadow-lg shadow-emerald-950/30'
                  : 'text-slate-300 hover:bg-white/5 hover:text-white'
              }`}
            >
              <Mic className="h-4 w-4" />
              <span className="hidden sm:inline">Recording Studio</span>
              <span className="sm:hidden">Studio</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveTab('explore');
                loadCategories();
                loadLexicon(searchQuery, selectedCategory);
              }}
              className={`flex min-h-11 items-center gap-2 rounded-xl px-3 text-sm font-semibold transition sm:px-4 ${
                activeTab === 'explore'
                  ? 'bg-emerald-400 text-emerald-950 shadow-lg shadow-emerald-950/30'
                  : 'text-slate-300 hover:bg-white/5 hover:text-white'
              }`}
            >
              <BookOpen className="h-4 w-4" />
              <span>Explore</span>
            </button>
          </nav>
        </div>
      </header>

      <main className="relative flex-1 overflow-hidden">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-[540px] bg-[radial-gradient(ellipse_at_top,rgba(16,185,129,0.12),transparent_65%)]" />
        <div className="relative mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
        {activeTab === 'record' ? (
          <div>
            <div className="mx-auto mb-9 max-w-3xl text-center">
              <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-emerald-300/20 bg-emerald-300/[0.07] px-4 py-2 text-xs font-bold uppercase tracking-[0.2em] text-emerald-200">
                <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_12px_rgba(110,231,183,0.8)]" />
                A community language project
              </p>
              <h2 className="text-4xl font-black leading-[1.08] tracking-tight text-white sm:text-5xl lg:text-6xl">
                Keep Larteh alive,
                <span className="block bg-gradient-to-r from-emerald-200 via-emerald-400 to-amber-200 bg-clip-text text-transparent">
                  one voice at a time.
                </span>
              </h2>
              <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-slate-300 sm:text-lg">
                Help preserve everyday words and expressions for the next generation.
                Read the prompt, say it naturally in Larteh, and save your recording.
              </p>
            </div>
            {!recordingConsentAccepted ? (
              <section
                aria-labelledby="recording-consent-title"
                className="mx-auto max-w-3xl overflow-hidden rounded-[28px] border border-white/10 bg-[#101e19]/95 shadow-[0_30px_100px_rgba(0,0,0,0.4)]"
              >
                <div className="border-b border-white/10 bg-gradient-to-r from-emerald-400/[0.12] to-transparent px-6 py-6 sm:px-9 sm:py-8">
                  <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-emerald-200/20 bg-emerald-300/10 text-emerald-200">
                    <ShieldCheck className="h-6 w-6" />
                  </div>
                  <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-emerald-200">Before you begin</p>
                  <h3 id="recording-consent-title" className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
                    Your voice. Your choice.
                  </h3>
                  <p className="mt-2 max-w-xl text-sm leading-6 text-slate-300 sm:text-base">
                    Please take a moment to understand how your participation and recordings are handled.
                  </p>
                </div>
                <div className="space-y-5 px-6 py-6 sm:px-9 sm:py-8">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-4">
                      <p className="mb-1 text-sm font-bold text-white">Why we record</p>
                      <p className="text-sm leading-6 text-slate-400">
                        To preserve, document, and help people learn Larteh.
                      </p>
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-white/[0.035] p-4">
                      <p className="mb-1 text-sm font-bold text-white">Where it is kept</p>
                      <p className="text-sm leading-6 text-slate-400">
                        Recordings are stored privately and are not published by this app.
                      </p>
                    </div>
                  </div>
                  <div className="rounded-2xl border border-sky-200/10 bg-sky-200/[0.04] p-4">
                    <p className="mb-1 text-sm font-bold text-sky-100">Recording together as a family</p>
                    <p className="text-sm leading-6 text-slate-300">
                      Share this link with relatives. Each person can record every prompt once;
                      progress is kept separately on each person’s browser, while family coverage
                      shows how many prompts have at least one recording.
                    </p>
                    <p className="mt-2 text-xs leading-5 text-slate-400">
                      No email or name is collected. Progress is linked to an anonymous ID stored
                      in this browser, so using another device or clearing browser data starts a
                      separate contribution.
                    </p>
                  </div>
                  <div className="space-y-3 text-sm leading-6 text-slate-300">
                  <p>
                    Project maintainers may access recordings to manage and review the collection.
                    The app does not make recordings publicly available.
                  </p>
                  <p>
                    This consent does not authorize sharing recordings with outside organizations
                    or commercial licensing. Any future external use would require a separate
                    discussion and your permission.
                  </p>
                  <p>
                    Taking part is voluntary. You can stop before saving a recording. To ask about
                    removing recordings already saved, contact the project owner.
                  </p>
                  </div>
                <label
                  htmlFor="recording-consent"
                  className="flex cursor-pointer items-start gap-3 rounded-2xl border border-white/10 bg-[#09140f] p-4 text-sm font-semibold leading-6 text-white transition hover:border-emerald-300/40 sm:p-5"
                >
                  <input
                    id="recording-consent"
                    type="checkbox"
                    checked={recordingConsentChecked}
                    onChange={(event) => setRecordingConsentChecked(event.target.checked)}
                    className="mt-1 h-5 w-5 shrink-0 accent-emerald-400 focus:ring-2 focus:ring-emerald-300"
                  />
                  <span>
                    I have read and understand this information, and I agree to recording
                    and private storage as described above.
                  </span>
                </label>
                <button
                  type="button"
                  disabled={!recordingConsentChecked}
                  onClick={() => setRecordingConsentAccepted(true)}
                  className="flex min-h-14 w-full items-center justify-center gap-2 rounded-2xl bg-emerald-400 px-6 py-4 text-base font-bold text-emerald-950 transition hover:bg-emerald-300 focus:outline-none focus:ring-4 focus:ring-emerald-300/40 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400 sm:w-auto"
                >
                  I understand — continue <ArrowUpRight className="h-5 w-5" />
                </button>
                <p className="text-center text-xs text-slate-500 sm:text-left">
                  You can change your mind at any time before saving a recording.
                </p>
                </div>
              </section>
            ) : (
              <>
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
              </>
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
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-6 text-center text-xs text-slate-500">
        <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <span>Larteh (Gua) Language Preservation Project · Open-source platform, private recordings</span>
          <div className="flex items-center space-x-4">
            <span className="text-slate-400">Flask + PostgreSQL + React PWA</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
