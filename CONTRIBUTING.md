# Contributing

## Balance check: the frozen 0.32 stats

`tools/tfc_stats.py` (Python 3, standard library only) records every unit's and
weapon's numbers so the OpenRA 20250330 port can be compared against 0.32.

Frozen reference (generated from the mod at commit `ed02790`, 273 actors,
25 templates, 100 weapons; do not edit by hand). List columns (`weapons`, `traits`,
`extras`, `terrain_speeds`) are sorted so that order never shows up as a change:

- `tools/baseline-0.32-actors.csv` - one row per actor or `^template`
- `tools/baseline-0.32-weapons.csv` - one row per weapon

Blank cells mean "not set in the YAML", so the engine default applies (for
`vs_*` armour columns the default is 100). `source` lists the files that define the entry.

### Commands

```
# Regenerate a baseline from a 2014-format mod folder (the one holding mod.yaml).
# It reads the Rules and Weapons lists in mod.yaml and resolves Inherits,
# -Trait removals and later-file overrides.
python tools/tfc_stats.py baseline <MODDIR> [--out-dir DIR] [--prefix NAME]

# Compare a baseline against another CSV pair in the same schema.
# Prints added / removed / changed rows. Exit code 1 only if an actor or weapon
# from the baseline is missing from the second set; value changes are listed, not failures.
python tools/tfc_stats.py compare tools/baseline-0.32-actors.csv tools/baseline-0.32-weapons.csv NEW-actors.csv NEW-weapons.csv
# (options and the port-side commands: see "The ported mod's stats" below)

# Self-test (hand-checked values) against the 2014 mod at MODDIR (default: the repo root, or legacy-0.32
# on the port branch, where the 2014 mod lives).
python tools/tfc_stats.py selftest [MODDIR]
```

To regenerate the frozen files, check out `ed02790` (the 0.32 layout has `mod.yaml`
at the repo root) and run `baseline . --out-dir tools`. If the mod files move
within the repo, pass the new folder as `MODDIR`; `mod.yaml` paths of the form
`./mods/<name>/...` are read relative to it.

### The ported mod's stats: `port`, `check`, and the extended `compare`

The port (OpenRA release-20250330, Mod SDK layout, engine built into `./engine` by `make.cmd all`)
is read through the engine's own resolver, `OpenRA.Utility.exe tfc --resolved-rules NAME` and
`--resolved-weapons NAME` (inheritance, removals and file order already applied; names are case-sensitive).
Every value is converted back to 0.32 units, so a plain `compare` against the frozen baseline shows a pinned
or faithfully ported actor as unchanged.

```
# Every actor, template and weapon named in mods/tfc/mod.yaml (about 380 engine calls, about a minute with
# --jobs 4). Results are cached by file hash under %TEMP%\tfc-stats-cache, so a re-run with no file changes
# takes seconds. Alias: extract2025.
python tools/tfc_stats.py port --out-dir %TEMP%\tfc-stats [--repo .] [--engine .\engine] [--jobs 4] [--no-cache]
python tools/tfc_stats.py port --out-dir DIR --only tools/lanes/4a.txt      # only the names in a file
python tools/tfc_stats.py port --out-dir DIR --actors E1,MTNK --weapons Sniper

# Compare. --ignore takes columns, or extras.Trait.Field / terrain_speeds.Type; --only takes a names file
# (one per line, # comments) and limits BOTH sides to those names; --summary prints only the headline.
python tools/tfc_stats.py compare tools/baseline-0.32-actors.csv tools/baseline-0.32-weapons.csv \
    %TEMP%\tfc-stats\port-actors.csv %TEMP%\tfc-stats\port-weapons.csv \
    --ignore traits,inherits,source,faction_owner [--only tools/lanes/4a.txt] [--summary]

# One command for a lane: port + compare for just the names it owns.
python tools/tfc_stats.py check E1 MTNK Sniper --jobs 4
python tools/tfc_stats.py check --list tools/lanes/4g.txt [--actors A,B] [--weapons W,V] [--ignore COLS] [--summary]
```

`check` exit codes: **0** every listed name exists in the port (value differences are printed, they are not
failures); **1** a listed baseline actor or weapon is missing from the port, or the engine could not resolve it;
**2** usage problem: a name that is not in the baseline (names are case-sensitive), no names, or the engine is
not built. Its default `--ignore` is `traits,inherits,source,faction_owner`. `compare` itself exits 1 only for
missing names.

What `compare` prints, beyond the old output: a headline (baseline / present / missing / present and differing /
present and identical, for actors, templates and weapons separately) and a count of differing values per column.
`extras` and `terrain_speeds` are compared key by key (`extras.Cargo.MaxWeight`). A key that only the port has
(for example `Selectable.Priority`, which most 0.32 actors never set) is listed under "keys only the port has"
and is not counted as a change. Cells holding `<unmapped>`, and unmapped extras keys, are counted as "not
comparable", not as changes. Actor, weapon and husk names compare ignoring case (the 0.32 engine looked them up
case-insensitively); a blank `vs_*` cell equals 100 and a blank `burst_delay` equals 5 on both sides.

