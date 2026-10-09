$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../OutgoingRows.psm1') -Force
$f=Get-Content (Join-Path $PSScriptRoot 'outgoing-fixture.json') -Raw -Encoding UTF8|ConvertFrom-Json
$data=Read-OutgoingInputs -Spec $f
$script:n=0
function Check($v,$why){if(!$v){throw $why};$script:n++}
function Clone($v){ConvertFrom-Json (ConvertTo-Json -InputObject $v -Depth 90)}
function Reject($b,$why){$caught=$false;try{& $b|Out-Null}catch{$caught=$true};Check $caught $why}
$before=ConvertTo-Json -InputObject $data -Depth 90
$fb=ConvertTo-Json -InputObject $f -Depth 90
$m=New-OutgoingRowModel $data $f
$r=$m.outgoingRows
Check ($r.Count -eq 3) 'three real rows'
Check (($r.rowIdentifier.rawText -join ',') -ceq 'WP1,WP2,K1') 'raw row identifiers'
Check (@($r.rowId|Select-Object -Unique).Count -eq 3) 'independent row identities'
Check ($r[0].targetNameCandidate.statement.rawText -ceq '潜污泵1' -and $r[1].targetNameCandidate.statement.rawText -ceq '潜污泵2') 'separate pump names'
Check ($r[0].powerFieldCandidate.value -eq 1.5 -and $r[1].powerFieldCandidate.value -eq 1.5) 'individual raw power fields'
Check ($r[0].powerFieldCandidate.statement.handle -cne $r[1].powerFieldCandidate.statement.handle) 'equal power does not merge statements'
Check ($r[2].targetNameCandidate.statement.rawText -ceq '水位信号') 'K1 target literal only'
Check ($r[2].powerFieldCandidate.observationStatus -eq 'not_observed' -and $null -eq $r[2].powerFieldCandidate.value -and $null -eq $r[2].powerFieldCandidate.statement) 'no power is not zero or inherited Pe'
Check ($m.sharedConfigurationStatements.Count -eq 6) 'six shared statements stored once'
Check (@($m.sharedConfigurationStatements|Where-Object rawText -ceq 'Pe=1.5kW').Count -eq 1) 'Pe shared only'
Check (@($m.sharedConfigurationStatements|Where-Object rawText -ceq 'Ijs=2.85A').Count -eq 1) 'Ijs shared only'
foreach($row in $r){
 Check ($row.panelConfigurationId -ceq $f.panelConfigurationId -and $row.sourceSnapshot.sha256 -ceq $f.source.sha256) 'configuration and snapshot scope'
 Check ($row.modelType -eq 'OutgoingRowCandidate' -and $row.bindingStatus -eq 'candidate') 'candidate not Circuit'
 Check ($row.sharedConfigurationStatements.Count -eq 6 -and @($row.sharedConfigurationStatements|Where-Object {$_ -isnot [string]}).Count -eq 0) 'shared context is references not copied confirmed attributes'
 Check ($row.panelBoundaryContactEvidence.status -eq 'observed' -and $row.panelBoundaryContactEvidence.minimumResidual -le $f.tolerance) 'true geometric frame contact'
 Check ($row.panelBoundaryContactEvidence.meaning -eq 'geometric_contact_only_not_electrical_port' -and $row.electricalPortStatus -eq 'unresolved') 'contact is not port'
 Check ($row.terminalBindingStatus -eq 'unresolved') 'no actual terminal binding'
 Check ($row.switchProtectionEvidence.observationStatus -eq 'not_observed' -and $row.switchProtectionEvidence.individualDeviceEvidence.Count -eq 0) 'shared protection claim is not a switch device'
 Check ($row.dynamicBlockParameters.observationStatus -eq 'not_observed') 'no dynamic parameters invented'
 Check ($row.conduitToken.rawToken -ceq 'SC20' -and ($row.installationMethodTokens.rawToken -join ',') -ceq 'FC,WC') 'literal conduit and installation tokens'
 Check ($row.conduitToken.engineeringInterpretation -eq 'unresolved') 'SC20 not engineering diameter'
 Check ($row.cablePackageStatement.rawText -ceq '厂家成套电缆设备自带  SC20 FC,WC') 'full cable raw text retained'
 foreach($s in @($row.rowIdentifier,$row.targetNameCandidate.statement,$row.cablePackageStatement)+@($row.powerFieldCandidate.statement|Where-Object {$null -ne $_})){
  Check ($s.handle -and $s.rawText -and $s.layer -and $s.coordinates.insertion.Count -eq 3 -and $s.sourceSnapshot.sha256 -ceq $f.source.sha256 -and $s.rawRecord) 'field provenance including raw text layer coordinates'
 }
 Check ($row.outgoingGeometry.handle -and $row.outgoingGeometry.layer -and $row.outgoingGeometry.vertices.Count -eq 2 -and $row.outgoingGeometry.rawRecord) 'geometry original provenance'
}
Check ($m.procurementQuantityRuleCandidates.Count -eq 3) 'one independent rule candidate per source row'
foreach($rule in $m.procurementQuantityRuleCandidates){Check ($rule.status -eq 'candidate' -and $rule.quantityInclusion -eq 'unresolved' -and $rule.claim -ceq 'related cable may be supplied with equipment/package' -and $rule.sourceStatement.handle) 'no quantity exclusion'}
foreach($i in @(0,1)){Check ([math]::Abs($r[$i].gapEvidence.drawingUnitGap-269.984216) -lt 0.000001 -and $r[$i].gapEvidence.action -eq 'preserved_not_filled') 'known gap retained not filled'}
Check ($null -eq $r[2].additionalGeometry -and $null -eq $r[2].gapEvidence) 'no fabricated K1 tail geometry'
for($i=0;$i -lt 4;$i++){
 Check ([math]::Abs($r[0].alignmentEvidence[$i].transverseOffset-$r[1].alignmentEvidence[$i].transverseOffset) -lt 0.00001) 'WP1 WP2 repeated normalized layout'
}
Check ($before -ceq (ConvertTo-Json -InputObject $data -Depth 90)) 'upstream configuration and raw facts unchanged'
Check ($fb -ceq (ConvertTo-Json -InputObject $f -Depth 90)) 'fixture unchanged'
$json=ConvertTo-Json -InputObject $m -Depth 90
Check ($json -notmatch '"(?:Circuit|circuits|terminalConnections|electricalConnections|quantity|quantities|confirmedTarget|confirmedAttributes)"\s*:') 'no forbidden final models'
Check (($json|ConvertFrom-Json).outgoingRows.Count -eq 3) 'JSON roundtrip'
$round=$json|ConvertFrom-Json
Check ($round.outgoingRows[0].outgoingGeometry.vertices[0] -is [array] -and $round.outgoingRows[0].outgoingGeometry.vertices[0][0] -eq 40106.352405) 'JSON geometry remains numeric XYZ arrays'
foreach($key in @('projectId','regionId','localViewId','panelConfigurationId')){$g=Clone $f;$g.$key='different';Reject {New-OutgoingRowModel $data $g} "reject wrong $key"}
$g=Clone $f;$g.source.sha256='different';Reject {Read-OutgoingInputs $g} 'reader rejects changed report fingerprint'
$g=Clone $f;$g.configurationModel.sha256='different';Reject {Read-OutgoingInputs $g} 'reader rejects changed upstream artifact'
$x=Clone $data;$x.statements[0].sourceSnapshot.sha256='different';Reject {New-OutgoingRowModel $x $f} 'mixed source statement rejected'
$x=Clone $data;($x.statements|Where-Object handle -eq '161F2').rawText='changed';Reject {New-OutgoingRowModel $x $f} 'changed declaration rejected'
$x=Clone $data;$line=@($x.geometry|Where-Object handle -ceq '161E6')[0]
[array]::Reverse($line.vertices)
Check ((New-OutgoingRowModel $x $f).outgoingRows[0].panelBoundaryContactEvidence.status -eq 'observed') 'reversed line retains contact'
$x=Clone $data;$line=@($x.geometry|Where-Object handle -ceq '161E6')[0];$line.vertices[0][0]+=10
Check ((New-OutgoingRowModel $x $f).outgoingRows[0].panelBoundaryContactEvidence.status -eq 'not_observed') 'detached start not forced onto frame'
$x=Clone $data;($x.geometry|Where-Object handle -ceq '161F1').closed=$false
Reject {New-OutgoingRowModel $x $f} 'open frame rejected'
$g=Clone $f;$g.rows[0].powerHandle=$null;$g.rows[0].expectedPower=$null
Check ((New-OutgoingRowModel $data $g).outgoingRows[0].powerFieldCandidate.observationStatus -eq 'not_observed') 'no power inferred from shared Pe even on WP row'
$g=Clone $f;$g.tolerance=-1;Reject {New-OutgoingRowModel $data $g} 'invalid tolerance rejected'
$g=Clone $f;$g.rows+=,$g.rows[0];Reject {New-OutgoingRowModel $data $g} 'duplicate row selection rejected'
$source=Get-Content (Join-Path $PSScriptRoot '../OutgoingRows.psm1') -Raw -Encoding UTF8
Check ($source -notmatch 'QWB1|WP1|WP2|161E9|161F0|269\.984216|SC20') 'sample answers outside implementation'
"PASS: $script:n outgoing row checks; no CAD or quantity operations"
