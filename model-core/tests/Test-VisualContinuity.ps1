param([string]$OutputPath)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../VisualContinuity.psm1') -Force
function Assert($c,$m){if(!$c){throw $m}}
$root=Resolve-Path (Join-Path $PSScriptRoot '../..')
$rp=Join-Path $root 'outputs/fire-alarm-routing/results.json';$hash=(Get-FileHash $rp).Hash
$x=& (Join-Path $PSScriptRoot '../Read-VisualContinuity.ps1') -OutputPath $OutputPath
Assert (@($x.candidates|Where-Object continuityStatus -eq supported).Count -eq 7) 'Seven reviewed jumps'
Assert (@($x.candidates|Where-Object {$_.blockingReasons -contains 'jump_without_crossed_geometry'}).Count -eq 2) 'Two near collinear negatives blocked'
Assert ($x.rawComponentCount -eq 74 -and $x.continuityAdjustedGroupCountCandidate -eq 67 -and $x.rawEdgeCount -eq 76 -and $x.rawOpenEndpointCount -eq 148) 'Separate grouping only'
Assert ($x.affectedOpenEndpointRefs.Count -eq 14 -and $x.affectedRawComponentRefs.Count -eq 14 -and $x.potentialMergedGroups -eq 7) 'Affected references and candidate groups'
Assert ($x.createdRoutingEdges.Count -eq 0 -and $x.crossingConnections.Count -eq 0 -and @($x.candidates|Where-Object crossingConnectionAllowed).Count -eq 0) 'Crossed lines never connect'
Assert (@($x.candidates|Where-Object quantityLengthEffect -ne unresolved).Count -eq 0) 'No length admission'
# Controlled perturbations reuse generic inputs; neither handles nor expected lengths drive admission.
$r=Get-Content $rp -Raw -Encoding utf8|ConvertFrom-Json
$j=Get-Content (Join-Path $root 'outputs/routing-coverage-audit/crossing-jumps.json') -Raw -Encoding utf8|ConvertFrom-Json
$iv=Get-Content (Join-Path $root 'outputs/routing-coverage-audit/inventory.json') -Raw -Encoding utf8|ConvertFrom-Json
$gg=@($iv.entities|ForEach-Object {[pscustomobject]@{handle=$_.handle;sourceSnapshot=$r.sourceSnapshot;rawEntityRef=$r.sourceSnapshot+':'+$_.handle;vertices=$_.vertices;bulges=$_.bulges;layer=$_.layer}})
foreach($case in @('scope','layer','range','pattern','crossed_missing','direction','z','crossed_offset','crossed_collinear','crossed_source','ambiguous_pair')){
 $rr=$r|ConvertTo-Json -Depth 60|ConvertFrom-Json;$pair=$j.candidates[0]|ConvertTo-Json -Depth 60|ConvertFrom-Json;$pat=$x.pattern|ConvertTo-Json -Depth 60|ConvertFrom-Json;$geom=$gg|ConvertTo-Json -Depth 60|ConvertFrom-Json
 $edge=@($rr.edges|Where-Object edgeId -eq $pair.afterEdgeRef)[0]
 switch($case){
 'scope'{$edge.systemScope='unknown'}
 'layer'{$edge.layer='different'}
 'range'{$pat.maxGap=1}
 'pattern'{$pat.evidenceRefs=@()}
 'crossed_missing'{$pair.crossedEdgeRef=@()}
 'direction'{if($pair.endpointRefs[1] -eq $edge.fromNode){$edge.endXY[1]+=1000}else{$edge.startXY[1]+=1000}}
 'z'{@($rr.openEndpoints|Where-Object nodeRef -eq $pair.endpointRefs[1])[0].coordinates[2]=100}
 'crossed_offset'{foreach($g in $geom|Where-Object handle -in $pair.crossedEdgeRef){foreach($v in $g.vertices){$v[0]+=10000}}}
 'crossed_collinear'{foreach($g in $geom|Where-Object handle -in $pair.crossedEdgeRef){$g.vertices=@(@($rr.openEndpoints|Where-Object nodeRef -eq $pair.endpointRefs[0])[0].coordinates,@($rr.openEndpoints|Where-Object nodeRef -eq $pair.endpointRefs[1])[0].coordinates)}}
 'crossed_source'{foreach($g in $geom|Where-Object handle -in $pair.crossedEdgeRef){$g.sourceSnapshot='different'}}
 }
 $pairs=if($case -eq 'ambiguous_pair'){@($pair,$pair)}else{@($pair)}
 $out=New-RoutingContinuityView $rr $pairs $geom $pat
 Assert (@($out.candidates|Where-Object continuityStatus -eq supported).Count -eq 0) "Must not admit $case"
 Assert ($out.continuityAdjustedGroupCountCandidate -eq 74) "Must not group $case"
}
Assert ((Get-FileHash $rp).Hash -ceq $hash) 'Raw graph unchanged'
$coverage=Get-Content (Join-Path $root 'model-core/capabilities.json') -Raw -Encoding utf8|ConvertFrom-Json
$lengthCapability=@($coverage|Where-Object id -eq jump_length_semantics)[0]
Assert ($lengthCapability.status -eq 'needs_review' -and $lengthCapability.semanticStatus -eq 'unresolved') 'Capability status must remain schema compatible, length semantics unresolved'
Write-Host 'PASS VisualContinuity: 7 supported jumps, 2 blocked negatives; 74 raw components / 67 candidate groups; no crossing connection or length change'
