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

# Self-test of the resolver (hand-checked values) against the mod at MODDIR (default: repo root).
python tools/tfc_stats.py selftest [MODDIR]
```

To regenerate the frozen files, check out `ed02790` (the 0.32 layout has `mod.yaml`
at the repo root) and run `baseline . --out-dir tools`. If the mod files move
within the repo, pass the new folder as `MODDIR`; `mod.yaml` paths of the form
`./mods/<name>/...` are read relative to it.

### TODO (later task, not done yet): CSVs from the ported mod

`baseline` understands only the 2014 format. The port on OpenRA 20250330 needs
the same CSV schema produced from its resolved rules, for example through
`utility.cmd tfc --resolved-rules ACTOR` and `--resolved-weapons`. Write that
extractor, then feed its output to `compare` as the second CSV pair. Until
then `compare` can only be run on edited copies of the baseline.

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
