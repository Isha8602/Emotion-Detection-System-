import librosa
import numpy as np
import pickle
import os

SAMPLE_RATE = 22050
N_MELS = 128
USE_DELTAS = True   # must match your training configuration

# Load normalisation statistics if they exist (optional)
norm_stats_path = os.path.join(os.path.dirname(__file__), 'norm_stats.pkl')
if os.path.exists(norm_stats_path):
    with open(norm_stats_path, 'rb') as f:
        mean, std = pickle.load(f)
else:
    # If not saved, you can compute on the fly from a representative file,
    # but it's better to save them during training.
    mean, std = None, None
    print("Warning: norm_stats.pkl not found. Normalisation will be skipped.")

def extract_mel_spectrogram(audio, sr=SAMPLE_RATE):
    """Convert raw audio to log‑mel spectrogram with deltas."""
    mel = librosa.feature.melspectrogram(y=audio, sr=sr, n_mels=N_MELS, fmax=8000)
    log_mel = librosa.power_to_db(mel, ref=np.max)   # (n_mels, time)
    if USE_DELTAS:
        delta = librosa.feature.delta(log_mel)
        delta2 = librosa.feature.delta(log_mel, order=2)
        feat = np.concatenate((log_mel, delta, delta2), axis=0)  # (3*n_mels, time)
    else:
        feat = log_mel
    feat = feat.T   # (time, features)
    return feat

def normalize(feature, mean, std):
    """Apply z‑score normalisation."""
    return (feature - mean) / (std + 1e-8)

def process_audio(audio, sr=SAMPLE_RATE):
    """Full pipeline: extract features, normalise, return tensor."""
    feat = extract_mel_spectrogram(audio, sr)
    if mean is not None and std is not None:
        feat = normalize(feat, mean, std)
    # Convert to tensor and add batch dimension
    tensor = torch.tensor(feat, dtype=torch.float32).unsqueeze(0)  # (1, time, feat_dim)
    return tensor, feat.shape[0]   # also return length for packing