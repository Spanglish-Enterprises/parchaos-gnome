# System-wide Voice Dictation Specification

This document defines the architecture and behavior for ParchaOS's system-wide voice dictation feature (Ticket #119).

**Legal Note**: This integration uses `whisper.cpp` (`ggerganov/whisper.cpp`), which is an independent, MIT-licensed project. There is zero exposure to Inled's stack. The wrapper UI is 100% original.

## 1. Core Behavior
Provide users with an on-demand voice-to-text dictation tool that works in *any* text field across the entire OS (Wayland and XWayland).
- **Global Hotkey**: Triggered by a specific keyboard shortcut (e.g., `Super + D` or a double-tap of `Ctrl`), matching the reference desktop behavior.
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

## 4. As built (2026-09-29)
- Package `parchaos-dictation` (extension `parchaos-dictation@parchaos.org`, helpers in `/usr/libexec/parchaos-dictation/`). Shortcut **Ctrl+Alt+D** (gsettings `org.parchaos.dictation toggle-shortcut`; Super is avoided because xremap uses it).
- Fedora's `whisper-cpp` ships libraries only, no CLI, so transcription uses `python3-pywhispercpp` (`parchaos-dictation-transcribe`). Recording uses `pw-record` (pipewire-utils) at 16 kHz mono.
- **Not in the ISO and not required by parchaos-desktop.** `whisper-cpp` depends on the ROCm/HIP and OpenVINO libraries: installing it pulls 40 packages (53 MiB download), which the release-size limit (see DEVELOPMENT.md) cannot absorb. Users opt in with `sudo dnf install parchaos-dictation`.
- The model (`base.en`, 148 MB) is fetched on first use by `parchaos-dictation-model`, size and SHA-256 pinned in the script and checked before the file is used.
- Text is typed as key presses through a Clutter virtual keyboard (no clipboard, works in terminals). A keyboard layout can only type its own letters, so the transcriber reduces text to plain ASCII (curly quotes straight, accents dropped). English only for now.
- Tested in the isolated headless shell with stand-in recorder/transcriber typing into a GTK entry (`PARCHAOS_DICTATION_RECORDER/TRANSCRIBER/MODEL_TOOL` env overrides); not yet with a real microphone or real model.
