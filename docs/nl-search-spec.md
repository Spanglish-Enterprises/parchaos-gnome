# Natural-Language Search Specification

This document defines the approach for natural-language search in Parcher, ParchaOS's file manager (Ticket #120). The owner asked (2026-09-29) for it to live in the file manager's search, not in the app launcher; the first draft of this spec named the launcher.

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

## 4. As built (Parcher 48.7-19)
- The phrase reader is `parcher-natural-search.c` (patch `0005-natural-language-search.patch`), independent of the rest of Files and tested by `packaging/parcher/tests/natural-search-test.c`.
- Files already has a date-range filter and file-type groups on its search query. The patch reads the typed text, and when it names a time range ("today", "yesterday", "this/last week/month/year", "last 7 days", "past 2 weeks", "3 days ago") it sets those filters, shows a tag for each ("Last week", "PDF / PostScript"), and searches the remaining words in file names. Closing a tag removes the phrase from the entry.
- File types understood: pdf, image/photo/picture/screenshot, document, spreadsheet, presentation/slides, video/movie, audio/music. Text without a time range is searched exactly as before.
- The index is LocalSearch, queried by Files' own search engine; no separate SPARQL code.
- English only. Not yet supported: weekdays ("on Monday"), calendar dates, "created" versus "modified" wording.
