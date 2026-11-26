# The Forgotten Chapter (TFC)

An OpenRA mod: a Tiberian Dawn (`cnc`) derivative with a third faction, the Forgotten.

This branch (`port/20250330` and its phase branches) is the port of TFC from OpenRA
release-20141029 to **release-20250330**. The playable 0.32 version for the old engine lives on
the `legacy/20141029` branch (tag `v0.32-final-20141029`).

Status after Phase 1: the loadable mod `mods/tfc` is **pure stock 20250330 `cnc`** with TFC
title and metadata. No TFC rules, art or balance have been ported yet.

## Repository layout

| Path | What it is |
|---|---|
| `mods/tfc/` | The loadable mod. A copy of stock 20250330 `cnc` (engine `mods/cnc`), plus TFC's own override files (below). |
| `legacy-0.32/` | The complete 0.32 mod folder (2014 engine format), moved here with `git mv` so history follows each file. **Porting source only.** It is outside `mods/`, so the engine can never load it, and no tool reads it. |
| `engine/` | The OpenRA engine at the pinned release. Git-ignored; fetched and built by `make.cmd all`. |
| `mod.config`, `make.cmd`, `make.ps1`, `Makefile`, `fetch-engine.sh`, `launch-*.cmd/sh`, `utility.cmd/sh`, `packaging/`, `.github/` | The OpenRA Mod SDK (taken from `OpenRA/OpenRAModSDK` `master` at `df10393`, which pins `release-20250330`). |

Why two folders: the 2014 files must stay in the tree (the port reads them and `git log --follow`
works), but they are in a different manifest format and must not be loadable. `mods/tfc` therefore
starts as stock, and porting adds TFC's delta to it.

### The stock copy and the override files

Per the plan (Q2 option a), stock files are copied into `mods/tfc` and TFC changes live in
**separate override files**, so a stock file is not edited unless there is no alternative.
`mods/tfc/mod.yaml` already lists every file the later phases need, as placeholder files that
contain one comment line. Later workers fill the placeholders and **never edit `mod.yaml`**.

Load order matters: every `tfc-*` file is listed after the stock files it overrides.

| Area | Placeholder files (all under `mods/tfc/`) |
|---|---|
| GDI | `factions/gdi/rules/army.yaml`, `factions/gdi/rules/assault_apc.yaml`, `factions/gdi/sequences/army.yaml` |
| Nod | `factions/nod/rules/army.yaml`, `factions/nod/sequences/army.yaml` |
| Forgotten (tfa) | `factions/tfa/rules/army.yaml`, `factions/tfa/sequences/army.yaml` |
| Shared actor changes | `rules/tfc-overrides.yaml` |
| Stock units pinned to 2014 values (Q3) | `rules/tfc-stock-2014-pins.yaml` (loaded before the overrides) |
| World, factions, start units | `rules/tfc-world.yaml` |
| AI | `rules/tfc-ai.yaml` |
| Sequences of changed stock actors | `sequences/tfc-overrides.yaml` |
| Weapons | `weapons/tfc-retuned.yaml` (retuned stock weapons), `weapons/tfc-gdi.yaml`, `weapons/tfc-nod.yaml`, `weapons/tfc-tfa.yaml` (new weapons) |
| Voices, notifications, music | `audio/tfc-voices.yaml`, `audio/tfc-notifications.yaml`, `audio/tfc-music.yaml` |
| Chrome (UI) | `chrome/tfc-chrome.yaml` (image collections), `chrome/tfc-layout.yaml` (widget layout), `chrome/tfc-metrics.yaml` |
| Fluent strings | `fluent/tfc-mod.ftl` (title; live), `tfc-rules-shared.ftl`, `tfc-rules-gdi.ftl`, `tfc-rules-nod.ftl`, `tfc-rules-tfa.ftl`, `tfc-factions.ftl`, `tfc-chrome.ftl`, `tfc-campaign.ftl`, `tfc-lua.ftl` |

Deviations from stock `cnc` in the copy (everything else is byte-for-byte stock):

- `mod.yaml`: stock manifest with `cnc|` replaced by `tfc|`, a `$tfc: tfc` package, TFC metadata,
  the user-map folder `maps/tfc/{DEV_VERSION}`, and the placeholder entries above.
  `SupportsMapsFrom: cnc` and `ContentInstallerMod: cnc-content` are unchanged.
