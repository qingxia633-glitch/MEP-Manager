$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../SystemDiagram.psm1') -Force
$script:n=0
function Check($ok,$why){if(!$ok){throw $why};$script:n++;if($script:n % 20 -eq 0){Write-Host "Checked $($script:n): $why"}}
function Clone($v){ConvertFrom-Json (ConvertTo-Json -InputObject $v -Depth 90)}
# Controlled unit inputs are independent of gold Handles and drawing names.
$source=[pscustomobject]@{sha256='synthetic';path='in-memory';dwg='fixture'}
function Anchor($h,$y){[pscustomobject]@{handle=$h;type='INSERT';insertion=@(10,$y,0);sourceSnapshot=$source;rawRecord='raw';dynamicMetadata=@{properties=@();readStatus='read'}}}
function Statement($h,$text,$y){[pscustomobject]@{handle=$h;parentHandle=$null;rawText=$text;layer='arbitrary';insertion=@(20,$y,0);alignment=@();sourceSnapshot=$source;rawRecord=$text;coordinateStatus='WCS';referencePointType='Insertion_WCS';referencePoint=@(20,$y,0)}}
$anchors=@((Anchor 'one' 100),(Anchor 'two' 0))
$s=@((Statement 'a' 'SAME1' 100),(Statement 'b' 'SAME1' 0))
$v=New-DiagramLocalView $source $anchors $s 'v' 20
Check ($v.rows.Count -eq 2) 'controlled rows'
Check ($v.statements.Count -eq 2 -and $v.statements[0].handle -ne $v.statements[1].handle) 'duplicate text preserved'
Check (@($v.statements|Where-Object bindingStatus -ne unbound).Count -eq 0) 'layout is not semantic binding'
$amb=New-DiagramLocalView $source $anchors @((Statement 'middle' 'X1' 50)) 'v' 60
Check ($amb.statements[0].bindingStatus -eq 'ambiguous' -and $amb.statements[0].candidateRowIds.Count -eq 2) 'overlapping row bands preserve alternatives'
$out=New-DiagramLocalView $source $anchors @((Statement 'outside' 'X1' 400)) 'v' 20
Check ($out.statements[0].rowAssociationStatus -eq 'insufficient') 'no nearest row fallback'
$coincident=New-DiagramLocalView $source @((Anchor 'x' 1),(Anchor 'y' 1)) @() 'v' 20
Check (@($coincident.rows|Where-Object status -eq ambiguous).Count -eq 2) 'duplicate baselines ambiguous'
$moved=Clone $anchors;foreach($a in $moved){$a.insertion[1]+=800;$a.handle='new-'+$a.handle}
$movedS=Clone $s;foreach($a in $movedS){$a.referencePoint[1]+=800;$a.insertion[1]+=800;$a.handle='new-'+$a.handle}
$mv=New-DiagramLocalView $source $moved $movedS 'v' 20
Check ($mv.rows.Count -eq 2 -and $mv.alignmentEvidence[0].deltaY -eq $v.alignmentEvidence[0].deltaY) 'translation/Handle independence'
$bad=Clone $s;$bad[0].sourceSnapshot.sha256='other'
$caught=$false;try{New-DiagramLocalView $source $anchors $bad 'v' 20|Out-Null}catch{$caught=$true}
Check $caught 'reject cross snapshot statement'

