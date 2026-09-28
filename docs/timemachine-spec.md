# ParchaOS Time Machine Specification

This document outlines the architecture, behavior, and UI principles for `parchaos-timemachine`. 

**Legal Note**: This specification is drafted in a clean-room fashion. We do NOT look at, reference, or use Inled's Pulsar OS Time Machine clone. This tool will be an original GTK4 integration over the independent BSD-2-Clause `restic` project.

## 1. Core Behavior
The app provides automated, versioned backups with a browsable historical timeline.
- **Hourly Snapshots**: Uses `systemd` user timers (`parchaos-timemachine@.service` and `.timer`) to trigger an incremental backup every hour without user intervention.
- **Backend (restic)**: Relies entirely on `restic`. `restic mount` will be used to expose the backup repository as a FUSE filesystem, meaning every snapshot appears as a read-only directory tree containing the state of the filesystem at that exact time.
- **Retention**: Follows a standard retention policy (e.g., keep hourly for 24h, daily for a week, weekly for a month). Older snapshots are automatically pruned.

## 2. Storage Targets
- **Local Disks**: The user can designate an external USB/SATA drive as the primary repository.
- **Cloud Destinations**: Reuses the work from `parchaos-cloud`. If a user has `~/Cloud/<provider>` mounted via rclone, `restic` can seamlessly target it as an off-site repository.

## 3. User Interface (GTK4/Libadwaita)
- **Settings & Status**: A simple GTK4 control panel showing the backup destination, next scheduled backup time, and total disk space used.
- **Restore Browser ("Enter Time Machine")**: 
  - Instead of a traditional list of archives, the user enters a full-screen or maximized immersive mode.
  - A timeline scrubber (e.g., a right-side scrollbar or bottom slider) allows the user to step back through time.
  - As the scrubber moves, the UI simply browses the `restic mount` FUSE points (`/run/user/.../restic-mount/snapshots/<timestamp>/...`). 
  - The user can select a file/folder and hit a prominent "Restore" button to copy it back to their live `~` directory.
