import React, { useState, useEffect, useRef } from 'react';
import {
  Mic,
  Square,
  Pause,
  Play,
  RotateCcw,
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  Volume2,
  Clock,
  User,
  BookOpen,
  Sparkles,
  Tag,
  FileText,
  Loader2,
} from 'lucide-react';
import { fetchCategories, uploadLexiconEntry } from '../services/api';

/**
 * Common IPA & Orthographic characters in Larteh (Gua) and Ghanaian languages
 * for mobile keyboard quick-insertion.
 */
const PHONETIC_QUICK_KEYS = ['ɛ', 'ɔ', 'ŋ', 'ɲ', 'ʋ', 'ɖ', 'ɣ', 'kp', 'gb', 'tw', 'pw'];

const GRAMMATICAL_TYPES = [
  { value: 'noun', label: 'Noun (Adeyidie)' },
  { value: 'verb', label: 'Verb (Adeyɛ)' },
  { value: 'cardinal_number', label: 'Cardinal Number (Akontabuo)' },
  { value: 'day_of_week', label: 'Day of the Week (Dapɛn Da)' },
  { value: 'greeting', label: 'Greeting & Salutation' },
  { value: 'phrase', label: 'Common Phrase / Idiom' },
  { value: 'adjective', label: 'Adjective (Nkyerɛkyerɛmu)' },
  { value: 'adverb', label: 'Adverb' },
  { value: 'pronoun', label: 'Pronoun' },
  { value: 'interjection', label: 'Interjection' },
  { value: 'other', label: 'Other Classification' },
];

