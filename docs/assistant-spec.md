# AI Assistant Panel Specification

This document outlines the plain-English behavior, design principles, and architecture for ParchaOS's original AI assistant panel.

**Legal Note**: This specification is written in a strict clean-room environment. We have purposefully NOT reviewed, read, or referenced Inled's "Sayri" assistant code or designs. This assistant is 100% original ParchaOS work, relying on independent public APIs and standard GNOME Shell UI paradigms. 

## 1. Core Behavior
The AI Assistant provides users with a fast, system-level conversational interface (text and optionally voice) to ask questions, draft content, and issue simple system commands.
- **Trigger**: The assistant can be summoned via a keyboard shortcut (e.g., `Super + Space` or a dedicated hotkey) or a status icon in the ParchaOS menu bar.
- **Interaction**: 
  - Users can type queries into a persistent chat-like UI.
  - The assistant streams responses back in real-time.
- **Context**: (Future Phase) The assistant may be granted access to read the clipboard or currently focused window for context-aware answers.

## 2. Design & Visual Chrome
- **Panel Layout**: A floating overlay or a side-panel sliding in from the right of the screen, styled to match the ParchaOS "Glass" and "Classic" themes. 
- **Originality**: The panel will use original GTK4/GNOME Shell styling (libadwaita/CSS). It will NOT copy the specific layout, animations, or visual chrome of any competitor.
- **UI Elements**: A scrollable chat history view, a text input field at the bottom, a settings gear icon, and a clear-chat button.

## 3. Backend & AI Provider (Design Decision)
To balance capability with user privacy, the assistant will support dual backends, selectable in the settings:

1. **Local Model (Ollama)**:
   - **Pros**: 100% private, works offline, no recurring costs.
   - **Cons**: High hardware requirements, slower, less capable.
   - **Integration**: Communicates with a local Ollama daemon via its simple REST API (`localhost:11434`).
2. **Cloud Model (Claude / OpenAI API)**:
   - **Pros**: Instant, highly capable, minimal local system load.
   - **Cons**: Requires internet, requires the user to provide their own API key (for privacy and cost reasons).
   - **Integration**: The OS will securely store the user's API key in GNOME Keyring. It will never route through ParchaOS servers to prevent man-in-the-middle data collection.

## 4. Implementation Guidelines
- **Foundation**: A GNOME Shell Extension (like `parchaos-global-menu`), using `extension.js`, `metadata.json`, and `stylesheet.css`.
- **References**: All code will be written against GNOME Shell's official API documentation and standard open-source examples (e.g., how to build a `PanelMenu.Button` and a `PopupBaseMenuItem` with custom drawing).

## 5. Status and refinements (2026-09-30)
Only this specification exists; nothing is built. Findings from checking Fedora 44:
- **Local backend is available without extra repositories:** `ollama` (0.12), `llama-cpp` and `python3-ollama` are in Fedora's own repositories. The user still pulls a model (for example a 3 billion parameter one) with `ollama pull`; models carry their own licences, so the app names the model and never bundles one.
- **Cloud backend:** the Anthropic and OpenAI HTTP APIs are plain HTTPS with streamed replies, so no vendor SDK is needed (`python3-anthropic` is not in Fedora anyway). The key is stored with libsecret (GNOME Keyring), never in a file, never sent anywhere but that provider.
- **Shortcut:** the spec's Super+Space is likely wanted by the system-wide search (#34) and interacts with the Super-as-Ctrl remap; use Ctrl+Alt+Space (or a setting) instead.
- **Shape:** build it as a small GTK4/libadwaita chat window plus a top-bar button, not a shell extension with custom drawing. It is easier to test (a fake server can stand in for both backends), works the same in the live session, and can still be summoned by shortcut.
- **Privacy rules to keep:** nothing is sent until the user picks a backend; the cloud backend shows a clear "leaves this computer" note; clipboard or window context is off by default and per request.
- **Effort:** about two days for chat, streaming, both backends, key storage and Settings entry. Testing beyond fake servers needs the user's key or a machine that can run a model.
