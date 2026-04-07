# Audio Detection System – CNN/LSTM + Flask

A real‑time audio event detection web application that uses a hybrid **CNN‑LSTM** deep learning model to classify environmental sounds. The backend is built with **Flask** (Python) and serves a simple web interface for file upload or live microphone recording.

**Current model accuracy: 61%** (baseline – see [Performance](#performance)).

---

## 📋 Table of Contents

- [Features](#features)
- [System Architecture](#system-architecture)
- [Model Details](#model-details)
- [Performance](#performance)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Frontend Usage](#frontend-usage)
- [Future Improvements](#future-improvements)
- [License](#license)

---

## ✨ Features

- **Upload audio file** (WAV, MP3, OGG) for detection.
- **Live microphone recording** (Web Audio API) with real‑time classification.
- **Hybrid CNN‑LSTM model** – captures both local spectral patterns and long‑term temporal dependencies.
- **Flask REST API** – easy integration with other applications.
- **Visual feedback** – shows predicted class with confidence score and spectrogram preview.

---

## 🧠 System Architecture
