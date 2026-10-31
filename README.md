# Larteh Leingo (Gua Language Engine) 🇬🇭

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Stack: Flask + React](https://img.shields.io/badge/Stack-Flask%20%7C%20React%20%7C%20PostgreSQL-blue)](https://github.com/)

**Larteh Lingo** is an open-source digital preservation engine and community learning platform for **Larteh (Gua)**—a low-resource, native West African language spoken in the Eastern Region of Ghana.

The mission of this project is two-fold:
1. **Cultural Preservation:** Provide the global Ghanaian diaspora and future generations with an authentic, open-access mobile PWA to hear, learn, and preserve native pronunciations, common vocabulary, and oral traditions.
2. **Dataset Infrastructure:** Build a structured, phonetically aligned speech-to-text dataset (audio-text pairs) that can power future AI translation models, academic research, and linguistic documentation.

---

## 🌟 Key Features

- 🔊 **Native Speaker Audio:** High-bitrate voice recordings captured directly from elder native speakers.
- 📱 **Mobile-First PWA:** Fast, offline-capable React Progressive Web App with audio waveform previews and interactive flashcards.
- 🗣️ **Phonetic & Audio Engine:** Browser-based recording interface for easy crowdsourcing and lexical entries.
- 📊 **Structured AI Datasets:** Automated export pipeline generating JSONL/CSV datasets (Common Voice / Hugging Face compatible) for speech model training.
- 🔍 **Lexicon Search:** Instant search across Larteh spelling, phonetic scripts, and English translations.

---

## 🏗️ Architecture & Tech Stack

```text
[ React PWA / Vite ]  <--->  [ REST API / Flask ]  <--->  [ PostgreSQL DB ]
 (Web Audio Recorder)         (Python 3.11+)             (Lexical & Audio Metadata)
                                    │
                                    ▼
                          [ S3 / Cloudflare R2 ]
                           (Lossless Audio Storage)
