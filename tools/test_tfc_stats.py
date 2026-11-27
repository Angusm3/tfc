#!/usr/bin/env python3
"""Self-test for tfc_stats.py. Run:  python tools/tfc_stats.py selftest [MODDIR]
(or python tools/test_tfc_stats.py [MODDIR]).

MODDIR is a 2014-format mod folder (the one holding mod.yaml); default is the
repo root. Every expected value below was read by hand from the YAML at commit
ed02790, not copied from the script output.
"""
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tfc_stats as T  # noqa: E402

MODDIR = os.path.dirname(HERE)
B = None  # built mod, shared by all tests


def actor(n):
    return next(r for r in B["actor_rows"] if r["name"] == n)


def weapon(n):
    return next(r for r in B["weapon_rows"] if r["name"] == n)


def has_trait(n, trait):
    return any(k == trait or k.startswith(trait + "@") for k in B["actors"][n].children)


class ActorTests(unittest.TestCase):
    def check(self, name, **exp):
        a = actor(name)
        for k, v in exp.items():
            self.assertEqual(a[k], v, "%s.%s" % (name, k))

    def test_E1_gdi_single_inherit(self):  # gdi army.yaml E1 on ^Infantry (defaults.yaml)
        self.check("E1", cost="100", hp="50", armor="None", speed="56", sight_range="5c0",
                   weapons="M16", queue="Infantry.GDI, Infantry.Nod", build_palette_order="10", buildable="yes")

    def test_RMBO_earlier_file_wins(self):
        # rules/infantry.yaml is listed BEFORE the gdi army.yaml, so its Cost 0, HP 500, ScanRadius 5 win;
        # the gdi file only fills gaps: its Queue fills infantry.yaml's empty Queue, Prerequisites is new.
        self.check("RMBO", cost="0", hp="500", speed="71", sight_range="6c0", queue="Infantry.GDI",
                   prerequisites="eye, ~techlevel.high", weapons="Sniper")
        self.assertIn("AutoTarget.ScanRadius=5", actor("RMBO")["extras"])
        self.assertIn("Buildable.BuildLimit=1", actor("RMBO")["extras"])
        self.assertEqual(actor("RMBO")["source"], "rules/infantry.yaml+factions/gdi/rules/army.yaml")

    def test_MTNK_gdi_tank(self):
        self.check("MTNK", cost="800", hp="450", armor="Heavy", speed="85", rot="5", sight_range="6c0",
                   weapons="120mm", prerequisites="anyhq, ~techlevel.medium", queue="Vehicle.GDI")

    def test_ORCA_and_TRAN_aircraft(self):
        self.check("ORCA", cost="1200", hp="90", armor="Light", speed="186", rot="4", sight_range="10c0",
                   weapons="OrcaAAMissiles;OrcaAGMissiles", locomotor="Helicopter", queue="Aircraft.GDI")
        self.check("TRAN", cost="750", hp="90", armor="Light", speed="140", rot="5", weapons="",
                   other_weapons="HeliExplode", queue="Aircraft.GDI, Aircraft.Nod, Aircraft.Forgotten")

    def test_LTNK_nod(self):
        self.check("LTNK", cost="600", hp="360", armor="Heavy", speed="113", rot="7", sight_range="6c0",
                   weapons="70mm", queue="Vehicle.Nod")

    def test_SPC_nested_removal_and_lowercase_armor(self):  # nod army.yaml: Cloak: -RequiresUpgrade, Type: light
        self.check("SPC", cost="600", hp="150", armor="light", speed="128", rot="8", sight_range="7c0")
        cloak = B["actors"]["SPC"].children["Cloak"]
        self.assertNotIn("RequiresUpgrade", cloak.children)
        self.assertIn("-RequiresUpgrade", cloak.children)  # inert leftover, exactly as the engine keeps it
        self.assertEqual(cloak.children["InitialDelay"].value, "90")
        self.assertIn("RequiresUpgrade", B["actors"]["^Tank"].children["Cloak"].children)  # parent untouched

    def test_militia_tfa(self):
        self.check("militia", cost="80", hp="50", armor="None", speed="71", sight_range="6c0",
                   weapons="SKS", queue="Infantry.Forgotten", build_palette_order="10")

    def test_HUEY_tfa_owner(self):
        self.check("HUEY", cost="1200", hp="100", armor="Light", speed="140", rot="5", sight_range="10c0",
                   weapons="Hrockets", faction_owner="forgotten", prerequisites="anyhq")

    def test_sniperD_four_level_chain_with_minus_Buildable(self):
        # sniperD -> sniper -> ^ForgottenInfantry -> ^Infantry
        self.check("sniperD", cost="0", hp="1000", speed="28", sight_range="12c0", weapons="Scout2",
                   armor="None", buildable="no", inherits="sniper")
        self.check("sniper", hp="500", speed="99", sight_range="6c0", weapons="Scout", buildable="yes")
        self.assertEqual(B["actors"]["sniperD"].children["Cloak"].children["InitialDelay"].value, "0")

    def test_APC_E1_three_level(self):  # APC.E1 -> APC -> ^Tank, with -Buildable
        self.check("APC", cost="600", hp="200", armor="Heavy", speed="128", rot="8", sight_range="7c0",
                   weapons="APCGun;APCGun.AA", queue="Vehicle.GDI", prerequisites="pyle")
        self.check("APC.E1", cost="600", hp="200", speed="128", buildable="no", inherits="APC")
        self.assertEqual(actor("APC.E1")["weapons"], "APCGun;APCGun.AA;M16")

    def test_C1_civilian_removal(self):  # C1 -> ^CivInfantry (-AutoTarget -TakeCover) -> ^Infantry
        self.check("C1", cost="70", hp="25", speed="56", sight_range="2c0", weapons="Pistol", armor="None",
                   buildable="no")
        self.assertTrue(has_trait("^Infantry", "AutoTarget"))
        self.assertTrue(has_trait("^Infantry", "TakeCover"))
        self.assertFalse(has_trait("^CivInfantry", "AutoTarget"))
        self.assertFalse(has_trait("C1", "AutoTarget"))
        self.assertFalse(has_trait("C1", "TakeCover"))

    def test_TREX_dino_template(self):  # infantryV.yaml TREX -> ^DINO (defaults.yaml)
        self.check("TREX", cost="1000", hp="1000", armor="Wood", speed="113", sight_range="6c0",
                   weapons="teeth", queue="Biolab")

    def test_FACT_PROC_structures(self):
        self.check("FACT", cost="2000", hp="1400", armor="Wood")
        self.check("PROC", cost="1500", hp="900", power_drain="-50")


class WeaponTests(unittest.TestCase):
    def check(self, name, **exp):
        w = weapon(name)
        for k, v in exp.items():
            self.assertEqual(w[k], v, "%s.%s" % (name, k))

    def test_Sniper_weapons_over_weaponsV(self):  # weapons.yaml is first so it wins; weaponsV only adds ValidTargets
        self.check("Sniper", range="10c0", reload_delay="15", damage="150", spread="256",
                   valid_targets="Infantry", vs_None="100", vs_Wood="5", vs_Light="100", vs_Heavy="20",
                   vs_Concrete="", projectile="Bullet", projectile_speed="1c682", source="weapons.yaml+weaponsV.yaml")

    def test_Heal_first_file_wins(self):
        self.check("Heal", range="4c0", reload_delay="80", damage="-50", spread="213", vs_None="",
                   vs_Wood="0", vs_Light="0", vs_Heavy="0", vs_Concrete="0")

    def test_120mm_first_file_wins_and_extra_warheads_added(self):
        # reload 50 and Versus None 30 / Wood 75 from weapons.yaml; weaponsV.yaml adds Warhead@2Smu and @3Eff
        self.check("120mm", range="4c768", reload_delay="50", damage="40", spread="128", projectile_speed="682",
                   vs_None="30", vs_Wood="75", vs_Light="100", vs_Heavy="100", vs_Concrete="50", warhead_count="3")

    def test_Vulcan_tfc_values(self):  # weapons.yaml (TFC) first: ReloadDelay 40, not weaponsV's 2
        self.check("Vulcan", burst="3", reload_delay="40", range="5c0", damage="10", spread="128",
                   valid_targets="Ground", vs_None="100", vs_Wood="20", vs_Light="20", vs_Heavy="10",
                   vs_Concrete="0")

    def test_Tail_projectile_speed_from_V(self):
        self.check("Tail", range="1c0", reload_delay="30", damage="180", spread="213", projectile_speed="1c682",
                   vs_None="90", vs_Wood="10", vs_Light="30", vs_Heavy="10", vs_Concrete="10")

    def test_Colt45_weapons_only(self):
        self.check("Colt45", range="7c0", reload_delay="5", damage="50", spread="42", source="weapons.yaml",
                   vs_None="100", vs_Wood="0", vs_Light="0", vs_Heavy="0", vs_Concrete="0")

    def test_P90_valid_targets(self):
        self.check("P90", range="7c0", reload_delay="8", damage="100", valid_targets="Ground")

    def test_Tiberium_first_file_wins(self):
        self.check("Tiberium", reload_delay="4", damage="1", spread="42", death_type="6")

    def test_nested_Warhead_effects_are_not_warheads(self):
        # Colt45: Warhead@2Eff sits inside Warhead@1Dam, so the engine (top-level Warhead* only) never sees it.
        self.assertEqual(weapon("Colt45")["warhead_count"], "1")
        self.assertIn("NESTED(Warhead@2Eff in Warhead@1Dam)", weapon("Colt45")["warhead_other"])


