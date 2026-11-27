#!/usr/bin/env python3
"""tfc_stats.py - frozen-stats tool for The Forgotten Chapter (TFC).

Plain Python 3, standard library only.

Commands
  baseline MODDIR [--out-dir DIR] [--prefix NAME]
      Read a 2014-format (OpenRA release-20141029) mod folder, resolve the
      rules and weapons the way the engine does, and write two CSVs:
      <prefix>-actors.csv and <prefix>-weapons.csv (default prefix
      "baseline-0.32", default out dir = this script's folder).
  compare BASE_ACTORS BASE_WEAPONS NEW_ACTORS NEW_WEAPONS [--ignore COLS] [--only FILE] [--summary]
      Print added / removed / changed rows and values, then a headline (present,
      missing, differing, per-column counts). Exits 1 only if an actor or
      weapon present in the baseline is missing from the new set.
      --ignore: comma list of columns (or extras.Trait.Field / terrain_speeds.Type);
      --only: a file of names (one per line, # comments) to restrict both sides to.
  port [REPO] [--repo R] [--engine E] [--out-dir D] [--jobs N] [--no-cache]
       [--only FILE | --actors A,B --weapons W,V]      (alias: extract2025)
      Read the ported mod (OpenRA 20250330 Mod SDK repo) through the engine's own
      resolver (OpenRA.Utility --resolved-rules / --resolved-weapons) and write
      port-actors.csv and port-weapons.csv in the baseline's schema, every value
      converted back to 0.32 units. Needs ./engine built (make.cmd all).
  check NAME... [--list FILE] [--actors A,B] [--weapons W,V] [--ignore COLS]
      port for just those names, then compare with the frozen baseline.
      Exits 1 if a listed name is missing from the port, 2 if a name is not in the
      baseline or the engine is not built.
  selftest
      Run the built-in tests (they need the mod at commit ed02790 or the
      frozen CSVs; see tools/test_tfc_stats.py for the resolver checks).

How the 2014 engine resolves rules (PROVEN against the engine's own code by
calling OpenRA.Game.exe's MiniYaml methods, see CONTRIBUTING.md):
  * Files are read in the order mod.yaml lists them (Rules, Weapons) and folded
    with Aggregate(MergeLiberal): the EARLIER file wins every conflict; fields
    only in the later file are added. Nested nodes merge field by field.
  * `Inherits: Parent` (exact key only, case-sensitive name) is resolved
    recursively; the child wins over the parent; `-Key` deletes Key from the
    merged result at that level (also the child's own Key).
  * Weapons have no Inherits. Weapon and actor lookup is case-insensitive
    (names are lower-cased); armour types in `Versus` are case-sensitive.
"""
import csv
import os
import sys
from collections import OrderedDict

# --------------------------------------------------------------------------
# MiniYaml parsing and merging
# --------------------------------------------------------------------------


class Node:
    __slots__ = ("value", "children")

    def __init__(self, value=None, children=None):
        self.value = value
        self.children = children if children is not None else OrderedDict()

    def copy(self):
        return Node(self.value, OrderedDict((k, v.copy()) for k, v in self.children.items()))


class ParseError(Exception):
    pass


def parse_text(text, source="<text>"):
    """Parse MiniYaml text into a root Node (children keep file order). A key repeated at
    one level is an error."""
    root = Node()
    stack = [(-1, root)]
    for lineno, raw in enumerate(text.replace("\r\n", "\n").replace("\r", "\n").split("\n"), 1):
        line = raw
        # comments: '#' not preceded by a backslash
        i = 0
        while True:
            i = line.find("#", i)
            if i < 0:
                break
            if i > 0 and line[i - 1] == "\\":
                i += 1
                continue
            line = line[:i]
            break
        if not line.strip():
            continue
        depth = 0
        while depth < len(line) and line[depth] == "\t":
            depth += 1
        body = line[depth:]
        if body[:1] == " ":
            # engine would treat leading spaces as part of the key; flag it
            raise ParseError("%s:%d: leading spaces (tabs expected): %r" % (source, lineno, raw))
        body = body.rstrip()
        if ":" in body:
            key, _, value = body.partition(":")
            key = key.strip()
            value = value.strip() or None
        else:
            key, value = body.strip(), None
        if not key:
            raise ParseError("%s:%d: empty key" % (source, lineno))
        while stack and stack[-1][0] >= depth:
            stack.pop()
        if not stack or depth > stack[-1][0] + 1:
            raise ParseError("%s:%d: bad indentation" % (source, lineno))
        parent = stack[-1][1]
        node = parent.children.get(key)
        if node is None:
            node = Node(value)
            parent.children[key] = node
        else:  # the engine throws on repeated keys at one level (MiniYaml.Merge / ToDictionary)
            raise ParseError("%s:%d: duplicate key %r at the same level" % (source, lineno, key))
        stack.append((depth, node))
    return root


def liberal(a, b):
    """OpenRA 20141029 MiniYaml.MergeLiberal(a, b) on two Nodes; returns a new Node.

    The FIRST argument wins: for a key in both, children are merged
    recursively; a value is taken from `a` unless it is empty, then from `b`.
    Keys only in `b` are appended after a's keys. `-Key` nodes are kept as
    literal keys. Proven against the engine, see CONTRIBUTING.md."""
    out = Node(a.value if a.value is not None else b.value)
    for k, v in a.children.items():
        out.children[k] = liberal(v, b.children[k]) if k in b.children else v.copy()
    for k, v in b.children.items():
        if k not in a.children:
            out.children[k] = v.copy()
    return out


def merge_files(nodes):
    """Fold the file list the way RulesetCache.LoadYamlRules does:
    Aggregate(seed=empty, MergeLiberal), i.e. acc = liberal(acc, next_file).
    So the EARLIER file in mod.yaml wins every conflict."""
    acc = Node()
    for n in nodes:
        acc = liberal(acc, n)
    return acc


def strict(child, parent, path, warn=None):
    """OpenRA 20141029 MiniYaml.MergeStrict(child, parent), as ActorInfo.MergeWithParent uses it.

    Child wins like `liberal`. In addition, at every level, a child key `-X`
    deletes the key X from the merged result, including X defined by the child
    itself. Removing a key that exists in neither is an engine error ("Bogus yaml
    removals"). Nested `-X` nodes are left behind as inert leftovers."""
    out = Node(child.value if child.value is not None else parent.value)
    removed = set(k[1:] for k in child.children if k.startswith("-"))
    for r in removed:
        if r not in child.children and r not in parent.children:
            raise ParseError("Bogus yaml removals: %s: -%s removes nothing" % (path, r))
    for k, v in child.children.items():
        if k in removed:
            continue
        out.children[k] = strict(v, parent.children[k], path + "/" + k) if k in parent.children else v.copy()
    for k, v in parent.children.items():
        if k not in child.children and k not in removed:
            out.children[k] = v.copy()
    return out


class Resolver:
    """Resolves `Inherits` (actors) the way ActorInfo.MergeWithParent does.

    Only the exact key `Inherits` counts (`Inherits@x` is ignored by the
    engine), the parent name is matched case-sensitively, and a missing parent
    is an engine error."""

    def __init__(self, tree, what="actor", inherit=True):
        self.tree = tree
        self.what = what
        self.inherit = inherit
        self.resolved = {}
        self.warnings = []
        if inherit:
            for name, node in tree.children.items():
                for k in node.children:
                    if k.startswith("Inherits@"):
                        self.warnings.append("%s %s: %s is ignored by the 2014 engine (only plain Inherits counts)" % (what, name, k))

    def resolve(self, name, _stack=()):
        if name in self.resolved:
            return self.resolved[name]
        if name in _stack:
            raise ParseError("Inherits cycle: %s" % " -> ".join(_stack + (name,)))
        node = self.tree.children[name]
        pn = node.children["Inherits"].value if (self.inherit and "Inherits" in node.children) else None
        if not pn:
            result = node
        else:
            if pn not in self.tree.children:
                raise ParseError("Bogus inheritance -- actor type %s does not exist (from %s)" % (pn, name))
            result = strict(node, self.resolve(pn, _stack + (name,)), name)
            for k in [k for k in result.children if k.startswith("-")]:  # RemoveAll of leftover top-level removals
                del result.children[k]
        self.resolved[name] = result
        return result

    def resolve_all(self):
        for name in self.tree.children:
            self.resolve(name)
        return self.resolved


# --------------------------------------------------------------------------
# mod.yaml and file loading
# --------------------------------------------------------------------------