# Real read-only fixture exercises parsing, provenance, role separation and geometry.
$result=& (Join-Path $PSScriptRoot '../Read-LocalFixture.ps1')
Check ($result.rows.Count -eq 5) 'Q1-Q5 five rows'
Check ($result.statements.Count -eq 22) 'all selected text and attributes retained'
Check ($result.deviceCandidates.Count -eq 5) 'five instance-scoped symbol candidates'
Check ($result.dynamicBlockMetadataEvidence.Count -eq 5) 'independent dynamic evidence per instance'
for($i=0;$i -lt 5;$i++){
 $r=$result.rows[$i];$claims=@($result.statements|Where-Object {$_.id -in $r.statementCandidateIds})
 Check (@($claims|Where-Object rawText -eq ('Q'+($i+1))).Count -eq 1) 'row Q statement'
 Check (@($claims|Where-Object rawText -eq 'L1.2.3.N.PE').Count -eq 1) 'phase statement per row'
 Check ($r.status -eq 'candidate') 'row never promoted to circuit'
 Check (@($claims|Where-Object bindingStatus -ne unbound).Count -eq 0) 'no semantic bindings'
 Check ($result.dynamicBlockMetadataEvidence[$i].properties[0].value_RAW -ceq '"20A"') 'dynamic value kept raw'
 Check ($result.dynamicBlockMetadataEvidence[$i].properties[0].allowedValues_RAW -match '"32A"') 'allowed values retained'
 Check ($result.deviceCandidates[$i].geometryMembers.Count -eq 4) 'composite geometry members retained'
 Check ($result.deviceCandidates[$i].attributeEvidence.Count -eq 1) 'separate attribute definition evidence'
 Check ($result.deviceCandidates[$i].instanceAttributeEvidence.Count -eq 1) 'attached ATTRIB retained separately'
 Check (@($result.deviceCandidates[$i].instanceAttributeEvidence[0].fields|Where-Object {$_.Code -eq 1 -and $_.Value -ceq '"断路器"'}).Count -eq 1) 'original instance attribute text'
 Check ($result.deviceCandidates[$i].candidateRole -eq 'switching/protection-device-like') 'fixture supplied tentative role'
 Check (@($result.deviceCandidates[$i].attributeEvidence[0].Fields|Where-Object {$_.Code -eq 1 -and $_.Value -ceq '"断路器"'}).Count -eq 1) 'original ATTDEF text'
 Check ($result.deviceCandidates[$i].sourceInstancePath[1] -eq $r.rowBasis.handle) 'instance path prevents definition member deduplication'
}
foreach($index in @(2,3)){
 $r=$result.rows[$index];$claims=@($result.statements|Where-Object {$_.id -in $r.statementCandidateIds})
 Check (@($claims|Where-Object {$_.rawText -in @('QWB1','QWB4')}).Count -eq 2) 'R3/R4 retain both panel labels'
}
Check (@($result.statements|Where-Object rawText -eq QWB1).Count -eq 3) 'QWB1 repetitions are three raw statements'
Check (@($result.deviceCandidates|Where-Object {$_.humanConfirmations.Count -gt 0}).Count -eq 1) 'human confirmation not propagated to other instances'
Check ($result.deviceCandidates[3].humanConfirmations[0].outerHandle -eq '7EDD9') 'R4 scoped confirmation'
Check ($result.deviceCandidates[3].attributeEvidence[0].Handle -ne $result.deviceCandidates[3].humanConfirmations[0].id) 'CAD fact and human evidence separate'
$eq=$result.representationEquivalences[0]
Check ($eq.status -eq 'supported' -and $eq.geometryComparison.equal) 'computed line equivalence'
Check ($eq.styleComparison.equal) 'explicit styles equal'
Check ($eq.representationGroups.Count -eq 1 -and $eq.representationGroups[0].members.Count -eq 2) 'two raw expressions one equivalence group'
Check ($eq.visibilityState.aDXF60 -eq '1' -and $eq.visibilityState.bInsertDXF60 -eq '0') 'visibility swap retained'
Check ($eq.equivalenceScope.outerBlock -eq '*U404') 'definition scope not Q rows'
Check ($eq.geometryComparison.residual -lt 0.00001) 'transformed numeric endpoint comparison'
Check (@($result.PSObject.Properties.Name|Where-Object {$_ -in @('circuits','connections','quantities','engineeringObjects')}).Count -eq 0) 'no final objects/quantities'
Check ($eq.quantityStatus -eq 'not_computed') 'no quantity from equivalence'
Check (@($result.deviceCandidates[0].sourceTransforms.childInsertFields|Where-Object {$_.Value.PSObject.Properties.Name -contains 'PSDrive'}).Count -eq 0) 'probe markers contain no PowerShell provider metadata'
Check ((Clone $result).statements.Count -eq 22) 'JSON round trip'

