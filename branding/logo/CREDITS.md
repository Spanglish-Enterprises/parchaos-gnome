# ParchaOS logo — attribution

`parcha-logo-black.png` / `parcha-logo-white.png` are cropped (attribution
text removed from the image itself, per license, tracked here instead)
versions of:

**"Passion Fruit"** by **LUTFI GANI AL ACHMAD**, from
[The Noun Project](https://thenounproject.com/browse/icons/term/passion-fruit/),
licensed [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/).

Per CC BY 3.0, any distribution of this logo (the ISO, marketing pages,
app icons derived from it, etc.) must carry this attribution somewhere
reachable — this file, an About/Credits screen, or a NOTICE file at the
top of whatever ships it. Do not remove this file or the attribution
without replacing the logo with different, unencumbered artwork.

Original, unmodified source image (with the Noun Project watermark
intact) is not stored in this repo — only the cropped, production-ready
versions are, since the watermark is exactly what CC BY 3.0 requires we
credit *outside* the image rather than baked into it.

- `parcha-logo-black.png` — black on transparent, for light backgrounds.
- `parcha-logo-white.png` — white on transparent, for dark backgrounds
  (boot splash, dark wallpaper, SDDM/lock-screen contexts).
- `parcha-silhouette-black.png` / `parcha-silhouette-white.png` — a real
  derivative of the same logo (2026-09-23): the exact outer contour
  (fruit body + leaf/stem, same proportions and curves as the original)
  with the internal ring/seed-dot detail filled in solid, produced by
  flood-filling the original's own enclosed holes — not a redrawn
  approximation. Needed because the detailed version's fine internal
  linework visually collapses into noise at true menu-bar icon size
  (~16-20px); the silhouette stays crisp and recognizable at that size.
  Used for `packaging/parchaos-global-menu`'s panel icon; the detailed
  versions remain the default for every larger context (app icons,
  splash screens, etc.). Same CC BY 3.0 attribution applies to both.

Chosen 2026-09-22 to replace pearOS's own pear-shaped logo, matching
ParchaOS's actual name etymology ("Parcha" = passion fruit in Puerto
Rican Spanish) rather than continuing to reuse the pear motif that only
made sense for the pearOS-branded KDE variant.
