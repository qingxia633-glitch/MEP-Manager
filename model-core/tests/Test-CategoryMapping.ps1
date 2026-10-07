$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../CategoryMapping.psm1') -Force
$script:n=0
function Check($ok,$why){if(!$ok){throw $why};$script:n++}
function Clone($x){$x|ConvertTo-Json -Depth 40|ConvertFrom-Json}
$c=@{nodeRef='node';roleCandidate='role_a';systemIdentity='system_a';compartmentRef='zone';systemQuantityCandidate=1}
$b=@{compartmentRef='zone';polygonRef='polygon';boundaryStatus='supported';closed=$true;frameRef='target';vertices=@(@(0.,0.,0.),@(10.,0.,0.),@(10.,4.,0.),@(4.,4.,0.),@(4.,10.,0.),@(0.,10.,0.))}
$t=@{transformRef='transform';status='supported';polygonRef='polygon';targetFrameRef='target'}
$i=@{instanceRef='i';frameRef='target';position=@(2.,2.,0.)}
$r=@{instanceRef='i';roleRef='role:i';roles=@('role_a');roleStatus='explicit';status='supported';systemIdentity='system_a';sourceRefs=@('raw:i')}
function Run($cc=$c,$bb=$b,$tt=$t,$ii=@($i),$rr=@($r)){Resolve-CategoryToPlanInstanceSet $cc $bb $tt $ii $rr}
$x=Run
Check ($x.membersExplicit.Count -eq 1 -and $x.quantityConsistencyStatus -eq 'consistent_candidate') 'Basic mapping'
$z=Clone $t;$z.status='unresolved';Check ((Run -tt $z).membersExplicit.Count -eq 0) 'Unresolved transform'
$z=Clone $b;$z.boundaryStatus='partial';Check ((Run -bb $z).membersExplicit.Count -eq 0) 'Unconfirmed boundary'
$z=Clone $r;$z.roleStatus='unresolved';Check ((Run -rr @($z)).unresolved.Count -eq 1) 'Unknown role'
$z=Clone $r;$z.roleStatus='inherited_candidate';$x=Run -rr @($z);Check ($x.membersInherited.Count -eq 1 -and !$x.confirmedBinding) 'Inherited stays candidate'
$z=Clone $i;$z.position=@(0.,2.,0.);$x=Run -ii @($z);Check ($x.onBoundary.Count -eq 1 -and $x.membersExplicit.Count -eq 0) 'Boundary separate'
$z=Clone $c;$z.systemQuantityCandidate=99;$x=Run -cc $z;Check ($x.membersExplicit.Count -eq 1 -and $x.quantityDelta -eq 98 -and 'quantity_mismatch' -in $x.reviewItems.reason) 'No reverse selection'
$z=Clone $c;$z.compartmentRef='other';Check ((Run -cc $z).membersExplicit.Count -eq 0) 'Compartment isolation'
$z=Clone $r;$z.systemIdentity='other';Check ((Run -rr @($z)).membersExplicit.Count -eq 0) 'System isolation'
$z=Clone $i;$z.position=@(8.,8.,0.);Check ((Run -ii @($z)).outside.Count -eq 1) 'Concave polygon not bounds'
$z=Clone $c;$z.PSObject.Properties.Remove('systemQuantityCandidate');$x=Run -cc $z;Check ($x.membersExplicit.Count -eq 1 -and $x.quantityConsistencyStatus -eq 'comparison_unavailable') 'Missing quantity still maps'
$z=Clone $i;$z.frameRef='other';Check ((Run -ii @($z)).unresolved.Count -eq 1) 'Instance coordinate scope'
$z=Clone $r;$z.systemIdentity='unknown';Check ((Run -rr @($z)).unresolved.Count -eq 1) 'Unknown not wildcard'
$z=Clone $r;$z.status='partial';$x=Run -rr @($z);Check ($x.membersPartial.Count -eq 1 -and $x.roleSupportedExpressionCount -eq 0) 'Partial separate'
$z=Clone $r;$z.sourceRefs=@();Check ((Run -rr @($z)).unresolved.Count -eq 1) 'Role provenance required'
$z=Clone $r;$z.roles=@('role_a','role_b');Check ((Run -rr @($z)).unresolved.Count -eq 1) 'Multiple role ambiguity'
$z=Clone $b;$z.vertices=@(@(0.,0.,0.),@(10.,10.,0.),@(0.,10.,0.),@(10.,0.,0.));Check ((Run -bb $z).membersExplicit.Count -eq 0) 'Self-intersecting polygon blocked'
$z=Clone $i;$z|Add-Member compartmentRef other;Check ((Run -ii @($z)).unresolved.Count -eq 1) 'Conflicting instance compartment'
$before=@($c,$b,$t,$i,$r)|ConvertTo-Json -Depth 40;$null=Run
Check (($before) -ceq (@($c,$b,$t,$i,$r)|ConvertTo-Json -Depth 40)) 'No input mutation'
. (Join-Path $PSScriptRoot 'Read-CategoryMappingFixture.ps1')
foreach($f in @(Read-CategoryMappingFixture)){
 $x=Resolve-CategoryToPlanInstanceSet $f.category $f.compartment $f.transform $f.instances $f.roles
 Check ($x.membersExplicit.Count -eq $f.expectedExplicit) ('Explicit '+$f.name)
 Check ($x.membersInherited.Count -eq $f.expectedInherited) ('Inherited '+$f.name)
 Check ($x.quantityDelta -eq $f.expectedDelta) ('Delta '+$f.name)
 Check ($x.onBoundary.Count -eq 0 -and $x.unresolved.Count -eq 0) ('Classification '+$f.name)
 Check (!$x.confirmedBinding) 'Never confirmed'
 Check (@($x.assessments|Where-Object confirmedRole).Count -eq 0) 'No confirmed roles'
 Check (($x.membersExplicit.Count+$x.membersInherited.Count+$x.membersPartial.Count+$x.outside.Count+$x.onBoundary.Count+$x.unresolved.Count) -eq $f.instances.Count) 'Universe fully accounted for'
 Check (@($x.assessments|Where-Object {$null -eq $_.boundaryDistanceXY}).Count -eq 0) 'Real distance evaluated for every eligible instance'
 if($f.name -eq 'smoke_detector'){
  Check ('quantity_mismatch' -in $x.reviewItems.reason -and $x.completenessStatus -eq 'partial') 'Mismatch review remains open'
 }
 if($f.name -eq 'manual_call'){
  foreach($case in @(@('13974',100.152895),@('139B4',150.006002))){
   $a=@($x.assessments|Where-Object {$_.instanceRef.EndsWith(':'+$case[0])})
   Check ($a.Count -eq 1 -and [math]::Abs($a[0].boundaryDistanceXY-$case[1]) -lt 0.001) ('Corrected boundary distance '+$case[0])
  }
 }
 $x|Select-Object roleCandidate,roleSupportedExpressionCount,quantityConsistencyStatus,quantityDelta,completenessStatus,@{n='explicit';e={$_.membersExplicit.Count}},@{n='inherited';e={$_.membersInherited.Count}},@{n='outside';e={$_.outside.Count}}|ConvertTo-Json -Compress
}
"PASS: $script:n category mapping checks."

