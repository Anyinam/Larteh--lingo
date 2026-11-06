import React, { useEffect, useRef, useState } from 'react';
import { ArrowRight, Check, Mic, ShieldCheck, Square } from 'lucide-react';

const formatCount = (value) => new Intl.NumberFormat().format(value ?? 0);
const CONTRIBUTOR_STORAGE_KEY = 'larteh-studio-contributor-id';
const API_ORIGIN = import.meta.env.VITE_API_ORIGIN || '';

function createContributorId() {
  if (window.crypto?.randomUUID) {
    return window.crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (character) => {
    const randomValue = Math.floor(Math.random() * 16);
    return (character === 'x' ? randomValue : (randomValue & 0x3) | 0x8).toString(16);
  });
}

async function readJsonResponse(response, failureMessage) {
  const body = await response.text();
  try {
    return JSON.parse(body);
  } catch {
    if (!response.ok) {
      throw new Error(`Request failed (${response.status}). ${failureMessage}`);
    }
    throw new Error('The server returned an invalid response. Please try again.');
  }
}

async function encodeWav(recordedBlob) {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) {
    throw new Error('This browser cannot prepare a WAV recording.');
  }

  const audioContext = new AudioContextClass();
  try {
    const audioBuffer = await audioContext.decodeAudioData(await recordedBlob.arrayBuffer());
    const sampleCount = audioBuffer.length;
    const wavBuffer = new ArrayBuffer(44 + sampleCount * 2);
    const view = new DataView(wavBuffer);
    const writeString = (offset, value) => {
      for (let index = 0; index < value.length; index += 1) {
        view.setUint8(offset + index, value.charCodeAt(index));
      }
    };

    writeString(0, 'RIFF');
    view.setUint32(4, 36 + sampleCount * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, audioBuffer.sampleRate, true);
    view.setUint32(28, audioBuffer.sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(36, 'data');
    view.setUint32(40, sampleCount * 2, true);

    const channels = Array.from(
      { length: audioBuffer.numberOfChannels },
      (_, index) => audioBuffer.getChannelData(index),
    );
    for (let index = 0; index < sampleCount; index += 1) {
      const sample = channels.reduce((sum, channel) => sum + channel[index], 0) / channels.length;
      const clipped = Math.max(-1, Math.min(1, sample));
      view.setInt16(44 + index * 2, clipped < 0 ? clipped * 0x8000 : clipped * 0x7fff, true);
    }

    return new Blob([wavBuffer], { type: 'audio/wav' });
  } finally {
    await audioContext.close();
  }
}

