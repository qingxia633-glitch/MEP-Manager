param([Parameter(Mandatory)][string]$Report,[double]$Tolerance=0.00001)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'BlockProbe.psm1') -Force
$p=Read-BlockProbe $Report
$comparisons=@(for($i=0;$i -lt $p.Blocks.Count;$i++){for($j=$i+1;$j -lt $p.Blocks.Count;$j++){
 $a=$p.Blocks[$i];$b=$p.Blocks[$j]
 [pscustomobject]@{Left=$a.Name;Right=$b.Name;DefinitionHeader=(Compare-ProbeEntities @([pscustomobject]@{Handle='definition';Fields=@($a.Definition|Where-Object Code -ne 2)}) @([pscustomobject]@{Handle='definition';Fields=@($b.Definition|Where-Object Code -ne 2)}) content $Tolerance);Comparisons=@(foreach($m in @('content','geometry','style','visibility')){Compare-ProbeEntities $a.Entities $b.Entities $m $Tolerance})}
}})
[pscustomobject]@{Source=$p.SourcePath;Snapshot=$p.Snapshot;Tolerance=$Tolerance;Results=$comparisons;Limitations=@('Definition records only; pointer/identity fields excluded; no nested expansion.','Geometry comparison is ordered raw DXF representation comparison, not general geometric equivalence.','Tolerance applies to geometric numeric components, including angles in radians.','Visibility result is DXF/layer flag candidate evidence, not evaluated dynamic visibility.','Separate comparison categories are independent multisets, not proof of semantic role correspondence.');HumanObservation='User observed no obvious red-line or green composite-symbol shape difference between the selected 20A and 32A instances at current zoom; observation does not override CAD differences.'}|ConvertTo-Json -Depth 12
