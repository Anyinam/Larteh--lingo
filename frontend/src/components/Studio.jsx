import React, { useEffect, useRef, useState } from 'react';

const formatCount = (value) => new Intl.NumberFormat().format(value ?? 0);

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
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [recording, setRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [larteh, setLarteh] = useState('');
  const [phonetic, setPhonetic] = useState('');
  const [error, setError] = useState('');
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
    setLoading(true);
    setError('');
    setAudioBlob(null);
    try {
      const response = await fetch('/api/studio/next');
      const data = await response.json();
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
    fetchNext();
  }, []);

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
      const response = await fetch(`/api/studio/upload/${current.id}`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
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
    return <p className="p-8 text-center text-lg text-white" role="status">Loading Studio prompts…</p>;
  }

  if (!current && !error) {
    return (
      <section className="mx-auto mt-8 max-w-2xl rounded-2xl border border-green-700 bg-gray-900 p-8 text-center text-white">
        {stats && (
          <p className="mb-4 text-lg">
            Progress: {formatCount(stats.completed)} / {formatCount(stats.total)} items recorded
            {' '}({Number(stats.percentage ?? 0).toFixed(1)}%)
          </p>
        )}
        <h2 className="text-3xl font-bold text-green-300">All prompts are recorded</h2>
        <p className="mt-2 text-lg text-gray-200">Thank you for helping preserve Larteh.</p>
      </section>
    );
  }

  return (
    <section className="mx-auto mt-8 max-w-2xl rounded-2xl border border-gray-700 bg-gray-900 p-5 text-white shadow-xl sm:p-8">
      {stats && (
        <div className="mb-8">
          <p className="mb-2 text-base font-semibold text-gray-100" aria-live="polite">
            Progress: {formatCount(stats.completed)} / {formatCount(stats.total)} items recorded
            {' '}({Number(stats.percentage ?? 0).toFixed(1)}%)
          </p>
          <div
            className="h-4 overflow-hidden rounded-full bg-gray-700"
            role="progressbar"
            aria-label="Recording progress"
            aria-valuemin="0"
            aria-valuemax={stats.total || 0}
            aria-valuenow={stats.completed || 0}
          >
            <div
              className="h-full rounded-full bg-green-500 transition-all"
              style={{ width: `${Math.min(100, Math.max(0, stats.percentage || 0))}%` }}
            />
          </div>
        </div>
      )}

      {current && (
        <>
          <div className="mb-6 rounded-xl border border-gray-600 bg-gray-800 p-6 sm:p-8">
            <p className="mb-4 inline-block rounded-full bg-indigo-900 px-4 py-1 text-sm font-bold uppercase tracking-wide text-indigo-100">
              {current.category}
            </p>
            <h1 className="text-4xl font-extrabold leading-tight text-white sm:text-5xl">
              {current.english}
            </h1>
            {current.twi && (
              <p className="mt-4 text-2xl italic text-gray-200">
                Twi: <span>{current.twi}</span>
              </p>
            )}
          </div>

          <div className="mb-6 grid gap-4 text-left sm:grid-cols-2">
            <div>
              <label htmlFor="studio-larteh" className="mb-2 block text-base font-semibold text-gray-100">
                Larteh transcription (optional)
              </label>
              <input
                id="studio-larteh"
                value={larteh}
                onChange={(event) => setLarteh(event.target.value)}
                className="w-full rounded-lg border border-gray-500 bg-gray-800 px-4 py-3 text-lg text-white placeholder:text-gray-400 focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-300"
                autoComplete="off"
              />
            </div>
            <div>
              <label htmlFor="studio-phonetic" className="mb-2 block text-base font-semibold text-gray-100">
                Phonetic transcription (optional)
              </label>
              <input
                id="studio-phonetic"
                value={phonetic}
                onChange={(event) => setPhonetic(event.target.value)}
                className="w-full rounded-lg border border-gray-500 bg-gray-800 px-4 py-3 text-lg text-white placeholder:text-gray-400 focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-300"
                autoComplete="off"
              />
            </div>
          </div>

          <div className="mb-6 flex flex-col justify-center gap-4 sm:flex-row">
            {!recording ? (
              <button
                type="button"
                onClick={startRecording}
                disabled={loading}
                className="min-h-16 rounded-full bg-red-700 px-8 py-4 text-xl font-bold text-white transition hover:bg-red-600 focus:outline-none focus:ring-4 focus:ring-red-300 disabled:opacity-60"
              >
                🔴 Start Recording
              </button>
            ) : (
              <button
                type="button"
                onClick={stopRecording}
                className="min-h-16 animate-pulse rounded-full bg-yellow-400 px-8 py-4 text-xl font-bold text-gray-950 transition hover:bg-yellow-300 focus:outline-none focus:ring-4 focus:ring-yellow-200"
              >
                ⏹️ Stop Recording
              </button>
            )}
          </div>

          {audioUrl && (
            <div className="space-y-4">
              <audio controls src={audioUrl} className="w-full" aria-label="Recording preview">
                Your browser does not support audio playback.
              </audio>
              <button
                type="button"
                onClick={saveAndNext}
                disabled={loading || recording}
                className="min-h-16 w-full rounded-xl bg-green-700 px-6 py-4 text-xl font-bold text-white transition hover:bg-green-600 focus:outline-none focus:ring-4 focus:ring-green-300 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? 'Uploading recording…' : '➔ Save & Next Word'}
              </button>
            </div>
          )}
        </>
      )}

      {error && (
        <div className="mt-5 rounded-lg border border-red-400 bg-red-950 p-4 text-lg text-red-100" role="alert">
          <p>{error}</p>
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
