#!/usr/bin/env python3
"""tfc_stats.py - frozen-stats tool for The Forgotten Chapter (TFC).

Plain Python 3, standard library only.

Commands
  baseline MODDIR [--out-dir DIR] [--prefix NAME]
      Read a 2014-format (OpenRA release-20141029) mod folder, resolve the
      rules and weapons the way the engine does, and write two CSVs:
      <prefix>-actors.csv and <prefix>-weapons.csv (default prefix
      "baseline-0.32", default out dir = this script's folder).
  compare BASE_ACTORS BASE_WEAPONS NEW_ACTORS NEW_WEAPONS
      Print added / removed / changed rows and values. Exits 1 only if an
      actor or weapon present in the baseline is missing from the new set.
  selftest
      Run the built-in tests (they need the mod at commit ed02790 or the
      frozen CSVs; see tools/test_tfc_stats.py for the resolver checks).

How the 2014 engine resolves rules (re-implemented here, no engine source
was available, so this follows MiniYaml.cs of release-20141029 as known):
  * Files are read in the order mod.yaml lists them (section Rules, Weapons).
  * Inside one file, repeated keys at the same level are merged.
  * Across files, a later file's node with the same key overrides the
    earlier one field by field (children merged recursively, a non-empty
    value replaces the earlier value).
  * `Inherits: Parent` (also `Inherits@x`) is resolved recursively; parents
    are applied first, then the node's own children on top.
  * A child key `-Trait` (or `-Trait@Id`) removes that key from what was
    inherited.
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
    """Parse MiniYaml text into an ordered list of (key, Node) top level pairs,
    with repeated keys at one level merged (MergeSelfPartial)."""
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
        else:  # repeated key in the same file: merge
            if value is not None:
                node.value = value
        stack.append((depth, node))
    return root


def merge_into(base, over, apply_removals=False, warn=None, path=""):
    """Merge `over` on top of `base` (both Nodes). Mutates base.

    With apply_removals, a child key `-Key` (at any depth) removes `Key` from
    what has been accumulated so far and is itself dropped; otherwise `-Key`
    nodes are kept as literal keys (needed while files are merged, before
    inheritance is resolved)."""
    if over.value is not None:
        base.value = over.value
    for k, v in over.children.items():
        if apply_removals and k.startswith("-"):
            if warn is not None:
                if k[1:] in over.children:
                    warn("%s: defines %s and also %s (ambiguous)" % (path or "(top)", k[1:], k))
                if k[1:] not in base.children:
                    warn("%s: %s removes nothing" % (path or "(top)", k))
            base.children.pop(k[1:], None)
        elif k in base.children:
            merge_into(base.children[k], v, apply_removals, warn, path + "/" + k)
        else:
            c = Node(None)
            base.children[k] = c
            merge_into(c, v, apply_removals, warn, path + "/" + k)


def merge_files(nodes):
    out = Node()
    for n in nodes:
        merge_into(out, n)
    return out


class Resolver:
    def __init__(self, tree, what="actor"):
        self.tree = tree          # Node whose children are the definitions
        self.what = what
        self.resolved = {}
        self.warnings = []
        self.lower = {k.lower(): k for k in tree.children}

    def _find(self, name, who):
        if name in self.tree.children:
            return name
        alt = self.lower.get(name.lower())
        if alt:
            self.warnings.append("%s %s inherits %r: matched case-insensitively to %r" % (self.what, who, name, alt))
            return alt
        return None

    def resolve(self, name, _stack=()):
        if name in self.resolved:
            return self.resolved[name]
        if name in _stack:
            raise ParseError("Inherits cycle: %s" % " -> ".join(_stack + (name,)))
        node = self.tree.children[name]
        result = Node(node.value)
        own = OrderedDict()
        for k, v in node.children.items():
            if k == "Inherits" or k.startswith("Inherits@"):
                parent = v.value
                pk = self._find(parent, name) if parent else None
                if pk is None:
                    raise ParseError("unresolved Inherits: %s -> %s" % (name, parent))
                merge_into(result, self.resolve(pk, _stack + (name,)))
            else:
                own[k] = v
        own_node = Node(None, own)
        merge_into(result, own_node, True, lambda m, n=name: self.warnings.append("%s %s %s" % (self.what, n, m)), "")
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
    r["terrain_speeds"] = ";".join(ts)
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
    r["weapons"] = ";".join(uniq(arm))
    other = []
    for tk, t in defn.children.items():
        if tk == "Armament" or tk.startswith("Armament@"):
            continue
        for fn in ("Weapon", "EmptyWeapon"):
            if fn in t.children and t.children[fn].value:
                other.append(t.children[fn].value)
    r["other_weapons"] = ";".join(uniq(other))
    r["inherits"] = ";".join(v.value for k, v in raw_node.children.items()
                             if (k == "Inherits" or k.startswith("Inherits@")) and v.value)
    r["traits"] = ";".join(defn.children.keys())
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
    r["extras"] = ";".join(ex)
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
    wres = Resolver(wtree, "weapon")
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
# compare command
# --------------------------------------------------------------------------


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        rows = OrderedDict((r["name"], r) for r in rd)
        return rd.fieldnames, rows


def diff_sets(label, base_cols, base, new_cols, new, out):
    missing = [n for n in base if n not in new]
    added = [n for n in new if n not in base]
    changed = []
    cols = list(base_cols) + [c for c in new_cols if c not in base_cols]
    for n in base:
        if n in new:
            for c in cols:
                if c == "name":
                    continue
                a, b = base[n].get(c, ""), new[n].get(c, "")
                if a != b:
                    changed.append((n, c, a, b))
    out.append("== %s: baseline %d, new %d ==" % (label, len(base), len(new)))
    out.append("removed (in baseline, missing from new): %d" % len(missing))
    for n in missing:
        out.append("  - %s" % n)
    out.append("added (new only): %d" % len(added))
    for n in added:
        out.append("  + %s" % n)
    out.append("changed values: %d" % len(changed))
    if changed:
        w1 = max(len(c[0]) for c in changed)
        w2 = max(len(c[1]) for c in changed)
        out.append("  %-*s  %-*s  %s" % (w1, label[:-1].lower(), w2, "field", "baseline -> new"))
        for n, c, a, b in changed:
            out.append("  %-*s  %-*s  %r -> %r" % (w1, n, w2, c, a, b))
    out.append("")
    return len(missing)


def cmd_compare(args):
    if len(args) != 4:
        print(__doc__)
        return 2
    ac, ar = read_csv(args[0])
    wc, wr = read_csv(args[1])
    nac, nar = read_csv(args[2])
    nwc, nwr = read_csv(args[3])
    out = []
    m = diff_sets("Actors", ac, ar, nac, nar, out)
    m += diff_sets("Weapons", wc, wr, nwc, nwr, out)
    print("\n".join(out))
    if m:
        print("FAIL: %d baseline actor(s)/weapon(s) missing from the new set" % m)
        return 1
    print("OK: nothing from the baseline is missing")
    return 0


# --------------------------------------------------------------------------


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[1], argv[2:]
    if cmd == "baseline":
        return cmd_baseline(rest)
    if cmd == "compare":
        return cmd_compare(rest)
    if cmd == "selftest":
        here = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, here)
        import test_tfc_stats
        return test_tfc_stats.run(rest)
    print("unknown command %r" % cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
