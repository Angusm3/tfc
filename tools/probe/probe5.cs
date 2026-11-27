using System; using System.Collections.Generic; using System.IO; using System.Linq; using System.Reflection; using OpenRA; using OpenRA.GameRules; using OpenRA.Traits; using OpenRA.FileSystem; using OpenRA.Mods.RA; using OpenRA.Mods.RA.Power; using OpenRA.Mods.RA.Buildings;
// probe5: what the 2014 engine does with power, build time and storage as written in the 0.32 rules.
//  - is there a `Power` field on the Building trait (BuildingInfo)?  (reflection)
//  - power the engine really applies: every PowerInfo.Amount on the actor (the `Power: Amount:` trait)
//  - CustomBuildTimeValueExts.GetBuildTime(ActorInfo) (engine call) for actors with and without CustomBuildTimeValue
//  - StoresResourcesInfo.Capacity as the engine parsed it
// Usage: probe5.exe <probe dir holding mods/tfc>
public static class Program {
  static object T(ActorInfo a, string n) { return a.Traits.WithInterface<ITraitInfo>().FirstOrDefault(x => x.GetType().Name == n); }
  static object F(object o, string f) { return o == null ? null : o.GetType().GetField(f).GetValue(o); }
  static int Pow(ActorInfo a) { return a.Traits.WithInterface<ITraitInfo>().Where(x => x.GetType().Name == "PowerInfo").Sum(x => (int)F(x, "Amount")); }
  static object BuildTime(ActorInfo a) { var v = T(a, "ValuedInfo"); if (v == null) return "<no Valued>"; var m = v.GetType().Assembly.GetType("OpenRA.Mods.RA.Buildings.CustomBuildTimeValueExts").GetMethod("GetBuildTime"); return m.Invoke(null, new object[] { a }); }
  static object Cap(ActorInfo a) { var t = a.Traits.WithInterface<ITraitInfo>().FirstOrDefault(x => x.GetType().Name == "StoresResourcesInfo"); return t == null ? null : t.GetType().GetField("Capacity").GetValue(t); }
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

    Console.WriteLine("\n=== fields of the engine's BuildingInfo (the `Building:` trait), as loaded by the mod's own assembly");
    var bt = rs.Actors["atwr"].Traits.WithInterface<ITraitInfo>().First(x => x.GetType().Name == "BuildingInfo").GetType();
    foreach (var f in bt.GetFields()) Console.WriteLine("    {0} {1}", f.FieldType.Name, f.Name);
    Console.WriteLine("BuildingInfo has a field named Power: {0}", bt.GetField("Power") != null);
    var pt = rs.Actors["nuke"].Traits.WithInterface<ITraitInfo>().First(x => x.GetType().Name == "PowerInfo").GetType();
    Console.WriteLine("fields of PowerInfo (the `Power:` trait): " + string.Join(", ", pt.GetFields().Select(f => f.Name)));

    Console.WriteLine("\n=== power the engine applies (sum of PowerInfo.Amount), actors with any Power trait");
    foreach (var a in rs.Actors.Values.OrderBy(x => x.Name)) {
      var n = a.Traits.WithInterface<ITraitInfo>().Count(x => x.GetType().Name == "PowerInfo");
      if (n > 0) Console.WriteLine("    {0,-12} Power traits={1} amount={2}", a.Name, n, Pow(a));
    }
    Console.WriteLine("\n=== named buildings");
    foreach (var n in new[] { "atwr", "silo", "hand", "vlcn", "gtwr", "gun", "sam", "proc", "nuke", "hq", "obli", "pyle", "weap" }) {
      ActorInfo a; if (!rs.Actors.TryGetValue(n, out a)) { Console.WriteLine("    {0}: no such actor", n); continue; }
      Console.WriteLine("    {0,-6} PowerInfo amount={1,5}  Cost={2,5} CustomBuildTimeValue={3} engine GetBuildTime={4} StoresResources.Capacity={5}", n, Pow(a), F(T(a, "ValuedInfo"), "Cost") ?? "-", F(T(a, "CustomBuildTimeValueInfo"), "Value") ?? "<none>", BuildTime(a), Cap(a) ?? "<none>");
    }
    Console.WriteLine("\n=== all actors with StoresResources / CustomBuildTimeValue");
    foreach (var a in rs.Actors.Values.OrderBy(x => x.Name)) {
      var st = Cap(a); var cbt = F(T(a, "CustomBuildTimeValueInfo"), "Value");
      if (st != null || cbt != null) Console.WriteLine("    {0,-10} Capacity={1} CustomBuildTimeValue={2} Cost={3} engine GetBuildTime={4}", a.Name, st ?? "-", cbt ?? "-", F(T(a, "ValuedInfo"), "Cost") ?? "-", BuildTime(a));
    }
  }
}
