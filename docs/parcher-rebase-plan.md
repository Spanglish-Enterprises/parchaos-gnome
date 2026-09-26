# Parcher: rebasing onto current Nautilus

Status: plan (2026-09-26, ticket #47). Parcher (`packaging/parcher/`) is
Pulsar OS's Finder, a fork of **Nautilus 48.7**, running on a GNOME 50
desktop. Fedora 44 ships Nautilus **50.3**.

## What the fork changes

Measured against the GNOME 48.7 release tarball (`diff -ruN`, excluding
translations and help): **72 hunks in 20 files**, plus packaging files
(`DEBIAN/`, helper scripts) that ParchaOS doesn't use. By feature:

| Feature | Files |
|---|---|
| Color tags: live folder tinting, per-color filters in the sidebar | `nautilus-tag-manager.{c,h}`, `nautilus-file.c`, `nautilus-grid-cell.c` + `.ui`, `nautilus-files-view.{c,h}` + context-menu `.ui`, `nautilus-starred-directory.c`, `nautilus-internal-place-file.c` |
| Sidebar sections (colors, cloud drives) | `gtk/nautilusgtkplacessidebar.c`, `...private.h` |
| Toolbar and window layout (rounded corners, integrated controls) | `nautilus-toolbar.c` + `.ui`, `nautilus-window.c` + `.ui`, history/view-controls `.ui`, `style.css` |
| App identity | `nautilus-application.c` |

ParchaOS adds its own changes in the spec's `%prep` (the "Cloud Drives"
sidebar title, the "Parcher" app name).

## Why it isn't a simple rebase

A dry run of the fork's diff against 50.3: most C hunks still apply
(with offsets), but:

- **The UI moved to Blueprint.** All six `.ui` files the fork edits are
  now `.blp` in 50 (`nautilus-toolbar.blp`, `nautilus-window.blp`, ...).
  Those edits have to be re-expressed in Blueprint.
- **The places sidebar was replaced.** `gtk/nautilusgtkplacessidebar.c`
  (GTK's copied sidebar) is gone; Nautilus 50 has its own sidebar
  (`nautilus-sidebar-row.blp` and friends). The color-filter and cloud
  sections must be rebuilt on the new sidebar.
- `nautilus-grid-cell.c` (5 of 9 hunks fail), `nautilus-file.c` and
  `style.css` conflict.

Estimate: the color-tag core is a moderate port; the sidebar sections and
layout are a reimplementation.

## Plan

1. **Packaging first (no behavior change).** Switch `packaging/parcher/`
   from Pulsar's tarball to the GNOME release tarball plus a patch
   series, one patch per feature above, split from the 48.7 diff. Build
   and compare against today's Parcher. After this, Pulsar's repository
   is no longer needed to build, and each feature can be ported on its
   own.
2. **Port to 50.x, feature by feature**, in this order: color tags
   (core), then toolbar/window layout (Blueprint), then sidebar sections
   (new sidebar API). App identity and the ParchaOS `%prep` changes carry
   over as they are.
3. **Test** in the headless shell harness (file views, tags, sidebar)
   and on the real desktop, then ship as `parcher` 50.x with
   `Obsoletes: nautilus < 51` bumped to the next major.

Until then:

- `parcher` has `Obsoletes: nautilus < 51`, so Fedora's Nautilus 50 can't
  be installed alongside it or pulled in to replace it.
- CI (`.github/workflows/lint.yml`, fork-versions) warns while Fedora's
  Nautilus is ahead of Parcher's base.
- **Security fixes:** watch Nautilus 48.x/50.x release notes and Fedora
  nautilus updates (`dnf updateinfo list nautilus`). A security fix in
  code the fork doesn't touch applies as a patch in the spec; one in
  code the fork touches needs a manual backport.
