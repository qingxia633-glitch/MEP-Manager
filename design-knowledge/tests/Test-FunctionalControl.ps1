$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../FunctionalControl.psm1') -Force
function Check($ok,$why){if(!$ok){throw $why}}
$root=Resolve-Path (Join-Path $PSScriptRoot '../..')
$path='local_test_data/system-t8t3-textlayout-snapshot-20260924/MEP-full-entity-report.txt'
$hash='7360ADB34A4E0BACACD2768261FBB3E19835C07C65F9F4959F94BAE5751A249F'
Check ((Get-FileHash (Join-Path $root $path)).Hash -eq $hash) 'Pinned real snapshot'
$raw=Get-Content (Join-Path $root $path) -Raw -Encoding UTF8
$records=@{};foreach($b in [regex]::Split($raw,'(?m)^EntityHandle=')){$h=($b -split '"')[1];if($h){$records[$h]=$b}}
$scope='EW-0015/ALZ1-B1'
$handles=@('19BB7','19959','1998F','6DF29','6DF27','1995D','19977','1997A','19975','19979','199BE','1997E','19986','19987','1998D','199C2')
$refs=@(foreach($h in $handles){Check ($records.ContainsKey($h)) "Missing $h";[pscustomobject]@{id=$h;sourcePath=$path;sourceSnapshot=$hash;handle=$h;scopeRef=$scope;resolved=$true}})
# Reviewed candidates only; raw facts stay in the source snapshot.
$quantity=[pscustomobject]@{id='quantity';sourceRef='6DF29';rawQuantity=5;quantityMeaningCandidate='IO module representation';physicalObjectCount='unresolved';channelCount='unresolved'}
$refs+= [pscustomobject]@{id='quantity';sourcePath=$path;sourceSnapshot=$hash;handle='6DF29';scopeRef=$scope;resolved=$true}
$rels=@(
 [pscustomobject]@{id='function-region';kind='function_control_region';fromRef='19BB7';toRef='19959';status='partial';evidenceRefs=@('1995D','6DF29')},
 [pscustomobject]@{id='module-function';kind='module_function';fromRef='1998F';toRef='19BB7';status='partial';evidenceRefs=@('6DF27','6DF29','1995D')}
)
$circuits=@('19977','1997A','19975','19979','199BE');$targets=@('1997E','19986','19987','1998D','199C2')
for($i=0;$i -lt 5;$i++){
 Check ($records[$circuits[$i]] -match ('Text_RAW="W'+($i+1)+'"')) 'Circuit text'
 $rels+=[pscustomobject]@{id="target-$i";kind='circuit_target';fromRef=$circuits[$i];toRef=$targets[$i];status='partial';evidenceRefs=@($circuits[$i],$targets[$i])}
 $rels+=[pscustomobject]@{id="io-$i";kind='circuit_io';fromRef=$circuits[$i];toRef=$null;status='unresolved';evidenceRefs=@()}
 $rels+=[pscustomobject]@{id="io-target-$i";kind='io_target';fromRef=$null;toRef=$targets[$i];status='unresolved';evidenceRefs=@()}
}
Check ($records['6DF29'] -match 'Text_RAW="端子箱内5\(I/O\)"') 'Quantity source unchanged'
Check ($records['19BB7'] -match 'Text_RAW="切非"') 'Function source'
$c=[pscustomobject]@{id='alz-control';scopeRef=$scope;functionRef='19BB7';functionRole='切非';sourceDeviceRef='19959';sourceCircuitRef=$null;controlledTargetRef=$null;controlRepresentationRef='1998F';moduleRepresentationRef='1998F';quantityCandidateRef='quantity';quantityRoleCandidate=$quantity.quantityMeaningCandidate;references=$refs;relations=$rels;cardinalityCandidate='unresolved';cardinalityBasis='none';cardinalityEvidenceRefs=@()}
$x12=[pscustomobject]@{hostStatus='partial';specificCountingUnit='unresolved';moduleToTargetCardinality='unresolved'}
$before=$c|ConvertTo-Json -Depth 20 -Compress;$other=$x12|ConvertTo-Json -Compress
function Clone{$before|ConvertFrom-Json}
$r=New-FunctionalControlRelationCandidate $c
Check ($r.relationStatus -eq 'partial' -and $r.cardinalityStatus -eq 'unresolved') 'Independent relation and cardinality'
Check (@($r.relations|Where-Object relationStatus -EQ partial).Count -eq 7) 'Seven partial relations'
Check (@($r.relations|Where-Object relationStatus -EQ unresolved).Count -eq 10) 'Ten unresolved IO bindings'
Check (@($r.relations|Where-Object confirmed).Count -eq 0 -and !$r.confirmed) 'No confirmed edges'
Check ($r.physicalObjectCount -eq 'unresolved' -and $r.channelCount -eq 'unresolved') 'Quantity not physical count'
$x=Clone;$x.cardinalityCandidate='one_to_one';$x.cardinalityBasis='equal_counts';$x.cardinalityEvidenceRefs=@('6DF29')
Check ((New-FunctionalControlRelationCandidate $x).cardinalityStatus -eq 'unresolved') 'Equal counts never bind'
$x=Clone;$x.relations[0].status='supported'
Check (@((New-FunctionalControlRelationCandidate $x).relations|Where-Object relationStatus -EQ unresolved).Count -eq 10) 'One relation does not upgrade another'
$x=Clone;$x.relations[2].evidenceRefs=@('missing')
Check ((New-FunctionalControlRelationCandidate $x).relations[2].relationStatus -eq 'unresolved') 'Missing provenance downgrades'
$x=Clone;$x.references[7].scopeRef='other-sheet'
Check ((New-FunctionalControlRelationCandidate $x).relations[5].relationStatus -eq 'unresolved') 'Cross-scope references blocked'
$x=Clone;$x.functionRole='another-function';$x.id='another-sample'
Check ((New-FunctionalControlRelationCandidate $x).relationStatus -eq 'partial') 'No function keyword policy'
Check (($c|ConvertTo-Json -Depth 20 -Compress) -ceq $before) 'Input not mutated'
Check (($x12|ConvertTo-Json -Compress) -ceq $other) 'External x12 unchanged'
Check (($r|ConvertTo-Json -Depth 20) -notmatch '"rawText"|"RawEntity"') 'Only references, no copied facts'
$x=Clone;$x.relations[3].status='supported'
Check ((New-FunctionalControlRelationCandidate $x).relations[3].relationStatus -eq 'unresolved') 'Missing IO cannot be supported'
$renamed=$before;foreach($h in $handles){$renamed=$renamed.Replace('"'+$h+'"','"alias-'+$h+'"')}
Check ((New-FunctionalControlRelationCandidate ($renamed|ConvertFrom-Json)).relationStatus -eq 'partial') 'No Handle keyed policy'
foreach($type in @('control_cardinality_unresolved','control_target_unresolved','io_quantity_semantics_unresolved','circuit_control_binding_unresolved')){Check (@($r.reviewItems|Where-Object type -EQ $type).Count -gt 0) $type}
Write-Host 'PASS FunctionalControl: real EW-0015 fixture, independent grains, provenance, scope, quantity and negative checks'
