"""Deterministic MFCC and log-mel feature extraction for Studio WAV files."""

import io
import wave

import numpy as np

from backend.app.utils.ml_audio_processor import process_and_resample_audio


def _hz_to_mel(frequency: np.ndarray) -> np.ndarray:
    return 2595.0 * np.log10(1.0 + frequency / 700.0)


def _mel_to_hz(mel: np.ndarray) -> np.ndarray:
    return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)


def _mel_filterbank(
    sample_rate: int,
    n_fft: int,
    n_mels: int,
) -> np.ndarray:
    low_mel = _hz_to_mel(np.array([0.0]))[0]
    high_mel = _hz_to_mel(np.array([sample_rate / 2]))[0]
    mel_points = np.linspace(low_mel, high_mel, n_mels + 2)
    hz_points = _mel_to_hz(mel_points)
    bin_points = np.floor((n_fft + 1) * hz_points / sample_rate).astype(int)
    filters = np.zeros((n_mels, n_fft // 2 + 1), dtype=np.float32)

    for mel_index in range(n_mels):
        left, center, right = bin_points[mel_index:mel_index + 3]
        for bin_index in range(left, center):
            if center > left:
                filters[mel_index, bin_index] = (bin_index - left) / (center - left)
        for bin_index in range(center, right):
            if right > center:
                filters[mel_index, bin_index] = (right - bin_index) / (right - center)
    return filters


def extract_acoustic_features(
    audio_bytes: bytes,
    target_sample_rate: int = 16000,
    n_mels: int = 80,
    n_mfcc: int = 13,
) -> dict:
    """Return log-mel and MFCC arrays, normalized audio metadata, and frame times."""
    if target_sample_rate <= 0:
        raise ValueError("Target sample rate must be a positive integer.")
    if n_mels <= 0 or n_mels > 257:
        raise ValueError("n_mels must be between 1 and 257.")
    if n_mfcc <= 0 or n_mfcc > n_mels:
        raise ValueError("n_mfcc must be between 1 and n_mels.")

    wav_bytes, duration_sec, sample_rate = process_and_resample_audio(
        audio_bytes,
        target_sample_rate=target_sample_rate,
    )
    with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
        if wav_file.getnchannels() != 1 or wav_file.getsampwidth() != 2:
            raise ValueError("Normalized audio must be mono 16-bit PCM WAV.")
        samples = np.frombuffer(wav_file.readframes(wav_file.getnframes()), dtype="<i2")

    signal = samples.astype(np.float32) / 32768.0
    if signal.size == 0:
        raise ValueError("Audio payload contains no samples.")

    frame_length = int(round(0.025 * sample_rate))
    hop_length = int(round(0.010 * sample_rate))
    n_fft = 1 << (frame_length - 1).bit_length()
    half_frame = frame_length // 2
    padding_mode = "reflect" if signal.size > 1 else "edge"
    padded = np.pad(signal, (half_frame, half_frame), mode=padding_mode)
    frame_count = 1 + max(0, (len(padded) - frame_length) // hop_length)
    frames = np.stack([
        padded[start:start + frame_length]
        for start in range(0, frame_count * hop_length, hop_length)
    ])
    window = np.hamming(frame_length).astype(np.float32)
    spectrum = np.fft.rfft(frames * window, n=n_fft, axis=1)
    power_spectrum = (np.abs(spectrum) ** 2 / n_fft).astype(np.float32)
    filterbank = _mel_filterbank(sample_rate, n_fft, n_mels)
    mel_spectrogram = np.maximum(power_spectrum @ filterbank.T, 1e-10)
    log_mel = np.log(mel_spectrogram)

    mel_count = log_mel.shape[1]
    coefficients = np.arange(n_mfcc, dtype=np.float32)[:, None]
    mel_bins = np.arange(mel_count, dtype=np.float32)[None, :]
    dct_basis = np.cos(np.pi / mel_count * (mel_bins + 0.5) * coefficients)
    dct_basis[0] *= np.sqrt(1.0 / mel_count)
    if n_mfcc > 1:
        dct_basis[1:] *= np.sqrt(2.0 / mel_count)
    mfcc = (log_mel @ dct_basis.T).astype(np.float32)

    return {
        "mfcc": mfcc,
        "mel_spectrogram": log_mel.astype(np.float32),
        "frame_times_sec": (np.arange(frame_count) * hop_length / sample_rate).astype(np.float32),
        "duration_sec": duration_sec,
        "sample_rate": sample_rate,
    }
