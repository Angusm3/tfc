param($t,$m,$asm='OpenRA.Game.exe')
$p=$PSScriptRoot
& 'C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe' -NoProfile -ExecutionPolicy Bypass -File "$p\il.ps1" $t $m $asm 2>&1 | % { $_ -replace 'System.Collections.Generic.','' -replace 'OpenRA\.','' -replace ', Game, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null','' -replace 'System\.Func`\d\[[^\]]*\]','Func' }

