$p=$PSScriptRoot
foreach($f in 'OpenRA.Mods.RA.dll','OpenRA.Mods.Common.dll','OpenRA.Game.exe'){ $a=[Reflection.Assembly]::LoadFrom("$p\$f"); try{$ts=$a.GetTypes()}catch{$ts=$_.Exception.Types|?{$_}}
 foreach($t in $ts){ foreach($m in $t.GetMethods([Reflection.BindingFlags]'Public,NonPublic,Static,Instance,DeclaredOnly')){ try{ $b=$m.GetMethodBody(); if(-not $b){continue}; $il=$b.GetILAsByteArray(); $mod=$m.Module
   for($i=0;$i -lt $il.Length-4;$i++){ if($il[$i] -eq 0x28 -or $il[$i] -eq 0x6F){ try{ $r=$mod.ResolveMember([BitConverter]::ToInt32($il,$i+1)); if($r.Name -eq 'IsValidAgainst' -and $r.DeclaringType.Name -eq 'WeaponInfo'){ "$f $($t.FullName)::$($m.Name)"; break } }catch{} } } }catch{} } } }
