param([string]$OutputDirectory)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'SystemScopePropagation.psm1') -Force
Import-Module (Join-Path $PSScriptRoot 'EvidenceAdmission.psm1') -Force
Import-Module (Join-Path $PSScriptRoot 'EvidenceInvestigationAdapter.psm1') -Force
Import-Module (Join-Path $PSScriptRoot '../model-core/FireGoldenSample.psm1')
$root=Join-Path $PSScriptRoot '../local_test_data'
$fire=Read-FireGoldenModel
$req=@($fire.requirements|Where-Object requirementId -In @('req:phone-relation','req:broadcast','req:membership'))
$tasks=@($req|ForEach-Object {[pscustomobject]@{requirement=$_;context=[pscustomobject]@{mode='engineering_task'}}})
$specs=@(
 @('EW-0002','ew0002-design-statements-reviewed-v2-20260924.json','ew0002-hierarchy-bridge-validated-20260924.json'),
 @('EW-0004','ew0004-design-statements-20260925.json','ew0004-hierarchy-bridge-20260925.json')
)
if($OutputDirectory){if(Test-Path -LiteralPath $OutputDirectory){throw 'Existing run directory protected'};New-Item -ItemType Directory -Path $OutputDirectory|Out-Null}
$summary=@()
foreach($spec in $specs){
 $sp=Join-Path $root $spec[1];$hp=Join-Path $root $spec[2]
 $s=Get-Content $sp -Raw|ConvertFrom-Json;$h=Get-Content $hp -Raw|ConvertFrom-Json
 $scoped=Add-DesignSystemScopes $s $h $req[0].scope.projectId
 $e=ConvertTo-DesignEvidenceAdmission $scoped
 $all=@($e.statementEvidence)+@($e.referenceEvidence)
 $result=Invoke-EvidenceInvestigation $all $tasks
 $run=[pscustomobject]@{sheet=$spec[0];sourceRegistration=[pscustomobject]@{projectId=$req[0].scope.projectId;basis='user-confirmed same project; does not establish building applicability'};provenance=@([pscustomobject]@{path=$sp;sha256=(Get-FileHash $sp).Hash},[pscustomobject]@{path=$hp;sha256=(Get-FileHash $hp).Hash});statements=$scoped;admission=$e;requirements=$req;consumption=$result}
 if($OutputDirectory){$run|ConvertTo-Json -Depth 80|Set-Content -LiteralPath (Join-Path $OutputDirectory ($spec[0]+'.json')) -Encoding UTF8}
 $summary+=,[pscustomobject]@{sheet=$spec[0];evidence=$all.Count;systems=@($all|Group-Object systemIdentity|Select-Object Name,Count);scopeStatus=@($all|Group-Object evidenceSystemScopeStatus|Select-Object Name,Count);consumption=@(foreach($q in $req){[pscustomobject]@{requirement=$q.requiredFact;relevant=@($result.evaluations|Where-Object {$_.requirementRef -eq $q.requirementId -and $_.status -eq 'task_relevant'}).Count;notApplicable=@($result.evaluations|Where-Object {$_.requirementRef -eq $q.requirementId -and $_.status -eq 'not_applicable'}).Count;status=$q.status}});searchScopes=$result.searchScopes.Count;supports=$result.supports.Count;hints=$result.hints.Count}
}
$summary|ConvertTo-Json -Depth 10
