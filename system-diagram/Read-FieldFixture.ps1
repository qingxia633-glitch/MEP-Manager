param([string]$Fixture=(Join-Path $PSScriptRoot 'tests/field-fixture.json'))
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'SystemDiagram.psm1') -Force
Import-Module (Join-Path $PSScriptRoot 'FieldCandidates.psm1') -Force
$f=Get-Content -LiteralPath $Fixture -Raw -Encoding UTF8|ConvertFrom-Json
$path=Join-Path (Join-Path $PSScriptRoot '..') $f.source.path
if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $f.source.sha256){throw 'Survey snapshot changed; review required'}
$snapshot=Read-DiagramSnapshot $path
$anchors=@($snapshot.entities|Where-Object effectiveName_RAW -ceq $f.effectiveName|Sort-Object {$_.insertion[0]})
if(!$anchors.Count){throw 'No selected family anchors'}
$buckets=@()
foreach($a in $anchors){
 # This fixture adapter supports the surveyed unrotated, unit-scale family.
 # Unknown/other transforms require a new coordinate adapter, not silent reuse.
 foreach($code in @(41,42,43,50)){
  $m=[regex]::Match($a.rawRecord,'BlockTransform_or_Array_DXF=\('+ $code +' \. ([^)]+)\)')
  $expected=if($code -eq 50){0}else{1}
  if(!$m.Success -or [double]::Parse($m.Groups[1].Value,[cultureinfo]::InvariantCulture) -ne $expected){throw 'Unsupported survey anchor transform'}
 }
 if($a.rawRecord -notmatch 'Normal_DXF210=\(0\.000000 0\.000000 1\.000000\)'){throw 'Unsupported survey normal'}
 $bucket=@($buckets|Where-Object {[math]::Abs($_.referenceX-$a.insertion[0]) -le $f.window.anchorXTolerance})
 if($bucket.Count -gt 1){throw 'Ambiguous horizontal group'}
 if(!$bucket.Count){$buckets+=,[pscustomobject]@{referenceX=$a.insertion[0];anchors=@($a)}}else{$bucket[0].anchors+=,$a}
}
$views=@()
foreach($bucket in $buckets){
 $selection=@(foreach($s in $snapshot.statements){
  if($s.referencePoint.Count -ne 3){continue}
  $inWindow=$false
  foreach($a in $bucket.anchors){
   $dx=$s.referencePoint[0]-$a.insertion[0];$dy=$s.referencePoint[1]-$a.insertion[1]
   if($dx -ge $f.window.minX -and $dx -le $f.window.maxX -and [math]::Abs($dy) -le $f.window.halfY){$inWindow=$true}
  }
  if($inWindow){$s}
 })
 $views+=,(New-DiagramLocalView -Snapshot $snapshot.sourceSnapshot -RowInserts $bucket.anchors -Statements $selection -LocalViewId ($f.scopeId+'/layout-group-'+($views.Count+1)) -RowBand $f.window.halfY)
}
$survey=Get-DiagramFieldCandidates -Views $views -Rules $f.roleRules -Variants $f.layoutVariants -ScopeId $f.scopeId
# Preserve the original five-row fixture and R1..R5 identities in a separate
# analysis scope. These are not additional rows in the 34-row survey count.
$local=& (Join-Path $PSScriptRoot 'Read-LocalFixture.ps1')
$localModel=Get-DiagramFieldCandidates -Views @($local) -Rules $f.roleRules -Variants $f.layoutVariants -ScopeId $local.localViewId
[pscustomobject]@{sourceSnapshot=$snapshot.sourceSnapshot;observationWindow=$f.window;surveyViews=$views;surveyModel=$survey;localView=$local;localModel=$localModel;scopeNote='layout groups are not confirmed drawing regions; local five rows also occur in survey; do not add counts'}