def read_file(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8-sig")


def mod_section(modyaml_text, section):
    """Return the list of path entries under a top-level `section:` in mod.yaml."""
    out, inside = [], False
    for raw in modyaml_text.replace("\r\n", "\n").split("\n"):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[0] not in " \t":
            inside = raw.split(":")[0].strip() == section
            continue
        if inside:
            out.append(raw.strip())
    return out


def local_path(moddir, entry):
    """Map a mod.yaml entry like ./mods/tfc/rules/x.yaml to a file under moddir."""
    e = entry.replace("\\", "/")
    if e.startswith("./"):
        e = e[2:]
    parts = e.split("/")
    if len(parts) >= 3 and parts[0] == "mods":
        e = "/".join(parts[2:])  # drop mods/<modname>/
    return os.path.join(moddir, *e.split("/"))


def load_section(moddir, section):
    text = read_file(os.path.join(moddir, "mod.yaml"))
    files, trees, sources = [], [], {}
    for entry in mod_section(text, section):
        p = local_path(moddir, entry)
        if not os.path.isfile(p):
            raise ParseError("mod.yaml lists %s but the file does not exist (%s)" % (entry, p))
        files.append(entry)
        t = parse_text(read_file(p), entry)
        trees.append(t)
        short = entry.replace("\\", "/").replace("./mods/", "", 1)
        short = short.split("/", 1)[1] if "/" in short else short
        for k in t.children:
            sources.setdefault(k, []).append(short)
    return files, merge_files(trees), sources


# --------------------------------------------------------------------------
# Field access helpers on a resolved definition
# --------------------------------------------------------------------------


def traits(defn, base):
    """All trait nodes whose name is `base` or `base@Id`, as [(key, Node)]."""
    return [(k, v) for k, v in defn.children.items() if k == base or k.startswith(base + "@")]


def field(defn, trait, name, default=""):
    for _, t in traits(defn, trait):
        if name in t.children and t.children[name].value is not None:
            return t.children[name].value
    return default


def first_field(defn, trait_names, name):
    for tn in trait_names:
        v = field(defn, tn, name, None)
        if v is not None:
            return v
    return ""


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------

LOCOMOTORS = ("Mobile", "Helicopter", "Plane", "Aircraft")
# Other numeric traits a player feels, collected into "extras" as Trait.Field=value
EXTRA_FIELDS = [
    ("Cargo", "MaxWeight"), ("Cargo", "Types"), ("Cargo", "PipCount"),
    ("Passenger", "Weight"),
    ("Harvester", "Capacity"), ("Harvester", "Resources"),
    ("StoresResources", "Capacity"),
    ("Mobile", "Crushes"),
    ("LimitedAmmo", "Ammo"), ("Reloads", "Count"), ("Reloads", "Period"),
    ("AutoTarget", "ScanRadius"),
    ("Health", "Radius"),
    ("Buildable", "BuildLimit"),
    ("Capturable", "CaptureThreshold"),
    ("Capturable", "Type"),
    ("Captures", "CaptureTypes"),
    ("Selectable", "Priority"),
    ("Transforms", "IntoActor"),
    ("Repairable", "RepairPercent"),
    ("RepairableBuilding", "RepairPercent"),
    ("RepairsUnits", "HpPerStep"),
    ("RepairsUnits", "Interval"),
    ("SelfHealing", "Step"), ("SelfHealing", "Ticks"),
    ("Cloak", "InitialDelay"), ("Cloak", "CloakDelay"),
    ("DetectCloaked", "Range"),
    ("Chronoshiftable", "Duration"),
    ("Bridge", "Long"),
    ("LeavesHusk", "HuskActor"),
    ("Explodes", "Weapon"), ("Explodes", "EmptyWeapon"),
    ("TakeCover", "ProneSpeed"),
    ("Wall", "Type"),
    ("ProductionQueue", "Type"), ("ProductionQueue", "BuildSpeed"),
    ("ProductionQueue", "LowPowerSlowdown"),
    ("ProvidesPrerequisite", "Prerequisite"),
    ("SupportPowerManager", ""),
    ("GivesBounty", "Percentage"),
    ("GivesCashOnCapture", "Amount"),
    ("CustomSellValue", "Value"),
    ("Sellable", "SellSound"),
    ("EngineerRepair", ""),
    ("Production", "Produces"),
    ("PrimaryBuilding", ""),
    ("Cargo", "UnloadFacing"),
    ("Turreted", "ROT"), ("Turreted", "InitialFacing"), ("Turreted", "Offset"),
    ("Turreted", "Speed"),
    ("Helicopter", "RearmBuildings"), ("Helicopter", "RepairBuildings"),
    ("Plane", "RearmBuildings"), ("Plane", "RepairBuildings"),
    ("Plane", "ROT"),
    ("Aircraft", "RearmBuildings"),
    ("AttackBase", "FacingTolerance"), ("AttackHeli", "FacingTolerance"),
    ("AttackPlane", "FacingTolerance"), ("AttackTurreted", ""),
    ("Husk", ""),
    ("Tooltip", "GenericName"),
    ("TargetableUnit", "TargetTypes"),
    ("Targetable", "TargetTypes"),
    ("Crushable", "CrushClasses"),
    ("Crushable", "CrushSound"),
    ("GainsExperience", "Upgrades"),
    ("GainsStatUpgrades", ""),
]
ACTOR_COLUMNS = [
    "name", "kind", "tooltip", "faction_owner", "buildable", "queue", "prerequisites",
    "build_palette_order", "cost", "build_duration", "build_duration_modifier",
    "hp", "armor", "locomotor", "speed", "rot", "sight_range", "terrain_speeds",
    "power", "power_drain", "weapons", "other_weapons", "inherits", "source", "traits", "extras",
]


def uniq(seq):
    seen, out = set(), []
    for s in seq:
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def flatten(node, prefix=""):
    """Children of node as 'a.b=value' strings (used for terrain speeds)."""
    out = []
    for k, v in node.children.items():
        if v.value is not None:
            out.append("%s%s=%s" % (prefix, k, v.value))
        out.extend(flatten(v, prefix + k + "."))
    return out


def actor_row(name, defn, raw_node, known_weapons):
    r = OrderedDict((c, "") for c in ACTOR_COLUMNS)
    r["name"] = name
    r["kind"] = "template" if name.startswith("^") else "actor"
    r["tooltip"] = field(defn, "Tooltip", "Name")
    r["cost"] = field(defn, "Valued", "Cost")
    bd = traits(defn, "Buildable")
    r["buildable"] = "yes" if bd else "no"
    r["queue"] = field(defn, "Buildable", "Queue")
    r["prerequisites"] = field(defn, "Buildable", "Prerequisites")
    r["faction_owner"] = field(defn, "Buildable", "Owner")
    r["build_palette_order"] = field(defn, "Buildable", "BuildPaletteOrder")
    r["build_duration"] = field(defn, "Buildable", "BuildDuration")
    r["build_duration_modifier"] = field(defn, "Buildable", "BuildDurationModifier")
    r["hp"] = field(defn, "Health", "HP")
    r["armor"] = field(defn, "Armor", "Type")
    loco = [t for t in LOCOMOTORS if traits(defn, t)]
    r["locomotor"] = "+".join(loco)
    r["speed"] = first_field(defn, LOCOMOTORS, "Speed")
    r["rot"] = first_field(defn, LOCOMOTORS, "ROT")
    r["sight_range"] = field(defn, "RevealsShroud", "Range")
    ts = []
    for _, t in traits(defn, "Mobile"):
        if "TerrainSpeeds" in t.children:
            ts = flatten(t.children["TerrainSpeeds"])
    r["terrain_speeds"] = ";".join(sorted(ts))
    amounts = []
    for _, t in traits(defn, "Power"):
        if "Amount" in t.children and t.children["Amount"].value is not None:
            amounts.append(int(t.children["Amount"].value))
    pos = [a for a in amounts if a > 0]
    neg = [a for a in amounts if a < 0]
    r["power"] = str(sum(pos)) if pos else ""
    r["power_drain"] = str(sum(neg)) if neg else ""
    arm = []
    for _, t in traits(defn, "Armament"):
        w = t.children.get("Weapon")
        if w is not None and w.value:
            arm.append(w.value)
    r["weapons"] = ";".join(sorted(uniq(arm)))
    other = []
    for tk, t in defn.children.items():
        if tk == "Armament" or tk.startswith("Armament@"):
            continue
        for fn in ("Weapon", "EmptyWeapon"):
            if fn in t.children and t.children[fn].value:
                other.append(t.children[fn].value)
    r["other_weapons"] = ";".join(sorted(uniq(other)))
    r["inherits"] = ";".join(v.value for k, v in raw_node.children.items()
                             if (k == "Inherits" or k.startswith("Inherits@")) and v.value)
    r["traits"] = ";".join(sorted(k for k in defn.children if k != "Inherits" and not k.startswith("-")))
    ex = []
    done = set()
    for tn, fn in EXTRA_FIELDS:
        if (tn, fn) in done:
            continue
        done.add((tn, fn))
        if fn == "":
            continue
        for tk, t in traits(defn, tn):
            if fn in t.children and t.children[fn].value is not None:
                ex.append("%s.%s=%s" % (tk, fn, t.children[fn].value))
    r["extras"] = ";".join(sorted(ex))
    return r


def base_name(k):
    return k.split("@")[0]


def versus_columns(weapons):
    cols = []
    for w in weapons.values():
        for k, v in w.children.items():
            if base_name(k) == "Warhead":
                vs = v.children.get("Versus")
                if vs:
                    for a in vs.children:
                        if a not in cols:
                            cols.append(a)
    # keep a conventional order for the usual armour types
    order = ["None", "Wood", "Light", "Heavy", "Concrete"]
    cols.sort(key=lambda c: (order.index(c) if c in order else len(order), c))
    return cols


WEAPON_BASE_COLUMNS = [
    "name", "range", "min_range", "reload_delay", "burst", "burst_delay", "charges",
    "valid_targets", "invalid_targets", "projectile", "projectile_speed",
    "projectile_inaccuracy", "projectile_other",
    "damage", "spread", "warhead_type", "warhead_count", "death_type", "damaging_warheads",
    "versus_armour",
]


def weapon_rows(weapons, sources=None):
    vs_cols = versus_columns(weapons)
    cols = WEAPON_BASE_COLUMNS[:-1] + ["vs_" + c for c in vs_cols] + ["warhead_other", "source"]
    rows = []
    for name, w in weapons.items():
        r = OrderedDict((c, "") for c in cols)
        r["name"] = name
        c = w.children

        def g(k):
            return c[k].value if k in c and c[k].value is not None else ""
        r["range"] = g("Range")
        r["min_range"] = g("MinRange")
        r["reload_delay"] = g("ReloadDelay")
        r["burst"] = g("Burst")
        r["burst_delay"] = g("BurstDelay")
        r["charges"] = g("Charges")
        r["valid_targets"] = g("ValidTargets")
        r["invalid_targets"] = g("InvalidTargets")
        proj = c.get("Projectile")
        if proj is not None:
            r["projectile"] = proj.value or ""
            r["projectile_speed"] = proj.children["Speed"].value if "Speed" in proj.children and proj.children["Speed"].value else ""
            r["projectile_inaccuracy"] = proj.children["Inaccuracy"].value if "Inaccuracy" in proj.children and proj.children["Inaccuracy"].value else ""
            r["projectile_other"] = ";".join("%s=%s" % (k, v.value) for k, v in proj.children.items()
                                              if k not in ("Speed", "Inaccuracy") and v.value is not None)
        whs = [(k, v) for k, v in c.items() if base_name(k) == "Warhead"]
        r["warhead_count"] = str(len(whs))
        dmg_whs = [(k, v) for k, v in whs if "Damage" in v.children]
        r["damaging_warheads"] = str(len(dmg_whs))
        if dmg_whs:
            k0, w0 = dmg_whs[0]
            r["warhead_type"] = w0.value or ""
            r["damage"] = w0.children["Damage"].value or ""
            r["spread"] = w0.children["Spread"].value if "Spread" in w0.children and w0.children["Spread"].value else ""
            r["death_type"] = w0.children["DeathType"].value if "DeathType" in w0.children and w0.children["DeathType"].value else ""
            vs = w0.children.get("Versus")
            if vs:
                for a, v in vs.children.items():
                    r["vs_" + a] = v.value or ""
        elif whs:
            r["warhead_type"] = whs[0][1].value or ""
        other = []
        for k, v in whs:
            if "Damage" in v.children:
                if k != k0:
                    other.append("%s:%s damage=%s" % (k, v.value, v.children["Damage"].value))
            else:
                other.append("%s:%s" % (k, v.value))
            # warheads nested under a warhead are not read by the 2014 engine
            for kk, vv in v.children.items():
                if base_name(kk) == "Warhead":
                    other.append("NESTED(%s in %s):%s" % (kk, k, vv.value))
        r["warhead_other"] = ";".join(other)
        r["source"] = "+".join(sources.get(name, [])) if sources else ""
        rows.append(r)
    return cols, rows


# --------------------------------------------------------------------------
# baseline command
# --------------------------------------------------------------------------


def build(moddir, quiet=False):
    """Load and resolve a mod. Returns a dict with rules, weapons, rows and diagnostics."""
    rfiles, rtree, rsrc = load_section(moddir, "Rules")
    wfiles, wtree, wsrc = load_section(moddir, "Weapons")
    res = Resolver(rtree, "actor")
    resolved = res.resolve_all()
    wres = Resolver(wtree, "weapon", inherit=False)
    wresolved = wres.resolve_all()
    rows = []
    for name, defn in resolved.items():
        row = actor_row(name, defn, rtree.children[name], wresolved)
        row["source"] = "+".join(rsrc.get(name, []))
        rows.append(row)
    wcols, wrows = weapon_rows(wresolved, wsrc)
    problems = []
    wlower = set(k.lower() for k in wresolved)  # the engine looks weapons up case-insensitively
    for r in rows:
        for wn in (r["weapons"] + ";" + r["other_weapons"]).split(";"):
            if wn and wn.lower() not in wlower:
                problems.append("actor %s references unknown weapon %s" % (r["name"], wn))
    return {
        "rule_files": rfiles, "weapon_files": wfiles,
        "actors": resolved, "weapons": wresolved,
        "actor_rows": rows, "weapon_cols": wcols, "weapon_rows": wrows,
        "warnings": res.warnings + wres.warnings, "problems": problems,
    }


def write_csv(path, cols, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cols)
        for r in rows:
            w.writerow([r.get(c, "") for c in cols])


def cmd_baseline(args):
    out_dir = os.path.dirname(os.path.abspath(__file__))
    prefix = "baseline-0.32"
    pos = []
    i = 0
    while i < len(args):
        if args[i] == "--out-dir":
            out_dir = args[i + 1]
            i += 2
        elif args[i] == "--prefix":
            prefix = args[i + 1]
            i += 2
        else:
            pos.append(args[i])
            i += 1
    if len(pos) != 1:
        print(__doc__)
        return 2
    try:
        b = build(pos[0])
    except (ParseError, OSError, KeyError) as e:
        print("ERROR: %s" % e)
        return 1
    os.makedirs(out_dir, exist_ok=True)
    ap = os.path.join(out_dir, prefix + "-actors.csv")
    wp = os.path.join(out_dir, prefix + "-weapons.csv")
    write_csv(ap, ACTOR_COLUMNS, b["actor_rows"])
    write_csv(wp, b["weapon_cols"], b["weapon_rows"])
    n_t = sum(1 for r in b["actor_rows"] if r["kind"] == "template")
    n_a = len(b["actor_rows"]) - n_t
    print("rules files: %d, weapon files: %d" % (len(b["rule_files"]), len(b["weapon_files"])))
    print("actors: %d, templates: %d, weapons: %d" % (n_a, n_t, len(b["weapon_rows"])))
    print("unresolved Inherits: 0, parse errors: 0")
    for p in b["problems"]:
        print("PROBLEM: " + p)
    for w in b["warnings"]:
        print("warning: " + w)
    print("wrote " + ap)
    print("wrote " + wp)
    return 0


# --------------------------------------------------------------------------
# dump command (used to prove the resolver against the engine's own output)
# --------------------------------------------------------------------------


def flat_lines(node, depth=1):
    out = []
    for k, v in node.children.items():
        out.append("%s%s: %s" % ("\t" * depth, k, v.value if v.value is not None else "<null>"))
        out.extend(flat_lines(v, depth + 1))
    return out


def cmd_dump(args):
    """dump MODDIR OUTDIR: write resolved-actors.txt / resolved-weapons.txt in the same flat
    format as the engine-side probe (see tools/probe/ and CONTRIBUTING.md)."""
    if len(args) != 2:
        print(__doc__)
        return 2
    b = build(args[0])
    os.makedirs(args[1], exist_ok=True)
    for fname, defs in (("resolved-actors.txt", b["actors"]), ("resolved-weapons.txt", b["weapons"])):
        with open(os.path.join(args[1], fname), "w", newline="\n", encoding="utf-8") as f:
            for name, node in defs.items():
                f.write("@@ %s" % name + "\n")
                for ln in flat_lines(node):
                    f.write(ln + "\n")
    print("wrote resolved-actors.txt and resolved-weapons.txt in " + args[1])
    return 0


# --------------------------------------------------------------------------
# port command: the 20250330 side, converted back to 0.32 units
# --------------------------------------------------------------------------
#
# CONVERSIONS (modern 20250330 value -> 0.32 baseline value). Every one is also in CONTRIBUTING.md.
#   Health HP, warhead Damage ........ / 100   (stock E1 5000 -> 50, Heal -5000 -> -50)
#   ChangesHealth Step ............... / 100   (written as SelfHealing Step; Delay is written as Ticks)
#   TurnSpeed (Mobile, Aircraft,
#     Turreted), InitialFacing,
#     AttackAircraft FacingTolerance . / 4     (1023 -> 255.75; 20 -> 5; the 0-255 facing scale became 0-1023)
#   BurstDelays ...................... first entry only (0.32 had one BurstDelay)
#   MinRange 0, Burst 1 .............. the defaults; written as an empty cell, as the baseline does
#   DamageTypes ...................... the *Death name -> DeathType number (BulletDeath 1, RippedApartDeath 2,
#                                      SmallExplosionDeath 3, ExplosionDeath 4, FireDeath 5, TiberiumDeath 6,
#                                      DefaultDeath 1)
#   WDist (Range, MinRange, Spread,
#     projectile Speed, Inaccuracy) .. written as the baseline writes it: below 1024 a plain integer, else NcM
#   DetectCloaked Range .............. whole cells as a bare integer (2c0 -> 2); otherwise the WDist
#   TakeCover SpeedModifier .......... / 100 (60 -> 0.6, written as ProneSpeed)
#   ProductionQueue LowPowerModifier . / 100 (200 -> 2, written as LowPowerSlowdown; absent = default 100 -> 1)
#   ProductionQueue BuildDurationModifier
#                                      100 (the default) -> BuildSpeed ".4"; any other value is written as the text
#                                      "BuildDurationModifier=N" so that it shows as a difference (only the 100 <-> .4
#                                      pair is documented in the design note, so no other value is guessed)
#   Buildable BuildDuration -1 and
#     BuildDurationModifier 60 ....... the modern defaults; written as an empty cell (the baseline cell is empty too)
#   Aircraft ......................... locomotor "Helicopter" if CanHover is true, else "Plane"
#   Mobile Locomotor ................. terrain_speeds and Mobile.Crushes come from World's Locomotor@* whose Name
#                                      matches; the modern Bridge terrain type (0.32 had none) is dropped
#   AmmoPool Ammo / ReloadAmmoPool
#     Count, Delay ................... LimitedAmmo.Ammo, Reloads.Count, Reloads.Period
#   StoresResources Capacity ......... Harvester.Capacity on an actor that has a Harvester, else StoresResources.Capacity
#   SpawnActorOnDeath Actor .......... LeavesHusk.HuskActor (instances without Probability; the ones with it are the Vice mutation)
#   Aircraft: Repairable RepairActors, Rearmable RearmActors -> <Helicopter|Plane>.RepairBuildings / .RearmBuildings
#   AttackAircraft FacingTolerance ... AttackHeli.FacingTolerance (Helicopter) or AttackPlane.FacingTolerance, / 4
#   FireWarheadsOnDeath Weapon,
#     EmptyWeapon .................... other_weapons, and Explodes.Weapon / Explodes.EmptyWeapon
#   Tooltip Name / GenericName ....... resolved through the Fluent files (later file wins); an unresolvable key is
#                                      written as "<fluent:key>"
# Columns with no modern counterpart carry the marker MARKER (see UNMAPPED_COLUMNS and UNMAPPED_EXTRAS); compare
# reports them as "not comparable" instead of as a change.

import hashlib
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

MARKER = "<unmapped>"
UNMAPPED_ACTOR_COLUMNS = {
    "faction_owner": "0.32 Buildable Owner; modern builds are gated by the production queue per faction",
}
UNMAPPED_WEAPON_COLUMNS = {
    "charges": "0.32 Charges; the modern engine has no equivalent",
    "projectile_other": "0.32 projectile fields (High, Angle, ROT, RangeLimit...) became differently named fields",
    "warhead_other": "0.32 text about nested/extra warheads; modern files have no nested warheads",
}
UNMAPPED_COLUMNS = {}
UNMAPPED_COLUMNS.update(UNMAPPED_ACTOR_COLUMNS)
UNMAPPED_COLUMNS.update(UNMAPPED_WEAPON_COLUMNS)
# 0.32 extras keys (Trait.Field) the port does not emit because the modern trait does not carry the same meaning.
UNMAPPED_EXTRAS = {
    "Health.Radius": "0.32 target radius; modern uses HitShape (a different model)",
    "TargetableUnit.TargetTypes": "the TargetTypes vocabulary changed (C4, Repair, Heal types); owned by lane 4e",
    "Capturable.Type": "capture types were renamed in the modern capture model (owner question: militia capture)",
    "Capturable.CaptureThreshold": "no modern field (0.32 whole-health capture rule)",
    "Captures.CaptureTypes": "capture types were renamed in the modern capture model",
    "Cargo.PipCount": "modern pips are WithCargoPipsDecoration (a rendering trait)",
}
DEATH_TYPES = {"BulletDeath": "1", "RippedApartDeath": "2", "SmallExplosionDeath": "3", "ExplosionDeath": "4",
               "FireDeath": "5", "TiberiumDeath": "6", "DefaultDeath": "1"}


def frac(v):
    try:
        return Fraction(str(v).strip())
    except (ValueError, ZeroDivisionError):
        return None


def fmt(x):
    """A Fraction as a short decimal: integers plain, otherwise up to 4 decimals with no trailing zeros."""
    if x.denominator == 1:
        return str(x.numerator)
    s = "%.4f" % (x.numerator / x.denominator)
    return s.rstrip("0").rstrip(".")


def divide(v, k):
    """Value v (text) divided by k, as text. Unparsable text is returned as '<bad:text>'."""
    if v is None or v == "":
        return ""
    f = frac(v)
    return fmt(f / k) if f is not None else "<bad:%s>" % v


def wdist_total(v):
    m = re.match(r"^(-?)(\d+)c(\d+)$", v.strip())
    if m:
        t = int(m.group(2)) * 1024 + int(m.group(3))
        return -t if m.group(1) else t
    if re.match(r"^-?\d+$", v.strip()):
        return int(v.strip())
    return None


def wdist(v):
    """Canonical WDist text as the baseline writes it: below 1024 a plain integer, else NcM."""
    if v is None or v == "":
        return ""
    t = wdist_total(v)
    if t is None:
        return v
    if abs(t) < 1024:
        return str(t)
    return "%dc%d" % (t // 1024, t % 1024)


def cells_or_wdist(v):
    if v is None or v == "":
        return ""
    t = wdist_total(v)
    if t is None:
        return v
    return str(t // 1024) if t % 1024 == 0 else wdist(v)


def trait_instances(defn, base):
    return traits(defn, base)


def suffix(key):
    return key[key.index("@"):] if "@" in key else ""


# --- Fluent -----------------------------------------------------------------

def package_dir(repo, engine, pkg):
    if pkg == "tfc":
        return os.path.join(repo, "mods", "tfc")
    return os.path.join(engine, "mods", pkg)


def port_path(repo, engine, entry, modid="tfc"):
    pkg, _, rest = entry.partition("|")
    if not rest:
        raise ParseError("mod.yaml entry without a package: %s" % entry)
    if pkg == modid:
        pkg = "tfc"
    return os.path.join(package_dir(repo, engine, pkg), *rest.split("/"))


def load_fluent(repo, engine):
    text = read_file(os.path.join(repo, "mods", "tfc", "mod.yaml"))
    msgs = {}
    for entry in mod_section(text, "FluentMessages"):
        p = port_path(repo, engine, entry)
        if not os.path.isfile(p):
            continue
        cur = None
        for raw in read_file(p).replace("\r\n", "\n").split("\n"):
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            m = re.match(r"^([A-Za-z][\w-]*)\s*=\s*(.*)$", raw)
            if m:
                cur = {"": m.group(2).strip(), "attrs": {}}
                msgs[m.group(1)] = cur  # a later file replaces the whole message
                continue
            m = re.match(r"^\s+\.([\w-]+)\s*=\s*(.*)$", raw)
            if m and cur is not None:
                cur["attrs"][m.group(1)] = m.group(2).strip()
                continue
            if raw[:1] in " \t" and cur is not None and cur[""] != "" and not raw.strip().startswith("["):
                cur[""] += " " + raw.strip()
            elif not raw[:1] in " \t":
                cur = None
    return msgs


def fluent_text(msgs, key):
    if not key:
        return ""
    mid, _, attr = key.partition(".")
    m = msgs.get(mid)
    if m is None:
        return "<fluent:%s>" % key
    v = m["attrs"].get(attr) if attr else m[""]
    return v if v else "<fluent:%s>" % key


# --- file lists, names, engine calls ------------------------------------------

def port_files(repo, engine, section):
    text = read_file(os.path.join(repo, "mods", "tfc", "mod.yaml"))
    out = []
    for entry in mod_section(text, section):
        p = port_path(repo, engine, entry)
        if not os.path.isfile(p):
            raise ParseError("mod.yaml lists %s but the file does not exist (%s)" % (entry, p))
        out.append((entry, p))
    return out


def port_names(repo, engine, section):
    """Every top-level name (with its case) in the section's files, in first-seen order, with the files that
    define it and the Inherits values written for it (a plain list; the merged result is not needed)."""
    names, sources, inherits = [], {}, {}
    for entry, p in port_files(repo, engine, section):
        tree = parse_text(read_file(p), entry)
        short = entry.split("|", 1)[1]
        for k, v in tree.children.items():
            if k.startswith("-"):
                continue
            if k not in sources:
                names.append(k)
            sources.setdefault(k, []).append(short)
            for ik, iv in v.children.items():
                if (ik == "Inherits" or ik.startswith("Inherits@")) and iv.value:
                    if iv.value not in inherits.setdefault(k, []):
                        inherits[k].append(iv.value)
    return names, sources, inherits


def engine_command(engine):
    if os.name == "nt":
        exe = os.path.join(engine, "bin", "OpenRA.Utility.exe")
        return [exe] if os.path.isfile(exe) else None
    dll = os.path.join(engine, "bin", "OpenRA.Utility.dll")
    return ["dotnet", dll] if os.path.isfile(dll) else None


def mod_id(repo):
    cfg = os.path.join(repo, "mod.config")
    if os.path.isfile(cfg):
        for line in read_file(cfg).splitlines():
            if line.startswith("MOD_ID="):
                return line.split("=", 1)[1].strip().strip('"')
    return "tfc"


class Engine:
    """Runs `OpenRA.Utility.exe <mod> --resolved-rules|--resolved-weapons NAME` the way utility.cmd does: from the
    engine folder, with MOD_SEARCH_PATHS=<repo>\\mods,./mods and ENGINE_DIR=.. . Results are cached by content
    hash of the section's files (a changed file invalidates the whole section)."""

    def __init__(self, repo, engine, cache=True, jobs=4):
        self.repo, self.engine, self.jobs = repo, engine, jobs
        self.cmd = engine_command(engine)
        if self.cmd is None:
            raise OSError("engine not built: %s has no OpenRA.Utility (run make.cmd all)" % engine)
        self.mod = mod_id(repo)
        self.env = dict(os.environ, MOD_SEARCH_PATHS=os.path.join(repo, "mods") + ",./mods", ENGINE_DIR="..")
        self.cache_root = None
        if cache:
            self.cache_root = os.path.join(tempfile.gettempdir(), "tfc-stats-cache",
                                           hashlib.sha1(os.path.abspath(repo).lower().encode()).hexdigest()[:10])
        self._dirs = {}
        self.calls = 0
        self.cached = 0

    def _dir(self, section):
        if self.cache_root is None:
            return None
        if section not in self._dirs:
            h = hashlib.sha1()
            ver = os.path.join(self.engine, "VERSION")
            if os.path.isfile(ver):
                with open(ver, "rb") as f:
                    h.update(f.read())
            for entry, p in port_files(self.repo, self.engine, section):
                h.update(entry.encode())
                with open(p, "rb") as f:
                    h.update(f.read())
            d = os.path.join(self.cache_root, section.lower() + "-" + h.hexdigest()[:16])
            os.makedirs(d, exist_ok=True)
            self._dirs[section] = d
        return self._dirs[section]

    def _one(self, section, name):
        flag = "--resolved-rules" if section == "Rules" else "--resolved-weapons"
        d = self._dir(section)
        fn = os.path.join(d, hashlib.sha1(name.encode()).hexdigest()[:20] + ".txt") if d else None
        if fn and os.path.isfile(fn):
            self.cached += 1
            return name, read_file(fn), None
        err = ""
        for _ in range(2):
            r = subprocess.run(self.cmd + [self.mod, flag, name], cwd=self.engine, env=self.env,
                               capture_output=True)
            self.calls += 1
            out = r.stdout.decode("utf-8", "replace")
            if r.returncode == 0:
                if fn:
                    with open(fn, "w", encoding="utf-8", newline="\n") as f:
                        f.write(out)
                return name, out, None
            err = (out + r.stderr.decode("utf-8", "replace")).strip().splitlines()
            err = err[0] if err else "exit %d" % r.returncode
        return name, None, err

    def resolve(self, section, names):
        """{name: Node} for the names, and {name: error} for failures."""
        ok, bad = {}, {}
        self._dir(section)  # create the cache folder before the threads start
        with ThreadPoolExecutor(max(1, self.jobs)) as ex:
            for name, text, err in ex.map(lambda n: self._one(section, n), names):
                if text is None:
                    bad[name] = err
                else:
                    try:
                        ok[name] = parse_text(text, "%s %s" % (section, name))
                    except ParseError as e:
                        bad[name] = str(e)
        return ok, bad


# --- row building -----------------------------------------------------------------

def world_locomotors(world):
    out = {}
    if world is None:
        return out
    for k, v in world.children.items():
        if k == "Locomotor" or k.startswith("Locomotor@"):
            n = v.children.get("Name")
            if n is not None and n.value:
                out[n.value] = v
    return out


def aircraft_class(defn):
    ac = traits(defn, "Aircraft")
    if not ac:
        return ""
    for _, t in ac:
        c = t.children.get("CanHover")
        if c is not None and (c.value or "").lower() == "true":
            return "Helicopter"
    return "Plane"


def pfield(defn, trait, name):
    """First non-empty value of trait[name] over the trait's instances, else None."""
    for _, t in traits(defn, trait):
        if name in t.children and t.children[name].value is not None:
            return t.children[name].value
    return None


def port_extras(defn, aclass, loco_node, msgs):
    ex = {}

    def put(old_trait, old_field, value):
        if value is not None and value != "":
            ex["%s.%s" % (old_trait, old_field)] = value

    # (new trait, new field, old trait, old field, conversion)
    table = [
        ("AutoTarget", "ScanRadius", "AutoTarget", "ScanRadius", None),
        ("Buildable", "BuildLimit", "Buildable", "BuildLimit", None),
        ("Cargo", "MaxWeight", "Cargo", "MaxWeight", None),
        ("Cargo", "Types", "Cargo", "Types", None),
        ("Cloak", "InitialDelay", "Cloak", "InitialDelay", None),
        ("Cloak", "CloakDelay", "Cloak", "CloakDelay", None),
        ("Crushable", "CrushClasses", "Crushable", "CrushClasses", None),
        ("Crushable", "CrushSound", "Crushable", "CrushSound", None),
        ("CustomSellValue", "Value", "CustomSellValue", "Value", None),
        ("DetectCloaked", "Range", "DetectCloaked", "Range", cells_or_wdist),
        ("FireWarheadsOnDeath", "Weapon", "Explodes", "Weapon", None),
        ("FireWarheadsOnDeath", "EmptyWeapon", "Explodes", "EmptyWeapon", None),
        ("Harvester", "Resources", "Harvester", "Resources", None),
        ("AmmoPool", "Ammo", "LimitedAmmo", "Ammo", None),
        ("ReloadAmmoPool", "Count", "Reloads", "Count", None),
        ("ReloadAmmoPool", "Delay", "Reloads", "Period", None),
        ("Production", "Produces", "Production", "Produces", None),
        ("RepairableBuilding", "RepairPercent", "RepairableBuilding", "RepairPercent", None),
        ("Selectable", "Priority", "Selectable", "Priority", None),
        ("ChangesHealth", "Step", "SelfHealing", "Step", lambda v: divide(v, 100)),
        ("ChangesHealth", "Delay", "SelfHealing", "Ticks", None),
        ("TakeCover", "SpeedModifier", "TakeCover", "ProneSpeed", lambda v: divide(v, 100)),
        ("Transforms", "IntoActor", "Transforms", "IntoActor", None),
        ("Turreted", "TurnSpeed", "Turreted", "ROT", lambda v: divide(v, 4)),
        ("Turreted", "InitialFacing", "Turreted", "InitialFacing", lambda v: divide(v, 4)),
        ("Turreted", "Offset", "Turreted", "Offset", None),
    ]
    for nt, nf, ot, of, conv in table:
        for tk, t in traits(defn, nt):
            if nf in t.children and t.children[nf].value is not None:
                v = t.children[nf].value
                put(ot + suffix(tk), of, conv(v) if conv else v)
    # husk: SpawnActorOnDeath without a Probability (the Probability ones are the Vice mutation)
    for tk, t in traits(defn, "SpawnActorOnDeath"):
        if "Actor" in t.children and t.children["Actor"].value and "Probability" not in t.children:
            put("LeavesHusk" + suffix(tk), "HuskActor", t.children["Actor"].value)
    # Harvester capacity lives on StoresResources
    has_harv = bool(traits(defn, "Harvester"))
    for tk, t in traits(defn, "StoresResources"):
        if "Capacity" in t.children and t.children["Capacity"].value is not None:
            put("Harvester" if has_harv else "StoresResources", "Capacity", t.children["Capacity"].value)
    # production queues
    for tk, t in traits(defn, "ProductionQueue"):
        sfx = suffix(tk)
        if "Type" in t.children and t.children["Type"].value:
            put("ProductionQueue" + sfx, "Type", t.children["Type"].value)
        d = frac(t.children["BuildDurationModifier"].value) if "BuildDurationModifier" in t.children else Fraction(100)
        put("ProductionQueue" + sfx, "BuildSpeed", ".4" if d == 100 else "BuildDurationModifier=%s" %
            (t.children["BuildDurationModifier"].value))
        lp = t.children["LowPowerModifier"].value if "LowPowerModifier" in t.children else "100"
        put("ProductionQueue" + sfx, "LowPowerSlowdown", divide(lp, 100))
    # aircraft: class-prefixed keys
    if aclass:
        for _, t in traits(defn, "Aircraft"):
            if aclass == "Plane" and "TurnSpeed" in t.children:
                put("Plane", "ROT", divide(t.children["TurnSpeed"].value, 4))
        rp = pfield(defn, "Repairable", "RepairActors")
        if rp is not None:
            put(aclass, "RepairBuildings", rp)
        ra = pfield(defn, "Rearmable", "RearmActors")
        if ra is not None:
            put(aclass, "RearmBuildings", ra)
        ft = pfield(defn, "AttackAircraft", "FacingTolerance")
        if ft is not None:
            put("AttackHeli" if aclass == "Helicopter" else "AttackPlane", "FacingTolerance", divide(ft, 4))
    # crushes come from the locomotor
    if loco_node is not None and "Crushes" in loco_node.children and loco_node.children["Crushes"].value:
        put("Mobile", "Crushes", loco_node.children["Crushes"].value)
    # tooltip generic name through Fluent
    gn = pfield(defn, "Tooltip", "GenericName")
    if gn:
        put("Tooltip", "GenericName", fluent_text(msgs, gn))
    return ex


def port_actor_row(name, defn, sources, inherits, locos, msgs):
    r = OrderedDict((c, "") for c in ACTOR_COLUMNS)
    r["name"] = name
    r["kind"] = "template" if name.startswith("^") else "actor"
    tn = pfield(defn, "Tooltip", "Name")
    r["tooltip"] = fluent_text(msgs, tn) if tn else ""
    r["faction_owner"] = MARKER
    r["buildable"] = "yes" if traits(defn, "Buildable") else "no"
    r["queue"] = pfield(defn, "Buildable", "Queue") or ""
    r["prerequisites"] = pfield(defn, "Buildable", "Prerequisites") or ""
    r["build_palette_order"] = pfield(defn, "Buildable", "BuildPaletteOrder") or ""
    r["cost"] = pfield(defn, "Valued", "Cost") or ""
    bd = pfield(defn, "Buildable", "BuildDuration")
    r["build_duration"] = "" if bd in (None, "-1") else bd
    bm = pfield(defn, "Buildable", "BuildDurationModifier")
    r["build_duration_modifier"] = "" if bm in (None, "60") else bm
    r["hp"] = divide(pfield(defn, "Health", "HP"), 100)
    r["armor"] = pfield(defn, "Armor", "Type") or ""
    aclass = aircraft_class(defn)
    loco = []
    if traits(defn, "Mobile"):
        loco.append("Mobile")
    if aclass:
        loco.append(aclass)
    r["locomotor"] = "+".join(loco)
    r["speed"] = pfield(defn, "Mobile", "Speed") or pfield(defn, "Aircraft", "Speed") or ""
    ts = pfield(defn, "Mobile", "TurnSpeed")
    if ts is None:
        ts = pfield(defn, "Aircraft", "TurnSpeed")
    r["rot"] = divide(ts, 4) if ts is not None else ""
    r["sight_range"] = pfield(defn, "RevealsShroud", "Range") or ""
    loco_node = None
    ln = pfield(defn, "Mobile", "Locomotor")
    if ln is not None:
        loco_node = locos.get(ln)
        if loco_node is None:
            r["terrain_speeds"] = "<missing-locomotor:%s>" % ln
        else:
            tsn = loco_node.children.get("TerrainSpeeds")
            items = [i for i in (flatten(tsn) if tsn is not None else []) if i.split("=")[0].split(".")[0] != "Bridge"]
            r["terrain_speeds"] = ";".join(sorted(items))
    amounts = []
    for _, t in traits(defn, "Power"):
        if "Amount" in t.children and t.children["Amount"].value is not None:
            amounts.append(int(t.children["Amount"].value))
    pos = [a for a in amounts if a > 0]
    neg = [a for a in amounts if a < 0]
    r["power"] = str(sum(pos)) if pos else ""
    r["power_drain"] = str(sum(neg)) if neg else ""
    arm = [t.children["Weapon"].value for _, t in traits(defn, "Armament")
           if "Weapon" in t.children and t.children["Weapon"].value]
    r["weapons"] = ";".join(sorted(uniq(arm)))
    other = []
    for _, t in traits(defn, "FireWarheadsOnDeath"):
        for fn in ("Weapon", "EmptyWeapon"):
            if fn in t.children and t.children[fn].value:
                other.append(t.children[fn].value)
    r["other_weapons"] = ";".join(sorted(uniq(other)))
    r["inherits"] = ";".join(inherits.get(name, []))
    r["source"] = "+".join(sources.get(name, []))
    r["traits"] = ";".join(sorted(k for k in defn.children if k != "Inherits" and not k.startswith("-")))
    ex = port_extras(defn, aclass, locos.get(ln) if ln else None, msgs)
    r["extras"] = ";".join(sorted("%s=%s" % (k, v) for k, v in ex.items()))
    return r


def port_weapon_rows(weapons, sources):
    vs_cols = versus_columns(weapons)
    cols = WEAPON_BASE_COLUMNS[:-1] + ["vs_" + c for c in vs_cols] + ["warhead_other", "source"]
    rows = []
    for name, w in weapons.items():
        r = OrderedDict((c, "") for c in cols)
        r["name"] = name
        c = w.children

        def g(k):
            return c[k].value if k in c and c[k].value is not None else ""
        r["range"] = wdist(g("Range"))
        mr = wdist(g("MinRange"))
        r["min_range"] = "" if mr == "0" else mr  # an explicit 0 is the default
        r["reload_delay"] = g("ReloadDelay")
        r["burst"] = "" if g("Burst") == "1" else g("Burst")  # an explicit 1 is the default
        bd = g("BurstDelays")
        r["burst_delay"] = bd.split(",")[0].strip() if bd else ""
        r["charges"] = MARKER
        r["valid_targets"] = g("ValidTargets")
        r["invalid_targets"] = g("InvalidTargets")
        proj = c.get("Projectile")
        if proj is not None:
            r["projectile"] = proj.value or ""
            sp = proj.children.get("Speed")
            r["projectile_speed"] = wdist(sp.value) if sp is not None and sp.value else ""
            ia = proj.children.get("Inaccuracy")
            r["projectile_inaccuracy"] = wdist(ia.value) if ia is not None and ia.value else ""
        r["projectile_other"] = MARKER
        whs = [(k, v) for k, v in c.items() if base_name(k) == "Warhead"]
        r["warhead_count"] = str(len(whs))
        dmg_whs = [(k, v) for k, v in whs if "Damage" in v.children]
        r["damaging_warheads"] = str(len(dmg_whs))
        if dmg_whs:
            w0 = dmg_whs[0][1]
            r["warhead_type"] = w0.value or ""
            r["damage"] = divide(w0.children["Damage"].value, 100)
            sp = w0.children.get("Spread")
            r["spread"] = wdist(sp.value) if sp is not None and sp.value else ""
            dt = w0.children.get("DamageTypes")
            if dt is not None and dt.value:
                found = [DEATH_TYPES[t.strip()] for t in dt.value.split(",") if t.strip() in DEATH_TYPES]
                r["death_type"] = found[0] if found else ""
            vs = w0.children.get("Versus")
            if vs:
                for a, v in vs.children.items():
                    r["vs_" + a] = v.value or ""
        elif whs:
            r["warhead_type"] = whs[0][1].value or ""
        r["warhead_other"] = MARKER
        r["source"] = "+".join(sources.get(name, []))
        rows.append(r)
    return cols, rows


def extract_port(repo, engine, actors=None, weapons=None, jobs=4, cache=True, log=None):
    """Read the ported mod through the engine. actors / weapons: lists of names to restrict to (None = all).
    Returns (actor_rows, weapon_cols, weapon_rows, errors, stats). errors = {kind:name: message}."""
    log = log or (lambda s: None)
    eng = Engine(repo, engine, cache, jobs)
    anames, asrc, ainh = port_names(repo, engine, "Rules")
    wnames, wsrc, _ = port_names(repo, engine, "Weapons")
    if actors is not None:
        anames = [n for n in anames if n in set(actors)]
    if weapons is not None:
        wnames = [n for n in wnames if n in set(weapons)]
    log("resolving %d actors and %d weapons (jobs=%d)" % (len(anames), len(wnames), jobs))
    world, werr = eng.resolve("Rules", ["World"])
    arules, aerr = eng.resolve("Rules", anames)
    wres, werr2 = eng.resolve("Weapons", wnames)
    msgs = load_fluent(repo, engine)
    locos = world_locomotors(world.get("World"))
    errors = {}
    for n, e in list(aerr.items()):
        errors["actor:" + n] = e
    for n, e in list(werr2.items()):
        errors["weapon:" + n] = e
    for n, e in werr.items():
        errors["actor:" + n] = e
    arows = [port_actor_row(n, arules[n], asrc, ainh, locos, msgs) for n in anames if n in arules]
    wcols, wrows = port_weapon_rows(OrderedDict((n, wres[n]) for n in wnames if n in wres), wsrc)
    return arows, wcols, wrows, errors, {"calls": eng.calls, "cached": eng.cached}


def parse_opts(args, spec):
    """Tiny option parser: spec {'--name': 'flag'|'value'}. Returns (opts, positionals)."""
    opts, pos, i = {}, [], 0
    while i < len(args):
        a = args[i]
        if a in spec:
            if spec[a] == "flag":
                opts[a] = True
                i += 1
            else:
                if i + 1 >= len(args):
                    raise ValueError("%s needs a value" % a)
                opts[a] = args[i + 1]
                i += 2
        elif a.startswith("--"):
            raise ValueError("unknown option %s" % a)
        else:
            pos.append(a)
            i += 1
    return opts, pos


def read_name_list(path):
    out = []
    for line in read_file(path).splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def default_repo():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cmd_port(args):
    spec = {"--repo": "value", "--engine": "value", "--out-dir": "value", "--jobs": "value", "--no-cache": "flag",
            "--only": "value", "--actors": "value", "--weapons": "value"}
    try:
        o, pos = parse_opts(args, spec)
    except ValueError as e:
        print("ERROR: %s" % e)
        return 2
    repo = os.path.abspath(o.get("--repo", pos[0] if pos else default_repo()))
    engine = os.path.abspath(o.get("--engine", os.path.join(repo, "engine")))
    out_dir = o.get("--out-dir", os.path.join(tempfile.gettempdir(), "tfc-stats"))
    actors = weapons = None
    if "--only" in o:
        names = read_name_list(o["--only"])
        actors = weapons = names
    if "--actors" in o:
        actors = o["--actors"].split(",")
    if "--weapons" in o:
        weapons = o["--weapons"].split(",")
    try:
        arows, wcols, wrows, errors, st = extract_port(repo, engine, actors, weapons, int(o.get("--jobs", 4)),
                                                       "--no-cache" not in o, log=print)
    except (OSError, ParseError) as e:
        print("ERROR: %s" % e)
        return 2
    os.makedirs(out_dir, exist_ok=True)
    ap, wp = os.path.join(out_dir, "port-actors.csv"), os.path.join(out_dir, "port-weapons.csv")
    write_csv(ap, ACTOR_COLUMNS, arows)
    write_csv(wp, wcols, wrows)
    print("actors: %d, weapons: %d, engine calls: %d, from cache: %d" % (len(arows), len(wrows), st["calls"], st["cached"]))
    for k, e in errors.items():
        print("ERROR: %s: %s" % (k, e))
    print("wrote " + ap)
    print("wrote " + wp)
    return 2 if errors else 0


# --------------------------------------------------------------------------
# compare command
# --------------------------------------------------------------------------

SPLIT_COLUMNS = ("extras", "terrain_speeds")
# The 0.32 engine looked actors and weapons up case-insensitively, and the stock 20250330 names are spelled
# differently in case (MTNK.Husk and mtnk.husk are the same thing there), so these cells compare ignoring case.
CASE_INSENSITIVE = ("weapons", "other_weapons", "extras.Explodes.Weapon", "extras.Explodes.EmptyWeapon",
                    "extras.LeavesHusk.HuskActor", "extras.Transforms.IntoActor")
DEFAULT_IGNORE = ("traits", "inherits", "source", "faction_owner")


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        rows = OrderedDict((r["name"], r) for r in rd)
        return rd.fieldnames, rows


def split_items(v):
    out = OrderedDict()
    for item in v.split(";"):
        if item:
            k, _, val = item.partition("=")
            out[k] = val
    return out


def norm_cell(col, v):
    if col.startswith("vs_") and v == "":
        return "100"  # a missing armour type took 100 percent in both engines
    if col == "burst_delay" and v == "":
        return "5"    # the default delay between burst shots is 5 ticks in both engines
    return v


def row_changes(col, a, b, ignore):
    """[(label, a, b, kind)] for one column of one row. kind: 'changed', 'added' (an extras / terrain key only the
    port has) or 'n/a' (port side not comparable)."""
    if col in ignore:
        return []
    if b == MARKER:
        return [(col, a, b, "n/a")] if a != "" else []
    if col in SPLIT_COLUMNS:
        ia, ib = split_items(a), split_items(b)
        out = []
        for k in list(ia) + [k for k in ib if k not in ia]:
            label = "%s.%s" % (col, k)
            if label in ignore:
                continue
            va, vb = ia.get(k, ""), ib.get(k, "")
            if va == vb or (re.sub(r"@[^.]*", "", label) in CASE_INSENSITIVE and va.lower() == vb.lower()):
                continue
            if col == "extras" and k not in ib and k in UNMAPPED_EXTRAS:
                out.append((label, va, "", "n/a"))
            elif va == "" and col in SPLIT_COLUMNS:
                out.append((label, va, vb, "added"))  # a key the baseline did not have: listed, not counted as a change
            else:
                out.append((label, va, vb, "changed"))
        return out
    a, b = norm_cell(col, a), norm_cell(col, b)
    if col in CASE_INSENSITIVE and a.lower() == b.lower():
        return []
    return [(col, a, b, "changed")] if a != b else []


def diff_sets(label, base_cols, base, new_cols, new, out, ignore=(), only=None, detail=True, stats=None):
    """Append a report to `out`; returns the number of baseline rows missing from the new set.
    stats (optional dict) receives counts for the headline."""
    if only is not None:
        base = OrderedDict((n, r) for n, r in base.items() if n in only)
    missing = [n for n in base if n not in new]
    added = [n for n in new if n not in base] if only is None else []
    changed, na, plus = [], [], []
    cols = list(base_cols) + [c for c in new_cols if c not in base_cols]
    differing = OrderedDict()
    for n in base:
        if n in new:
            for c in cols:
                if c == "name":
                    continue
                for lab, a, b, kind in row_changes(c, base[n].get(c, ""), new[n].get(c, ""), ignore):
                    {"changed": changed, "added": plus, "n/a": na}[kind].append((n, lab, a, b))
                    if kind == "changed":
                        differing.setdefault(n, 0)
                        differing[n] += 1
    present = len(base) - len(missing)
    out.append("== %s: baseline %d, new %d ==" % (label, len(base), len(new)))
    out.append("removed (in baseline, missing from new): %d" % len(missing))
    for n in missing:
        low = [m for m in new if m.lower() == n.lower()]
        out.append("  - %s%s" % (n, "  (the new set has %r: names are case-sensitive)" % low[0] if low else ""))
    if only is None:
        out.append("added (new only): %d" % len(added))
        if detail:
            for n in added:
                out.append("  + %s" % n)
    out.append("changed values: %d in %d row(s)" % (len(changed), len(differing)))
    if changed and detail:
        w1 = max(len(c[0]) for c in changed)
        w2 = max(len(c[1]) for c in changed)
        out.append("  %-*s  %-*s  %s" % (w1, label[:-1].lower(), w2, "field", "baseline -> new"))
        for n, c, a, b in changed:
            out.append("  %-*s  %-*s  %r -> %r" % (w1, n, w2, c, a, b))
    out.append("keys only the port has (extras / terrain_speeds, not counted as changes): %d" % len(plus))
    if plus and detail:
        for n, c, a, b in plus:
            out.append("  + %s  %s = %r" % (n, c, b))
    out.append("not comparable (no modern counterpart): %d value(s)" % len(na))
    out.append("")
    if stats is not None:
        percol = OrderedDict()
        for n, c, a, b in changed:
            percol[c] = percol.get(c, 0) + 1
        stats.update(baseline=len(base), present=present, missing=len(missing), differing=len(differing),
                     identical=present - len(differing), added=len(added), changed_values=len(changed), port_only_keys=len(plus),
                     percol=percol, not_comparable=len(na), missing_names=missing)
    return len(missing)


def compare_sets(args_paths, ignore=(), only=None, detail=True):
    """Returns (report text lines, missing count, stats dict)."""
    ac, ar = read_csv(args_paths[0])
    wc, wr = read_csv(args_paths[1])
    nac, nar = read_csv(args_paths[2])
    nwc, nwr = read_csv(args_paths[3])
    out = []
    st = {}
    st["actors"], st["templates"], st["weapons"] = {}, {}, {}
    m = 0
    kinds = {"actors": "actor", "templates": "template"}
    for key, kind in kinds.items():
        sub = OrderedDict((n, r) for n, r in ar.items() if r.get("kind", "actor") == kind
                          and (only is None or n in only))
        if kind == "template" and not sub:
            continue
        if kind == "actor":
            nsub = OrderedDict((n, r) for n, r in nar.items() if r.get("kind", "actor") == "actor")
            m += diff_sets("Actors", ac, sub, nac, nsub, out, ignore, only, detail, st[key])
        else:
            nsub = OrderedDict((n, r) for n, r in nar.items() if r.get("kind") == "template")
            m += diff_sets("Templates", ac, sub, nac, nsub, out, ignore, only, detail, st[key])
    m += diff_sets("Weapons", wc, wr, nwc, nwr, out, ignore, only, detail, st["weapons"])
    return out, m, st


def summary_lines(st):
    lines = ["== headline =="]
    for key, title in (("actors", "actors"), ("templates", "templates"), ("weapons", "weapons")):
        s = st.get(key)
        if not s:
            continue
        lines.append("%-9s baseline %3d | present %3d | missing %3d | present and differing %3d | present and identical %3d" % (
            title, s["baseline"], s["present"], s["missing"], s["differing"], s["identical"]))
    for key in ("actors", "templates", "weapons"):
        s = st.get(key)
        if s and s["percol"]:
            lines.append("differing values per column, %s (a value, not a row; extras and terrain_speeds are per key):" % key)
            for c, n in sorted(s["percol"].items(), key=lambda kv: (-kv[1], kv[0])):
                lines.append("  %-34s %d" % (c, n))
    return lines


def cmd_compare(args):
    spec = {"--ignore": "value", "--only": "value", "--summary": "flag"}
    try:
        o, pos = parse_opts(args, spec)
    except ValueError as e:
        print("ERROR: %s" % e)
        return 2
    if len(pos) != 4:
        print(__doc__)
        return 2
    ignore = set(x for x in o.get("--ignore", "").split(",") if x)
    only = set(read_name_list(o["--only"])) if "--only" in o else None
    out, m, st = compare_sets(pos, ignore, only, detail="--summary" not in o)
    print("\n".join(out))
    print("\n".join(summary_lines(st)))
    if m:
        print("FAIL: %d baseline actor(s)/weapon(s) missing from the new set" % m)
        return 1
    print("OK: nothing from the baseline is missing")
    return 0


def cmd_check(args):
    """check NAME... [--list FILE] [--actors A,B] [--weapons W,V] [--repo R] [--engine E] [--ignore COLS]
    Runs port for just those names, then compares them with the frozen baseline."""
    spec = {"--list": "value", "--actors": "value", "--weapons": "value", "--repo": "value", "--engine": "value",
            "--ignore": "value", "--jobs": "value", "--no-cache": "flag", "--out-dir": "value", "--baseline-dir": "value",
            "--summary": "flag"}
    try:
        o, pos = parse_opts(args, spec)
    except ValueError as e:
        print("ERROR: %s" % e)
        return 2
    here = os.path.dirname(os.path.abspath(__file__))
    bdir = o.get("--baseline-dir", here)
    ba_cols, ba = read_csv(os.path.join(bdir, "baseline-0.32-actors.csv"))
    bw_cols, bw = read_csv(os.path.join(bdir, "baseline-0.32-weapons.csv"))
    names = list(pos)
    if "--list" in o:
        names += read_name_list(o["--list"])
    a_names = [n for n in o.get("--actors", "").split(",") if n] + [n for n in names if n in ba]
    w_names = [n for n in o.get("--weapons", "").split(",") if n] + [n for n in names if n in bw]
    unknown = [n for n in names if n not in ba and n not in bw]
    unknown += [n for n in o.get("--actors", "").split(",") if n and n not in ba]
    unknown += [n for n in o.get("--weapons", "").split(",") if n and n not in bw]
    if unknown:
        print("ERROR: not in the baseline (names are case-sensitive): %s" % ", ".join(sorted(set(unknown))))
        return 2
    if not a_names and not w_names:
        print("ERROR: no names given (use NAME..., --list FILE, --actors or --weapons)")
        return 2
    repo = os.path.abspath(o.get("--repo", default_repo()))
    engine = os.path.abspath(o.get("--engine", os.path.join(repo, "engine")))
    out_dir = o.get("--out-dir") or tempfile.mkdtemp(prefix="tfc-check-")
    try:
        arows, wcols, wrows, errors, st = extract_port(repo, engine, a_names, w_names, int(o.get("--jobs", 4)),
                                                       "--no-cache" not in o)
    except (OSError, ParseError) as e:
        print("ERROR: %s" % e)
        return 2
    os.makedirs(out_dir, exist_ok=True)
    ap, wp = os.path.join(out_dir, "port-actors.csv"), os.path.join(out_dir, "port-weapons.csv")
    write_csv(ap, ACTOR_COLUMNS, arows)
    write_csv(wp, wcols, wrows)
    ignore = set(x for x in o.get("--ignore", ",".join(DEFAULT_IGNORE)).split(",") if x)
    out, m, cst = compare_sets([os.path.join(bdir, "baseline-0.32-actors.csv"),
                                os.path.join(bdir, "baseline-0.32-weapons.csv"), ap, wp],
                               ignore, set(a_names) | set(w_names), detail="--summary" not in o)
    print("\n".join(out))
    for k, e in errors.items():
        print("ERROR: engine could not resolve %s: %s" % (k, e))
    print("\n".join(summary_lines(cst)))
    if m or errors:
        print("FAIL: %d listed baseline name(s) missing from the port, %d engine error(s)" % (m, len(errors)))
        return 1
    print("OK: every listed name is present (values above are differences to the baseline, not failures)")
    return 0


# --------------------------------------------------------------------------


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[1], argv[2:]
    if cmd == "baseline":
        return cmd_baseline(rest)
    if cmd == "dump":
        return cmd_dump(rest)
    if cmd == "compare":
        return cmd_compare(rest)
    if cmd in ("port", "extract2025"):
        return cmd_port(rest)
    if cmd == "check":
        return cmd_check(rest)
    if cmd == "selftest":
        here = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, here)
        import test_tfc_stats
        return test_tfc_stats.run(rest)
    print("unknown command %r" % cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
