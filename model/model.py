import torch
import torch.nn as nn
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence

class EmotionCNN_LSTM(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers, num_classes, dropout=0.4):
        super().__init__()
        self.conv1 = nn.Conv1d(in_channels=input_dim, out_channels=64, kernel_size=5, padding=2)
        self.bn1 = nn.BatchNorm1d(64)
        self.conv2 = nn.Conv1d(64, 128, kernel_size=5, padding=2)
        self.bn2 = nn.BatchNorm1d(128)
        self.pool = nn.MaxPool1d(2)
        self.dropout_cnn = nn.Dropout(dropout)

        self.lstm = nn.LSTM(
            input_size=128, hidden_size=hidden_dim, num_layers=num_layers,
            batch_first=True, bidirectional=True, dropout=dropout
        )
        self.dropout_lstm = nn.Dropout(dropout)
        self.attention = nn.Linear(hidden_dim * 2, 1)
        self.fc = nn.Linear(hidden_dim * 2, num_classes)

    def forward(self, x, lengths):
        # x: (batch, time, features)
        x = x.permute(0, 2, 1)          # (batch, features, time)
        x = torch.relu(self.bn1(self.conv1(x)))
        x = self.pool(x)
        x = torch.relu(self.bn2(self.conv2(x)))
        x = self.pool(x)
        x = self.dropout_cnn(x)

        x = x.permute(0, 2, 1)          # (batch, new_time, 128)
        new_lengths = lengths // 4       # because of two MaxPool1d(2)

        packed = pack_padded_sequence(x, new_lengths.cpu(), batch_first=True, enforce_sorted=False)
        lstm_out, _ = self.lstm(packed)
        lstm_out, _ = pad_packed_sequence(lstm_out, batch_first=True)   # (batch, new_time, hidden*2)

        # Attention over time
        attn_weights = torch.softmax(self.attention(lstm_out), dim=1)   # (batch, new_time, 1)
        context = torch.sum(attn_weights * lstm_out, dim=1)             # (batch, hidden*2)
        context = self.dropout_lstm(context)

        out = self.fc(context)
        return out