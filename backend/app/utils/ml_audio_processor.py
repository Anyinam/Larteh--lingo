"""
ML Audio Utility for Speech Model Ingestion (Wav2Vec 2.0 / Whisper / TTS).

Provides high-performance audio conversion, resample normalization (16kHz mono PCM WAV),
and precise speech duration calculations for Hugging Face / Common Voice datasets.
"""

import io
import warnings
from typing import Union, BinaryIO, Tuple
from pydub import AudioSegment

# Suppress runtime warnings from pydub if ffmpeg/avconv is not globally installed
warnings.filterwarnings("ignore", category=RuntimeWarning, module="pydub.utils")


def process_and_resample_audio(
    file_bytes: Union[bytes, io.BytesIO, BinaryIO],
    target_sample_rate: int = 16000,
) -> Tuple[bytes, float, int]:
    """
    Resample and normalize an audio recording to the ML standard:
    16kHz, single-channel (mono), 16-bit uncompressed PCM WAV.

    Args:
        file_bytes: Raw audio byte buffer or binary file-like object.
        target_sample_rate: Target audio frequency in Hz (default: 16000 Hz).

    Returns:
        Tuple[bytes, float, int]:
            - resampled_wav_bytes: 16kHz mono WAV byte buffer ready for S3/R2 upload.
            - duration_sec: Exact audio duration in seconds (float, rounded to 4 decimals).
            - sample_rate: The resulting sample rate (integer, e.g. 16000).

    Raises:
        ValueError: If file_bytes is empty or cannot be parsed as valid audio.
    """
    if not file_bytes:
        raise ValueError("Audio input cannot be empty.")

    # Convert to bytes if stream or BytesIO
    if isinstance(file_bytes, bytes):
        raw_data = file_bytes
    elif hasattr(file_bytes, "read"):
        if hasattr(file_bytes, "seek"):
            file_bytes.seek(0)
        raw_data = file_bytes.read()
    else:
        raise TypeError(f"Unsupported audio type: {type(file_bytes)}")

    if len(raw_data) == 0:
        raise ValueError("Audio payload contains 0 bytes.")

    buffer = io.BytesIO(raw_data)

    # 1. Parse Audio Segment (support native WAV without external ffprobe dependency)
    audio: AudioSegment
    try:
        if raw_data.startswith(b"RIFF") and b"WAVE" in raw_data[:16]:
            audio = AudioSegment.from_file(buffer, format="wav")
        else:
            # Let pydub inspect or fallback
            audio = AudioSegment.from_file(buffer)
    except Exception as err:
        # Fallback attempt forcing wav decode
        try:
            buffer.seek(0)
            audio = AudioSegment.from_file(buffer, format="wav")
        except Exception:
            raise ValueError(f"Unable to parse audio stream: {err}") from err

    # 2. Resample to ML Standard: 16kHz, mono (1 channel), 16-bit PCM (sample_width=2)
    resampled = (
        audio.set_frame_rate(target_sample_rate)
        .set_channels(1)
        .set_sample_width(2)
    )

    # 3. Calculate exact duration in seconds
    duration_sec = round(len(resampled) / 1000.0, 4)
    sample_rate = resampled.frame_rate

    # 4. Export normalized 16-bit mono WAV buffer
    export_buffer = io.BytesIO()
    resampled.export(export_buffer, format="wav")
    export_buffer.seek(0)
    resampled_wav_bytes = export_buffer.getvalue()

    return resampled_wav_bytes, duration_sec, sample_rate

