using System; using System.Collections.Generic; using System.Linq; using System.Reflection; using OpenRA;
public static class Program {
  static List<MiniYamlNode> P(string s){ return MiniYaml.FromString(s); }
  static void S(string title, List<MiniYamlNode> l){ Console.WriteLine("--- "+title); Console.Write(l.WriteToString()); }
  static MethodInfo mwp = typeof(ActorInfo).GetMethod("MergeWithParent", BindingFlags.NonPublic|BindingFlags.Public|BindingFlags.Static);
  static void Inh(string title, string file){
    Console.WriteLine("--- INHERIT: "+title);
    var d = P(file).ToDictionary(n=>n.Key, n=>n.Value);
    try {
      var r = (MiniYaml)mwp.Invoke(null, new object[]{ d["C"], d });
      Console.Write(r.Nodes.WriteToString());
    } catch(Exception e){ Console.WriteLine("threw: "+(e.InnerException??e).Message); }
  }
  public static void Main(){
    S("Liberal(A: Cost empty ; B: Cost 7)", MiniYaml.MergeLiberal(P("U:\n\tCost:\n\tX: 1\n"),P("U:\n\tCost: 7\n")));
    S("Liberal(A: Cost 5 ; B: Cost empty)", MiniYaml.MergeLiberal(P("U:\n\tCost: 5\n"),P("U:\n\tCost:\n")));
    S("Liberal(top-level value) A: U: a ; B: U: b", MiniYaml.MergeLiberal(P("U: a\n"),P("U: b\n")));
    try { S("Liberal(A has dup key W twice ; B has W)", MiniYaml.MergeLiberal(P("W:\n\tR: 1\nW:\n\tS: 2\n"),P("W:\n\tT: 3\n"))); } catch(Exception e){ Console.WriteLine("dupA threw "+(e.InnerException??e).Message); }
    try { S("Liberal(A empty ; B dup W)", MiniYaml.MergeLiberal(new List<MiniYamlNode>(),P("W:\n\tR: 1\nW:\n\tS: 2\n"))); } catch(Exception e){ Console.WriteLine("dupB threw "+(e.InnerException??e).Message); }
    try { Console.WriteLine("ToDictionary on dup: " + P("W:\n\tR: 1\nW:\n\tS: 2\n").ToDictionary(n=>n.Key,n=>n.Value).Count); } catch(Exception e){ Console.WriteLine("ToDictionary dup threw: "+e.Message); }
    string par="P:\n\tHealth:\n\t\tHP: 10\n\t\tRadius: 5\n\tCloak:\n\t\tReq: cloak\n\t\tDelay: 90\n\tFoo:\n\t\tX: 1\n\tFoo@2:\n\t\tX: 2\n";
    Inh("child overrides value, removes Foo and Cloak/Req", par+"C:\n\tInherits: P\n\tHealth:\n\t\tHP: 99\n\t-Foo:\n\tCloak:\n\t\t-Req:\n");
    Inh("child key order (child adds Z first)", par+"C:\n\tInherits: P\n\tZ:\n\t\tV: 1\n\tHealth:\n\t\tHP: 99\n");
    Inh("child defines Foo and -Foo", par+"C:\n\tInherits: P\n\tFoo:\n\t\tX: 5\n\t-Foo:\n");
    Inh("child -Foo then Foo (order)", par+"C:\n\tInherits: P\n\t-Foo:\n\tFoo:\n\t\tX: 5\n");
    Inh("-Foo that removes nothing", par+"C:\n\tInherits: P\n\t-Nope:\n");
    Inh("-Foo@2 only removes the suffixed key", par+"C:\n\tInherits: P\n\t-Foo@2:\n");
    Inh("empty child value does not blank parent", par+"C:\n\tInherits: P\n\tHealth:\n\t\tHP:\n");
    Inh("three levels, middle removes, last re-adds", par+"M:\n\tInherits: P\n\t-Foo:\n\t-Health:\n\nC:\n\tInherits: M\n\tHealth:\n\t\tHP: 1\n");
    Inh("Inherits@x (suffixed) ignored?", par+"C:\n\tInherits@1: P\n\tHealth:\n\t\tHP: 99\n");
    Inh("unknown parent", "C:\n\tInherits: Nope\n");
    Inh("case: Inherits: p vs P", par+"C:\n\tInherits: p\n");
    // across two files then inheritance: file1 (earlier) has Foo, file2 (later) has -Foo
    var f1 = P("P:\n\tFoo:\n\t\tX: 1\n\tBar:\n\t\tY: 1\nC:\n\tInherits: P\n\tFoo:\n\t\tX: 9\n");
    var f2 = P("C:\n\t-Foo:\n\t-Bar:\n");
    var m = MiniYaml.MergeLiberal(f1, f2);
    var d2 = m.ToDictionary(n=>n.Key, n=>n.Value);
    Console.WriteLine("--- two files: earlier C has Foo, later C has -Foo,-Bar; merged-then-inherited:");
    Console.Write(((MiniYaml)mwp.Invoke(null,new object[]{d2["C"],d2})).Nodes.WriteToString());
    var m2 = MiniYaml.MergeLiberal(f2, f1); var d3 = m2.ToDictionary(n=>n.Key, n=>n.Value);
    Console.WriteLine("--- reversed order (the -Foo file first):");
    Console.Write(((MiniYaml)mwp.Invoke(null,new object[]{d3["C"],d3})).Nodes.WriteToString());
  }
}
