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
- **Dependencies** (checked 2026-09-30 against Fedora 44): Waydroid is in Fedora's own repositories (1.6.3; no separate COPR needed) and pulls in `lxc`, `dnsmasq`, `nftables` and `waydroid-selinux`. Fedora's kernel already has the Android binder driver built in (`CONFIG_ANDROID_BINDER_IPC=y`, `CONFIG_ANDROID_BINDERFS=y`), and current Waydroid no longer needs the old ashmem module, so no `kernel-modules-extra` change, DKMS or akmod is needed.

## 4. Status and what is still open (2026-09-30)
Only this specification exists; nothing is packaged yet, so the ticket was closed too early and has been reopened.

What a first version needs:
1. **Set up (root, once):** `waydroid init` downloads the Android image (LineageOS-based, about 800 MB, from Waydroid's own servers; ParchaOS does not redistribute it) and needs administrator rights, so the app asks through polkit. It also needs the `waydroid-container` system service enabled, and a firewalld rule so the `waydroid0` bridge is trusted (otherwise Android has no network).
2. **Session:** `waydroid session start` per user, on demand (first app launch), stopped when the last Android app closes.
3. **Apps:** `waydroid app list/install/launch/remove`; Waydroid writes desktop entries into the user's applications folder, which the launcher already lists.
4. **App:** a small GTK4 "Android Apps" window: Set up, Install an APK, list with Open and Remove, Stop Android.

Risks to test on real hardware before shipping: a GPU with working GBM/EGL (not a virtual machine's software renderer), Wayland session (ParchaOS is), Secure Boot is unaffected (no kernel module). Google apps are not included by Waydroid; the user chooses an app store (F-Droid, Aurora) themselves.
