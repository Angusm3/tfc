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

    def test_RMBO_later_file_override(self):  # infantry.yaml (Cost 0, Queue empty) overridden by gdi army.yaml
        self.check("RMBO", cost="1000", hp="150", speed="71", sight_range="6c0", queue="Infantry.GDI",
                   prerequisites="eye, ~techlevel.high", weapons="Sniper")
        self.assertIn("Buildable.BuildLimit=1", actor("RMBO")["extras"])  # kept from infantry.yaml
        self.assertEqual(actor("RMBO")["source"], "rules/infantry.yaml+factions/gdi/rules/army.yaml")

    def test_MTNK_gdi_tank(self):
        self.check("MTNK", cost="800", hp="450", armor="Heavy", speed="85", rot="5", sight_range="6c0",
                   weapons="120mm", prerequisites="anyhq, ~techlevel.medium", queue="Vehicle.GDI")

    def test_ORCA_and_TRAN_aircraft(self):
        self.check("ORCA", cost="1200", hp="90", armor="Light", speed="186", rot="4", sight_range="10c0",
                   weapons="OrcaAGMissiles;OrcaAAMissiles", locomotor="Helicopter", queue="Aircraft.GDI")
        self.check("TRAN", cost="750", hp="90", armor="Light", speed="140", rot="5", weapons="",
                   other_weapons="HeliExplode", queue="Aircraft.GDI, Aircraft.Nod, Aircraft.Forgotten")

    def test_LTNK_nod(self):
        self.check("LTNK", cost="600", hp="360", armor="Heavy", speed="113", rot="7", sight_range="6c0",
                   weapons="70mm", queue="Vehicle.Nod")

    def test_SPC_nested_removal_and_lowercase_armor(self):  # nod army.yaml: Cloak: -RequiresUpgrade, Type: light
        self.check("SPC", cost="600", hp="150", armor="light", speed="128", rot="8", sight_range="7c0")
        cloak = B["actors"]["SPC"].children["Cloak"]
        self.assertNotIn("RequiresUpgrade", cloak.children)
        self.assertNotIn("-RequiresUpgrade", cloak.children)
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

    def test_Sniper_weaponsV_over_weapons(self):  # field-by-field override, untouched Versus keys survive
        self.check("Sniper", range="6c0", reload_delay="40", damage="100", spread="42",
                   valid_targets="Infantry", vs_None="100", vs_Wood="5", vs_Light="100", vs_Heavy="20",
                   vs_Concrete="", projectile="Bullet", projectile_speed="1c682", source="weapons.yaml+weaponsV.yaml")

    def test_Heal_override(self):
        self.check("Heal", range="4c0", reload_delay="4", damage="-1", spread="42", vs_None="",
                   vs_Wood="0", vs_Light="0", vs_Heavy="0", vs_Concrete="0")

    def test_120mm_override_and_extra_warheads(self):
        self.check("120mm", range="4c768", reload_delay="40", damage="40", spread="128", projectile_speed="682",
                   vs_None="25", vs_Wood="100", vs_Light="100", vs_Heavy="100", vs_Concrete="50", warhead_count="3")

    def test_Vulcan_keeps_burst(self):  # Burst 3 only in weapons.yaml, rest overridden in weaponsV.yaml
        self.check("Vulcan", burst="3", reload_delay="2", range="6c0", damage="100", spread="426",
                   valid_targets="Ground, Water", vs_None="100", vs_Wood="25", vs_Light="100", vs_Heavy="35",
                   vs_Concrete="0")

    def test_Tail_projectile_speed_from_V(self):
        self.check("Tail", range="1c0", reload_delay="30", damage="180", spread="213", projectile_speed="1c682",
                   vs_None="90", vs_Wood="10", vs_Light="30", vs_Heavy="10", vs_Concrete="10")

    def test_Colt45_weapons_only(self):
        self.check("Colt45", range="7c0", reload_delay="5", damage="50", spread="42", source="weapons.yaml",
                   vs_None="100", vs_Wood="0", vs_Light="0", vs_Heavy="0", vs_Concrete="0")

    def test_P90_valid_targets(self):
        self.check("P90", range="7c0", reload_delay="8", damage="100", valid_targets="Ground")

    def test_Tiberium_override(self):
        self.check("Tiberium", reload_delay="16", damage="2", spread="42", death_type="6")


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
        self.assertEqual(list(r["C"].children), ["B"])
        self.assertEqual(list(r["C"].children["B"].children), ["Z"])
        self.assertEqual(list(r["^P"].children), ["A", "B"])

    def test_later_file_overrides_and_self_merge(self):
        a = T.parse_text("U:\n\tHealth:\n\t\tHP: 10\n\t\tRadius: 5\n")
        b = T.parse_text("U:\n\tHealth:\n\t\tHP: 20\nU:\n\tValued:\n\t\tCost: 7\n")
        m = T.merge_files([a, b])
        self.assertEqual(m.children["U"].children["Health"].children["HP"].value, "20")
        self.assertEqual(m.children["U"].children["Health"].children["Radius"].value, "5")
        self.assertEqual(m.children["U"].children["Valued"].children["Cost"].value, "7")

    def test_unresolved_inherits_is_an_error(self):
        tree = T.parse_text("A:\n\tInherits: ^Nope\n")
        with self.assertRaises(T.ParseError):
            T.Resolver(tree).resolve_all()


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