class ResolverTests(unittest.TestCase):
    def test_counts(self):
        kinds = [r["kind"] for r in B["actor_rows"]]
        self.assertEqual((kinds.count("actor"), kinds.count("template")), (273, 25))
        self.assertEqual(len(B["weapon_rows"]), 100)

    def test_no_unknown_weapon_references(self):
        self.assertEqual(B["problems"], [])

    def test_removal_is_scoped_to_the_resolved_actor(self):
        tree = T.parse_text("^P:\n\tA:\n\t\tX: 1\n\tB:\n\t\tY: 2\nC:\n\tInherits: ^P\n\t-A:\n\tB:\n\t\t-Y:\n\t\tZ: 3\n")
        r = T.Resolver(tree).resolve_all()
        self.assertEqual(list(r["C"].children), ["Inherits", "B"])
        self.assertEqual(list(r["C"].children["B"].children), ["-Y", "Z"])  # Y gone, inert -Y left (engine behaviour)
        self.assertEqual(list(r["^P"].children), ["A", "B"])

    def test_unresolved_inherits_is_an_error(self):
        for src in ("A:\n\tInherits: ^Nope\n", "^P:\n\tX:\n\nA:\n\tInherits: ^p\n"):  # missing, wrong case
            with self.assertRaises(T.ParseError):
                T.Resolver(T.parse_text(src)).resolve_all()

    def test_removing_something_that_does_not_exist_is_an_engine_error(self):
        tree = T.parse_text("P:\n\tX:\nC:\n\tInherits: P\n\t-Nope:\n")
        with self.assertRaises(T.ParseError):
            T.Resolver(tree).resolve_all()

    def test_duplicate_keys_in_one_file_are_an_error(self):
        with self.assertRaises(T.ParseError):
            T.parse_text("W:\n\tR: 1\nW:\n\tS: 2\n")


# The tiny files below are the ones run through the real OpenRA.Game.exe (probe1.cs / probe2.cs, see
# CONTRIBUTING.md); the expected values are the engine's own output.
PROBE_TFC = ("Vulcan:\n\tReloadDelay: 40\n\tBurst: 3\n\tWarhead@1Dam: SpreadDamage\n\t\tDamage: 10\n"
             "\t\tVersus:\n\t\t\tNone: 100\n\t\t\tConcrete: 0\n")
PROBE_STOCK = ("Vulcan:\n\tReloadDelay: 2\n\tRange: 6c0\n\tWarhead@1Dam: SpreadDamage\n\t\tDamage: 100\n"
               "\t\tVersus:\n\t\t\tNone: 50\n\t\t\tHeavy: 35\nOnlyStock:\n\tRange: 1c0\n")
PROBE_PARENT = ("P:\n\tHealth:\n\t\tHP: 10\n\t\tRadius: 5\n\tCloak:\n\t\tReq: cloak\n\t\tDelay: 90\n"
                "\tFoo:\n\t\tX: 1\n\tFoo@2:\n\t\tX: 2\n")


def flat(node):
    return T.flat_lines(node, 0)


class EnginePrecedenceTests(unittest.TestCase):
    """Pins the merge rules that were proven against the real 2014 engine."""

    def test_earlier_file_wins_and_nested_children_merge(self):
        # engine: MergeLiberal(tfc, stock) => ReloadDelay 40 (first file), Range 6c0 added, Versus merged
        m = T.merge_files([T.parse_text(PROBE_TFC), T.parse_text(PROBE_STOCK)])
        self.assertEqual(flat(m.children["Vulcan"]), [
            "ReloadDelay: 40", "Burst: 3", "Warhead@1Dam: SpreadDamage", "\tDamage: 10", "\tVersus: <null>",
            "\t\tNone: 100", "\t\tConcrete: 0", "\t\tHeavy: 35", "Range: 6c0"])
        self.assertEqual(list(m.children), ["Vulcan", "OnlyStock"])

    def test_listing_order_decides(self):
        # engine: MergeLiberal(stock, tfc) => ReloadDelay 2 (first file is now stock), Burst 3 added
        m = T.merge_files([T.parse_text(PROBE_STOCK), T.parse_text(PROBE_TFC)])
        self.assertEqual(flat(m.children["Vulcan"]), [
            "ReloadDelay: 2", "Range: 6c0", "Warhead@1Dam: SpreadDamage", "\tDamage: 100", "\tVersus: <null>",
            "\t\tNone: 50", "\t\tHeavy: 35", "\t\tConcrete: 0", "Burst: 3"])

    def test_empty_value_is_filled_from_later_file_but_not_the_reverse(self):
        m = T.merge_files([T.parse_text("U:\n\tCost:\n\tX: 1\n"), T.parse_text("U:\n\tCost: 7\n")])
        self.assertEqual(m.children["U"].children["Cost"].value, "7")
        m = T.merge_files([T.parse_text("U:\n\tCost: 5\n"), T.parse_text("U:\n\tCost:\n")])
        self.assertEqual(m.children["U"].children["Cost"].value, "5")

    def test_removals_across_files_and_inheritance(self):
        # engine: earlier file defines Foo, later file says -Foo -Bar: Foo is removed even though C defined it itself
        f1 = T.parse_text("P:\n\tFoo:\n\t\tX: 1\n\tBar:\n\t\tY: 1\nC:\n\tInherits: P\n\tFoo:\n\t\tX: 9\n")
        f2 = T.parse_text("C:\n\t-Foo:\n\t-Bar:\n")
        for order in ((f1, f2), (f2, f1)):
            r = T.Resolver(T.merge_files(list(order))).resolve_all()
            self.assertEqual(flat(r["C"]), ["Inherits: P"])

    def _inherit(self, text, child="C"):
        return flat(T.Resolver(T.parse_text(PROBE_PARENT + text)).resolve_all()[child])

    def test_inherit_child_wins_removes_and_orders(self):
        self.assertEqual(self._inherit("C:\n\tInherits: P\n\tHealth:\n\t\tHP: 99\n\t-Foo:\n\tCloak:\n\t\t-Req:\n"),
                         ["Inherits: P", "Health: <null>", "\tHP: 99", "\tRadius: 5", "Cloak: <null>",
                          "\t-Req: <null>", "\tDelay: 90", "Foo@2: <null>", "\tX: 2"])

    def test_inherit_own_definition_and_removal_of_same_key_removes_it(self):
        want = ["Inherits: P", "Health: <null>", "\tHP: 10", "\tRadius: 5", "Cloak: <null>", "\tReq: cloak",
                "\tDelay: 90", "Foo@2: <null>", "\tX: 2"]
        self.assertEqual(self._inherit("C:\n\tInherits: P\n\tFoo:\n\t\tX: 5\n\t-Foo:\n"), want)
        self.assertEqual(self._inherit("C:\n\tInherits: P\n\t-Foo:\n\tFoo:\n\t\tX: 5\n"), want)

    def test_inherit_suffixed_removal_and_empty_value(self):
        out = self._inherit("C:\n\tInherits: P\n\t-Foo@2:\n")
        self.assertIn("Foo: <null>", out)
        self.assertNotIn("Foo@2: <null>", out)
        out = self._inherit("C:\n\tInherits: P\n\tHealth:\n\t\tHP:\n")
        self.assertIn("\tHP: 10", out)  # an empty child value does not blank the parent

    def test_inherit_three_levels_and_suffixed_Inherits_ignored(self):
        out = self._inherit("M:\n\tInherits: P\n\t-Foo:\n\t-Health:\n\nC:\n\tInherits: M\n\tHealth:\n\t\tHP: 1\n")
        self.assertEqual(out, ["Inherits: M", "Health: <null>", "\tHP: 1", "Cloak: <null>", "\tReq: cloak",
                               "\tDelay: 90", "Foo@2: <null>", "\tX: 2"])
        self.assertEqual(self._inherit("C:\n\tInherits@1: P\n\tHealth:\n\t\tHP: 99\n"),
                         ["Inherits@1: P", "Health: <null>", "\tHP: 99"])


