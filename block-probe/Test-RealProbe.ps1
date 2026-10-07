param([string]$Report=(Join-Path $PSScriptRoot '../local_test_data/block-probe-20260916/block-definition-probe.txt'))
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'BlockProbe.psm1') -Force
$p=Read-BlockProbe $Report
if($p.Snapshot -ne 'BC42924C4B4FB3089DC5FC3DF371F145014165544A26E56B963526B5E136140C'){throw 'Real acceptance fixture changed; review snapshot before updating expectations'}
$out=& (Join-Path $PSScriptRoot 'Compare-Blocks.ps1') -Report $Report
$result=$out|ConvertFrom-Json
$n=0
function Check($ok,$msg){if(!$ok){throw $msg};$script:n++}
Check ($result.Results.Count -eq 6) 'all six definition pairs complete without errors'
foreach($pair in $result.Results){
 Check ($pair.Comparisons.Count -eq 4) 'all comparison modes'
 foreach($r in $pair.Comparisons){Check ($r.LeftCount -eq 81 -and $r.RightCount -eq 81) 'preserve direct entity multiplicity'}
 $c=$pair.Comparisons|Where-Object Mode -eq content
 $expected=if($pair.Right -eq '*U404' -or $pair.Left -eq '*U404'){79}else{81}
 Check ($c.Matched -eq $expected) 'preserve reviewed normalized content result'
}
# Visibility multiset counts alone cannot detect a swap between different entities.
$a=$p.Blocks|Where-Object Name -eq '*U401';$d=$p.Blocks|Where-Object Name -eq '*U404'
foreach($spec in @(@('30257','30545',$false,$true),@('3025A','3053C',$true,$false))){
 $ae=$a.Entities|Where-Object Handle -eq $spec[0];$de=$d.Entities|Where-Object Handle -eq $spec[1]
 Check ((@($ae.Fields|Where-Object {$_.Code -eq 60 -and $_.Value -eq '1'}).Count -gt 0) -eq $spec[2]) 'reviewed left visibility'
 Check ((@($de.Fields|Where-Object {$_.Code -eq 60 -and $_.Value -eq '1'}).Count -gt 0) -eq $spec[3]) 'reviewed right visibility'
}
"PASS: $n real probe regression checks; output not saved"
