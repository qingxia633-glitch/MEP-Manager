# Fixed Handles and reviewed lexical compatibility belong only to this real fixture.
function Read-SmokeRoleFixture {
 $root=Join-Path $PSScriptRoot '../..'
 function ReadSource($relative,$document){
  $p=Join-Path $root $relative;$s=[IO.File]::ReadAllText($p)
  if(!$s.Contains($document) -or $s -notmatch '(?m)^END_OF_REPORT'){throw "Invalid fixture $relative"}
  @{text=$s;document=$document;hash=(Get-FileHash $p -Algorithm SHA256).Hash;path=$relative}
 }
 function Value($s,$key){[regex]::Match($s,'(?m)^'+[regex]::Escape($key)+'="([^"\r\n]*)"').Groups[1].Value}
 $doc='EX-BX地下车库火灾报警平面图_t8_t3.dwg';$name='$Equip$00002649'
 $plan=ReadSource 'local_test_data/fire-alarm-full-snapshot-20260923/MEP-full-entity-report.txt' $doc
 $probe=ReadSource 'local_test_data/fire-alarm-smoke-block-Equip00002649-probe-20260926/block-definition-probe.txt' $doc
 $legend=ReadSource 'local_test_data/system-t8t3-verified-snapshot-20260916/MEP-full-entity-report.txt' 'EX-BX地下车库说明及配电箱系统_t8_t3.dwg'
 if((Value $probe.text Block_BEGIN) -cne $name){throw 'Wrong definition'}
 $att=@([regex]::Split($probe.text,'(?m)^SourceInternalHandle=')|Where-Object {$_ -match '(?m)^DXF_Type="ATTDEF"' -and (Value $_ 'DXF:2') -eq 'A'})
 if($att.Count -ne 1 -or (Value $att[0] 'DXF:1') -ne '感烟探测器'){throw 'Reviewed default changed'}
 $semanticRef='reviewed-smoke-role-compatibility:current-drawings-only'
 $de=New-RoleEvidenceSource block_definition_default 'smoke_detector' (Value $att[0] 'DXF:1') $doc $probe.hash $name @($probe.path+':102F8') $semanticRef
 $lr=@([regex]::Split($legend.text,'(?m)^EntityHandle=')|Where-Object {$_ -match '^"23986"'})[0]
 $ln=@([regex]::Split($legend.text,'(?m)^EntityHandle=')|Where-Object {$_ -match '^"23896"'})[0]
 if((Value $lr BlockName) -cne $name -or (Value $lr AttributeText_RAW) -ne '感烟火灾探测器' -or (Value $ln Text_RAW) -ne '感烟探测器'){throw 'Legend evidence changed'}
 $le=New-RoleEvidenceSource project_legend 'smoke_detector' (Value $ln Text_RAW) $legend.document $legend.hash $name @($legend.path+':23986',$legend.path+':23896') $semanticRef
 $instances=@(foreach($b in [regex]::Split($plan.text,'(?m)^EntityHandle=')){
  if($b -notmatch '^"([^"]+)"'){continue};$h=$Matches[1]
  if((Value $b BlockName) -cne $name){continue}
  $own=@();$state='absent_in_snapshot'
  foreach($m in [regex]::Matches($b,'(?m)^Attribute_DXF=(.*)$')){
   $raw=$m.Groups[1].Value
   if($raw -notmatch '\(2 \. "A"\)'){continue}
   $value=[regex]::Match($raw,'\(1 \. "([^"]*)"\)').Groups[1].Value
   $ah=[regex]::Match($raw,'\(5 \. "([^"]*)"\)').Groups[1].Value
   $state=if($value){'present'}else{'present_empty'}
   if($value){if($value -ne '感烟探测器（点型）'){throw 'Unreviewed instance role'}
    $own+=New-RoleEvidenceSource instance_explicit 'smoke_detector' $value $doc $plan.hash $name @($plan.path+':'+$ah) $semanticRef
   }
  }
  $v=[regex]::Match($b,'(?m)^Insertion_WCS=\(([^)]+)\)').Groups[1].Value -split '\s+'
  [pscustomobject]@{instanceRef=($plan.path+':'+$h);sourceDocument=$doc;snapshot=$plan.hash;scopeId='fire-alarm-plan/current-definition';definitionRef=$name;dynamicStatus=$(if($b -match '(?m)^IsDynamicBlock=:vlax-false\r?$'){'static'}else{'unknown'});roleAttributeState=$state;evidence=$own;position=[double[]]$v}
 })
 $definition=[pscustomobject]@{sourceDocument=$doc;snapshot=$probe.hash;scopeId='fire-alarm-plan/current-definition';definitionRef=$name;dynamicStatus=$(if($probe.text -match '(?m)^DefinitionIsDynamicBlock=:vlax-false\r?$'){'static'}else{'unknown'});visibilityStateStatus='single';evidence=@($de,$le)}
 # Existing verified transform only; no refit or use of system quantity for membership.
 Add-Type -Path (Join-Path $root 'design-knowledge/SheetGeometry.cs')
 $zone=[IO.File]::ReadAllText((Join-Path $root 'local_test_data/architecture-fire-compartment-zone1-block-probe-20260926/block-definition-probe.txt'))
 $b=@([regex]::Split($zone,'(?m)^SourceInternalHandle=')|Where-Object {$_ -match '^"55DF5"'})[0]
 $poly=[double[][]]@([regex]::Matches($b,'(?m)^DXF:10=\(([^)]+)\)')|ForEach-Object {$v=$_.Groups[1].Value -split '\s+'; ,@(([double]$v[0]+555932139.9856748),([double]$v[1]+553155197.1740737),0.0)})
 if($poly.Count -ne 52){throw 'Polygon changed'}
 $inside=@($instances|Where-Object {[MepSheet.Geometry]::Point($poly,$_.position,0.001) -eq 1}|ForEach-Object instanceRef)
 $system=ReadSource 'local_test_data/fire-system-full-snapshot-20260925/MEP-full-entity-report.txt' 'EX-BX地下车库弱电消防系统图_t8_t3.dwg'
 $q=@([regex]::Split($system.text,'(?m)^EntityHandle=')|Where-Object {$_ -match '^"15DBE"'})[0]
 [pscustomobject]@{definition=$definition;instances=$instances;insideRefs=$inside;polygonRef='local_test_data/architecture-fire-compartment-zone1-block-probe-20260926/block-definition-probe.txt:55DF5';quantity=[int](Value $q Text_RAW);quantityRef=($system.path+':15DBE');quantitySnapshot=$system.hash}
}
