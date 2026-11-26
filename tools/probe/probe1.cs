using System; using System.Collections.Generic; using System.Linq; using OpenRA;
public static class Program {
  static List<MiniYamlNode> P(string s){ return MiniYaml.FromString(s); }
  static void S(string title, List<MiniYamlNode> l){ Console.WriteLine("--- "+title); Console.Write(l.WriteToString()); }
  public static void Main(){
    string tfc="Vulcan:\n\tReloadDelay: 40\n\tBurst: 3\n\tWarhead@1Dam: SpreadDamage\n\t\tDamage: 10\n\t\tVersus:\n\t\t\tNone: 100\n\t\t\tConcrete: 0\n";
    string stock="Vulcan:\n\tReloadDelay: 2\n\tRange: 6c0\n\tWarhead@1Dam: SpreadDamage\n\t\tDamage: 100\n\t\tVersus:\n\t\t\tNone: 50\n\t\t\tHeavy: 35\nOnlyStock:\n\tRange: 1c0\n";
    S("MergeLiberal(A=tfc, B=stock)  [loader does Aggregate(seed, MergeLiberal): acc=Liberal(acc, nextFile)]", MiniYaml.MergeLiberal(P(tfc),P(stock)));
    S("MergeLiberal(A=stock, B=tfc)", MiniYaml.MergeLiberal(P(stock),P(tfc)));
    try { S("MergeStrict(tfc, stock)", MiniYaml.MergeStrict(P(tfc),P(stock))); } catch(Exception e){ Console.WriteLine("MergeStrict threw: "+e.Message); }
    string f1="U:\n\tCloak:\n\t\tA: 1\n\t\tB: 2\n\tFoo:\n\t\tX: 1\n";
    string f2="U:\n\t-Foo:\n\tCloak:\n\t\t-A:\n";
    S("-Removals: Liberal(f1 defines Foo,Cloak.A ; f2 has -Foo, Cloak/-A)", MiniYaml.MergeLiberal(P(f1),P(f2)));
    S("-Removals: Liberal(f2, f1)", MiniYaml.MergeLiberal(P(f2),P(f1)));
    S("case: Liberal(Tail, tail)", MiniYaml.MergeLiberal(P("Tail:\n\tRange: 1c0\n"),P("tail:\n\tRange: 2c0\n")));
    S("duplicate key within one file (FromString only)", P("W:\n\tRange: 1\nW:\n\tReload: 2\n"));
    S("MergeLiberal(Cost: 5 ; Cost: <empty>)", MiniYaml.MergeLiberal(P("U:\n\tCost: 5\n"),P("U:\n\tCost:\n")));
    S("MergeLiberal(Cost: 5 ; Cost: 7)", MiniYaml.MergeLiberal(P("U:\n\tCost: 5\n"),P("U:\n\tCost: 7\n")));
  }
}
