# Natural-Language Search Specification

This document defines the approach for integrating natural-language search into the ParchaOS Launcher (Ticket #120).

**Legal Note**: This is a pure extension of our existing, original `parchaos-launcher` code. There is zero legal exposure.

## 1. Core Behavior
The goal is to allow users to find files in the launcher using conversational timeframes and filetypes (e.g., "that PDF from last week" or "spreadsheets from yesterday") instead of relying solely on exact substring matching of filenames.

- **Non-Destructive**: Traditional substring matching for applications and files MUST remain intact. Typing a plain app name (e.g., "Firefox") must work exactly as it does today without any performance regression.
- **Scope (v1)**: We will not use a heavy ML/LLM model for this. Instead, we will rely on structured regex parsing and existing system indexers.

## 2. Technical Approach
The implementation will reside entirely within the existing `packaging/parchaos-launcher/files/extension.js` and related files. 

Two primary building blocks available on stock Fedora will be leveraged:
1. **Phrase Parsing**: 
   - A lightweight regex and GLib date-phrase parser will intercept relative-time terms ("yesterday", "last week", "this month", "last 7 days").
   - It will convert these natural-language terms into absolute UNIX timestamp date ranges.
2. **GNOME Tracker3 integration**: 
   - `org.freedesktop.Tracker3` (the stock D-Bus service and SPARQL query interface) is already running on Fedora Workstation systems. 
   - Instead of building a custom file indexer, the launcher will convert the parsed date ranges and file-type keywords ("pdf", "image", "document") into a Tracker SPARQL query.
   - Tracker3 will rapidly return the exact file metadata (filename, path, modified-date) matching the query criteria.

## 3. UI/UX
- The user experience is entirely invisible. The user types naturally into the existing launcher search bar.
- If the phrase matches a natural-language pattern (e.g., `<filetype> from <timeframe>`), the parsed results are seamlessly appended to the standard search results list.