export default function AudioRecorderForm({ onEntryCreated }) {
  // -------------------------------------------------------------------------
  // Form State
  // -------------------------------------------------------------------------
  const [formData, setFormData] = useState({
    larteh_text: '',
    phonetic_script: '',
    english_translation: '',
    category_id: '',
    grammatical_type: 'noun',
    speaker_name: 'Dad',
    cultural_notes: '',
  });

  const [categories, setCategories] = useState([]);
  const [isLoadingCategories, setIsLoadingCategories] = useState(true);

  // -------------------------------------------------------------------------
  // Audio & Recording State
  // -------------------------------------------------------------------------
  // Status: 'idle' | 'recording' | 'paused' | 'recorded' | 'playing'
  const [recordStatus, setRecordStatus] = useState('idle');
  const [recordSeconds, setRecordSeconds] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [playbackTime, setPlaybackTime] = useState(0);
  const [playbackDuration, setPlaybackDuration] = useState(0);

  // -------------------------------------------------------------------------
  // Upload & UI Status
  // -------------------------------------------------------------------------
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState(null);
  const [successEntry, setSuccessEntry] = useState(null);

  // -------------------------------------------------------------------------
  // References
  // -------------------------------------------------------------------------
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerIntervalRef = useRef(null);
  const audioPlayerRef = useRef(null);
  const lartehInputRef = useRef(null);

  // Load categories on mount
  useEffect(() => {
    loadCategoriesList();
    return () => {
      // Cleanup object URL on unmount to prevent memory leaks
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
      clearInterval(timerIntervalRef.current);
    };
  }, []);

  async function loadCategoriesList() {
    try {
      setIsLoadingCategories(true);
      const data = await fetchCategories();
      setCategories(data);
      if (data.length > 0 && !formData.category_id) {
        setFormData((prev) => ({ ...prev, category_id: String(data[0].id) }));
      }
    } catch (err) {
      console.warn('Could not load categories:', err);
    } finally {
      setIsLoadingCategories(false);
    }
  }

  // -------------------------------------------------------------------------
  // MediaRecorder API Controls
  // -------------------------------------------------------------------------
  const startRecording = async () => {
    setErrorMessage(null);
    setSuccessEntry(null);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 48000,
        },
      });

      // Detect optimal supported mimeType
      let mimeType = 'audio/webm;codecs=opus';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        if (MediaRecorder.isTypeSupported('audio/webm')) {
          mimeType = 'audio/webm';
        } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
          mimeType = 'audio/mp4';
        } else {
          mimeType = ''; // Let browser choose default
        }
      }

      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const detectedType = recorder.mimeType || 'audio/webm';
        const blob = new Blob(audioChunksRef.current, { type: detectedType });
        setAudioBlob(blob);

        if (audioUrl) URL.revokeObjectURL(audioUrl);
        const newUrl = URL.createObjectURL(blob);
        setAudioUrl(newUrl);
        setRecordStatus('recorded');

        // Stop all audio tracks to release microphone hardware
        stream.getTracks().forEach((track) => track.stop());
      };

      recorder.start(100); // Collect data chunks every 100ms
      setRecordStatus('recording');
      setRecordSeconds(0);

      // Start timer
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = setInterval(() => {
        setRecordSeconds((sec) => sec + 1);
      }, 1000);
    } catch (err) {
      console.error('Microphone access denied or error:', err);
      setErrorMessage(
        'Unable to access microphone. Please grant audio permissions in your browser.'
      );
    }

  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && recordStatus === 'recording') {
      mediaRecorderRef.current.pause();
      setRecordStatus('paused');
      clearInterval(timerIntervalRef.current);
    }
  };

  const resumeRecording = () => {
    if (mediaRecorderRef.current && recordStatus === 'paused') {
      mediaRecorderRef.current.resume();
      setRecordStatus('recording');
      timerIntervalRef.current = setInterval(() => {
        setRecordSeconds((sec) => sec + 1);
      }, 1000);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && (recordStatus === 'recording' || recordStatus === 'paused')) {
      mediaRecorderRef.current.stop();
      clearInterval(timerIntervalRef.current);
    }
  };

  const resetRecording = () => {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioBlob(null);
    setAudioUrl(null);
    setRecordSeconds(0);
    setPlaybackTime(0);
    setPlaybackDuration(0);
    setRecordStatus('idle');
  };

  // -------------------------------------------------------------------------
  // Audio Playback Controls
  // -------------------------------------------------------------------------
  const togglePlayPreview = () => {
    if (!audioPlayerRef.current) return;

    if (audioPlayerRef.current.paused) {
      audioPlayerRef.current.play();
      setRecordStatus('playing');
    } else {
      audioPlayerRef.current.pause();
      setRecordStatus('recorded');
    }
  };

  // -------------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------------
  const formatTime = (secs) => {
    const minutes = Math.floor(secs / 60);
    const seconds = Math.floor(secs % 60);
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  };

  const handleInsertChar = (char) => {
    setFormData((prev) => ({
      ...prev,
      larteh_text: prev.larteh_text + char,
    }));
    if (lartehInputRef.current) {
      lartehInputRef.current.focus();
    }
  };

  // -------------------------------------------------------------------------
  // Form Submission
  // -------------------------------------------------------------------------
  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage(null);

    // Validation
    if (!formData.larteh_text.trim()) {
      setErrorMessage('Please enter the Larteh spelling.');
      return;
    }
    if (!formData.phonetic_script.trim()) {
      setErrorMessage('Please provide phonetic transcription (e.g. [e-kɔ]).');
      return;
    }
    if (!formData.english_translation.trim()) {
      setErrorMessage('Please provide the English translation.');
      return;
    }

    try {
      setIsSubmitting(true);
      setUploadProgress(20);

      const payload = new FormData();
      payload.append('larteh_text', formData.larteh_text.trim());
      payload.append('phonetic_script', formData.phonetic_script.trim());
      payload.append('english_translation', formData.english_translation.trim());
      if (formData.category_id) {
        payload.append('category_id', formData.category_id);
      }
      payload.append('grammatical_type', formData.grammatical_type);
      payload.append('speaker_name', formData.speaker_name.trim() || 'Dad');
      if (formData.cultural_notes.trim()) {
        payload.append('cultural_notes', formData.cultural_notes.trim());
      }

      // Append recorded audio file blob if present
      if (audioBlob) {
        const fileExt = audioBlob.type.includes('wav') ? 'wav' : 'webm';
        const filename = `${formData.larteh_text.toLowerCase().replace(/\s+/g, '_')}_${Date.now()}.${fileExt}`;
        payload.append('audio', audioBlob, filename);
      }

      setUploadProgress(65);
      const res = await uploadLexiconEntry(payload);
      setUploadProgress(100);

      setSuccessEntry(res.data);
      if (onEntryCreated) {
        onEntryCreated(res.data);
      }

      // Reset audio and clear form for next word
      resetRecording();
      setFormData((prev) => ({
        ...prev,
        larteh_text: '',
        phonetic_script: '',
        english_translation: '',
        cultural_notes: '',
      }));
    } catch (err) {
      console.error('Submission error:', err);
      setErrorMessage(err.message || 'Failed to upload lexicon entry.');
    } finally {
      setIsSubmitting(false);
      setUploadProgress(0);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto bg-slate-800/80 backdrop-blur-md border border-slate-700/80 rounded-2xl shadow-2xl p-4 sm:p-6 lg:p-8">
      {/* Header Banner */}
      <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-700/60">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-larteh-600 to-forest-500 flex items-center justify-center text-white shadow-lg shadow-larteh-600/20">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              Larteh Lexicon Recorder
              <span className="text-xs px-2 py-0.5 rounded-full bg-forest-500/20 text-forest-400 font-semibold border border-forest-500/30">
                Gua 🇬🇭
              </span>
            </h2>
            <p className="text-xs text-slate-400">Capture voice recordings and linguistic metadata</p>
          </div>
        </div>
      </div>

      {/* Notifications */}
      {errorMessage && (
        <div className="mb-5 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-rose-400" />
          <div className="flex-1">{errorMessage}</div>
        </div>
      )}

      {successEntry && (
        <div className="mb-5 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-sm flex items-start gap-3 animate-fade-in">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5 text-emerald-400" />
          <div>
            <span className="font-semibold text-white">Preserved Successfully! </span>
            <span>
              "{successEntry.larteh_text}" ({successEntry.english_translation}) was saved to the Larteh archive.
            </span>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------- */}
      {/* 1. MEDIA RECORDER SECTION */}
      {/* ------------------------------------------------------------------- */}
      <div className="mb-8 p-5 rounded-2xl bg-slate-900/90 border border-slate-700/70 shadow-inner">
        <div className="flex items-center justify-between mb-4">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <Volume2 className="w-4 h-4 text-larteh-400" /> Native Speaker Audio Clip
          </span>
          <span className="text-xs font-mono px-2 py-1 rounded bg-slate-800 text-slate-300 flex items-center gap-1">
            <Clock className="w-3.5 h-3.5 text-larteh-400" />
            {formatTime(recordStatus === 'recorded' || recordStatus === 'playing' ? playbackTime || recordSeconds : recordSeconds)}
          </span>
        </div>

        {/* Dynamic Visualizer / Waveform State */}
        <div className="h-20 w-full rounded-xl bg-slate-950/60 border border-slate-800 flex items-center justify-center relative overflow-hidden mb-5">
          {recordStatus === 'recording' && (
            <div className="flex items-center space-x-1.5 h-12">
              <span className="w-1.5 bg-rose-500 rounded-full animate-bar-1" />
              <span className="w-1.5 bg-rose-400 rounded-full animate-bar-2" />
              <span className="w-1.5 bg-rose-500 rounded-full animate-bar-3" />
              <span className="w-1.5 bg-rose-400 rounded-full animate-bar-4" />
              <span className="w-1.5 bg-rose-500 rounded-full animate-bar-5" />
              <span className="w-1.5 bg-rose-400 rounded-full animate-bar-2" />
              <span className="w-1.5 bg-rose-500 rounded-full animate-bar-1" />
            </div>
          )}

          {recordStatus === 'paused' && (
            <div className="text-amber-400 font-medium text-xs tracking-wider uppercase flex items-center gap-2">
              <Pause className="w-4 h-4 animate-pulse" /> Recording Paused
            </div>
          )}

          {recordStatus === 'idle' && (
            <div className="text-slate-500 text-xs text-center px-4">
              Tap the microphone below to begin lossless voice capture
            </div>
          )}

          {(recordStatus === 'recorded' || recordStatus === 'playing') && (
            <div className="w-full px-4 flex items-center gap-3">
              <button
                type="button"
                onClick={togglePlayPreview}
                className="w-10 h-10 rounded-full bg-forest-500 hover:bg-forest-600 text-white flex items-center justify-center flex-shrink-0 transition-transform active:scale-95 shadow-md shadow-forest-500/30"
                title={recordStatus === 'playing' ? 'Pause Preview' : 'Play Preview'}
              >
                {recordStatus === 'playing' ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
              </button>
              <div className="flex-1">
                <input
                  type="range"
                  min="0"
                  max={playbackDuration || recordSeconds || 1}
                  step="0.1"
                  value={playbackTime}
                  onChange={(e) => {
                    const time = parseFloat(e.target.value);
                    setPlaybackTime(time);
                    if (audioPlayerRef.current) audioPlayerRef.current.currentTime = time;
                  }}
                  className="w-full accent-forest-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                />
              </div>
              <button
                type="button"
                onClick={resetRecording}
                className="p-2 text-slate-400 hover:text-rose-400 transition"
                title="Discard & Re-record"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* Hidden Audio Player for Previewing */}
        {audioUrl && (
          <audio
            ref={audioPlayerRef}
            src={audioUrl}
            onTimeUpdate={() => {
              if (audioPlayerRef.current) {
                setPlaybackTime(audioPlayerRef.current.currentTime);
              }
            }}
            onLoadedMetadata={() => {
              if (audioPlayerRef.current) {
                setPlaybackDuration(audioPlayerRef.current.duration);
              }
            }}
            onEnded={() => {
              setRecordStatus('recorded');
              setPlaybackTime(0);
            }}
          />
        )}

        {/* Mobile-First Recorder Action Buttons */}
        <div className="flex items-center justify-center gap-3">
          {recordStatus === 'idle' && (
            <button
              type="button"
              onClick={startRecording}
              className="relative group flex items-center gap-2.5 px-6 py-3.5 rounded-full bg-rose-600 hover:bg-rose-500 text-white font-semibold text-sm shadow-lg shadow-rose-600/30 transition-all active:scale-95"
            >
              <Mic className="w-5 h-5 text-white animate-pulse" />
              <span>Record Voice</span>
            </button>
          )}

          {(recordStatus === 'recording' || recordStatus === 'paused') && (
            <>
              {recordStatus === 'recording' ? (
                <button
                  type="button"
                  onClick={pauseRecording}
                  className="px-4 py-2.5 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-xs font-semibold flex items-center gap-1.5 transition active:scale-95"
                >
                  <Pause className="w-4 h-4" /> Pause
                </button>
              ) : (
                <button
                  type="button"
                  onClick={resumeRecording}
                  className="px-4 py-2.5 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 text-xs font-semibold flex items-center gap-1.5 transition active:scale-95"
                >
                  <Play className="w-4 h-4" /> Resume
                </button>
              )}

              <button
                type="button"
                onClick={stopRecording}
                className="px-5 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-rose-600/20 transition active:scale-95"
              >
                <Square className="w-4 h-4 fill-current" /> Stop
              </button>
            </>
          )}

          {recordStatus === 'recorded' && (
            <span className="text-xs text-emerald-400 font-medium flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-full">
              <CheckCircle2 className="w-4 h-4" /> Audio ready for archive
            </span>
          )}
        </div>
      </div>

      {/* ------------------------------------------------------------------- */}
      {/* 2. LINGUISTIC & METADATA FORM */}
      {/* ------------------------------------------------------------------- */}
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Larteh Spelling */}
        <div>
          <label className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5 flex items-center justify-between">
            <span>
              Larteh Spelling (Gua) <span className="text-rose-400">*</span>
            </span>
            <span className="text-[11px] font-normal text-slate-400">e.g., Ekɔ, Idu, Epwɛ</span>
          </label>
          <input
            ref={lartehInputRef}
            type="text"
            required
            value={formData.larteh_text}
            onChange={(e) => setFormData({ ...formData, larteh_text: e.target.value })}
            placeholder="Enter word or phrase in Larteh..."
            className="w-full px-4 py-2.5 rounded-xl bg-slate-900/90 border border-slate-700 focus:border-larteh-500 focus:ring-2 focus:ring-larteh-500/30 text-white placeholder-slate-500 text-base transition outline-none"
          />

          {/* Quick-Insert Orthographic Keyboard Strip */}
          <div className="mt-2 flex items-center flex-wrap gap-1.5">
            <span className="text-[11px] text-slate-400 font-medium mr-1">Quick symbols:</span>
            {PHONETIC_QUICK_KEYS.map((char) => (
              <button
                key={char}
                type="button"
                onClick={() => handleInsertChar(char)}
                className="px-2 py-1 rounded-md bg-slate-700/60 hover:bg-larteh-600/40 hover:text-white border border-slate-600 text-xs font-mono text-slate-200 transition active:scale-90"
              >
                {char}
              </button>
            ))}
          </div>
        </div>

        {/* Phonetic Pronunciation & English Translation */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5">
              Phonetic Script (IPA) <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={formData.phonetic_script}
              onChange={(e) => setFormData({ ...formData, phonetic_script: e.target.value })}
              placeholder="e.g. [e-kɔ], [i-du]"
              className="w-full px-4 py-2.5 rounded-xl bg-slate-900/90 border border-slate-700 focus:border-larteh-500 focus:ring-2 focus:ring-larteh-500/30 text-white placeholder-slate-500 text-sm font-mono transition outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5">
              English Translation <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              value={formData.english_translation}
              onChange={(e) => setFormData({ ...formData, english_translation: e.target.value })}
              placeholder="e.g. One (1), Sunday"
              className="w-full px-4 py-2.5 rounded-xl bg-slate-900/90 border border-slate-700 focus:border-larteh-500 focus:ring-2 focus:ring-larteh-500/30 text-white placeholder-slate-500 text-sm transition outline-none"
            />
          </div>
        </div>

        {/* Category & Grammatical Type */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5 flex items-center gap-1.5">
              <Tag className="w-3.5 h-3.5 text-larteh-400" /> Category
            </label>
            <select
              value={formData.category_id}
              onChange={(e) => setFormData({ ...formData, category_id: e.target.value })}
              disabled={isLoadingCategories}
              className="w-full px-4 py-2.5 rounded-xl bg-slate-900/90 border border-slate-700 focus:border-larteh-500 focus:ring-2 focus:ring-larteh-500/30 text-white text-sm transition outline-none"
            >
              <option value="">-- General Vocabulary --</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name} ({cat.entries_count || 0})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5 flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5 text-larteh-400" /> Grammatical Type
            </label>
            <select
              value={formData.grammatical_type}
              onChange={(e) => setFormData({ ...formData, grammatical_type: e.target.value })}
              className="w-full px-4 py-2.5 rounded-xl bg-slate-900/90 border border-slate-700 focus:border-larteh-500 focus:ring-2 focus:ring-larteh-500/30 text-white text-sm transition outline-none"
            >
              {GRAMMATICAL_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Speaker Name */}
        <div>
          <label className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5 flex items-center gap-1.5">
            <User className="w-3.5 h-3.5 text-larteh-400" /> Native Speaker Attribution
          </label>
          <input
            type="text"
            value={formData.speaker_name}
            onChange={(e) => setFormData({ ...formData, speaker_name: e.target.value })}
            placeholder="e.g. Dad, Nana Kwaku, Elder Ofei"
            className="w-full px-4 py-2.5 rounded-xl bg-slate-900/90 border border-slate-700 focus:border-larteh-500 focus:ring-2 focus:ring-larteh-500/30 text-white placeholder-slate-500 text-sm transition outline-none"
          />
        </div>

        {/* Cultural & Usage Notes */}
        <div>
          <label className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-1.5 flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-larteh-400" /> Cultural & Etymological Notes
          </label>
          <textarea
            rows="2"
            value={formData.cultural_notes}
            onChange={(e) => setFormData({ ...formData, cultural_notes: e.target.value })}
            placeholder="Contextual usage, historical origin, or traditional significance..."
            className="w-full px-4 py-2 rounded-xl bg-slate-900/90 border border-slate-700 focus:border-larteh-500 focus:ring-2 focus:ring-larteh-500/30 text-white placeholder-slate-500 text-sm transition outline-none resize-none"
          />
        </div>

        {/* Submission Button with Feedback */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3.5 px-6 rounded-xl bg-gradient-to-r from-larteh-600 via-larteh-500 to-forest-500 hover:from-larteh-500 hover:to-forest-400 text-white font-bold text-sm shadow-xl shadow-larteh-600/20 flex items-center justify-center gap-2 transition-all active:scale-[0.99] disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Uploading to Larteh Engine ({uploadProgress}%)...</span>
              </>
            ) : (
              <>
                <UploadCloud className="w-5 h-5" />
                <span>Save to Language Archive</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
