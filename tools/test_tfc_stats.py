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


def run(argv=()):
    global B, MODDIR
    if argv:
        MODDIR = argv[0]
    B = T.build(MODDIR)
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    res = unittest.TextTestRunner(verbosity=1).run(suite)
    print("selftest: %d run, %d failed, %d errors, %d skipped" % (
        res.testsRun, len(res.failures), len(res.errors), len(res.skipped)))
    return 0 if res.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