- `fluent/cnc.ftl`: the two `mod-title` / `mod-windowtitle` lines moved to `fluent/tfc-mod.ftl`.
- `maps/*/map.yaml` (37 campaign maps): `cnc|rules/...` and `cnc|fluent/...` references changed to
  `tfc|...`, since those packages now live in `tfc`. `RequiresMod: cnc` is unchanged.

### Content

The mod uses the engine's content installer (`ContentInstallerMod: cnc-content`, which lives in
the engine's `mods/cnc-content`, not in this repo) and reads the C&C game files from the Support
folder `Content/cnc` (the same place stock `cnc` uses, so content already installed for stock
OpenRA is reused). Otherwise use "Manage Content" on the main menu.

## Build, check, run (Windows)

Needs the **.NET 6 SDK** (the engine's `net6.0` target). A newer SDK installed alongside also
works for building (verified: SDK 10.0.402 building the 6.0 targets, 0 errors, only NETSDK1138 and
NU1901 warnings), but the game itself runs on the .NET 6 runtime.

The Mod SDK offers exactly these `make.cmd` (-> `make.ps1`) targets. Verified by reading the
scripts and by running each one marked "ran":

| Command | What it does |
|---|---|
| `make.cmd all` | Fetches `engine/` at `ENGINE_VERSION` if missing and builds it (ran). Then prints "No custom solution file found. Aborting." and stops: harmless, TFC has no C# solution. |
| `make.cmd test` | `utility.cmd tfc --check-yaml`: lint of rules, weapons, sequences, Fluent references and every map (ran; about 15 s). Exits 1 on errors. |
| `make.cmd check` | Static C# checks (StyleCop, explicit interfaces). Only builds the engine here (no `.sln`). |
| `make.cmd check-scripts` | `luac -p` over `mods/*/maps/*/*.lua`. Needs `luac.exe` (Lua 5.1) on PATH; not installed here, so **not run**. |
| `make.cmd version [tag]` | Rewrites `Version:` in `mods/tfc/mod.yaml` from the git tag. For release time. |
| `make.cmd clean` | Cleans the engine build. |

Direct tool commands:

- `utility.cmd tfc --check-yaml` is the same lint as `make.cmd test`.
- Other engine `OpenRA.Utility` commands (`--check-missing-sprites`, `--resolved-rules`,
  `--extract-yaml-strings`, ...): run `utility.cmd` with no arguments to list them.
  `--check-missing-sprites` needs the C&C game files in the utility's default Support folder
  (`%USERPROFILE%\Documents\OpenRA\Content\cnc` on Windows); without them it reports about 2200
  "not found" lines, which is a missing-content result, not a mod fault.
- `launch-game.cmd` starts the game with `Game.Mod=tfc`. To keep a run away from your normal
  OpenRA settings, use `launch-game.cmd Engine.SupportDir=C:\some\folder` (put the C&C `.mix`
  files in that folder's `Content\cnc`). Note the engine still keeps a mod-metadata cache in
  `%APPDATA%\OpenRA\ModMetadata`, which it may tidy.

`make.cmd test` honours the environment variable `TREAT_WARNINGS_AS_ERRORS=true`, which turns lint
warnings (for example unused Fluent keys) into errors. CI sets it.

### CI

`.github/workflows/ci.yml` (from the SDK, unchanged) runs on every push and pull request:

- Linux (.NET 6): `make check`, `make check-packaging-scripts`, `make check-scripts`,
  `make TREAT_WARNINGS_AS_ERRORS=true test`.
- Linux (mono): `make RUNTIME=mono check` and `test`.
- Windows (.NET 6): `.\make.ps1 check`, `check-scripts`, `test`, warnings as errors.

`.github/workflows/packaging.yml` builds Windows, macOS and Linux packages when a tag is pushed.

### Differences from the stock Mod SDK

- `make.ps1` and `fetch-engine.sh` no longer delete the engine's `CheckFluentReferences` lint (the
  SDK deletes it only because its Example mod cannot pass it). TFC passes it, so Fluent errors are
  caught.
- `mod.config`: `MOD_ID="tfc"`, `ENGINE_VERSION="release-20250330"`, `PACKAGING_COPY_CNC_DLL="True"`
  (the manifest loads `OpenRA.Mods.Cnc.dll`), and `PACKAGING_COPY_ENGINE_FILES` copies the engine's
  `cnc-content` and `common-content` mods into packages (packaging itself is untested). TFC identity
  strings are set.
- The SDK's example mod, `OpenRA.Mods.Example` and `ExampleMod.sln` were removed (TFC has no C#).
- `.gitattributes` keeps `* text=auto` (the SDK's `* text=lf` would also rewrite binary files).
