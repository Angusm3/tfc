param($pat)
$p=$PSScriptRoot
foreach($f in 'OpenRA.Game.exe','OpenRA.Mods.Common.dll','OpenRA.Mods.RA.dll','OpenRA.Mods.Cnc.dll'){ $a=[Reflection.Assembly]::LoadFrom("$p\$f"); try{$ts=$a.GetTypes()}catch{$ts=$_.Exception.Types|?{$_}}; foreach($t in $ts){ if($t.FullName -match $pat){ "$f  $($t.FullName)" } } }
