# Contributing

## Balance check: the frozen 0.32 stats

`tools/tfc_stats.py` (Python 3, standard library only) records every unit's and
weapon's numbers so the OpenRA 20250330 port can be compared against 0.32.

Frozen reference (generated from the mod at commit `ed02790`, 273 actors,
25 templates, 100 weapons; do not edit by hand):

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
