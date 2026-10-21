# Kokoro TTS Neural Speech Models

LearnWeave uses local ONNX inference with [Kokoro-82M](https://github.com/thewh1teagle/kokoro-onnx) for speech synthesis.

The model weights and voice pack are automatically searched in this directory:
- `kokoro-v1.0.onnx` (~325 MB)
- `voices.bin` (~28 MB)

Download commands (if not already downloaded):
```powershell
Invoke-WebRequest -Uri "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx" -OutFile "models/kokoro-v1.0.onnx"
Invoke-WebRequest -Uri "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin" -OutFile "models/voices.bin"
```