class CsvAndCompareTests(unittest.TestCase):
    def test_frozen_csv_matches_regeneration(self):
        frozen_a = os.path.join(HERE, "baseline-0.32-actors.csv")
        frozen_w = os.path.join(HERE, "baseline-0.32-weapons.csv")
        if not (os.path.isfile(frozen_a) and os.path.isfile(frozen_w)):
            self.skipTest("frozen CSVs not present")
        with tempfile.TemporaryDirectory() as d:
            T.write_csv(os.path.join(d, "a.csv"), T.ACTOR_COLUMNS, B["actor_rows"])
            T.write_csv(os.path.join(d, "w.csv"), B["weapon_cols"], B["weapon_rows"])
            with open(os.path.join(d, "a.csv"), "rb") as f1, open(frozen_a, "rb") as f2:
                self.assertEqual(f1.read().replace(b"\r\n", b"\n"), f2.read().replace(b"\r\n", b"\n"))
            with open(os.path.join(d, "w.csv"), "rb") as f1, open(frozen_w, "rb") as f2:
                self.assertEqual(f1.read().replace(b"\r\n", b"\n"), f2.read().replace(b"\r\n", b"\n"))

    def test_compare_fails_only_on_missing(self):
        with tempfile.TemporaryDirectory() as d:
            T.write_csv(os.path.join(d, "a.csv"), T.ACTOR_COLUMNS, B["actor_rows"])
            T.write_csv(os.path.join(d, "w.csv"), B["weapon_cols"], B["weapon_rows"])
            args = [os.path.join(d, "a.csv"), os.path.join(d, "w.csv")]
            changed = [dict(r) for r in B["actor_rows"]]
            changed[0]["hp"] = "99999"
            T.write_csv(os.path.join(d, "a2.csv"), T.ACTOR_COLUMNS, changed)
            T.write_csv(os.path.join(d, "a3.csv"), T.ACTOR_COLUMNS, changed[1:])
            old = sys.stdout
            sys.stdout = io.StringIO()
            try:
                self.assertEqual(T.cmd_compare(args + args), 0)
                self.assertEqual(T.cmd_compare(args + [os.path.join(d, "a2.csv"), args[1]]), 0)  # value change
                self.assertEqual(T.cmd_compare(args + [os.path.join(d, "a3.csv"), args[1]]), 1)  # missing actor
            finally:
                sys.stdout = old



# ==========================================================================
# The port side (20250330): conversions, extractor, compare options, check
# ==========================================================================
import csv  # noqa: E402
import shutil  # noqa: E402

REPO = os.path.dirname(HERE)
ENGINE = os.path.join(REPO, "engine")
HAVE_ENGINE = T.engine_command(ENGINE) is not None and os.path.isfile(os.path.join(REPO, "mods", "tfc", "mod.yaml"))
NEED_ENGINE = "engine not built (run make.cmd all): skipping the engine-backed tests"
BASE_A = os.path.join(HERE, "baseline-0.32-actors.csv")
BASE_W = os.path.join(HERE, "baseline-0.32-weapons.csv")


def quiet(fn, *a, **k):
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        rc = fn(*a, **k)
        return rc, sys.stdout.getvalue()
    finally:
        sys.stdout = old


def od(d):
    return T.OrderedDict(d)


