using System; using System.Collections.Generic; using System.IO; using System.Linq; using System.Reflection; using OpenRA; using OpenRA.GameRules; using OpenRA.Traits; using OpenRA.FileSystem; using OpenRA.Mods.RA;
// Loads the real 0.32 mod through the 2014 engine (ModData + RulesetCache.LoadDefaultRules) and reports what the
// engine itself parsed: warhead and weapon target defaults, and the armour modifier an actor takes.
public static class Program {
  static string J(string[] a) { return a == null ? "<null>" : "[" + string.Join(",", a) + "]"; }
  public static void Main(string[] args) {
    Directory.SetCurrentDirectory(args[0]);
    Directory.CreateDirectory(Path.Combine(args[0], "logs")); Log.LogPath = Path.Combine(args[0], "logs") + Path.DirectorySeparatorChar; foreach (var c in new[]{"perf","debug","sync","graphics","geoip","server","irc","nat","sound"}) Log.AddChannel(c, c + ".log");
    Game.Settings = new Settings(null, new Arguments());
    var md = new ModData("tfc");
    typeof(Game).GetField("modData", BindingFlags.NonPublic | BindingFlags.Public | BindingFlags.Static).SetValue(null, md);
    GlobalFileSystem.UnmountAll();
    foreach (var kv in md.Manifest.Folders) GlobalFileSystem.Mount(kv);
    var rs = md.RulesetCache.LoadDefaultRules();
    Console.WriteLine("loaded: actors={0} weapons={1}", rs.Actors.Count, rs.Weapons.Count);
    Console.WriteLine("--- defaults of a bare warhead / armour");
    var wh = new SpreadDamageWarhead();
    Console.WriteLine("Warhead default ValidTargets={0} InvalidTargets={1} AffectsParent={2} ValidStances={3}", J(wh.ValidTargets), J(wh.InvalidTargets), wh.AffectsParent, wh.ValidStances);
    var ai = new ArmorInfo();
    Console.WriteLine("ArmorInfo default Type={0}", ai.Type ?? "<null>");
    Console.WriteLine("--- weapons");
    foreach (var name in args.Skip(1)) {
      WeaponInfo w; if (!rs.Weapons.TryGetValue(name.ToLowerInvariant(), out w)) { Console.WriteLine(name + ": MISSING"); continue; }
      Console.WriteLine("{0}: weapon ValidTargets={1} Invalid={2} Burst={3} BurstDelay={4} ReloadDelay={5}", name, J(w.ValidTargets), J(w.InvalidTargets), w.Burst, w.BurstDelay, w.ReloadDelay);
      foreach (var x in w.Warheads) {
        var d = x as DamageWarhead;
        Console.WriteLine("    {0} ValidTargets={1} Invalid={2}{3}", x.GetType().Name, J(x.ValidTargets), J(x.InvalidTargets), d != null ? " Damage=" + d.Damage : "");
      }
    }
  }
}