$f=Get-Content (Join-Path $PSScriptRoot 'local-fixture.json') -Raw -Encoding UTF8|ConvertFrom-Json
$root=Join-Path $PSScriptRoot '../..'
$op=Read-DiagramProbe (Join-Path $root $f.sources.outer.path);$cp=Read-DiagramProbe (Join-Path $root $f.sources.child.path)
$renamed=Clone $op;$renamedChild=Clone $cp;$sel=Clone $f.equivalenceFixture
foreach($b in $renamed.Blocks){foreach($e in $b.Entities){$e.Handle='rename-'+$e.Handle}}
foreach($b in $renamedChild.Blocks){foreach($e in $b.Entities){$e.Handle='rename-'+$e.Handle}}
$sel.directHandle='rename-'+$sel.directHandle;$sel.childInsertHandle='rename-'+$sel.childInsertHandle;$sel.childLineHandle='rename-'+$sel.childLineHandle
Check ((New-RepresentationEquivalence $renamed $renamedChild $sel).geometryComparison.equal) 'equality independent of Handle'
$changed=Clone $cp;$b=$changed.Blocks|Where-Object Name -eq $sel.childBlock
$e=$b.Entities|Where-Object Handle -eq $f.equivalenceFixture.childLineHandle
($e.Fields|Where-Object Code -eq 10|Select-Object -First 1).Value='(11117.92326442582 0)'
$diff=New-RepresentationEquivalence $op $changed $f.equivalenceFixture
Check (!$diff.geometryComparison.equal -and $diff.representationGroups.Count -eq 2) 'different geometry not collapsed'
$changed=Clone $cp;$b=$changed.Blocks|Where-Object Name -eq $sel.childBlock;$e=$b.Entities|Where-Object Handle -eq $f.equivalenceFixture.childLineHandle
($e.Fields|Where-Object Code -eq 62).Value='3'
Check (!(New-RepresentationEquivalence $op $changed $f.equivalenceFixture).styleComparison.equal) 'style difference retained'
$changed=Clone $cp;$b=$changed.Blocks|Where-Object Name -eq $sel.childBlock;$e=$b.Entities|Where-Object Handle -eq $f.equivalenceFixture.childLineHandle
$vertices=@($e.Fields|Where-Object Code -eq 10);$first=$vertices[0].Value;$vertices[0].Value=$vertices[1].Value;$vertices[1].Value=$first
Check ((New-RepresentationEquivalence $op $changed $f.equivalenceFixture).geometryComparison.equal) 'reversed endpoints equivalent'
($e.Fields|Where-Object Code -eq 42|Select-Object -First 1).Value='0.5'
$caught=$false;try{New-RepresentationEquivalence $op $changed $f.equivalenceFixture|Out-Null}catch{$caught=$true}
Check $caught 'unsupported curved geometry rejected'
$changed=Clone $cp;$b=$changed.Blocks|Where-Object Name -eq $sel.childBlock;$e=$b.Entities|Where-Object Handle -eq $f.equivalenceFixture.childLineHandle
($e.Fields|Where-Object Code -eq 40|Select-Object -First 1).Value='50'
$caught=$false;try{New-RepresentationEquivalence $op $changed $f.equivalenceFixture|Out-Null}catch{$caught=$true}
Check $caught 'unsupported variable width rejected'
$snap=Read-DiagramSnapshot (Join-Path $root $f.sources.diagram.path);$r4=$snap.entities|Where-Object handle -eq 7EDD9
Check ((New-DeviceCandidate $r4 $op $cp $f.probeCorrespondence $null $f.localViewId).candidateRole -eq 'unclassified') 'generic constructor does not assume switch role'
foreach($value in @('32A','40A','63A')){
 $altered=Clone $r4;$altered.dynamicMetadata.properties[0].value_RAW='"'+$value+'"'
 $d=New-DeviceCandidate $altered $op $cp $f.probeCorrespondence $null $f.localViewId
 Check ($d.dynamicPropertyRaw[0].value_RAW -ceq ('"'+$value+'"')) 'other dynamic values unchanged without engineering inference'
}
$hc=Clone $result.humanConfirmations[0];$hc.localViewId='other'
$caught=$false;try{New-DeviceCandidate $r4 $op $cp $f.probeCorrespondence $hc $f.localViewId|Out-Null}catch{$caught=$true}
Check $caught 'human confirmation view scope enforced'
$hc=Clone $result.humanConfirmations[0];$hc.sourceSnapshot.sha256='other'
$caught=$false;try{New-DeviceCandidate $r4 $op $cp $f.probeCorrespondence $hc $f.localViewId|Out-Null}catch{$caught=$true}
Check $caught 'human confirmation snapshot scope enforced'
$hc=Clone $result.humanConfirmations[0];$hc.outerHandle='another-instance'
$caught=$false;try{New-DeviceCandidate $r4 $op $cp $f.probeCorrespondence $hc $f.localViewId|Out-Null}catch{$caught=$true}
Check $caught 'human confirmation instance scope enforced'
"PASS: $script:n system diagram checks; five rows, 22 statements, five device candidates, one definition equivalence; no output file"