class ConversionTests(unittest.TestCase):
    def test_divide_and_fmt(self):
        self.assertEqual(T.divide("5000", 100), "50")
        self.assertEqual(T.divide("-5000", 100), "-50")
        self.assertEqual(T.divide("1023", 4), "255.75")
        self.assertEqual(T.divide("20", 4), "5")
        self.assertEqual(T.divide("60", 100), "0.6")
        self.assertEqual(T.divide("150", 100), "1.5")
        self.assertEqual(T.divide("", 100), "")
        self.assertEqual(T.divide(None, 4), "")
        self.assertEqual(T.divide("abc", 4), "<bad:abc>")

    def test_wdist_written_the_way_the_baseline_writes_it(self):
        self.assertEqual(T.wdist("4c768"), "4c768")
        self.assertEqual(T.wdist("5c0"), "5c0")
        self.assertEqual(T.wdist("5120"), "5c0")      # a bare integer is a WDist
        self.assertEqual(T.wdist("0c512"), "512")     # below one cell: a plain integer
        self.assertEqual(T.wdist("1c682"), "1c682")
        self.assertEqual(T.wdist("213"), "213")
        self.assertEqual(T.wdist(""), "")

    def test_every_baseline_wdist_cell_is_already_canonical(self):
        # the canonical form must reproduce the baseline's own spelling, or compare would invent differences
        with open(BASE_W, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for col in ("range", "min_range", "spread", "projectile_speed", "projectile_inaccuracy"):
            for r in rows:
                self.assertEqual(T.wdist(r[col]), r[col], "%s.%s" % (r["name"], col))

    def test_cells_or_wdist(self):
        self.assertEqual(T.cells_or_wdist("2c0"), "2")
        self.assertEqual(T.cells_or_wdist("2c512"), "2c512")

    def test_death_names_follow_the_design_note_table(self):
        self.assertEqual([T.DEATH_TYPES[n] for n in ("BulletDeath", "RippedApartDeath", "SmallExplosionDeath",
                                                       "ExplosionDeath", "FireDeath", "TiberiumDeath")],
                         ["1", "2", "3", "4", "5", "6"])
        self.assertEqual(T.DEATH_TYPES["DefaultDeath"], "1")


STOCK_WORLD = (
    "Locomotor@TRACKED:\n\tName: tracked\n\tCrushes: wall, crate, infantry\n\tTerrainSpeeds:\n\t\tClear: 80\n\t\tRough: 70\n"
    "\t\tRoad: 100\n\t\tBridge: 100\n\t\tTiberium: 70\n\t\t\tPathingCost: 300\n\t\tBeach: 70\n"
    "Locomotor@NAVAL:\n\tName: naval\n\tTerrainSpeeds:\n\t\tWater: 100\n")
STOCK_MTNK = (
    "Tooltip:\n\tGenericName: meta-tank\n\tName: actor-mtnk.name\n"
    "Mobile:\n\tLocomotor: tracked\n\tTurnSpeed: 20\n\tSpeed: 85\n"
    "Valued:\n\tCost: 800\nBuildable:\n\tBuildDuration: -1\n\tBuildDurationModifier: 60\n\tQueue: Vehicle.GDI\n"
    "\tPrerequisites: anyhq, ~techlevel.medium\n\tBuildPaletteOrder: 40\n"
    "Health:\n\tHP: 45000\nArmor:\n\tType: Heavy\nRevealsShroud:\n\tRange: 6c0\n"
    "Turreted:\n\tTurnSpeed: 20\n\tInitialFacing: 200\n"
    "Armament:\n\tWeapon: 120mm\nFireWarheadsOnDeath:\n\tWeapon: UnitExplodeSmall\n\tEmptyWeapon: UnitExplodeSmall\n"
    "SpawnActorOnDeath:\n\tActor: MTNK.Husk\nSpawnActorOnDeath@VICE:\n\tProbability: 5\n\tActor: vice\n"
    "ChangesHealth@ELITE:\n\tStep: 200\n\tDelay: 100\n\tRequiresCondition: rank-elite\n"
    "ProductionQueue@A:\n\tType: Vehicle.GDI\n\tLowPowerModifier: 200\n"
    "ProductionQueue@B:\n\tType: Vehicle.Nod\n\tBuildDurationModifier: 150\n")
STOCK_ORCA = ("Aircraft:\n\tCanHover: True\n\tVTOL: true\n\tTurnSpeed: 28\n\tSpeed: 186\n"
              "AttackAircraft:\n\tFacingTolerance: 80\nRepairable:\n\tRepairActors: hpad\nRearmable:\n\tRearmActors: hpad\n"
              "AmmoPool:\n\tAmmo: 6\nReloadAmmoPool:\n\tDelay: 100\n\tCount: 2\n")
STOCK_120MM = (
    "ReloadDelay: 40\nRange: 4c768\nProjectile: Bullet\n\tImage: 120MM\n\tSpeed: 682\n\tInaccuracy: 813\n"
    "Warhead@1Dam: SpreadDamage\n\tSpread: 128\n\tDamage: 4000\n\tVersus:\n\t\tNone: 25\n\t\tHeavy: 100\n"
    "\tDamageTypes: Prone50Percent, TriggerProne, ExplosionDeath\n"
    "Warhead@3Eff: CreateEffect\n\tExplosions: small_frag\n"
    "BurstDelays: 15, 20\nBurst: 2\nMinRange: 0\n")


class PortRowTests(unittest.TestCase):
    """port_actor_row / port_weapon_rows on small hand-written resolved text (no engine). The expected values were
    worked out by hand from the conversion table."""

    @classmethod
    def setUpClass(cls):
        cls.locos = T.world_locomotors(T.parse_text(STOCK_WORLD))
        cls.msgs = {"actor-mtnk": {"": "", "attrs": {"name": "Medium Tank"}}, "meta-tank": {"": "Tank", "attrs": {}}}
        cls.mtnk = T.port_actor_row("MTNK", T.parse_text(STOCK_MTNK), {"MTNK": ["rules/vehicles.yaml"]},
                                    {"MTNK": ["^Tank"]}, cls.locos, cls.msgs)
        cls.orca = T.port_actor_row("ORCA", T.parse_text(STOCK_ORCA), {}, {}, cls.locos, cls.msgs)

    def test_actor_numbers_are_back_in_2014_units(self):
        r = self.mtnk
        self.assertEqual((r["hp"], r["rot"], r["speed"], r["cost"], r["armor"], r["sight_range"]),
                         ("450", "5", "85", "800", "Heavy", "6c0"))
        self.assertEqual((r["tooltip"], r["kind"], r["buildable"], r["locomotor"]), ("Medium Tank", "actor", "yes", "Mobile"))
        self.assertEqual((r["queue"], r["prerequisites"], r["build_palette_order"]),
                         ("Vehicle.GDI", "anyhq, ~techlevel.medium", "40"))
        self.assertEqual(r["source"], "rules/vehicles.yaml")
        self.assertEqual(r["inherits"], "^Tank")

    def test_default_build_time_fields_are_empty_cells(self):
        self.assertEqual((self.mtnk["build_duration"], self.mtnk["build_duration_modifier"]), ("", ""))
        r = T.port_actor_row("X", T.parse_text("Buildable:\n\tBuildDuration: 2080\n\tBuildDurationModifier: 50\n"),
                             {}, {}, self.locos, self.msgs)
        # 2080 ticks-units x 50 percent = 1040 ticks; the 0.32 value for 1040 ticks is 1040 / 0.4 = 2600
        self.assertEqual((r["build_duration"], r["build_duration_modifier"]), ("2600", ""))

    def test_terrain_speeds_come_from_the_world_locomotor_and_drop_bridge(self):
        self.assertEqual(self.mtnk["terrain_speeds"],
                         "Beach=70;Clear=80;Road=100;Rough=70;Tiberium.PathingCost=300;Tiberium=70")
        self.assertIn("Mobile.Crushes=wall, crate, infantry", self.mtnk["extras"])

    def test_missing_locomotor_is_loud(self):
        r = T.port_actor_row("X", T.parse_text("Mobile:\n\tLocomotor: nope\n"), {}, {}, self.locos, self.msgs)
        self.assertEqual(r["terrain_speeds"], "<missing-locomotor:nope>")

    def test_extras_conversions(self):
        ex = T.split_items(self.mtnk["extras"])
        self.assertEqual(ex["Turreted.ROT"], "5")
        self.assertEqual(ex["Turreted.InitialFacing"], "50")
        self.assertEqual(ex["SelfHealing@ELITE.Step"], "2")
        self.assertEqual(ex["SelfHealing@ELITE.Ticks"], "100")
        self.assertEqual(ex["Explodes.Weapon"], "UnitExplodeSmall")
        self.assertEqual(ex["LeavesHusk.HuskActor"], "MTNK.Husk")   # the Probability one is the Vice mutation, skipped
        self.assertNotIn("LeavesHusk@VICE.HuskActor", ex)
        self.assertEqual(ex["Tooltip.GenericName"], "Tank")
        self.assertEqual(ex["ProductionQueue@A.LowPowerSlowdown"], "2")
        self.assertEqual(ex["ProductionQueue@A.BuildSpeed"], ".4")
        self.assertEqual(ex["ProductionQueue@B.LowPowerSlowdown"], "1")
        self.assertEqual(ex["ProductionQueue@B.BuildSpeed"], "BuildDurationModifier=150")
        self.assertEqual(self.mtnk["other_weapons"], "UnitExplodeSmall")

    def test_aircraft(self):
        r = self.orca
        self.assertEqual((r["locomotor"], r["rot"], r["speed"]), ("Helicopter", "7", "186"))
        ex = T.split_items(r["extras"])
        self.assertEqual(ex["AttackHeli.FacingTolerance"], "20")
        self.assertEqual((ex["Helicopter.RepairBuildings"], ex["Helicopter.RearmBuildings"]), ("hpad", "hpad"))
        self.assertEqual((ex["LimitedAmmo.Ammo"], ex["Reloads.Count"], ex["Reloads.Period"]), ("6", "2", "100"))
        plane = T.port_actor_row("P", T.parse_text("Aircraft:\n\tTurnSpeed: 20\n\tSpeed: 300\n"), {}, {}, self.locos, self.msgs)
        self.assertEqual(plane["locomotor"], "Plane")
        self.assertEqual(T.split_items(plane["extras"])["Plane.ROT"], "5")

    def test_unmapped_columns_carry_the_marker(self):
        self.assertEqual(self.mtnk["faction_owner"], T.MARKER)
        cols, rows = T.port_weapon_rows(od({"120mm": T.parse_text(STOCK_120MM)}), {"120mm": ["weapons/x.yaml"]})
        for c in ("charges", "projectile_other", "warhead_other"):
            self.assertEqual(rows[0][c], T.MARKER)

    def test_weapon_numbers_are_back_in_2014_units(self):
        cols, rows = T.port_weapon_rows(od({"120mm": T.parse_text(STOCK_120MM)}), {"120mm": ["weapons/x.yaml"]})
        r = rows[0]
        self.assertEqual((r["range"], r["reload_delay"], r["damage"], r["spread"], r["death_type"]),
                         ("4c768", "40", "40", "128", "4"))
        self.assertEqual((r["projectile"], r["projectile_speed"], r["projectile_inaccuracy"]), ("Bullet", "682", "813"))
        self.assertEqual((r["burst"], r["burst_delay"], r["min_range"]), ("2", "15", ""))   # first BurstDelays entry
        self.assertEqual((r["warhead_type"], r["warhead_count"], r["damaging_warheads"]), ("SpreadDamage", "2", "1"))
        self.assertEqual((r["vs_None"], r["vs_Heavy"]), ("25", "100"))
        self.assertEqual(r["source"], "weapons/x.yaml")

    def test_weapon_defaults_are_empty_cells(self):
        cols, rows = T.port_weapon_rows(od({"W": T.parse_text("Burst: 1\nMinRange: 0\n")}), {})
        self.assertEqual((rows[0]["burst"], rows[0]["min_range"]), ("", ""))


class FluentTests(unittest.TestCase):
    def test_later_file_wins_and_attributes_resolve(self):
        with tempfile.TemporaryDirectory() as d:
            repo, eng = os.path.join(d, "repo"), os.path.join(d, "engine")
            os.makedirs(os.path.join(repo, "mods", "tfc", "fluent"))
            os.makedirs(os.path.join(eng, "mods", "common", "fluent"))
            with open(os.path.join(repo, "mods", "tfc", "mod.yaml"), "w", newline="\n") as f:
                f.write("FluentMessages:\n\tcommon|fluent/a.ftl\n\ttfc|fluent/b.ftl\n\ttfc|fluent/missing.ftl\n")
            with open(os.path.join(eng, "mods", "common", "fluent", "a.ftl"), "w", newline="\n") as f:
                f.write("# c\nactor-e1 =\n    .name = Old Name\n    .description = d\nmeta-tank = Tank\n")
            with open(os.path.join(repo, "mods", "tfc", "fluent", "b.ftl"), "w", newline="\n") as f:
                f.write("actor-e1 =\n    .name = Minigunner\nmeta-long = first\n    second\n")
            msgs = T.load_fluent(repo, eng)
            self.assertEqual(T.fluent_text(msgs, "actor-e1.name"), "Minigunner")
            self.assertEqual(T.fluent_text(msgs, "meta-tank"), "Tank")
            self.assertEqual(T.fluent_text(msgs, "meta-long"), "first second")
            self.assertEqual(T.fluent_text(msgs, "actor-e1.description"), "<fluent:actor-e1.description>")  # whole message replaced
            self.assertEqual(T.fluent_text(msgs, "nope.name"), "<fluent:nope.name>")


def write_pair(d, prefix, arows, wcols, wrows):
    a, w = os.path.join(d, prefix + "-a.csv"), os.path.join(d, prefix + "-w.csv")
    T.write_csv(a, T.ACTOR_COLUMNS, arows)
    T.write_csv(w, wcols, wrows)
    return a, w


class CompareOptionTests(unittest.TestCase):
    """compare on the frozen baseline edited by hand."""

    @classmethod
    def setUpClass(cls):
        cls.ac, cls.ar = T.read_csv(BASE_A)
        cls.wc, cls.wr = T.read_csv(BASE_W)

    def rows(self):
        return [T.OrderedDict(r) for r in self.ar.values()], [T.OrderedDict(r) for r in self.wr.values()]

    def run_compare(self, arows, wrows, *opts):
        with tempfile.TemporaryDirectory() as d:
            a, w = write_pair(d, "n", arows, self.wc, wrows)
            return quiet(T.cmd_compare, [BASE_A, BASE_W, a, w] + list(opts))

    def test_identical_sets_are_unchanged_with_headline(self):
        ar, wr = self.rows()
        rc, out = self.run_compare(ar, wr)
        self.assertEqual(rc, 0)
        self.assertIn("changed values: 0 in 0 row(s)", out)
        self.assertIn("actors    baseline 273 | present 273 | missing   0 | present and differing   0 | present and identical 273", out)
        self.assertIn("weapons   baseline 100 | present 100 | missing   0", out)

    def test_changed_value_is_reported_with_both_values_and_counted_per_column(self):
        ar, wr = self.rows()
        next(r for r in ar if r["name"] == "MTNK")["hp"] = "460"
        rc, out = self.run_compare(ar, wr)
        self.assertEqual(rc, 0)
        self.assertIn("MTNK", out)
        self.assertIn("'450' -> '460'", out)
        self.assertIn("present and differing   1", out)
        self.assertRegex(out, r"\n  hp +1\n")

    def test_ignore_and_only(self):
        ar, wr = self.rows()
        next(r for r in ar if r["name"] == "MTNK")["hp"] = "460"
        next(r for r in ar if r["name"] == "E1")["cost"] = "101"
        rc, out = self.run_compare(ar, wr, "--ignore", "hp")
        self.assertNotIn("'450' -> '460'", out)
        self.assertIn("'100' -> '101'", out)
        with tempfile.TemporaryDirectory() as d:
            lst = os.path.join(d, "l.txt")
            with open(lst, "w") as f:
                f.write("# lane\nMTNK\n120mm\n")
            rc, out = self.run_compare(ar, wr, "--only", lst)
            self.assertIn("'450' -> '460'", out)
            self.assertNotIn("'100' -> '101'", out)
            self.assertIn("Actors: baseline 1, new", out)
            self.assertIn("Weapons: baseline 1, new", out)

    def test_missing_name_fails_even_with_only(self):
        ar, wr = self.rows()
        ar = [r for r in ar if r["name"] != "MTNK"]
        with tempfile.TemporaryDirectory() as d:
            lst = os.path.join(d, "l.txt")
            with open(lst, "w") as f:
                f.write("MTNK\nE1\n")
            rc, out = self.run_compare(ar, wr, "--only", lst)
            self.assertEqual(rc, 1)
            self.assertIn("  - MTNK", out)
        rc, out = self.run_compare(ar, wr)
        self.assertEqual(rc, 1)

    def test_missing_name_mentions_a_case_only_near_miss(self):
        ar, wr = self.rows()
        next(r for r in ar if r["name"] == "MTNK")["name"] = "mtnk"
        rc, out = self.run_compare(ar, wr)
        self.assertEqual(rc, 1)
        self.assertIn("the new set has 'mtnk'", out)

    def test_marker_cells_are_not_changes(self):
        ar, wr = self.rows()
        for r in ar:
            r["faction_owner"] = T.MARKER
        rc, out = self.run_compare(ar, wr)
        self.assertEqual(rc, 0)
        self.assertIn("changed values: 0 in 0 row(s)", out)
        self.assertIn("not comparable (no modern counterpart): 1 value(s)", out)   # only HUEY has a faction_owner

    def test_extras_and_terrain_are_compared_per_key(self):
        ar, wr = self.rows()
        m = next(r for r in ar if r["name"] == "MTNK")
        m["extras"] = m["extras"].replace("Cloak.CloakDelay=90", "Cloak.CloakDelay=91") + ";Selectable.Priority=10"
        m["terrain_speeds"] = m["terrain_speeds"].replace("Clear=80", "Clear=100")
        rc, out = self.run_compare(ar, wr)
        self.assertIn("extras.Cloak.CloakDelay", out)
        self.assertIn("'90' -> '91'", out)
        self.assertIn("terrain_speeds.Clear", out)
        self.assertIn("keys only the port has (extras / terrain_speeds, not counted as changes): 1", out)
        self.assertIn("+ MTNK  extras.Selectable.Priority = '10'", out)
        self.assertIn("present and differing   1", out)

    def test_unmapped_extras_key_missing_from_the_port_is_not_a_change(self):
        ar, wr = self.rows()
        e = next(r for r in ar if r["name"] == "E1")
        self.assertIn("Health.Radius", e["extras"])
        e["extras"] = ";".join(i for i in e["extras"].split(";") if not i.startswith("Health.Radius"))
        rc, out = self.run_compare(ar, wr)
        self.assertIn("changed values: 0 in 0 row(s)", out)
        self.assertIn("not comparable (no modern counterpart): 1 value(s)", out)

    def test_blank_armour_column_means_100_on_both_sides(self):
        ar, wr = self.rows()
        w = next(r for r in wr if r["name"] == "Heal")
        self.assertEqual(w["vs_None"], "")
        w["vs_None"] = "100"
        rc, out = self.run_compare(ar, wr)
        self.assertIn("changed values: 0 in 0 row(s)", out)

    def test_actor_and_weapon_names_compare_ignoring_case(self):
        ar, wr = self.rows()
        m = next(r for r in ar if r["name"] == "MTNK")
        m["weapons"] = "120MM"
        m["extras"] = m["extras"].replace("MTNK.Husk", "mtnk.husk")
        rc, out = self.run_compare(ar, wr)
        self.assertIn("changed values: 0 in 0 row(s)", out)

    def test_headline_counts_templates_separately(self):
        ar, wr = self.rows()
        ar = [r for r in ar if r["name"] != "^Tank"]
        rc, out = self.run_compare(ar, wr)
        self.assertEqual(rc, 1)
        self.assertIn("templates baseline  25 | present  24 | missing   1", out)
        self.assertIn("actors    baseline 273 | present 273 | missing   0", out)


class CheckCommandTests(unittest.TestCase):
    def test_unknown_name_is_exit_2(self):
        rc, out = quiet(T.cmd_check, ["NOT_AN_ACTOR"])
        self.assertEqual(rc, 2)
        self.assertIn("not in the baseline", out)

    def test_no_names_is_exit_2(self):
        rc, out = quiet(T.cmd_check, [])
        self.assertEqual(rc, 2)

    def test_names_are_case_sensitive(self):
        rc, out = quiet(T.cmd_check, ["mtnk"])
        self.assertEqual(rc, 2)

    def test_engine_not_built_is_exit_2_with_a_message(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "mods", "tfc"))
            with open(os.path.join(d, "mods", "tfc", "mod.yaml"), "w") as f:
                f.write("Rules:\n\ttfc|rules/a.yaml\n")
            rc, out = quiet(T.cmd_check, ["E1", "--repo", d])
            self.assertEqual(rc, 2)
            self.assertIn("engine not built", out)

    def test_names_list_file(self):
        with tempfile.TemporaryDirectory() as d:
            lst = os.path.join(d, "l.txt")
            with open(lst, "w") as f:
                f.write("# comment\nNOPE_ONE\n")
            rc, out = quiet(T.cmd_check, ["--list", lst])
            self.assertEqual(rc, 2)
            self.assertIn("NOPE_ONE", out)


