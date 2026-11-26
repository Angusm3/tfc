using System; using System.Collections.Generic; using System.IO; using System.Linq; using System.Reflection; using System.Text; using OpenRA;
// Replays what OpenRA release-20141029 RulesetCache.LoadYamlRules + ActorInfo.MergeWithParent do, using the
// engine's own static methods, over the mod's Rules and Weapons file lists, and dumps every resolved definition.
public static class Program {
  static void Flat(StringBuilder sb, List<MiniYamlNode> nodes, int d) {
    foreach (var n in nodes) {
      sb.Append(new string('\t', d)).Append(n.Key).Append(": ").Append(n.Value.Value ?? "<null>").Append('\n');
      Flat(sb, n.Value.Nodes, d + 1);
    }
  }
  static List<string> Section(string modyaml, string section) {
    var res = new List<string>(); bool inside = false;
    foreach (var raw in File.ReadAllLines(modyaml)) {
      if (raw.Trim().Length == 0 || raw.TrimStart().StartsWith("#")) continue;
      if (raw[0] != ' ' && raw[0] != '\t') { inside = raw.Split(':')[0].Trim() == section; continue; }
      if (inside) res.Add(raw.Trim());
    }
    return res;
  }
  static List<MiniYamlNode> Load(string root, string modyaml, string section) {
    var acc = new List<MiniYamlNode>();   // seed = map.RuleDefinitions (empty for default rules)
    foreach (var e in Section(modyaml, section)) {
      var rel = e.StartsWith("./mods/") ? e.Substring(7).Split(new[]{'/'}, 2)[1] : e;
      var nodes = MiniYaml.FromFile(Path.Combine(root, rel.Replace('/', Path.DirectorySeparatorChar)));
      acc = MiniYaml.MergeLiberal(acc, nodes);     // exactly Aggregate(seed, MergeLiberal) from LoadYamlRules
    }
    return acc;
  }
  public static void Main(string[] args) {
    string root = args[0], outDir = args[1], modyaml = Path.Combine(root, "mod.yaml");
    var rules = Load(root, modyaml, "Rules");
    var weapons = Load(root, modyaml, "Weapons");
    var dict = rules.ToDictionary(n => n.Key, n => n.Value);   // throws on duplicate keys, like the loader's yy
    var mwp = typeof(ActorInfo).GetMethod("MergeWithParent", BindingFlags.NonPublic | BindingFlags.Public | BindingFlags.Static);
    var sbA = new StringBuilder();
    foreach (var n in rules) {
      var r = (MiniYaml)mwp.Invoke(null, new object[] { n.Value, dict });
      sbA.Append("@@ ").Append(n.Key).Append('\n'); Flat(sbA, r.Nodes, 1);
    }
    var sbW = new StringBuilder();
    var wd = weapons.ToDictionary(n => n.Key, n => n.Value);
    foreach (var n in weapons) { sbW.Append("@@ ").Append(n.Key).Append('\n'); Flat(sbW, n.Value.Nodes, 1); }
    File.WriteAllText(Path.Combine(outDir, "engine-actors.txt"), sbA.ToString());
    File.WriteAllText(Path.Combine(outDir, "engine-weapons.txt"), sbW.ToString());
    Console.WriteLine("actors/templates: " + rules.Count + "  weapons: " + weapons.Count);
  }
}
