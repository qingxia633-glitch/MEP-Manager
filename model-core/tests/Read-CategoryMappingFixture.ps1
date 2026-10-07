# Reviewed real-source adapters. Handles, vocabulary and registration belong here, never in the mapper.
function Read-CategoryMappingFixture {
 Import-Module (Join-Path $PSScriptRoot '../RoleInheritance.psm1') -Force
 . (Join-Path $PSScriptRoot 'Read-SmokeRoleFixture.ps1')
 $smoke=Read-SmokeRoleFixture
 $inherited=Resolve-DeviceRoleInheritance $smoke.definition $smoke.instances
 $root=Join-Path $PSScriptRoot '../..'
 $planPath='local_test_data/fire-alarm-full-snapshot-20260923/MEP-full-entity-report.txt'
 $systemPath='local_test_data/fire-system-full-snapshot-20260925/MEP-full-entity-report.txt'
 $plan=[IO.File]::ReadAllText((Join-Path $root $planPath));$system=[IO.File]::ReadAllText((Join-Path $root $systemPath))
 function V($b,$key){[regex]::Match($b,'(?m)^'+[regex]::Escape($key)+'="([^"\r\n]*)"').Groups[1].Value}
 $sys=@{};foreach($b in [regex]::Split($system,'(?m)^EntityHandle=')){if($b -match '^"([^"]+)"'){$sys[$Matches[1]]=$b}}
 $probe=[IO.File]::ReadAllText((Join-Path $root ($smoke.polygonRef -replace ':55DF5$','')))
 $boundary=@([regex]::Split($probe,'(?m)^SourceInternalHandle=')|Where-Object {$_ -match '^"55DF5"'})[0]
 $vertices=[double[][]]@([regex]::Matches($boundary,'(?m)^DXF:10=\(([^)]+)\)')|ForEach-Object {$v=$_.Groups[1].Value -split '\s+'; ,@(([double]$v[0]+555932139.9856748),([double]$v[1]+553155197.1740737),0.0)})
 if($vertices.Count -ne 52 -or $boundary -notmatch '(?m)^Closed_RAW=:vlax-true|(?m)^DXF:70=1'){
  if($vertices.Count -ne 52 -or $boundary -notmatch '(?m)^Closed_RAW=T'){throw 'Fixture polygon evidence changed'}
 }
 $compartment=@{compartmentRef='AW-0009/防火分区1';polygonRef=$smoke.polygonRef;boundaryStatus='supported';closed=$true;frameRef=$planPath;vertices=$vertices;holes=@()}
 $transform=@{transformRef='reviewed-wall-registration:AW0009-to-fire-plan/translation-0--257900';status='supported';polygonRef=$smoke.polygonRef;targetFrameRef=$planPath}
 $specs=@(
  @{name='manual_call';node='15DF5';q='15DC0';systemRole='带电话插孔的手动报警按钮';rawRole='带火警电话插孔的手动报警按钮';explicit=10;inherited=0;delta=0},
  @{name='heat_detector';node='15E85';q='15E84';systemRole='感温火灾探测器';rawRole='感温探测器（点型）';explicit=12;inherited=0;delta=0},
  @{name='smoke_detector';node='15DF0';q='15DBE';systemRole='感烟探测器';rawRole='感烟探测器（点型）';explicit=20;inherited=88;delta=4}
 )
 foreach($spec in $specs){
  if((V $sys[$spec.node] AttributeText_RAW) -ne $spec.systemRole){throw 'System role changed'}
  $rawQuantity=V $sys[$spec.q] Text_RAW
  if($rawQuantity -notmatch '^[xX×]?(\d+)$'){throw 'Unreviewed quantity expression'};$quantity=[int]$Matches[1]
  $instances=@();$roles=@()
  if($spec.name -eq 'smoke_detector'){
   foreach($i in $smoke.instances){$instances+=@{instanceRef=$i.instanceRef;position=$i.position;frameRef=$planPath}}
   foreach($r in $inherited.instances){$roles+=@{instanceRef=$r.instanceRef;roleRef=($r.instanceRef+'/inheritance');roles=$r.roles;roleStatus=$r.roleStatus;status=$r.status;systemIdentity='fire_alarm';sourceRefs=$r.sourceRefs}}
  }else{
   foreach($b in [regex]::Split($plan,'(?m)^EntityHandle=')){
    if($b -notmatch '^"([^"]+)"'){continue};$h=$Matches[1]
    if((V $b DXF_Type) -ne 'INSERT'){continue}
    $attrs=@([regex]::Matches($b,'(?m)^Attribute_DXF=(.*)$')|Where-Object {$_.Groups[1].Value -match '\(2 \. "A"\)'})
    if($attrs.Count -ne 1){continue}
    $raw=$attrs[0].Groups[1].Value;$name=[regex]::Match($raw,'\(1 \. "([^"]*)"\)').Groups[1].Value
    if($name -ne $spec.rawRole){continue}
    $ah=[regex]::Match($raw,'\(5 \. "([^"]*)"\)').Groups[1].Value
    $p=[double[]]([regex]::Match($b,'(?m)^Insertion_WCS=\(([^)]+)\)').Groups[1].Value -split '\s+')
    $ref=$planPath+':'+$h;$instances+=@{instanceRef=$ref;frameRef=$planPath;position=$p}
    $roles+=@{instanceRef=$ref;roleRef=($ref+'/explicit');roles=@($spec.name);roleStatus='explicit';status='supported';systemIdentity='fire_alarm';sourceRefs=@($planPath+':'+$ah);compatibilityRef='reviewed-device-category-and-alarm-interface-context'}
   }
  }
  $category=@{nodeRef=($systemPath+':'+$spec.node);roleCandidate=$spec.name;systemIdentity='fire_alarm';compartmentRef=$compartment.compartmentRef;systemQuantityCandidate=$quantity;quantityRef=($systemPath+':'+$spec.q)}
  [pscustomobject]@{name=$spec.name;category=$category;compartment=$compartment;transform=$transform;instances=$instances;roles=$roles;expectedExplicit=$spec.explicit;expectedInherited=$spec.inherited;expectedDelta=$spec.delta}
 }
}