@unittest.skipUnless(HAVE_ENGINE, NEED_ENGINE)
class EngineBackedStockTests(unittest.TestCase):
    """Runs the real 20250330 engine on this repo's mods/tfc (a few calls)."""

    def test_E1_on_stock_matches_the_baseline_after_conversion(self):
        arows, wcols, wrows, errors, st = T.extract_port(REPO, ENGINE, ["E1", "MTNK", "World"], ["Sniper"], 3)
        self.assertEqual(errors, {})
        e1 = next(r for r in arows if r["name"] == "E1")
        self.assertEqual((e1["hp"], e1["cost"], e1["armor"], e1["weapons"]), ("50", "100", "None", "M16"))  # stock 5000 / 100
        self.assertEqual(e1["tooltip"], "Minigunner")
        self.assertEqual(wrows[0]["name"], "Sniper")

    def test_names_are_collected_with_case_and_sources(self):
        names, sources, inherits = T.port_names(REPO, ENGINE, "Rules")
        self.assertIn("E1", names)
        self.assertTrue(any(n.startswith("^") for n in names))
        self.assertTrue(sources["E1"][0].startswith("rules/") or sources["E1"][0].startswith("factions/"))

    def test_check_passes_for_a_present_name_and_fails_for_a_missing_one(self):
        rc, out = quiet(T.cmd_check, ["E1", "--summary", "--jobs", "2"])
        self.assertEqual(rc, 0, out)
        self.assertIn("OK: every listed name is present", out)
        rc, out = quiet(T.cmd_check, ["Colt45", "--summary", "--jobs", "2"])   # not a stock 20250330 weapon
        self.assertEqual(rc, 1, out)
        self.assertIn("  - Colt45", out)

    def test_port_command_writes_the_two_csvs(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = quiet(T.cmd_port, ["--actors", "E1", "--weapons", "Sniper", "--out-dir", d, "--jobs", "2"])
            self.assertEqual(rc, 0, out)
            ac, ar = T.read_csv(os.path.join(d, "port-actors.csv"))
            self.assertEqual(list(ac), T.ACTOR_COLUMNS)
            self.assertEqual(list(ar), ["E1"])
            wc, wr = T.read_csv(os.path.join(d, "port-weapons.csv"))
            self.assertEqual(list(wr), ["Sniper"])
            self.assertEqual(wc[:3], ["name", "range", "min_range"])


# --- the round-trip proof ---------------------------------------------------------------------------------------
# Take stock actors and weapons, write their 0.32 baseline values into a throwaway override file in a scratch copy of
# the mod (using the design note's conversions BY HAND, below: no tfc_stats code is used to make the override), run
# the extractor, and require compare to show them unchanged. Then break one value on purpose and require compare to
# report exactly that.

RT_ACTORS = ["E1", "MTNK", "ARTY", "LTNK", "FTNK", "NUKE", "ORCA", "BIKE"]
RT_WEAPONS = ["Sniper", "Vulcan", "Laser", "227mm.stnk", "HighV", "Grenade", "120mm", "Rockets"]
DEATH_NAMES = {"1": "BulletDeath", "2": "RippedApartDeath", "3": "SmallExplosionDeath", "4": "ExplosionDeath",
               "5": "FireDeath", "6": "TiberiumDeath"}
# Columns the override cannot reach, and why; they are excluded from the round-trip compare and printed.
RT_IGNORE = {
    "traits": "not a value", "inherits": "not a value", "source": "not a value", "faction_owner": "unmapped",
    "tooltip": "Fluent text, not rules", "extras.Tooltip.GenericName": "Fluent text, not rules",
    "weapons": "the Armament weapon names are lane 4g's job, not a unit conversion",
    "other_weapons": "FireWarheadsOnDeath weapon names are not a unit conversion",
    "extras.Explodes.Weapon": "weapon names", "extras.Explodes.EmptyWeapon": "weapon names",
    "extras.LeavesHusk.HuskActor": "husk actor names", "buildable": "cannot remove a Buildable trait here",
    "prerequisites": "a list cannot be emptied by an override", "queue": "a list cannot be emptied by an override",
    "build_palette_order": "only written when the baseline has one", "locomotor": "trait class, not a unit conversion",
    "warhead_count": "extra CreateEffect warheads are left modern (note 3.7)",
    "valid_targets": "a list cannot be emptied by an override", "invalid_targets": "a list cannot be emptied by an override",
    "projectile": "projectile type is not changed by an override",
    "extras.Helicopter.RearmBuildings": "stock ORCA has no Rearmable trait; an override cannot add one",
}


def hand_actor_override(row, stock_node):
    """YAML lines for one actor from a baseline row. Conversions written out by hand from the design note 3.2."""
    out = [row["name"] + ":"]
    ex = {}
    for item in row["extras"].split(";"):
        if item:
            k, _, v = item.partition("=")
            ex[k] = v

    def has(key):
        return key in stock_node.children

    blocks = T.OrderedDict()

    def add(trait, **fields):
        blocks.setdefault(trait, T.OrderedDict()).update({k: v for k, v in fields.items() if v is not None})

    if row["cost"]:
        add("Valued", Cost=row["cost"])
    if row["hp"]:
        add("Health", HP=int(row["hp"]) * 100)                         # HP x100
    if row["armor"]:
        add("Armor", Type=row["armor"])
    if row["rot"] or row["speed"]:
        t = "Mobile" if row["locomotor"] == "Mobile" else "Aircraft"
        add(t, Speed=row["speed"] or None, TurnSpeed=int(row["rot"]) * 4 if row["rot"] else None)   # ROT x4
    if row["sight_range"]:
        add("RevealsShroud", Range=row["sight_range"])
    for key in sorted(ex):
        v = ex[key]
        trait, _, field = key.partition(".")
        base = trait.split("@")[0]
        if base == "SelfHealing" and has("ChangesHealth" + trait[len("SelfHealing"):]):
            inst = "ChangesHealth" + trait[len("SelfHealing"):]
            if field == "Step":
                add(inst, Step=int(v) * 100, PercentageStep=0)         # step x100 (the elite step is a flat amount)
            else:
                add(inst, Delay=v)
        elif base == "DetectCloaked" and field == "Range" and has("DetectCloaked"):
            add("DetectCloaked", Range="%sc0" % v)                      # cells to WDist
        elif base == "Cloak" and has("Cloak"):
            add("Cloak", **{field: v})
        elif base == "AutoTarget" and has("AutoTarget"):
            add("AutoTarget", ScanRadius=v)
        elif base == "Crushable" and field == "CrushSound" and has("Crushable"):
            add("Crushable", CrushSound=v)
        elif base == "Selectable" and has("Selectable"):
            add("Selectable", Priority=v)
        elif base == "Turreted" and field == "ROT" and has(trait):
            add(trait, TurnSpeed=int(round(float(v) * 4)))
        elif base == "TakeCover" and has("TakeCover"):
            add("TakeCover", SpeedModifier=int(round(float(v) * 100)))
        elif base == "RepairableBuilding" and has("RepairableBuilding"):
            add("RepairableBuilding", RepairPercent=v)
    for trait, fields in blocks.items():
        if fields:
            out.append("	%s:" % trait)
            for k, v in fields.items():
                out.append("		%s: %s" % (k, v))
    return out if len(out) > 1 else []


def hand_world_override(rows_by_loco):
    """World locomotor terrain speeds from baseline rows: {locomotor: row}."""
    out = ["World:"]
    for loco, row in sorted(rows_by_loco.items()):
        out.append("\tLocomotor@%s:" % loco.upper())
        ts = {}
        for item in row["terrain_speeds"].split(";"):
            k, _, v = item.partition("=")
            t, _, sub = k.partition(".")
            ts.setdefault(t, {})[sub or "speed"] = v
        out.append("\t\tTerrainSpeeds:")
        for t in sorted(ts):
            out.append("\t\t\t%s: %s" % (t, ts[t]["speed"]))
            if "PathingCost" in ts[t]:
                out.append("\t\t\t\tPathingCost: %s" % ts[t]["PathingCost"])
        crushes = [i.split("=", 1)[1] for i in row["extras"].split(";") if i.startswith("Mobile.Crushes=")]
        if crushes:
            out.append("\t\tCrushes: %s" % crushes[0])
    return out


def hand_weapon_override(row):
    out = [row["name"] + ":"]
    if row["range"]:
        out.append("\tRange: %s" % row["range"])
    out.append("\tMinRange: %s" % (row["min_range"] or "0"))             # blank = the default 0
    out.append("\tBurst: %s" % (row["burst"] or "1"))                     # blank = the default 1
    if row["reload_delay"]:
        out.append("\tReloadDelay: %s" % row["reload_delay"])
    out.append("	BurstDelays: %s" % (row["burst_delay"] or "5"))          # blank = the default 5 ticks
    if row["valid_targets"]:
        out.append("\tValidTargets: %s" % row["valid_targets"])
    if row["invalid_targets"]:
        out.append("\tInvalidTargets: %s" % row["invalid_targets"])
    if row["projectile_speed"] or row["projectile_inaccuracy"]:
        out.append("\tProjectile: %s" % row["projectile"])
        if row["projectile_speed"]:
            out.append("\t\tSpeed: %s" % row["projectile_speed"])
        if row["projectile_inaccuracy"]:
            out.append("\t\tInaccuracy: %s" % row["projectile_inaccuracy"])
    out.append("\tWarhead@1Dam: %s" % row["warhead_type"])
    out.append("\t\tDamage: %d" % (int(row["damage"]) * 100))             # damage x100
    if row["spread"]:
        out.append("\t\tSpread: %s" % row["spread"])
    out.append("\t\tVersus:")
    for armour in ("None", "Wood", "Light", "Heavy", "Concrete"):
        out.append("\t\t\t%s: %s" % (armour, row.get("vs_" + armour) or "100"))   # blank = 100, written explicitly
    if row["death_type"]:
        out.append("\t\tDamageTypes: Prone50Percent, TriggerProne, %s" % DEATH_NAMES[row["death_type"]])
    return out


@unittest.skipUnless(HAVE_ENGINE, NEED_ENGINE)
class RoundTripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = os.environ.get("TFC_STATS_SCRATCH")
        cls._tmp = None
        if root:
            cls.root = os.path.join(root, "roundtrip")
            if os.path.isdir(cls.root):
                shutil.rmtree(cls.root)
            os.makedirs(cls.root)
        else:
            cls._tmp = tempfile.TemporaryDirectory(prefix="tfc-roundtrip-")
            cls.root = cls._tmp.name
        cls.repo = os.path.join(cls.root, "repo")
        shutil.copytree(os.path.join(REPO, "mods", "tfc"), os.path.join(cls.repo, "mods", "tfc"),
                        ignore=shutil.ignore_patterns("maps"))
        shutil.copy(os.path.join(REPO, "mod.config"), cls.repo)
        # throwaway override files, listed LAST so that they win over whatever any lane has put in the real files
        mod = os.path.join(cls.repo, "mods", "tfc", "mod.yaml")
        with open(mod, newline="") as f:
            text = f.read().replace("\r\n", "\n")
        text = cls._append(text, "Rules", "tfc|rules/zz-roundtrip.yaml")
        text = cls._append(text, "Weapons", "tfc|weapons/zz-roundtrip.yaml")
        text = "\n".join(l for l in text.split("\n") if not l.strip().startswith("tfc|maps"))  # the copy has no maps
        with open(mod, "w", newline="\n") as f:
            f.write(text)
        cls.ac, cls.ar = T.read_csv(BASE_A)
        cls.wc, cls.wr = T.read_csv(BASE_W)
        cls.put_files("", "")  # listed in mod.yaml, so they must exist; empty = pure stock
        eng = T.Engine(cls.repo, ENGINE, cache=False, jobs=4)
        stock, errs = eng.resolve("Rules", RT_ACTORS)
        assert not errs, errs
        cls.stock = stock
        cls.locos = {}
        for n in RT_ACTORS:
            ln = T.pfield(stock[n], "Mobile", "Locomotor")
            if ln:
                prev = cls.locos.get(ln)
                assert prev is None or cls.ar[prev]["terrain_speeds"] == cls.ar[n]["terrain_speeds"], (
                    "actors %s and %s share locomotor %s but 0.32 gave them different terrain speeds" % (prev, n, ln))
                cls.locos.setdefault(ln, n)
        cls.write_override()

    @classmethod
    def tearDownClass(cls):
        if cls._tmp is not None:
            cls._tmp.cleanup()

    @staticmethod
    def _append(text, section, entry):
        inside, last = False, None
        lines = text.split("\n")
        for i, l in enumerate(lines):
            if l and l[0] not in " \t#":
                inside = l.split(":")[0].strip() == section
            elif inside and l.strip():
                last = i
        lines.insert(last + 1, "\t" + entry)
        return "\n".join(lines)

    @classmethod
    def write_override(cls, wrong=None):
        actors = []
        for n in RT_ACTORS:
            actors += hand_actor_override(cls.ar[n], cls.stock[n])
        world = hand_world_override({ln: cls.ar[n] for ln, n in cls.locos.items()})
        text = "\n".join(actors + world) + "\n"
        weapons = []
        for n in RT_WEAPONS:
            weapons += hand_weapon_override(cls.wr[n])
        wtext = "\n".join(weapons) + "\n"
        if wrong:
            assert wrong[0] in text, wrong
            text = text.replace(*wrong)
        cls.actor_yaml, cls.weapon_yaml = text, wtext
        cls.put_files(text, wtext)

    @classmethod
    def put_files(cls, text, wtext):
        with open(os.path.join(cls.repo, "mods", "tfc", "rules", "zz-roundtrip.yaml"), "w", newline="\n") as f:
            f.write(text)
        with open(os.path.join(cls.repo, "mods", "tfc", "weapons", "zz-roundtrip.yaml"), "w", newline="\n") as f:
            f.write(wtext)

    @classmethod
    def extract_and_compare(cls):
        arows, wcols, wrows, errors, st = T.extract_port(cls.repo, ENGINE, RT_ACTORS, RT_WEAPONS, 4, cache=False)
        assert not errors, errors
        d = os.path.join(cls.root, "out")
        os.makedirs(d, exist_ok=True)
        a, w = write_pair(d, "port", arows, wcols, wrows)
        names = os.path.join(cls.root, "names.txt")
        with open(names, "w") as f:
            f.write("\n".join(RT_ACTORS + RT_WEAPONS) + "\n")
        return quiet(T.cmd_compare, [BASE_A, BASE_W, a, w, "--ignore", ",".join(sorted(RT_IGNORE)), "--only", names])

    def test_1_stock_alone_differs_so_the_proof_is_not_vacuous(self):
        self.put_files("", "")
        try:
            rc, out = self.extract_and_compare()
        finally:
            self.write_override()
        with open(os.path.join(self.root, "roundtrip-before-override.txt"), "w", newline="\n") as f:
            f.write(out)
        self.assertIn("MTNK", out)
        self.assertIn("actors    baseline %3d | present %3d | missing   0 | present and differing %3d" % (
            len(RT_ACTORS), len(RT_ACTORS), len(RT_ACTORS)), out)

    def test_2_baseline_values_written_by_hand_come_back_unchanged(self):
        rc, out = self.extract_and_compare()
        with open(os.path.join(self.root, "roundtrip-compare.txt"), "w", newline="\n") as f:
            f.write("ignored columns (and why):\n" + "\n".join("  %-30s %s" % kv for kv in sorted(RT_IGNORE.items())) + "\n\n")
            f.write("override rules/zz-roundtrip.yaml:\n" + self.actor_yaml + "\noverride weapons/zz-roundtrip.yaml:\n" + self.weapon_yaml + "\n")
            f.write(out)
        self.assertEqual(rc, 0, out)
        self.assertEqual(out.count("changed values: 0 in 0 row(s)"), 2, out)   # actors and weapons
        self.assertIn("actors    baseline %3d | present %3d | missing   0 | present and differing   0" % (len(RT_ACTORS), len(RT_ACTORS)), out)
        self.assertIn("weapons   baseline %3d | present %3d | missing   0 | present and differing   0" % (len(RT_WEAPONS), len(RT_WEAPONS)), out)

    def test_3_one_deliberately_wrong_value_is_reported(self):
        self.write_override(wrong=("\t\tHP: 45000\n", "\t\tHP: 46000\n"))   # MTNK 450 -> 460
        try:
            rc, out = self.extract_and_compare()
        finally:
            self.write_override()
        with open(os.path.join(self.root, "roundtrip-wrong-value.txt"), "w", newline="\n") as f:
            f.write(out)
        self.assertIn("MTNK", out)
        self.assertIn("'450' -> '460'", out)
        self.assertIn("present and differing   1", out)
        self.assertIn("changed values: 1 in 1 row(s)", out)


PROBE_DIR = os.path.join(HERE, "probe")


def probe_text(name):
    with open(os.path.join(PROBE_DIR, name), encoding="utf-8-sig") as f:
        return f.read()


class ProbeProvenTests(unittest.TestCase):
    """What tools/probe/*.cs proved against the real 2014 OpenRA.Game.exe, pinned (the probe outputs are committed)."""

    def test_probe_outputs_state_the_engine_defaults(self):
        p4 = probe_text("probe4-out.txt")
        # A.1: a warhead (and a weapon) defaults to [Ground,Water]; an airborne aircraft carries [Air]
        self.assertIn("new SpreadDamageWarhead(): ValidTargets=[Ground,Water] InvalidTargets=[]", p4)
        self.assertIn("TargetableAircraftInfo airborne=[Air]", p4)
        # A.2: no Armor trait takes 100 from every weapon, Armor None takes the weapon's None entry
        self.assertIn("vs camera         Armor=<no trait> -> DamageVersus = 100", p4)
        self.assertIn("vs e1             Armor=None       -> DamageVersus = 30", p4)
        self.assertIn("vs spc            Armor=light      -> DamageVersus = 100", p4)
        # A.3: weapon defaults
        self.assertIn("bare weapon: Burst=1 BurstDelay=5 ReloadDelay=1", p4)
        p5 = probe_text("probe5-out.txt")
        self.assertIn("BuildingInfo has a field named Power: False", p5)
        self.assertIn("gun    PowerInfo amount=  -20  Cost=  600 CustomBuildTimeValue=1440 engine GetBuildTime=1440", p5)
        self.assertIn("atwr   PowerInfo amount=    0  Cost= 1000 CustomBuildTimeValue=<none> engine GetBuildTime=1500", p5)

    def test_the_17_weapons_cannot_hit_aircraft(self):
        want = {"TowerMissle", "Deagle", "TechMachineGun", "Dozergun", "Frockets", "Hrockets", "TSARocket",
                "OsirisMissiles", "OsirisMissiles2", "MarMG", "MarPanzershrek", "QuadCannon", "Glauncher",
                "NestMachineGunAA", "LMG", "MammothMissiles2", "MachineGun2"}
        air = {n for n, w in B["weapons"].items() if "Air" in (T.target_list(w, "ValidTargets") or [])}
        dead = {n for n in air if not T.weapon_hits_air(B["weapons"][n])}
        self.assertEqual(dead, want)  # 17, and exactly these
        self.assertEqual(len(dead), 17)
        # TowerMissle's damage warhead has an explicit ValidTargets: Ground (from weaponsV.yaml); the others rely on the default
        self.assertEqual(T.target_list(B["weapons"]["TowerMissle"].children["Warhead@1Dam"], "ValidTargets"), ["Ground"])
        self.assertIsNone(T.target_list(B["weapons"]["LMG"].children["Warhead@1Dam"], "ValidTargets"))
        # weapons that do hit aircraft: the AA weapons and the ones whose damage warhead lists Air
        for n in ("SAMMissile", "Patriot", "OrcaAAMissiles", "HeliAAGun", "MammothMissiles", "Rockets"):
            self.assertTrue(T.weapon_hits_air(B["weapons"][n]), n)

    def test_air_rule_on_tiny_weapons(self):
        def w(text):
            return T.parse_text(text)
        self.assertFalse(T.weapon_hits_air(w("ValidTargets: Ground, Air\nWarhead@1Dam: SpreadDamage\n\tDamage: 5\n")))
        self.assertTrue(T.weapon_hits_air(w("ValidTargets: Ground, Air\nWarhead@1Dam: SpreadDamage\n\tDamage: 5\n\tValidTargets: Air\n")))
        self.assertFalse(T.weapon_hits_air(w("ValidTargets: Air\nWarhead@1Dam: SpreadDamage\n\tDamage: 5\n\tValidTargets: Air\n\tInvalidTargets: Air\n")))
        self.assertFalse(T.weapon_hits_air(w("ValidTargets: Ground\nWarhead@1Dam: SpreadDamage\n\tDamage: 5\n\tValidTargets: Air\n")))
        # an effect warhead (no Damage) cannot make a weapon valid
        self.assertFalse(T.weapon_hits_air(w("ValidTargets: Air\nWarhead@1Eff: CreateEffect\n\tValidTargets: Air\n")))


class BaselineGapTests(unittest.TestCase):
    """Part B of the gap fixes: power, build time and storage as the 0.32 engine really read them."""

    def row(self, name):
        return actor(name)

    def test_building_power_is_dead_yaml_and_kept_in_its_own_column(self):
        # 2014 BuildingInfo has no Power field (probe5): `Building: Power: n` did nothing, only `Power: Amount:` counts
        for name, dead in (("ATWR", "-40"), ("SILO", "-10"), ("HAND", "-20"), ("VLCN", "-20")):
            r = self.row(name)
            self.assertEqual((r["power"], r["power_drain"], r["building_power_ignored"]), ("", "", dead), name)
        # GUN has the real trait only; HQ keeps its -40 from `Power: Amount`
        self.assertEqual((self.row("GUN")["power_drain"], self.row("GUN")["building_power_ignored"]), ("-20", ""))
        self.assertEqual(self.row("PROC")["power_drain"], "-50")
        self.assertEqual(self.row("NUKE")["power"], "100")

    def test_both_power_spellings_on_text(self):
        d = T.parse_text("Building:\n\tPower: -20\n")
        r = T.actor_row("X", d, d, {})
        self.assertEqual((r["power_drain"], r["building_power_ignored"]), ("", "-20"))
        d = T.parse_text("Power:\n\tAmount: -30\nBuilding:\n\tPower: -20\n")
        r = T.actor_row("X", d, d, {})
        self.assertEqual((r["power_drain"], r["building_power_ignored"]), ("-30", "-20"))

    def test_custom_build_time_value_is_captured(self):
        # engine: ticks = (CustomBuildTimeValue or cost x 1.5) x BuildSpeed .4 -> GUN/GTWR 1440 x .4 = 576 ticks,
        # SAM 2160 x .4 = 864, and a plain 600-cost unit 900 x .4 = 360
        for name, v in (("GUN", "1440"), ("GTWR", "1440"), ("SAM", "2160"), ("E1", ""), ("ATWR", ""), ("MTNK", "")):
            self.assertEqual(self.row(name)["build_duration"], v, name)
        self.assertEqual(self.row("GUN")["build_duration_modifier"], "")
        self.assertEqual(sum(1 for r in B["actor_rows"] if r["build_duration"]), 3)

    def test_building_storage_is_in_extras(self):
        for name, cap in (("PROC", "2000"), ("SILO", "2400"), ("RFNRY", "1500")):
            self.assertIn("StoresResources.Capacity=" + cap, self.row(name)["extras"], name)

    def test_the_changed_baseline_cells(self):
        # only the 16 dead `Building: Power` values and the 3 CustomBuildTimeValue cells differ from the old baseline
        ign = {r["name"]: r["building_power_ignored"] for r in B["actor_rows"] if r["building_power_ignored"]}
        self.assertEqual(len(ign), 16)
        self.assertEqual(ign["TSLA"], "-200")
        self.assertEqual(ign["SLAR"], "50")


class PortGapTests(unittest.TestCase):
    """Port-side conversions for the gap fixes, hand-derived (no engine needed)."""

    @classmethod
    def setUpClass(cls):
        cls.locos = T.world_locomotors(T.parse_text(STOCK_WORLD))

    def prow(self, text, name="X"):
        return T.port_actor_row(name, T.parse_text(text), {}, {}, self.locos, {})

    def test_build_duration_arithmetic(self):
        f = T.build_duration_to_old
        # 0.32: GUN/GTWR 1440 x .4 = 576 ticks. Modern ticks = BuildDuration x 60 percent, so BuildDuration must be
        # 576 / 0.6 = 960 (and 960 x 0.6 / 0.4 = 1440 comes back). 1440 would be 864 ticks, 1.5 times too slow.
        self.assertEqual(f("960", None, "600"), "1440")
        self.assertEqual(f("1440", None, "600"), "2160")
        # SAM: 2160 x .4 = 864 ticks = 1440 x 0.6
        self.assertEqual(f("1440", None, "750"), "2160")
        # defaults: no BuildDuration (or -1) and modifier 60 give cost x 0.6 ticks = the 0.32 default -> blank
        self.assertEqual(f(None, None, "600"), "")
        self.assertEqual(f("-1", "60", "1000"), "")
        # an explicit duration equal to the cost is the same as the default: 600 x .6 = 360 ticks, 360 / .4 = 900 = 600 x 1.5
        self.assertEqual(f("600", None, "600"), "")
        # a different modifier: cost 1000 at 50 percent = 500 ticks -> 1250 in 0.32 units (default would be 1500)
        self.assertEqual(f(None, "50", "1000"), "1250")
        self.assertEqual(f("2080", "50", "1500"), "2600")

    def test_build_duration_in_a_port_row(self):
        r = self.prow("Valued:\n\tCost: 600\nBuildable:\n\tBuildDuration: 960\n")
        self.assertEqual((r["build_duration"], r["build_duration_modifier"]), ("1440", ""))
        # the value the lane wrote, 1440, converts to 2160 and so shows up against the baseline's 1440
        r = self.prow("Valued:\n\tCost: 600\nBuildable:\n\tBuildDuration: 1440\n")
        self.assertEqual(r["build_duration"], "2160")

    def test_angle_conversion_and_the_255_rule(self):
        f = T.angle_to_old
        self.assertEqual([f(v) for v in ("1023", "1020", "20", "16", "40", "1022", "")],
                         ["255", "255", "5", "4", "10", "255.5", ""])
        self.assertEqual(self.prow("Aircraft:\n\tTurnSpeed: 1023\n\tSpeed: 100\n")["rot"], "255")
        self.assertEqual(self.prow("Mobile:\n\tTurnSpeed: 1023\n")["rot"], "255")
        self.assertEqual(self.prow("Mobile:\n\tTurnSpeed: 20\n")["rot"], "5")
        self.assertIn("Turreted.ROT=255", self.prow("Turreted:\n\tTurnSpeed: 1023\n")["extras"])
        self.assertIn("Turreted.InitialFacing=108", self.prow("Turreted:\n\tInitialFacing: 432\n")["extras"])
        self.assertIn("Plane.ROT=255", self.prow("Aircraft:\n\tTurnSpeed: 1023\n\tSpeed: 300\n")["extras"])

    def test_building_storage_maps_to_stores_resources(self):
        self.assertIn("StoresResources.Capacity=2400", self.prow("StoresPlayerResources:\n\tCapacity: 2400\n")["extras"])
        # a harvester's own capacity is still Harvester.Capacity
        ex = self.prow("Harvester:\n\tResources: Tiberium\nStoresResources:\n\tCapacity: 20\n")["extras"]
        self.assertIn("Harvester.Capacity=20", ex)
        self.assertNotIn("StoresResources.Capacity", ex)

    def test_dead_building_power_column_is_unmapped_not_a_difference(self):
        r = self.prow("Power:\n\tAmount: -20\n")
        self.assertEqual((r["power_drain"], r["building_power_ignored"]), ("-20", T.MARKER))
        self.assertEqual(T.row_changes("building_power_ignored", "-40", T.MARKER, ()), [("building_power_ignored", "-40", T.MARKER, "n/a")])

    def test_blank_armour_is_not_none(self):
        # no Armor trait (blank) and Armor Type None differ: 120mm does 100 to the first and 30 to the second
        self.assertEqual(T.row_changes("armor", "", "None", ()), [("armor", "", "None", "changed")])
        self.assertEqual(T.row_changes("armor", "None", "", ()), [("armor", "None", "", "changed")])
        self.assertEqual(T.row_changes("armor", "", "", ()), [])
        out = []
        T.diff_sets("Actors", ["name", "armor"], {"BRIDGE1": {"name": "BRIDGE1", "armor": ""}},
                    ["name", "armor"], {"BRIDGE1": {"name": "BRIDGE1", "armor": "None"}}, out)
        self.assertTrue(any("no Armor trait = 100% from every weapon" in ln for ln in out), out)
        # a case difference between real types stays case-insensitive-free: Light vs light is a change
        self.assertEqual(T.row_changes("armor", "Light", "light", ()), [("armor", "Light", "light", "changed")])



def run(argv=()):
    global B, MODDIR
    if argv:
        MODDIR = argv[0]
    elif not os.path.isfile(os.path.join(MODDIR, "mod.yaml")) and os.path.isfile(os.path.join(MODDIR, "legacy-0.32", "mod.yaml")):
        MODDIR = os.path.join(MODDIR, "legacy-0.32")  # the port branch keeps the 2014 mod here
    B = T.build(MODDIR)
    if not HAVE_ENGINE:
        print(NEED_ENGINE)
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    res = unittest.TextTestRunner(verbosity=1).run(suite)
    print("selftest: %d run, %d failed, %d errors, %d skipped" % (
        res.testsRun, len(res.failures), len(res.errors), len(res.skipped)))
    return 0 if res.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
