#!/bin/bash
# Setup HuggingFace token for speaker diarization
# Usage: sudo ./setup-hf-token.sh YOUR_HF_TOKEN

if [ -z "$1" ]; then
    echo "Usage: $0 <huggingface_token>"
    echo ""
    echo "To get a token:"
    echo "  1. Accept model terms at: https://huggingface.co/pyannote/speaker-diarization-3.1"
    echo "  2. Create token at: https://huggingface.co/settings/tokens"
    exit 1
fi

HF_TOKEN="$1"

# Update the systemd service
sudo tee /etc/systemd/system/audio-checker.service > /dev/null << EOF
[Unit]
Description=Audio Quality Checker API
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/.openclaw/workspace/tools/audio-quality-checker/backend
Environment="PATH=/home/ubuntu/.openclaw/workspace/tools/audio-quality-checker/backend/venv/bin"
Environment="HF_TOKEN=${HF_TOKEN}"
ExecStart=/home/ubuntu/.openclaw/workspace/tools/audio-quality-checker/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart audio-checker

echo ""
echo "✅ HuggingFace token configured!"
echo ""
echo "Verifying service status..."
sleep 3
systemctl status audio-checker --no-pager | head -10

echo ""
echo "Speaker diarization should now work in deep mode analysis."