#### Conversions (modern value to the 0.32 baseline column)

| 0.32 column | Modern source | Conversion |
|---|---|---|
| `hp` | `Health: HP` | / 100 |
| `damage` (first damaging warhead) | `Warhead@..: Damage` | / 100 (heal damage is negative) |
| `rot`, `Turreted.ROT`, `Plane.ROT` | `Mobile` / `Aircraft` / `Turreted: TurnSpeed` | / 4, except **1023 becomes 255** (the design note's `255 -> 1023` rule maps the top of the scale, so 255 x 4 = 1020 is not what 0.32's 255 became; 1020 also gives 255). Any other value that is not a multiple of 4 is written as a decimal |
| `Turreted.InitialFacing` | `Turreted: InitialFacing` | / 4 (same 1023 -> 255 rule) |
| `AttackHeli.FacingTolerance` | `AttackAircraft: FacingTolerance` | / 4 (same rule; `AttackPlane.` on a plane) |
| `SelfHealing[@X].Step` | `ChangesHealth[@X]: Step` | / 100 (`PercentageStep` is not shown) |
| `SelfHealing[@X].Ticks` | `ChangesHealth[@X]: Delay` | unchanged |
| `burst_delay` | `BurstDelays` | first entry only (0.32 had one value) |
| `death_type` | first `DamageTypes` token that is a death name | BulletDeath 1, RippedApartDeath 2, SmallExplosionDeath 3, ExplosionDeath 4, FireDeath 5, TiberiumDeath 6, DefaultDeath 1 |
| `range`, `min_range`, `spread`, `projectile_speed`, `projectile_inaccuracy` | same fields | WDist written as the baseline writes it: below 1024 a plain integer, else `NcM`; `MinRange 0` and `Burst 1` (the defaults) are blank |
| `DetectCloaked.Range` | `DetectCloaked: Range` | whole cells become a bare integer (`2c0` is `2`) |
| `TakeCover.ProneSpeed` | `TakeCover: SpeedModifier` | / 100 |
| `ProductionQueue[@X].LowPowerSlowdown` | `LowPowerModifier` | / 100; absent is the default 100, so `1` |
| `ProductionQueue[@X].BuildSpeed` | queue `BuildDurationModifier` | 100 (the default) is `.4`; any other value is written as the text `BuildDurationModifier=N` so it shows as a difference (the design note documents only the 100 / .4 pair) |
| `build_duration`, `build_duration_modifier` | `Buildable: BuildDuration`, `BuildDurationModifier` | `build_duration` = (BuildDuration, or the cost when absent or -1) x modifier% (default 60) / 0.4: the 0.32 `CustomBuildTimeValue` that gives the same ticks. Blank when that equals the 0.32 default (cost x 1.5). `build_duration_modifier` is always blank (folded in). See "Build time" below |
| `locomotor` | `Mobile` / `Aircraft` | `Mobile`; an `Aircraft` with `CanHover: true` is `Helicopter`, otherwise `Plane` |
| `terrain_speeds`, `Mobile.Crushes` | `World` `Locomotor@*` whose `Name` is the actor's `Mobile: Locomotor` | same keys; the modern `Bridge` type (0.32 had none) is dropped. An unknown locomotor is written `<missing-locomotor:name>` |
| `LimitedAmmo.Ammo`, `Reloads.Count`, `Reloads.Period` | `AmmoPool: Ammo`, `ReloadAmmoPool: Count`, `Delay` | unchanged |
| `Harvester.Capacity` | `StoresResources: Capacity` (on an actor that has `Harvester`) | unchanged; other actors keep the key `StoresResources.Capacity` |
| `StoresResources.Capacity` (a building's storage: PROC 2000, SILO 2400, RFNRY 1500) | `StoresPlayerResources: Capacity` | unchanged |
| `other_weapons`, `Explodes.Weapon`, `Explodes.EmptyWeapon` | `FireWarheadsOnDeath` | unchanged (instances keep their `@suffix`) |
| `LeavesHusk.HuskActor` | `SpawnActorOnDeath: Actor` without `Probability` (those are the Vice mutation) | unchanged |
| `<Helicopter or Plane>.RepairBuildings`, `.RearmBuildings` | `Repairable: RepairActors`, `Rearmable: RearmActors` | unchanged |
| `tooltip`, `Tooltip.GenericName` | `Tooltip: Name`, `GenericName` (Fluent keys) | looked up in the `FluentMessages` files, later file wins; an unknown key is written `<fluent:key>` |
| `building_power_ignored` | none (0.32's `Building: Power` was ignored by the engine) | the cell is `<unmapped>` on the port side |
| `power`, `power_drain`, `cost`, `speed`, `armor`, `sight_range`, `queue`, `prerequisites`, `build_palette_order`, `weapons`, `vs_*`, `reload_delay`, `burst`, targets, projectile type and speed | same fields | unchanged |
| `inherits`, `source`, `traits` | the `Rules` files themselves, and the resolved trait names | information only (the resolver output has no `Inherits` lines) |

Extras keys copied unchanged where the modern trait has the same name and field: `AutoTarget.ScanRadius`,
`Buildable.BuildLimit`, `Cargo.MaxWeight`, `Cargo.Types`, `Cloak.InitialDelay`, `Cloak.CloakDelay`,
`Crushable.CrushClasses`, `Crushable.CrushSound`, `CustomSellValue.Value`, `Harvester.Resources`,
`Production.Produces`, `ProductionQueue.Type`, `RepairableBuilding.RepairPercent`, `Selectable.Priority`,
`Transforms.IntoActor`, `Turreted.Offset`. `extras` holds only keys the baseline holds; other modern fields are
not extracted.

#### Lossy and unmapped columns (marked, not guessed; `compare` counts them as "not comparable")

- Whole columns with the cell `<unmapped>`: actors `faction_owner` (0.32 `Buildable: Owner`; modern gates by queue
  and faction); weapons `charges`, `projectile_other` (High, Angle, ROT, RangeLimit... became differently named
  fields) and `warhead_other` (0.32 text about nested warheads).
- Extras keys the port does not emit (no modern counterpart, or the vocabulary changed): `Health.Radius` (modern
  HitShape), `TargetableUnit.TargetTypes` (vocabulary changed; lane 4e), `Capturable.Type`,
  `Capturable.CaptureThreshold`, `Captures.CaptureTypes` (the capture model changed) and `Cargo.PipCount` (a
  rendering trait).
- Lossy but compared: `burst_delay` (first of several), `ProductionQueue.BuildSpeed` (only the 100 / .4 pair),
  `SelfHealing.Step` (a modern percentage step is not shown), `death_type` (first death name only), `locomotor`
  (`Helicopter` versus `Plane` decided by `CanHover`) and `warhead_count` (modern files add effect warheads that
  the design note leaves modern, so use `--ignore warhead_count` for a pinning check).

The extractor changes neither the baseline CSVs nor anything under `mods/`.

#### Tests

`python tools/tfc_stats.py selftest` runs everything. The engine-backed tests (a few real engine calls, plus the
round-trip proof) skip with a message when `./engine` is not built. The round-trip proof copies `mods/tfc` into a
scratch folder (set `TFC_STATS_SCRATCH=<dir>` to keep it and its reports), lists a throwaway override file last in
its `Rules` and `Weapons`, writes eight actors' and eight weapons' baseline values into it with the conversions
above done by hand in the test, runs the extractor and requires `compare` to show them unchanged; it then breaks one
HP on purpose and requires exactly that difference to be reported.

### How the merge rules were proven

The 2014 engine has no rule dump, so the rules were proven against the engine's own code.
`OpenRA.Game.exe` (a 32-bit .NET assembly) was copied to a scratch folder and called read-only;
nothing under the engine folder was written. Sources are in `tools/probe/`:

- `il.ps1` decodes a method body (run with 32-bit PowerShell,
  `C:\Windows\SysWOW64\WindowsPowerShell/v1.0\powershell.exe -File il.ps1 OpenRA.RulesetCache LoadYamlRules`).
  It showed that `LoadYamlRules` is `files.Select(load).Aggregate(mapRules, MiniYaml.MergeLiberal)`, called in
  `Manifest.Rules` / `Manifest.Weapons` order (`mf.cs` prints that order), so `acc = MergeLiberal(acc, nextFile)`.
  `ActorInfo.MergeWithParent` is `MergeStrict(self, parent)` followed by removal of leftover top-level `-` nodes.
- `probe1.cs`, `probe2.cs` (compile with `C:\Windows\Microsoft.NET\Framework/v4.0.30319\csc.exe /platform:x86
  /r:OpenRA.Game.exe`) call `MergeLiberal`, `MergeStrict` and `MergeWithParent` on tiny files. Output is in
  `probe1-out.txt` and `probe2-out.txt` and is pinned by `EnginePrecedenceTests` in `test_tfc_stats.py`.
- `dump.cs` replays the real loader on the whole mod with the engine's methods and writes
  `engine-actors.txt` / `engine-weapons.txt`; `python tools/tfc_stats.py dump MODDIR OUT` writes the same format
  from the Python resolver and `python tools/probe/compare_dumps.py OUT` compares them. At `ed02790`:
  298 of 298 actor/template definitions and 100 of 100 weapons are identical, including child order.

Proven rules: the EARLIER file in `mod.yaml` wins every conflict (so `weapons.yaml` beats `weaponsV.yaml`,
`rules/infantry.yaml` beats the faction `army.yaml` files); fields only the later file has are added; nested
nodes merge field by field; an empty value is filled from the later file. `Inherits` is the exact key
`Inherits` (`Inherits@x` is ignored), the parent name is case-sensitive, the child wins, `-Key` deletes `Key`
at any level even if the child defined it itself, and removing a key that is not there is an engine error.
Actor and weapon names are lower-cased for lookup; `Versus` armour names are case-sensitive and an armour
type with no `Versus` entry takes 100 percent. A weapon only has the warheads that are top-level `Warhead*`
keys, so a `Warhead@2Eff` indented inside `Warhead@1Dam` is never read.

### Second probe round: what 0.32 effectively did (gap fixes)

Same method as above (read-only copy of `OpenRA.Game.exe` and the mod DLLs, 32-bit PowerShell and `csc.exe`).
`probe3.cs`/`probe4.cs`/`probe5.cs` load the **whole 0.32 mod through the engine** (`ModData` +
`RulesetCache.LoadDefaultRules`: 298 actors, 100 weapons, as the Python resolver counts) and print what the engine
parsed and what its own methods return. Outputs: `probe4-out.txt`, `probe5-out.txt` (pinned by `ProbeProvenTests`).
`ilq.ps1`/`il.ps1` decode IL (`.ctor` supported), `find.ps1` finds types, `callers.ps1` finds callers of a method.

- **Warhead targeting.** `Warhead.ValidTargets` defaults to `[Ground, Water]`, `InvalidTargets` to empty, and so does
  a weapon's. An airborne aircraft carries `[Air]` (`TargetableAircraft`; grounded: `Ground`). `Warhead.IsValidAgainst`
  needs a damage warhead (the base `CanTargetActor` is a constant false; `DamageWarhead` needs a Health trait and a
  `Versus` modifier above 0), then the warhead's own ValidTargets/InvalidTargets against the victim's types.
  `WeaponInfo.IsValidAgainst` = the weapon-level test **and** some warhead valid; `Armament.CheckFire`,
  `AttackBase.HasAnyValidWeapons` and `ChooseArmamentForTarget` all call it. So a weapon with `ValidTargets: Ground, Air`
  whose damage warhead lacks Air can neither be ordered to attack an aircraft nor damage it. 17 weapons are like that:
  TowerMissle (its warhead says `ValidTargets: Ground` explicitly), Deagle, TechMachineGun, Dozergun, Frockets,
  Hrockets, TSARocket, OsirisMissiles, OsirisMissiles2, MarMG, MarPanzershrek, QuadCannon, Glauncher,
  NestMachineGunAA (weapon-level `Air` only: it cannot target ground units either, so it can target nothing), LMG,
  MammothMissiles2, MachineGun2. `python tools/tfc_stats.py air legacy-0.32` lists them.
- **Armour.** `DamageWarhead.DamageVersus(actor)`: no `Armor` trait, or an `Armor` whose `Type` is unset, gives 100
  against every weapon; an `Armor: Type: None` gives the weapon's own `None` entry (120mm 30, Flamethrower 90), and a
  type that matches no key (`light` on SPC) gives 100. So a blank `armor` cell and `None` are different;
  `compare` reports the difference and says so. Eight 0.32 actors have Health and no Armor trait (the bridges,
  `camera`, `camera.small`, `flare`).
- **Weapon defaults.** `Burst` 1, `BurstDelay` 5, `ReloadDelay` 1, `Range` 0, `MinRange` 0, `Charges` false.
- **Power.** The 2014 `Building` trait has no `Power` field, so `Building: Power: -20` is silently ignored; only
  `Power: Amount:` counts. ATWR, SILO, HAND, VLCN and 12 other buildings carry such dead values (two of them 0) and drew 0 power in
  0.32. `power`/`power_drain` hold what the engine applies; the dead values are in `building_power_ignored`.
- **Build time.** Ticks = `GetBuildTime(actor)` x the queue's `BuildSpeed` (.4), and `GetBuildTime` is
  `CustomBuildTimeValue.Value`, or cost x 1.5 when the actor has none. `build_duration` is that `Value` for the three
  actors that set it (GUN 1440, GTWR 1440, SAM 2160) and blank otherwise. Modern ticks = `BuildDuration` x 60 percent,
  so GUN/GTWR (576 ticks) need `BuildDuration: 960` and SAM (864 ticks) `1440`; writing the 0.32 number 1440 on GUN
  gives 864 ticks.
- **Storage.** Building storage was already captured as `StoresResources.Capacity`; the port side now maps modern
  `StoresPlayerResources: Capacity` to it.