export default function Studio() {
  const [current, setCurrent] = useState(null);
  const [contributorId, setContributorId] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [recording, setRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [larteh, setLarteh] = useState('');
  const [phonetic, setPhonetic] = useState('');
  const [error, setError] = useState('');
  const [promptConflict, setPromptConflict] = useState(false);
  const recorderRef = useRef(null);
  const streamRef = useRef(null);

  useEffect(() => {
    if (!audioBlob) {
      setAudioUrl(null);
      return undefined;
    }

    const url = URL.createObjectURL(audioBlob);
    setAudioUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [audioBlob]);

  useEffect(() => () => {
    if (recorderRef.current?.state !== 'inactive') {
      recorderRef.current?.stop();
    }
    streamRef.current?.getTracks().forEach((track) => track.stop());
  }, []);

  const fetchNext = async () => {
    if (!contributorId) return;
    setLoading(true);
    setError('');
    setPromptConflict(false);
    setAudioBlob(null);
    try {
      const response = await fetch(`${API_ORIGIN}/api/studio/next`, {
        headers: { 'X-Contributor-ID': contributorId },
      });
      const data = await readJsonResponse(response, 'Could not load the next prompt.');
      setStats(data.stats ?? null);
      if (response.status === 404) {
        setCurrent(null);
        return;
      }
      if (!response.ok) {
        throw new Error(data.message || 'Could not load the next prompt.');
      }
      setCurrent(data.item);
      setLarteh(data.item?.larteh ?? '');
      setPhonetic(data.item?.phonetic ?? '');
    } catch (requestError) {
      setError(requestError.message || 'Could not load the next prompt.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    try {
      let savedContributorId = window.localStorage.getItem(CONTRIBUTOR_STORAGE_KEY);
      if (!savedContributorId) {
        savedContributorId = createContributorId();
        window.localStorage.setItem(CONTRIBUTOR_STORAGE_KEY, savedContributorId);
      }
      setContributorId(savedContributorId);
    } catch {
      setError('This browser cannot save your anonymous contributor ID. Please enable local storage and reload to keep your progress on this device.');
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (contributorId) fetchNext();
  }, [contributorId]);

  const startRecording = async () => {
    setError('');
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setError('Audio recording is not supported by this browser.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const preferredType = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
      ].find((type) => MediaRecorder.isTypeSupported(type));
      const recorder = new MediaRecorder(
        stream,
        preferredType ? { mimeType: preferredType } : undefined,
      );
      const chunks = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunks.push(event.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        setRecording(false);
        try {
          const recordedBlob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
          setAudioBlob(await encodeWav(recordedBlob));
        } catch (conversionError) {
          setError(conversionError.message || 'Could not prepare the WAV recording.');
        }
      };
      recorder.onerror = () => {
        setError('The recording could not be completed. Please try again.');
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        setRecording(false);
      };
      recorderRef.current = recorder;
      setAudioBlob(null);
      recorder.start();
      setRecording(true);
    } catch (recordingError) {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      setError(recordingError.message || 'Could not access the microphone.');
    }
  };

  const stopRecording = () => {
    if (recorderRef.current?.state === 'recording') {
      recorderRef.current.stop();
    }
  };

  const saveAndNext = async () => {
    if (!audioBlob || !current) return;

    setLoading(true);
    setError('');
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');
    formData.append('larteh', larteh);
    formData.append('phonetic', phonetic);

    try {
      const response = await fetch(`${API_ORIGIN}/api/studio/upload/${current.id}`, {
        method: 'POST',
        headers: { 'X-Contributor-ID': contributorId },
        body: formData,
      });
      const data = await readJsonResponse(response, 'The recording could not be uploaded.');
      if (response.status === 409) {
        setPromptConflict(true);
        setError(data.message || 'Another contributor saved this prompt first.');
        setLoading(false);
        return;
      }
      if (!response.ok) {
        throw new Error(data.message || 'The recording could not be uploaded.');
      }
      await fetchNext();
    } catch (requestError) {
      setError(requestError.message || 'The recording could not be uploaded.');
      setLoading(false);
    }
  };

  if (loading && !current) {
    return (
      <div className="mx-auto mt-8 max-w-4xl rounded-[28px] border border-white/10 bg-[#101e19] p-10 text-center text-slate-300" role="status">
        <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-2 border-emerald-300/20 border-t-emerald-300" />
        Loading your next prompt…
      </div>
    );
  }

  if (!current && !error) {
    return (
      <section className="mx-auto mt-8 max-w-4xl rounded-[28px] border border-emerald-300/20 bg-gradient-to-br from-[#11251c] to-[#0c1713] p-8 text-center text-white shadow-2xl sm:p-12">
        {stats && (
          <p className="mb-6 text-base font-semibold text-slate-300">
            Progress: {formatCount(stats.completed)} / {formatCount(stats.total)} items recorded
            {' '}({Number(stats.percentage ?? 0).toFixed(1)}%)
          </p>
        )}
        <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-3xl bg-emerald-300/10 text-emerald-200">
          <Check className="h-8 w-8" />
        </div>
        <h2 className="text-3xl font-bold text-white sm:text-4xl">Every prompt has a voice.</h2>
        <p className="mx-auto mt-3 max-w-lg text-lg leading-7 text-slate-300">
          You have completed this set. Thank you for helping preserve Larteh for the next generation.
        </p>
      </section>
    );
  }

  return (
    <section className="mx-auto mt-8 max-w-4xl overflow-hidden rounded-[28px] border border-white/10 bg-[#101e19]/95 text-white shadow-[0_30px_100px_rgba(0,0,0,0.4)]">
      {stats && (
        <div className="border-b border-white/10 px-6 py-5 sm:px-9">
          <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-emerald-200">Your contribution</p>
              <p className="mt-1 text-sm text-slate-400" aria-live="polite">
                {formatCount(stats.completed)} of {formatCount(stats.total)} prompts recorded
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Your progress on this device · family coverage: {formatCount(stats.family_completed)} prompts
              </p>
            </div>
            <span className="text-lg font-bold tabular-nums text-white">
              {Number(stats.percentage ?? 0).toFixed(1)}%
            </span>
          </div>
          <div
            className="h-2.5 overflow-hidden rounded-full bg-white/10"
            role="progressbar"
            aria-label="Recording progress"
            aria-valuemin="0"
            aria-valuemax={stats.total || 0}
            aria-valuenow={stats.completed || 0}
          >
            <div
              className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-300 transition-all duration-500"
              style={{ width: `${Math.min(100, Math.max(0, stats.percentage || 0))}%` }}
            />
          </div>
        </div>
      )}

      {current && (
        <div className="px-6 py-6 sm:px-9 sm:py-8">
          <div className="mb-6 flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Read this prompt aloud in Larteh</p>
              <p className="mt-1 text-sm text-slate-400">Take your time. Speak naturally.</p>
              <p className="mt-1 text-xs text-slate-500">Each family contributor can record this prompt once.</p>
            </div>
            <span className="hidden items-center gap-2 rounded-full border border-emerald-300/15 bg-emerald-300/[0.07] px-3 py-2 text-xs font-semibold text-emerald-200 sm:inline-flex">
              <ShieldCheck className="h-4 w-4" /> Private recording
            </span>
          </div>

          <div className="relative mb-7 overflow-hidden rounded-[24px] border border-emerald-200/10 bg-gradient-to-br from-[#173629] via-[#12271f] to-[#102019] p-6 sm:p-9">
            <div className="pointer-events-none absolute -right-10 -top-20 h-56 w-56 rounded-full bg-emerald-300/[0.08] blur-3xl" />
            <div className="relative">
              <p className="mb-5 inline-flex rounded-full border border-amber-200/20 bg-amber-200/[0.08] px-3 py-1.5 text-xs font-bold uppercase tracking-[0.16em] text-amber-100">
                {current.category}
              </p>
              <h1 className="max-w-3xl text-4xl font-black leading-[1.08] tracking-tight text-white sm:text-6xl">
                {current.english}
              </h1>
              {current.twi && (
                <p className="mt-5 border-t border-white/10 pt-4 text-lg text-slate-300 sm:text-xl">
                  Twi context: <span className="font-medium italic text-emerald-100">{current.twi}</span>
                </p>
              )}
            </div>
          </div>

          <div className="mb-7 grid gap-4 text-left sm:grid-cols-2">
            <div>
              <label htmlFor="studio-larteh" className="mb-2 block text-sm font-semibold text-slate-200">
                Larteh transcription (optional)
              </label>
              <input
                id="studio-larteh"
                value={larteh}
                onChange={(event) => setLarteh(event.target.value)}
                placeholder="Add the Larteh word if known"
                className="min-h-14 w-full rounded-xl border border-white/10 bg-[#09140f] px-4 py-3 text-lg text-white placeholder:text-slate-500 focus:border-emerald-300/60 focus:outline-none focus:ring-2 focus:ring-emerald-300/20"
                autoComplete="off"
              />
            </div>
            <div>
              <label htmlFor="studio-phonetic" className="mb-2 block text-sm font-semibold text-slate-200">
                Phonetic transcription (optional)
              </label>
              <input
                id="studio-phonetic"
                value={phonetic}
                onChange={(event) => setPhonetic(event.target.value)}
                placeholder="Add pronunciation notes if known"
                className="min-h-14 w-full rounded-xl border border-white/10 bg-[#09140f] px-4 py-3 text-lg text-white placeholder:text-slate-500 focus:border-emerald-300/60 focus:outline-none focus:ring-2 focus:ring-emerald-300/20"
                autoComplete="off"
              />
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-[#0b1712] p-4 sm:p-5">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-semibold text-white">Voice recording</p>
                <p className="mt-1 text-sm text-slate-400">
                  {recording ? 'Recording in progress…' : audioUrl ? 'Preview your recording, or record again.' : 'Make sure you are somewhere quiet.'}
                </p>
              </div>
              <div className="flex h-9 items-center gap-1.5" aria-hidden="true">
                {[12, 21, 15, 27, 17, 24, 11, 20, 14].map((height, index) => (
                  <span
                    key={index}
                    className={`w-1 rounded-full bg-emerald-300/70 ${recording ? 'animate-pulse' : ''}`}
                    style={{ height: `${height}px`, animationDelay: `${index * 80}ms` }}
                  />
                ))}
              </div>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row">
            {!recording ? (
              <button
                type="button"
                onClick={startRecording}
                disabled={loading}
                className="flex min-h-14 flex-1 items-center justify-center gap-3 rounded-xl bg-rose-600 px-6 py-4 text-lg font-bold text-white transition hover:bg-rose-500 focus:outline-none focus:ring-4 focus:ring-rose-300/30 disabled:opacity-60"
              >
                <Mic className="h-5 w-5" /> {audioUrl ? 'Record again' : 'Start recording'}
              </button>
            ) : (
              <button
                type="button"
                onClick={stopRecording}
                className="flex min-h-14 flex-1 items-center justify-center gap-3 rounded-xl bg-amber-300 px-6 py-4 text-lg font-bold text-amber-950 transition hover:bg-amber-200 focus:outline-none focus:ring-4 focus:ring-amber-200/30"
              >
                <Square className="h-4 w-4 fill-current" /> Stop recording
              </button>
            )}
            </div>

          {audioUrl && (
            <div className="mt-4 space-y-4">
              <div className="rounded-xl border border-white/10 bg-[#101e19] p-3">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Recording preview</p>
                <audio controls src={audioUrl} className="w-full" aria-label="Recording preview">
                Your browser does not support audio playback.
                </audio>
              </div>
              <button
                type="button"
                onClick={saveAndNext}
                disabled={loading || recording}
                className="flex min-h-14 w-full items-center justify-center gap-3 rounded-xl bg-emerald-400 px-6 py-4 text-lg font-bold text-emerald-950 transition hover:bg-emerald-300 focus:outline-none focus:ring-4 focus:ring-emerald-300/30 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? 'Saving recording…' : <>Save recording & next prompt <ArrowRight className="h-5 w-5" /></>}
              </button>
            </div>
          )}
          </div>
        </div>
      )}

      {error && (
        <div className="m-6 rounded-xl border border-rose-400/30 bg-rose-950/60 p-4 text-base text-rose-100 sm:m-9" role="alert">
          <p>{error}</p>
          {promptConflict && current && (
            <button
              type="button"
              onClick={fetchNext}
              disabled={loading}
              className="mt-3 rounded-lg bg-rose-700 px-5 py-3 font-semibold text-white hover:bg-rose-600 disabled:opacity-60"
            >
              Load next prompt
            </button>
          )}
          {!current && (
            <button
              type="button"
              onClick={fetchNext}
              disabled={loading}
              className="mt-3 rounded-lg bg-red-700 px-5 py-3 font-semibold text-white hover:bg-red-600 disabled:opacity-60"
            >
              Try again
            </button>
          )}
        </div>
      )}
    </section>
  );
}
