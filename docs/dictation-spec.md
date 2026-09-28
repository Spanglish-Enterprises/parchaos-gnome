# System-wide Voice Dictation Specification

This document defines the architecture and behavior for ParchaOS's system-wide voice dictation feature (Ticket #119).

**Legal Note**: This integration uses `whisper.cpp` (`ggerganov/whisper.cpp`), which is an independent, MIT-licensed project. There is zero exposure to Inled's stack. The wrapper UI is 100% original.

## 1. Core Behavior
Provide users with an on-demand voice-to-text dictation tool that works in *any* text field across the entire OS (Wayland and XWayland).
- **Global Hotkey**: Triggered by a specific keyboard shortcut (e.g., `Super + D` or a double-tap of `Ctrl`), similar to macOS dictation.
- **Privacy-First**: Operates 100% locally. After the initial acoustic model is downloaded, no network connection is required. Audio data never leaves the machine.
- **Output**: Transcribed text is automatically inserted at the current cursor position.

## 2. Architecture & Implementation
The feature will be shipped as a new package `parchaos-dictation/` containing a GNOME Shell Extension.
- **Audio Capture**: Leverages GNOME's native PipeWire/GStreamer audio capture pipelines.
- **Transcription Engine**: Uses a local `whisper.cpp` binary. 
  - To prevent bloating the default ISO, the acoustic models (`base.en` or `small.en`, ~100-500MB) will be downloaded on-demand during the user's first initialization of the feature.
- **Text Insertion**: 
  - To inject text into arbitrary application windows securely under Wayland, the extension will use the exact `Clutter.VirtualInputDevice.notify_keyval()` technique already proven in `parchaos-global-menu/files/extension.js` (specifically the `sendKeyCombo()` helper).
  - This avoids reinventing synthetic keyboard input from scratch.

## 3. UI/UX
- **Recording Indicator**: While listening, a highly visible recording indicator (microphone icon) will appear in the top bar.
- **Status Menu**: We will reuse the `PanelMenu.Button` pattern (established in the WeatherIndicator of `parchaos-global-menu`) to provide a status icon and a popup menu to select language models or adjust input sensitivity.
