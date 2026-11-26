using System; using OpenRA;
public static class Program { public static void Main(){ var m = new Manifest("tfc"); Console.WriteLine("Rules:"); foreach(var r in m.Rules) Console.WriteLine("  "+r); Console.WriteLine("Weapons:"); foreach(var r in m.Weapons) Console.WriteLine("  "+r); } }
