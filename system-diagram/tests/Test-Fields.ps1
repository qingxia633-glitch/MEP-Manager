$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../FieldCandidates.psm1') -Force
$script:n=0
function Check($ok,$why){if(!$ok){throw $why};$script:n++}
function Clone($x){ConvertFrom-Json (ConvertTo-Json -InputObject $x -Depth 90)}
$r=& (Join-Path $PSScriptRoot '../Read-FieldFixture.ps1')
$m=$r.localModel;$survey=$r.surveyModel
Check ($survey.rowLayouts.Count -eq 34) '34 selected row expressions'
Check ($survey.columnPatterns.Count -eq 4) 'four observed candidate bands'
foreach($v in @(@('R1','single-QWB+kW'),@('R2','single-QWB+kW'),@('R3','double-QWB+kW'),@('R4','double-QWB+kW'),@('R5','single-QWB+kW'))){
 $row=$m.rowLayouts|Where-Object rowId -eq $v[0]
 Check ($row.layoutVariant -eq $v[1]) ('local variant '+$v[0])
}
foreach($h in @('7EDD4','7EDE6')){
 $role=@($m.fieldRoles|Where-Object {$_.sourceStatement.handle -eq $h -and $_.role -eq 'row_power_field'})
 Check ($role.Count -eq 1) 'shifted power retains candidate role'
 Check ($role[0].layoutEvidence[0].deltaX -gt 16000) 'actual shifted normalized position'
}
$hyp=$m.bindingHypotheses|Where-Object {$_.subject.handle -eq '7EDE6'}
Check ($hyp.status -eq 'unresolved') 'R4 unresolved'
Check ($hyp.candidateTargets.Count -eq 4) 'R4 row, two identifiers, group alternatives'
Check (@($hyp.candidateTargets|Where-Object kind -eq representation).Count -eq 2) 'both identifier representations'
Check (@($hyp.candidateTargets|Where-Object {$_.kind -eq 'representation'}|ForEach-Object handle|Sort-Object -Unique).Count -eq 2) 'identifiers retain independent identities'
Check ($hyp.missingEvidence.Count -gt 0 -and $hyp.opposingEvidence.Count -gt 0) 'uncertainty reasons explicit'
$hidden=@($survey.fieldRoles|Where-Object {$_.sourceStatement.rawText -eq 'JLM'})
Check ($hidden.Count -eq 5) 'five JLM raw declarations retained'
Check (@($hidden|Where-Object {$_.visibility.state -ne 'hidden_flag' -or $_.visibleFieldSupport}).Count -eq 0) 'hidden JLM never visible field support'
$cross=@($survey.fieldRoles|Where-Object {$_.sourceStatement.handle -eq '8946C' -and $_.role -eq 'cross-view-reference'})
Check ($cross.Count -eq 1) 'cross view statement candidate'
foreach($model in @($m,$survey)){
 Check (@($model.bindingHypotheses|Where-Object status -ne unresolved).Count -eq 0) 'no confirmed binding'
 Check (@($model.PSObject.Properties.Name|Where-Object {$_ -in @('circuits','quantities','connections')}).Count -eq 0) 'no circuit/quantity/connection collections'
 foreach($p in $model.columnPatterns){
  Check ($p.deltaX.distribution.Count -gt 0 -and $p.deltaX.max -ge $p.deltaX.min) 'range/distribution not fixed X'
  Check ($p.sourceSnapshot.sha256 -eq $model.sourceSnapshot.sha256 -and $p.supportingSamples.Count -gt 0) 'pattern provenance'
 }
}
foreach($v in @(@('single-QWB+kW',13),@('double-QWB+kW',2),@('WP+load/no-window-kW',8),@('WE+load/no-window-kW',6),@('JL+kW+hidden-attribute',5))){
 Check (@($survey.rowLayouts|Where-Object layoutVariant -eq $v[0]).Count -eq $v[1]) ('survey variant '+$v[0])
}
Check ((Clone $r).surveyModel.rowLayouts.Count -eq 34) 'plain data JSON roundtrip'
$band=$survey.columnPatterns|Where-Object candidateRole -eq 'identifier/load-expression'
Check ($band.exceptionSamples.Count -eq 5) 'hidden JLM retained as five exceptions instead of visible column samples'
Check ($band.frequency.rowCount -eq 29 -and $band.frequency.statementCount -eq 31) 'distinct identifier observations counted without merging representations'
$powerBand=$survey.columnPatterns|Where-Object candidateRole -eq 'power-expression'
Check ($powerBand.frequency.rowCount -eq 20) 'twenty observed row power fields'
$single=$powerBand.layoutVariant|Where-Object layoutVariant -eq 'single-QWB+kW'
$double=$powerBand.layoutVariant|Where-Object layoutVariant -eq 'double-QWB+kW'
Check ($double.deltaX.min -gt $single.deltaX.max) 'distinct shifted power distribution retained as variant'
Check (@($survey.fieldRoles|Where-Object {$_.sourceStatement.rawText -eq 'JLM' -and $_.visibility.renderedVisibility -ne 'not_verified'}).Count -eq 0) 'CAD flag does not fabricate rendering confirmation'
$before=$r.localView|ConvertTo-Json -Depth 90 -Compress
$config=Get-Content (Join-Path $PSScriptRoot 'field-fixture.json') -Raw -Encoding UTF8|ConvertFrom-Json
$again=Get-DiagramFieldCandidates -Views @($r.localView) -Rules $config.roleRules -Variants $config.layoutVariants -ScopeId 'controlled'
Check (($r.localView|ConvertTo-Json -Depth 90 -Compress) -ceq $before) 'derived layer does not mutate statements or raw facts'
# Move power closer to one QWB without changing row relation; no nearest target.
$moved=Clone $r.localView
$power=$moved.statements|Where-Object handle -eq 7EDE6
$power.insertion[0]-=1500;$power.alignment[0]-=1500
$test=Get-DiagramFieldCandidates @($moved) $config.roleRules $config.layoutVariants 'controlled'
$h=$test.bindingHypotheses|Where-Object {$_.subject.handle -eq '7EDE6'}
Check ($h.status -eq 'unresolved' -and $h.candidateTargets.Count -eq 4) 'nearer power does not select a box'
# Multiple lexical interpretations stay separate, never overwritten.
$rules=@($config.roleRules)+@([pscustomobject]@{id='alternative';pattern='^QWB\d+$';role='unresolved_label';band=$null})
$multi=Get-DiagramFieldCandidates @($r.localView) $rules $config.layoutVariants 'controlled'
Check (@($multi.fieldRoles|Where-Object {$_.sourceStatement.handle -eq '7EDE9'}).Count -eq 2) 'multiple roles per statement supported'
$bad=Clone $r.localView;$bad.statements[0].sourceSnapshot.sha256='other'
$caught=$false;try{Get-DiagramFieldCandidates @($bad) $config.roleRules $config.layoutVariants 'controlled'|Out-Null}catch{$caught=$true}
Check $caught 'reject mismatched statement snapshots'
$caught=$false;try{Get-DiagramFieldCandidates @($r.localView,$r.localView) $config.roleRules $config.layoutVariants 'controlled'|Out-Null}catch{$caught=$true}
Check $caught 'reject duplicate view scopes'
# Competing row associations stay alternatives rather than nearest ownership.
$amb=Clone $r.localView;$s=$amb.statements|Where-Object handle -eq 7EDE6
$s.candidateRowIds=@('R3','R4');$s.bindingStatus='ambiguous'
$a=Get-DiagramFieldCandidates @($amb) $config.roleRules $config.layoutVariants 'controlled'
$af=$a.fieldRoles|Where-Object {$_.sourceStatement.handle -eq '7EDE6'}
Check ($af.status -eq 'ambiguous' -and $af.layoutEvidence.Count -eq 2) 'competing row evidence preserved'
$ah=$a.bindingHypotheses|Where-Object {$_.subject.handle -eq '7EDE6'}
Check (@($ah.candidateTargets|Where-Object kind -eq row).Count -eq 2 -and $ah.status -eq 'unresolved') 'no forced row target'
Check (@(($a.columnPatterns|Where-Object candidateRole -eq 'power-expression').exceptionSamples|Where-Object {$_.sourceStatement.handle -eq '7EDE6'}).Count -eq 2) 'ambiguous samples excluded from stable band support'
"PASS: $script:n field candidate checks"
