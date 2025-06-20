# Xcode Fuckoff

Still a work in progress for the UI. A few features are incomplete.  
Built because I got sick of Xcode simulator junk showing up in Finder.

Still working on getting killing the CoreSimulatorService to work properly, but I got some schoolwork to do. Feel free to contribute if you want to help out.!!!
---

## Purpose

macOS users constantly encounter unwanted disk images and virtual mounts from Xcode.  
These include iOS simulators, device snapshots, runtime containers, and others that:

- Auto-mount silently without user interaction
- Return after being manually ejected
- Clutter Finder and Disk Utility with dozens of devices
- Consume disk I/O and increase SSD wear from metadata logs
- Reappear after reboots or even after quitting Xcode

Apple provides no reliable, user-facing method to suppress these volumes.  
After wasting hours trying to delete, eject, or disable them through `diskutil`, `launchctl`, and `simctl`, I built this app to do it all in one click.

---

## What It Does

- Scans for and ejects all Xcode/iOS simulator–related volumes
- Uses `diskutil`, `hdiutil`, `umount`, and fallback shell tools to force-unmount stubborn volumes
- Shuts down all running simulators via `xcrun simctl shutdown all`
- Deletes all simulator containers via `xcrun simctl delete all`
- Removes leftover simulator folders in `~/Library/Developer/CoreSimulator/Devices`
- Terminates CoreSimulator services and prevents auto-restart via `launchctl disable`
- Allows timed rescanning and repeat purging
- Supports logging and user-configurable filters

---

## Features

- PyQt6 desktop GUI
- Persistent settings with QSettings
- Progress bar and live logs
- Tray icon and window toggle
- Custom match filters for disk names
- Toggleable features:
  - Force eject
  - Nuclear deletion
  - Auto-rescan
  - Cache purge
- Dark theme UI

---

## Why It Was Built

Xcode wouldn't stop spawning background simulators and mounting useless volumes.  
Even after shutting it down, devices kept coming back. They don't just sit there — they write logs, consume storage, and cause confusion when opening Disk Utility.

Apple’s CoreSimulatorService is aggressive and persistent.  
This app removes all of it — cleanly and forcefully.

---

## How It Works (Still working on this, made this in a hurry I got finals, so if someone wants to help out i'd love that)

1. Uses `xcrun simctl` to shut down and delete all simulator devices.
2. Removes `/Users/yourname/Library/Developer/CoreSimulator/Devices/*` 
3. Unmounts any virtual disk images related to simulators.
4. Terminates CoreSimulator launch agents.
5. Disables CoreSimulator auto-respawn using:
   ```bash
   sudo launchctl disable system/com.apple.CoreSimulator.CoreSimulatorService