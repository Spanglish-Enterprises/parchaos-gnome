# Photo search (ticket #123)

Find pictures by what is in them: type "sunset over water" and get the pictures
that show one. Everything runs on the computer.

## How it works
- A small image model (CLIP ViT-B/32 by OpenAI, MIT licence, in ONNX form,
  quantised: 89 MB image half, 64 MB text half) turns each picture, and each
  search phrase, into 512 numbers. Pictures whose numbers are close to the
  phrase's are the matches. It runs with ONNX Runtime (Fedora's
  `python3-onnxruntime`) on the CPU: about 25 ms per picture.
- `parchaos-image-search index` walks the folders in
  `~/.config/parchaos-image-search/folders` (default `~/Pictures`), embeds new or
  changed pictures and drops deleted ones. A user timer does this hourly at idle
  priority, but only when the model is present.
- `parchaos-image-search search WORDS` and the GNOME search provider
  (`org.parchaos.ImageSearch.SearchProvider`, shown in the Overview search) rank
  the index against the phrase (minimum score 0.18, at most 8 results in the
  Overview).

## On by choice
Nothing runs until the user turns on Settings > Desktop > Photo search. That
runs `parchaos-image-search enable`: installs the engine
(`python3-onnxruntime`, `python3-numpy`, `python3-pillow`) through one polkit
prompt, downloads the model (size and SHA-256 pinned in the tool, discarded if
wrong), starts the timer and a first index. Off deletes the model and the index.
The engine is not on the ISO: ONNX Runtime pulls in about 40 packages.

## Not done
Parcher's own search does not use it yet (a patch to search by content there is
the natural next step); no text-in-images (OCR); English phrases work best; no
face or people grouping.
