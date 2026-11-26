param($typeName,$methodName)
$p=$PSScriptRoot
$a=[Reflection.Assembly]::LoadFrom("$p\OpenRA.Game.exe")
$one=@{};$two=@{}
foreach($f in [Reflection.Emit.OpCodes].GetFields()){ $o=$f.GetValue($null); if($o -is [Reflection.Emit.OpCode]){ if($o.Size -eq 1){$one[[int]$o.Value]=$o}else{$two[[int]($o.Value -band 0xFF)]=$o} } }
$t=$a.GetType($typeName)
$ms=$t.GetMethods([Reflection.BindingFlags]'Public,NonPublic,Static,Instance,DeclaredOnly') | ? {$_.Name -eq $methodName}
foreach($m in $ms){
 "##### $m"
 $il=$m.GetMethodBody().GetILAsByteArray(); $i=0; $mod=$m.Module
 while($i -lt $il.Length){
  $off=$i; $b=$il[$i]; $i++
  if($b -eq 0xFE){ $o=$two[[int]$il[$i]]; $i++ } else { $o=$one[[int]$b] }
  $arg=''
  switch($o.OperandType.ToString()){
   'InlineNone'{}
   'ShortInlineBrTarget'{ $arg='IL_{0:x}' -f ($i+1+[sbyte]$il[$i]); $i+=1}
   'ShortInlineI'{ $arg=$il[$i]; $i+=1}
   'ShortInlineVar'{ $arg=$il[$i]; $i+=1}
   'InlineVar'{ $arg=[BitConverter]::ToInt16($il,$i); $i+=2}
   'InlineBrTarget'{ $arg='IL_{0:x}' -f ($i+4+[BitConverter]::ToInt32($il,$i)); $i+=4}
   'InlineI'{ $arg=[BitConverter]::ToInt32($il,$i); $i+=4}
   'InlineI8'{ $i+=8}
   'ShortInlineR'{ $i+=4}
   'InlineR'{ $i+=8}
   'InlineSwitch'{ $n=[BitConverter]::ToInt32($il,$i); $i+=4+4*$n}
   'InlineString'{ $arg='"'+$mod.ResolveString([BitConverter]::ToInt32($il,$i))+'"'; $i+=4}
   default { $tok=[BitConverter]::ToInt32($il,$i); $i+=4
     try{ $r=$mod.ResolveMember($tok,$m.DeclaringType.GetGenericArguments(),$m.GetGenericArguments()); $arg="$($r.DeclaringType)::$r" }catch{ $arg="tok $tok" } }
  }
  '{0:x4}: {1} {2}' -f $off,$o.Name,$arg
 }
}
