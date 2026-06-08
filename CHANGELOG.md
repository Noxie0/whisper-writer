# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [2.0.1] - 2026-06-08
### Fixed
- `requirements.txt` was UTF-16 encoded — pip could not read it on a fresh install. Converted to UTF-8.
- Microphone device resolution: selecting a named device caused "Multiple input devices found" error because MME/DirectSound/WASAPI all share the same display name. Now resolves to the MME device which supports 16 000 Hz resampling natively.
- NVIDIA Broadcast (virtual mic) silently set as default on some machines, producing zero-amplitude audio. Selecting a real device in Settings → Recording → Sound Device now works correctly.

### Security / Portability
- `run.py`, `utils.py`, `main.py`: replaced all relative paths (`src/config.yaml`, `assets/`) with `__file__`-anchored absolute paths. App now starts correctly from any working directory, including Windows startup.
- `run.py`: subprocess inherits explicit `cwd=_ROOT` so it always runs from the project root.
- `input_simulation.py`: replaced `os.kill(SIGINT)` (unavailable on Windows) with `process.terminate()`.
- `input_simulation.py`: strip `\n`/`\r` from text before writing to dotool stdin (command injection prevention).

## [2.0.0] - 2026-06-08
### Added
- Full **Catppuccin Mocha** dark theme across every widget, scroll bar, dialog, and tab.
- **Logs tab** — real-time view of all app output, captured even when "Print to Terminal" is off. 500-line rolling buffer, clear button, thread-safe via `pyqtSignal`.
- **About tab** — project info, GitHub link, credits.
- **System tray icon** — minimize to tray; right-click menu with Show, Settings, Exit.
- **Microphone dropdown** — WASAPI-only device list matching Windows Sound Control Panel. No MME/DirectSound duplicates.
- **Rich help dialogs** — every `?` button shows a one-line TLDR on hover and a detailed HTML popup on click.
- `ww-logo-dark.png` / `ww-logo-dark.ico` — dark-background logo variant for tray icon.
- `ww-logo-light.png` / `ww-logo-light.ico` — light-background logo variant.
- All `.ico` files regenerated with rounded corners (20% radius) at 16/32/48/64/128/256 px.
- `assets/ww-settings-demo.gif` — settings UI demo added to README.

### Changed
- All setting labels and descriptions rewritten in plain English (e.g. `hold_to_record` → "Hold to Record").
- Vocabulary tab: larger font, clearer instructions, improved layout.
- `run.py` now automatically adds NVIDIA CUDA DLL directories to `PATH` so `ctranslate2` finds cuDNN/cuBLAS without manual setup.
- README fully rewritten: installation guide, settings reference tables, logs tab docs, roadmap, credits.
- Tray icon uses dark-background logo.

### Fixed
- Default config path now derived from `__file__` instead of relative cwd (portability fix).

## [1.0.1] - 2024-01-28
### Added
- New message to identify whether Whisper was being called using the API or running locally.
- Additional hold-to-talk and press-to-toggle recording methods.
- New configuration options: recording method, sound device, sample rate, hide status window.

### Changed
- Migrated from `whisper` to `faster-whisper`.
- Migrated from `pyautogui` to `pynput`.
- Migrated from `webrtcvad` to `webrtcvad-wheels`.
- Changed default activation key combo from `ctrl+alt+space` to `ctrl+shift+space`.
- Changed to using a local model rather than the API by default.

### Fixed
- Local model now only loaded once at startup.
- Auto-selects compute type to avoid warnings.
- Graceful degradation to CPU if CUDA unavailable.

## [1.0.0] - 2023-05-29
### Added
- Initial release of WhisperWriter.

[2.0.1]: https://github.com/Noxie0/whisper-writer/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/Noxie0/whisper-writer/compare/v1.0.1...v2.0.0
[1.0.1]: https://github.com/savbell/whisper-writer/releases/tag/v1.0.1
[1.0.0]: https://github.com/savbell/whisper-writer/releases/tag/v1.0.0
