param([string]$OutputPath)
$ErrorActionPreference='Stop'
function Assert($v,$m){if(!$v){throw $m}}
$x=& (Join-Path $PSScriptRoot '../Read-RoutePath.ps1') -OutputPath $OutputPath
Assert ($x.golden.Count -eq 1) 'One real Golden'
$g=$x.golden[0]
Assert ($g.pathTopology -eq 'simple_path' -and $g.geometryStatus -eq 'supported' -and $g.logicalStatus -eq 'unresolved') 'Independent statuses'
Assert ($g.startTermination.terminationType -eq 'device_terminated_candidate' -and $g.endTermination.terminationType -eq 'device_terminated_candidate') 'Two device terminations'
$sum=0.0;foreach($s in $g.orderedSteps|Where-Object kind -eq geometry){$sum+=$s.length}
Assert ([math]::Abs($sum-$g.raw2DLengthDrawingUnits) -lt .000001) 'Only real geometry contributes length'
Assert (!$x.sourceGraphModified -and !$x.deviceBridgeCreated -and $g.INSUNITS -eq 0 -and $g.lengthEffect -eq 'unresolved') 'No graph mutation or unit conversion'
Import-Module (Join-Path $PSScriptRoot '../RoutePath.psm1') -Force
# Controlled two real segments separated by a reviewed visual gap.
$r=[pscustomobject]@{systemScope='fire_alarm';sourceSnapshot='test';compartmentRef='zone';nodes=@();edges=@()}
foreach($i in 0..3){$r.nodes+=,[pscustomobject]@{nodeId="n$i";point=@($i,0,0)}}
foreach($pair in @(@(0,1),@(2,3))){$a=$pair[0];$b=$pair[1];$r.edges+=,[pscustomobject]@{edgeId="e$a";fromNode="n$a";toNode="n$b";startXY=@($a,0,0);endXY=@($b,0,0);segmentLength=1;rawEntityRef="test:h$a";systemScope='fire_alarm'}}
$t=[pscustomobject]@{compartmentRef='zone';terminations=@();endpointContacts=@();deviceAttachments=@();continuations=@()}
foreach($i in @(0,3)){$t.terminations+=,[pscustomobject]@{endpointRef="n$i";terminationType='device_terminated_candidate';status='supported_candidate';deviceRefs=@("d$i")}}
$j=[pscustomobject]@{sourceSnapshot='test';candidates=@([pscustomobject]@{candidateId='jump';beforeEndpointRef='n1';afterEndpointRef='n2';beforeEdgeRef='e0';afterEdgeRef='e2';continuityStatus='supported';crossingConnectionAllowed=$false;systemScopeCompatibility='compatible_candidate';topologySemantic='crossing_jump_continuation';gapDistance=1;evidenceRefs=@('crossed-not-connected')})}
$p=[pscustomobject]@{relations=@()}
$case=Find-PlanRoutePath $r $t $j $p 'test-view'
Assert ($case.golden.Count -eq 1 -and $case.golden[0].raw2DLength -eq 2 -and $case.golden[0].visualGapLength -eq 1) 'Visual gap separated from real length'
$t.terminations+=,[pscustomobject]@{endpointRef='n1';terminationType='terminal_box_boundary_candidate';status='supported_candidate';deviceRefs=@('DZX')}
Assert ((Find-PlanRoutePath $r $t $j $p 'test-view').golden.Count -eq 0) 'DZX cannot be crossed by jump'
$t.terminations=@($t.terminations|Where-Object endpointRef -ne n1)
$j.candidates[0].continuityStatus='partial'
Assert ((Find-PlanRoutePath $r $t $j $p 'test-view').golden.Count -eq 0) 'Unverified jump cannot complete route'
$j.candidates[0].continuityStatus='supported'
$j.candidates[0].crossingConnectionAllowed=$true
Assert ((Find-PlanRoutePath $r $t $j $p 'test-view').golden.Count -eq 0) 'Crossed connection forbidden'
$j.candidates=@();$t.continuations=@([pscustomobject]@{deviceRef='same-device';status='partial'})
Assert ((Find-PlanRoutePath $r $t $j $p 'test-view').golden.Count -eq 0) 'No device-mediated invented bridge'
# Actual T branch must remain a subgraph, never arbitrarily ordered.
$r.edges+=,[pscustomobject]@{edgeId='e1';fromNode='n1';toNode='n2';startXY=@(1,0,0);endXY=@(2,0,0);segmentLength=1;rawEntityRef='test:h1';systemScope='fire_alarm'}
$r.nodes+=,[pscustomobject]@{nodeId='nb';point=@(1,1,0)}
$r.edges+=,[pscustomobject]@{edgeId='eb';fromNode='n1';toNode='nb';startXY=@(1,0,0);endXY=@(1,1,0);segmentLength=1;rawEntityRef='test:hb';systemScope='fire_alarm'}
$case=Find-PlanRoutePath $r $t $j $p 'test-view'
Assert ($case.golden.Count -eq 0 -and $case.topologyAudit[0].pathTopology -eq 'branched_subgraph') 'Do not linearize branch'
$r.edges[0].systemScope='unknown';$blocked=$false;try{Find-PlanRoutePath $r $t $j $p 'test-view'|Out-Null}catch{$blocked=$true};Assert $blocked 'Unknown not wildcard'
$root=Split-Path (Split-Path $PSScriptRoot)
foreach($pin in $x.sourceArtifacts){Assert ((Get-FileHash (Join-Path $root $pin.path)).Hash -ceq $pin.sha256) 'Frozen source changed'}
Write-Output "PASS RoutePath: Golden=$($g.orderedEdgeHandles -join ','); raw=$($g.raw2DLengthDrawingUnits); visualGap=$($g.visualGapLength); branches/jumps/device bridge/scope negatives passed"
