Set-StrictMode -Version 2

# Consumes reviewed candidate evidence, not raw-text keywords or counts.
function New-FunctionalControlRelationCandidate {
 param([Parameter(Mandatory)]$InputCandidate)
 $c=$InputCandidate
 if(!$c.id -or !$c.scopeRef -or !$c.functionRole){throw 'Candidate identity, scope and function required'}
 $registry=@{}
 foreach($ref in $c.references){
  if(!$ref.id -or $registry.ContainsKey($ref.id)){throw 'Unique references required'}
  $registry[$ref.id]=$ref
 }
 function ValidRef($id){
  if(!$id -or !$registry.ContainsKey($id)){return $false}
  $v=$registry[$id]
  return ($v.resolved -and $v.scopeRef -ceq $c.scopeRef)
 }
 if(!(ValidRef $c.functionRef)){throw 'Function provenance missing or outside scope'}
 $reviews=New-Object 'Collections.Generic.List[object]'
 function Review($type,$owner){
  $id=$c.id+':review:'+ $type+':'+$owner
  $reviews.Add([pscustomobject]@{id=$id;type=$type;subjectRef=$owner;status='open';automaticResolution=$false})
  $id
 }
 $relations=@(foreach($r in $c.relations){
  if($r.kind -notin @('function_control_region','circuit_target','module_function','circuit_io','io_target')){throw 'Unknown relation grain'}
  if($r.status -notin @('supported','partial','unresolved')){throw 'Candidate status required'}
  $valid=(ValidRef $r.fromRef) -and (ValidRef $r.toRef) -and @($r.evidenceRefs).Count -gt 0
  foreach($e in $r.evidenceRefs){if(!(ValidRef $e)){$valid=$false}}
  $status=if($valid){$r.status}else{'unresolved'}
  $rr=@()
  if($status -ne 'supported'){
   $kind=if($r.kind -in @('circuit_io','io_target')){'circuit_control_binding_unresolved'}else{'control_target_unresolved'}
   $rr+=Review $kind $r.id
  }
  [pscustomobject]@{relationId=$r.id;relationType=$r.kind;fromRef=$r.fromRef;toRef=$r.toRef;relationStatus=$status;evidenceRefs=@($r.evidenceRefs);reviewItemRefs=$rr;confirmed=$false}
 })
 if($c.cardinalityCandidate -notin @('one_to_one','one_to_many','many_to_one','representative_for_group','unresolved')){throw 'Unknown cardinality'}
 $card='unresolved'
 # Quantity equality is deliberately not an admissible basis.
 if($c.cardinalityCandidate -ne 'unresolved' -and $c.cardinalityBasis -eq 'explicit_relation_evidence' -and @($c.cardinalityEvidenceRefs).Count){
  $ok=$true;foreach($e in $c.cardinalityEvidenceRefs){if(!(ValidRef $e)){$ok=$false}}
  if($ok){$card=$c.cardinalityCandidate}
 }
 $reviewRefs=@()
 if($card -eq 'unresolved'){$reviewRefs+=Review control_cardinality_unresolved $c.id}
 if($c.quantityCandidateRef -and !(ValidRef $c.quantityCandidateRef)){throw 'Quantity source missing or outside scope'}
 $reviewRefs+=Review io_quantity_semantics_unresolved $c.id
 foreach($field in @('sourceDeviceRef','sourceCircuitRef','controlledTargetRef','controlRepresentationRef','moduleRepresentationRef')){
  if($c.$field -and !(ValidRef $c.$field)){throw "Invalid $field"}
 }
 $status='unresolved'
 if(@($relations|Where-Object relationStatus -NE 'unresolved').Count){$status='partial'}
 if($relations.Count -and @($relations|Where-Object relationStatus -NE 'supported').Count -eq 0 -and $card -ne 'unresolved'){$status='supported'}
 [pscustomobject]@{
  modelType='FunctionalControlRelationCandidate';id=$c.id;scopeRef=$c.scopeRef
  functionRef=$c.functionRef;functionRole=$c.functionRole
  sourceDeviceRef=$c.sourceDeviceRef;sourceCircuitRef=$c.sourceCircuitRef;controlledTargetRef=$c.controlledTargetRef
  controlRepresentationRef=$c.controlRepresentationRef;moduleRepresentationRef=$c.moduleRepresentationRef
  quantityCandidateRef=$c.quantityCandidateRef;quantityRoleCandidate=$c.quantityRoleCandidate
  physicalObjectCount='unresolved';channelCount='unresolved'
  relationStatus=$status;cardinalityStatus=$card;relations=$relations
  cardinalityEvidenceRefs=@($c.cardinalityEvidenceRefs);cardinalityBasis=$c.cardinalityBasis
  evidenceRefs=@(@($c.functionRef)+@($c.quantityCandidateRef)+@($relations.evidenceRefs)+@($c.cardinalityEvidenceRefs)|Where-Object {$_}|Select-Object -Unique);reviewItemRefs=@($reviewRefs)+@($relations.reviewItemRefs)
  reviewItems=$reviews.ToArray();formalBinding=$false;confirmed=$false
 }
}
Export-ModuleMember -Function New-FunctionalControlRelationCandidate
