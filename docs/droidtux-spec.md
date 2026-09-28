# DroidTux Specification

This document defines the plain-English behavior and architecture for **DroidTux**, ParchaOS's Android app support layer. 

**Legal Note**: This spec is written entirely in a clean-room fashion. We do not use, read, or reference Inled's Pulsar OS implementation of DroidTux. This is an original integration wrapping the independent GPL-3.0 Waydroid project.

## 1. Core Behavior
DroidTux serves as a seamless bridge between ParchaOS and Waydroid, allowing users to install, manage, and run Android applications as if they were native Linux apps.
- **Install/Remove**: Users can install `.apk` files or launch an Android app store (e.g., F-Droid or Aurora Store).
- **Launch**: Android applications launch in their own windows on the Wayland compositor.
- **List**: Users can view all installed Android applications.

## 2. System Architecture
- **Wrapper**: DroidTux will be a thin GTK4 application (`parchaos-droidtux`) acting as a settings/launcher frontend for the `waydroid` CLI.
- **Commands used**: `waydroid session start`, `waydroid app install`, `waydroid app launch`, `waydroid app list`, and `waydroid app remove`.
- **Session Management**: A `systemd` user service will manage the Waydroid session lifecycle.
  - *Crucial Optimization*: The session will **not** start automatically at login. It will start on the *first* Android app launch to conserve system resources (RAM/CPU).

## 3. Desktop Integration
- **Launcher Integration**: Installed Android apps must surface inside `parchaos-launcher` identically to standard `.desktop` entries. Waydroid's built-in `.desktop` generation hooks will be utilized and synchronized with the ParchaOS launcher.
- **Icons**: Standard Android app icons will be extracted and displayed in the launcher and Parcha Dock.
- **Dependencies**: Waydroid relies on `binder` and `ashmem` kernel modules. The package `kernel-modules-extra` from Fedora will be leveraged, or an `akmod` package if necessary (to be verified on bare metal).
