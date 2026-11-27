using System; using System.Collections.Generic; using System.IO; using System.Linq; using System.Reflection; using OpenRA; using OpenRA.GameRules; using OpenRA.Traits; using OpenRA.FileSystem; using OpenRA.Mods.RA; using OpenRA.Mods.RA.Air;
// probe4: loads the real 0.32 mod through the 2014 engine and answers
//  A.1 warhead/weapon target defaults + which of the 17 weapons can damage aircraft
//  A.2 the armour modifier (DamageWarhead.DamageVersus, the engine's own method) for no Armor trait / Type None / unmatched type
//  A.3 default Burst, BurstDelay, ReloadDelay of a weapon that sets none of them
// Usage: probe4.exe <probe dir holding mods/tfc> <weapon names...>
public static class Program {
  static string J(string[] a) { return a == null ? "<null>" : "[" + string.Join(",", a) + "]"; }
  static bool Any(string[] a, string[] b) { return a.Intersect(b).Any(); }
  // Warhead.IsValidAgainst(Actor victim, Actor firedBy), decoded from the engine's IL (stance and AffectsParent ignored):
  //   CanTargetActor(victim.Info) && ValidTargets intersect victim ITargetable.TargetTypes && no InvalidTargets intersect
  static bool WarheadHits(Warhead x, ActorInfo victim, string[] types) {
    if (!x.GetType().IsSubclassOf(typeof(DamageWarhead))) return false;   // Warhead.CanTargetActor is the constant false
    if (!((DamageWarhead)x).CanTargetActor(victim, null)) return false;
    return Any(x.ValidTargets, types) && !Any(x.InvalidTargets, types);
  }
  // WeaponInfo.IsValidAgainst(Actor, Actor): weapon-level target test AND at least one warhead valid
  static bool WeaponCanTarget(WeaponInfo w, ActorInfo victim, string[] types) {
    return Any(w.ValidTargets, types) && !Any(w.InvalidTargets, types) && w.Warheads.Any(x => WarheadHits(x, victim, types));
  }
  public static void Main(string[] args) {
    Directory.SetCurrentDirectory(args[0]);
    Directory.CreateDirectory(Path.Combine(args[0], "logs")); Log.LogPath = Path.Combine(args[0], "logs") + Path.DirectorySeparatorChar;
    foreach (var c in new[]{"perf","debug","sync","graphics","geoip","server","irc","nat","sound"}) Log.AddChannel(c, c + ".log");
    Game.Settings = new Settings(null, new Arguments());
    var md = new ModData("tfc");
    typeof(Game).GetField("modData", BindingFlags.NonPublic | BindingFlags.Public | BindingFlags.Static).SetValue(null, md);
    GlobalFileSystem.UnmountAll();
    foreach (var kv in md.Manifest.Folders) GlobalFileSystem.Mount(kv);
    var rs = md.RulesetCache.LoadDefaultRules();
    Console.WriteLine("loaded: actors={0} weapons={1}", rs.Actors.Count, rs.Weapons.Count);

    Console.WriteLine("\n=== A.1 defaults");
    var wh = new SpreadDamageWarhead();
    Console.WriteLine("new SpreadDamageWarhead(): ValidTargets={0} InvalidTargets={1}", J(wh.ValidTargets), J(wh.InvalidTargets));
    Console.WriteLine("Warhead.CanTargetActor base class returns constant false; DamageWarhead.CanTargetActor = has Health && DamageVersus>0");

    Console.WriteLine("\n=== aircraft target types (TargetableAircraft: airborne uses TargetTypes, grounded uses GroundedTargetTypes)");
    var airSets = new Dictionary<string, List<string>>();
    ActorInfo airActor = null; string[] airTypes = null;
    foreach (var a in rs.Actors.Values) {
      foreach (var t in a.Traits.WithInterface<ITargetableInfo>()) {
        var types = t.GetTargetTypes();
        var ta = t as TargetableAircraftInfo;
        if (ta == null && !types.Contains("Air")) continue;
        var k = t.GetType().Name + " airborne=" + J(types) + (ta != null ? " grounded=" + J(ta.GroundedTargetTypes) : "");
        List<string> l; if (!airSets.TryGetValue(k, out l)) airSets[k] = l = new List<string>(); l.Add(a.Name);
        if (airActor == null && a.Name == "orca") { airActor = a; airTypes = types; }
      }
    }
    foreach (var kv in airSets) Console.WriteLine("{0}  <- {1} actors ({2}...)", kv.Key, kv.Value.Count, string.Join(",", kv.Value.Take(8)));
    var air = new { a = airActor };
    Console.WriteLine("\n=== per weapon (engine-parsed). 'hits air' = WeaponCanTarget vs a flying {0} (Health + Armor Light, types {1})", air.a.Name, J(airTypes));
    foreach (var name in args.Skip(1)) {
      WeaponInfo w; if (!rs.Weapons.TryGetValue(name.ToLowerInvariant(), out w)) { Console.WriteLine(name + ": MISSING"); continue; }
      Console.WriteLine("{0}: weapon ValidTargets={1} Invalid={2}  Burst={3} BurstDelay={4} ReloadDelay={5}", name, J(w.ValidTargets), J(w.InvalidTargets), w.Burst, w.BurstDelay, w.ReloadDelay);
      foreach (var x in w.Warheads) {
        var d = x as DamageWarhead;
        Console.WriteLine("    {0} ValidTargets={1} Invalid={2}{3}{4}", x.GetType().Name, J(x.ValidTargets), J(x.InvalidTargets), d != null ? " Damage=" + d.Damage : "", d != null ? " versusLight=" + d.DamageVersus(air.a) : "");
      }
      Console.WriteLine("    => weapon may target a flying aircraft: {0}; some warhead damages it: {1}", Any(w.ValidTargets, airTypes) && !Any(w.InvalidTargets, airTypes), w.Warheads.Any(x => WarheadHits(x, air.a, airTypes)));
      Console.WriteLine("    => WeaponInfo-level valid vs flying aircraft (target test AND some warhead): {0}", WeaponCanTarget(w, air.a, airTypes));
    }

    Console.WriteLine("\n=== whole mod: weapons whose weapon-level ValidTargets include Air, and whether the engine lets them hit a flying aircraft");
    foreach (var kv in rs.Weapons.OrderBy(k => k.Key)) {
      var w = kv.Value; if (!w.ValidTargets.Contains("Air")) continue;
      Console.WriteLine("    {0,-18} weaponTargets={1,-16} canTargetOrDamageAir={2}", kv.Key, J(w.ValidTargets), WeaponCanTarget(w, airActor, airTypes));
    }
    Console.WriteLine("\n=== A.2 armour modifier (DamageWarhead.DamageVersus, the engine's own method)");
    var ai = new ArmorInfo();
    Console.WriteLine("new ArmorInfo().Type = {0}", ai.Type ?? "<null>");
    var noArmor = rs.Actors.Values.Where(a => a.Traits.GetOrDefault<HealthInfo>() != null && a.Traits.GetOrDefault<ArmorInfo>() == null).ToList();
    var armorNoType = rs.Actors.Values.Where(a => a.Traits.GetOrDefault<ArmorInfo>() != null && a.Traits.GetOrDefault<ArmorInfo>().Type == null).ToList();
    Console.WriteLine("actors with Health but no Armor trait: {0} ({1}...); Armor trait with no Type: {2}", noArmor.Count, string.Join(",", noArmor.Take(8).Select(a => a.Name)), armorNoType.Count);
    var testers = new[] { "120mm", "Sniper", "70mm", "M16", "Flamethrower" };
    var subjects = new List<ActorInfo>();
    if (noArmor.Count > 0) subjects.Add(noArmor.First());
    foreach (var n in new[] { "e1", "mtnk", "spc", "fact" }) subjects.Add(rs.Actors[n]);
    foreach (var wn in testers) {
      var w = rs.Weapons[wn.ToLowerInvariant()]; var d = (DamageWarhead)w.Warheads.First(x => x is DamageWarhead);
      Console.WriteLine("{0}: Versus table={{{1}}}", wn, string.Join(", ", d.Versus.Select(kv => kv.Key + "=" + kv.Value)));
      foreach (var s in subjects) {
        var arm = s.Traits.GetOrDefault<ArmorInfo>();
        Console.WriteLine("    vs {0,-14} Armor={1,-10} -> DamageVersus = {2}", s.Name, arm == null ? "<no trait>" : (arm.Type ?? "<null type>"), d.DamageVersus(s));
      }
    }

    Console.WriteLine("\n=== A.3 weapon defaults (real engine: a weapon that sets none of them)");
    var bare = new WeaponInfo("bare", new MiniYaml("", new List<MiniYamlNode>{
      new MiniYamlNode("Projectile", new MiniYaml("Bullet")),
      new MiniYamlNode("Warhead", new MiniYaml("SpreadDamage", new List<MiniYamlNode>{ new MiniYamlNode("Damage", new MiniYaml("1")) }))}));
    Console.WriteLine("bare weapon: Burst={0} BurstDelay={1} ReloadDelay={2} Range={3} MinRange={4} Charges={5} ValidTargets={6}", bare.Burst, bare.BurstDelay, bare.ReloadDelay, bare.Range, bare.MinRange, bare.Charges, J(bare.ValidTargets));
    Console.WriteLine("weapons in the mod that set BurstDelay explicitly vs not (Burst>1 only):");
    foreach (var kv in rs.Weapons.OrderBy(k => k.Key)) if (kv.Value.Burst > 1) Console.WriteLine("    {0}: Burst={1} BurstDelay={2}", kv.Key, kv.Value.Burst, kv.Value.BurstDelay);
  }
}


