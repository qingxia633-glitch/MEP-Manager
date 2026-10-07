$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../PanelConfiguration.psm1') -Force
$f=Get-Content (Join-Path $PSScriptRoot 'panel-configuration-fixture.json') -Raw -Encoding UTF8|ConvertFrom-Json
$inputs=Read-PanelConfigurationInputs -Spec $f
$script:n=0
function Check($v,$message){if(!$v){throw $message};$script:n++}
function Clone($v){ConvertFrom-Json (ConvertTo-Json -InputObject $v -Depth 90)}
function Reject($body,$message){$failed=$false;try{& $body|Out-Null}catch{$failed=$true};Check $failed $message}
$before=ConvertTo-Json -InputObject $inputs -Depth 90
$fixtureBefore=ConvertTo-Json -InputObject $f -Depth 90
$m=New-PanelConfigurationModel $inputs $f
$c=$m.panelConfigurations[0];$r=$m.bindingHypotheses[0]
Check ($c.modelType -eq 'PanelConfigurationCandidate' -and $c.panelIdentifier.rawValue -ceq 'QWB1') 'configuration identity'
Check ($c.status -eq 'supported') 'reviewed definition region supported'
Check ($m.panelInstances[0].sourceRef.handle -ceq 'E1DB') 'selected plan instance'
Check ($m.panelInstances[0].identifierStatement.handle -ceq 'E1DE') 'attached identifier provenance'
Check ($r.relationType -eq 'usesConfiguration' -and $r.status -eq 'supported') 'supported scoped configuration relation'
Check ($r.subject -cne $r.candidateTargets[0]) 'instance and definition identities distinct'
Check ($m.panelInstances[0].sourceRef.sourceSnapshot.sha256 -cne $c.definitionRegion.sourceSnapshot.sha256) 'cross-DWG snapshots stay separate'
Check ($c.definitionRegion.boundary.handle -ceq '161EF' -and $c.definitionRegion.internalDeviceFrame.handle -ceq '161F1') 'confirmed local frame identities'
Check ($c.configurationAttributes.Count -eq 11) 'all individual declaration sources retained'
$pe=@($c.configurationAttributes|Where-Object field -ceq 'Pe')[0]
$ijs=@($c.configurationAttributes|Where-Object field -ceq 'Ijs')[0]
Check ($pe.value -eq 1.5 -and $pe.unit -ceq 'kW' -and $pe.handle -ceq '161F3') 'Pe parsed from source'
Check ($ijs.value -eq 2.85 -and $ijs.unit -ceq 'A' -and $ijs.handle -ceq '161F4') 'Ijs parsed independently'
Check (@($c.configurationAttributes|Where-Object status -ne 'candidate').Count -eq 0) 'attributes remain candidates'
Check (@($c.configurationAttributes|Where-Object valueBasis -ne 'drawing_statement_only').Count -eq 0) 'no computed engineering value'
foreach($a in $c.configurationAttributes){Check ($a.rawText -and $a.handle -and $a.sourceSnapshot.sha256 -ceq $f.sources.definition.sha256 -and $a.evidenceRefs.Count -gt 0) 'attribute provenance and evidence'}
Check ($c.outgoingRowCandidates.Count -eq 3 -and ($c.outgoingRowCandidates.rawLabel -join ',') -ceq 'WP1,WP2,K1') 'three outgoing expression candidates'
Check (@($c.outgoingRowCandidates|Where-Object semanticStatus -ne 'outgoing_expression_not_final_circuit').Count -eq 0) 'no automatic circuit interpretation'
$cables=@($c.configurationAttributes|Where-Object field -eq 'cablePackageStatement')
Check ($cables.Count -eq 3 -and @($cables.handle|Select-Object -Unique).Count -eq 3) 'repeated package text not merged'
Check (@($cables|Where-Object {$_.rawText.Contains('SC20 FC,WC')}).Count -eq 3) 'full original cable statements retained'
Check (@($cables|Where-Object {$_.value -ceq '厂家成套电缆设备自带'}).Count -eq 3) 'literal package excerpt separate from full statement'
$cs=@($m.statements|Where-Object handle -eq '161F2')[0]
Check ($cs.confirmedVisibleExcerpt -ceq '厂家成套电缆设备自带' -and !$cs.confirmedVisibleExcerpt.Contains('SC20')) 'human excerpt does not confirm other raw text'
Check (@($m.statements|Where-Object {$_.handle -in @('161FC','161EB') -and $_.visibilityStatus -eq 'not_individually_confirmed'}).Count -eq 2) 'human visibility not propagated to repeated text'
Check (@($c.configurationAttributes|Where-Object {$_.field -eq 'note' -and $_.handle -eq '162E1'}).Count -eq 1) 'local fire marking note retained'
Check ($m.humanConfirmations.Count -eq 2 -and $m.projectRules.Count -eq 1) 'human confirmations and project rule separate'
Check ($m.projectRules[0].scope.projectId -ceq $m.projectId) 'rule limited to project'
Check (@($m.panelInstances[0].otherRawStatements|Where-Object rawText -ceq '直流配电箱').Count -eq 1) 'unconfirmed old attribute declaration retained'
Check ($m.drawingSet.completeness -eq 'unknown') 'project completeness not inferred'
Check ($before -ceq (ConvertTo-Json -InputObject $inputs -Depth 90)) 'raw inputs unchanged'
Check ($fixtureBefore -ceq (ConvertTo-Json -InputObject $f -Depth 90)) 'fixture unchanged'
$json=ConvertTo-Json -InputObject $m -Depth 90
Check ($json -notmatch '"(?:Circuit|circuits|electricalConnections|quantities|quantity|centerPath|confirmedTarget)"\s*:') 'no final circuits connections quantities or confirmed target'
$round=$json|ConvertFrom-Json
Check ($round.panelConfigurations[0].configurationAttributes.Count -eq 11 -and $round.bindingHypotheses[0].status -eq 'supported') 'JSON roundtrip'
foreach($key in @('projectId','documentId','regionId','localViewId','snapshotSHA256')) {
 $g=Clone $f;$g.humanConfirmations.definition.scope.$key='other'
 Reject {New-PanelConfigurationModel $inputs $g} "reject migrated confirmation: $key"
}
$g=Clone $f;$g.humanConfirmations.definition.scope.anchorHandles[0]='other'
Reject {New-PanelConfigurationModel $inputs $g} 'reject other title anchors'
$g=Clone $f;$g.projectRule.scope.projectId='other'
Reject {New-PanelConfigurationModel $inputs $g} 'no global same-name rule'
$g=Clone $f;$g.projectRule=$null
Check ((New-PanelConfigurationModel $inputs $g).bindingHypotheses[0].status -eq 'candidate') 'missing rule cannot support relation'
$g=Clone $f;$g.humanConfirmations.definition=$null
Check ((New-PanelConfigurationModel $inputs $g).bindingHypotheses[0].status -eq 'candidate') 'missing definition review cannot support relation'
$g=Clone $f;$g.humanConfirmations.plan=$null
Check ((New-PanelConfigurationModel $inputs $g).bindingHypotheses[0].status -eq 'candidate') 'missing plan authorization cannot support relation'
$x=Clone $inputs;$x.definition.sourceSnapshot.sha256='new'
Reject {New-PanelConfigurationModel $x $f} 'changed snapshot same handles rejected'
$x=Clone $inputs;$x.definition.statements[0].sourceSnapshot.sha256='new'
Reject {New-PanelConfigurationModel $x $f} 'mixed snapshot statement rejected'
$x=Clone $inputs;($x.plan.statements|Where-Object handle -eq 'E1DE').parentHandle='other'
Reject {New-PanelConfigurationModel $x $f} 'attribute must belong to selected parent'
$x=Clone $inputs;($x.definition.statements|Where-Object handle -eq '161F3').rawText='Pe=99kW'
Reject {New-PanelConfigurationModel $x $f} 'changed reviewed declaration rejected'
$x=Clone $inputs;$g=Clone $f
($x.definition.statements|Where-Object handle -eq '161F0').rawText='OTHER'
$g.definition.expectedIdentifier='OTHER';($g.humanConfirmations.definition.visibleTextClaims|Where-Object handle -eq '161F0').excerpt='OTHER'
$different=New-PanelConfigurationModel $x $g
Check ($different.bindingHypotheses[0].status -eq 'ambiguous' -and $different.conflicts.Count -eq 1) 'different identifiers preserve conflict not forced binding'
Check (($different.conflicts[0].claims -join ',') -ceq 'QWB1,OTHER') 'both conflicting original claims retained'
$x=Clone $inputs;$g=Clone $f
# Rename every selected handle and the identifier in inputs plus selection/confirmations.
$handles=@($x.plan.entities.handle)+@($x.plan.statements.handle)+@($x.definition.statements.handle)+@($x.definition.geometry.handle)
$ix=ConvertTo-Json -InputObject $x -Depth 90;$fx=ConvertTo-Json -InputObject $g -Depth 90
foreach($h in ($handles|Sort-Object -Unique)){$ix=$ix.Replace('"'+$h+'"','"renamed-'+$h+'"');$fx=$fx.Replace('"'+$h+'"','"renamed-'+$h+'"')}
$ix=$ix.Replace('QWB1','OTHER_PANEL');$fx=$fx.Replace('QWB1','OTHER_PANEL')
Check ((New-PanelConfigurationModel ($ix|ConvertFrom-Json) ($fx|ConvertFrom-Json)).bindingHypotheses[0].status -eq 'supported') 'no hardcoded handle or identifier'
$x=Clone $inputs;$x.plan.entities[0].insertion=@(1,2,3)
Check ((New-PanelConfigurationModel $x $f).bindingHypotheses[0].status -eq 'supported') 'cross-DWG matching never uses XY proximity'
$source=Get-Content (Join-Path $PSScriptRoot '../PanelConfiguration.psm1') -Raw -Encoding UTF8
Check ($source -notmatch 'QWB1|161F0|E1DB|E1DE|161EF') 'sample selection outside generic model'
"PASS: $script:n panel configuration checks; real snapshots read only"
