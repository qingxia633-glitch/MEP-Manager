$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../DesignStatementBridge.psm1') -Force
$base=Get-Content (Join-Path $PSScriptRoot '../../local_test_data/ew0002-hierarchy-bridge-validated-20260924.json') -Raw|ConvertFrom-Json
$script:n=0
function Check($v,$m){$script:n++;if(!$v){throw "FAIL: $m"}}
$before=$base|ConvertTo-Json -Depth 80 -Compress
$r=ConvertTo-AutomaticDesignStatements $base
Check ($r.paragraphProcessing.Count -eq 46) 'all paragraphs use shared atomic pipeline'
Check (($base|ConvertTo-Json -Depth 80 -Compress) -ceq $before) 'upstream facts immutable'
Check ($r.atomicStatements.Count -gt 82) 'bridge paragraphs receive atomics'
Check ($r.designStatements.Count -eq @($r.atomicStatements|Where-Object {$_.rawText.Trim()}).Count) 'only nonempty atomics upgrade'
foreach($a in $r.atomicStatements|Where-Object {!$_.rawText.Trim()}){Check (@($r.designStatements|Where-Object atomicRef -EQ $a.statementId).Count -eq 0) 'blank atomic blocked'}
foreach($s in $r.designStatements){
 Check ($s.sheetId -eq $base.identity.sheetId -and $s.drawingNumber -eq 'EW-0002') 'sheet trace'
 Check ($s.rawText -ceq ($s.sourceSpans.rawText -join '')) 'raw body exactly reconstructed'
 Check ($s.sourceSpanRefs.Count -gt 0 -and $s.paragraphRef -and $s.columnScopeRef) 'trace fields'
 $columnRefs=@($base.coverage.rawTextDispositions|Where-Object {$_.rawEntityRef -in $s.sourceSpans.fragmentRef}|ForEach-Object columnScopeId|Select-Object -Unique)
 if($columnRefs.Count -eq 1){Check ($s.columnScopeRef -eq $columnRefs[0]) 'preserve upstream column scope reference rather than fabricate one'}
 Check ($s.applicabilityScope.buildingScope -eq 'unresolved' -and !$s.applicabilityScope.automaticApplication) 'scope not enlarged'
 foreach($span in $s.sourceSpans){$f=$base.after.rawTextRecords|Where-Object id -EQ $span.fragmentRef;Check ($f.rawText.Substring($span.start,$span.length) -ceq $span.rawText) 'span reverses to raw entity'}
}
$g=@($r.designStatements|Where-Object {$_.sourceEntityHandles -contains '23428' -or $_.sourceEntityHandles -contains '23401' -or $_.sourceEntityHandles -contains '23402'})
Check ($g.Count -eq 3) 'golden three atomics become distinct statements'
Check (@($g|Where-Object {$_.applicabilityScope.subjectScopeCandidate -eq '非消防负荷' -and $_.applicabilityScope.scopeSource -eq 'hierarchy'}).Count -eq 3) 'hierarchy subject preserved separately'
Check (@($g|ForEach-Object applicabilityConditions|Where-Object {$_.kind -eq 'qualitative_length' -and $_.thresholdStatus -eq 'unresolved'}).Count -eq 2) 'no short long thresholds invented'
$alts=@($g|ForEach-Object alternativeClauses)
Check ($alts.Count -eq 1 -and ($alts[0].options.rawText -join '|') -ceq '短路瞬时|短路短延时') 'two explicit alternative spans'
Check (@($g|Where-Object {$_.statementType -eq 'purpose_statement' -and $_.purposeRelation.subject_RAW -eq '短延时脱扣器'}).Count -eq 1) 'purpose subject connector goal linked'
Check (@($r.designStatements|Where-Object {$_.sourceEntityHandles -contains '23471' -or $_.sourceEntityHandles -contains '234DB'}).Count -eq 0) 'no other sheets'
foreach($p in $base.newParagraphs){Check (@($r.designStatements|Where-Object paragraphRef -EQ $p.paragraphId).Count -gt 0) 'every new bridge paragraph participates'}
Check ($r.formalEvidence.Count -eq 0 -and $r.quantities.Count -eq 0 -and $r.circuits.Count -eq 0) 'candidate endpoint only'
Check (@($r.reviewItems|Where-Object type -EQ empty_atomic_candidate).Count -eq @($r.atomicStatements|Where-Object {!$_.rawText.Trim()}).Count) 'all blank atomics reviewed'
Check (@($r.designStatements|ForEach-Object applicabilityConditions|Where-Object {$_.rawText -eq '当地供电部门要求，'}).Count -eq 0) 'lexical local authority is not when condition'
Check (@($r.designStatements|ForEach-Object alternativeClauses|ForEach-Object options|Where-Object {$_.rawText -match '^通过'}).Count -eq 0) 'preposition not promoted to alternative option'
Import-Module (Join-Path $PSScriptRoot '../ParagraphSemantics.psm1') -Force
$empty=Invoke-ParagraphSemanticCandidates @()
Check (@($empty.paragraphs).Count -eq 0) 'shared splitter preserves empty paragraph list'
$sem=Invoke-ParagraphSemanticCandidates $base.after.paragraphs
foreach($p in $base.after.paragraphs|Where-Object {$_.atomicStatements.Count}){
 $again=$sem.paragraphs|Where-Object paragraphId -EQ $p.paragraphId
 foreach($field in @('atomicStatements','conditions','exceptions','references','signalCandidates')){Check (($p.$field|ConvertTo-Json -Depth 30 -Compress) -ceq ($again.$field|ConvertTo-Json -Depth 30 -Compress)) "shared splitter preserves old $field"}
}
function Example([string]$Text){
 $x=$base|ConvertTo-Json -Depth 80|ConvertFrom-Json
 $f=$x.after.rawTextRecords[0];$f.id='sample:raw';$f.handle='synthetic';$f.rawText=$Text
 $p=$x.after.paragraphs[0];$p.paragraphId='sample:paragraph';$p.textFragments=@($f);$p.regionId='sample:region';$p.readingOrderCandidate.orderedFragmentIds=@($f.id);$p.readingOrderCandidate.confidence='high'
 $section=$x.hierarchy.sections[0];$section.sectionId='sample:section';$section.numberingRaw='9.8';$section.titleFragmentRefs=@($f.id);$section.fragmentRefs=@($f.id);$section.sourceRegion.regionRefs=@($p.regionId)
 $x.after.paragraphs=@($p);$x.after.rawTextRecords=@($f);$x.hierarchy.sections=@($section);$x.hierarchy.subItems=@()
 $disposition=$x.coverage.rawTextDispositions[0];$disposition.rawEntityRef=$f.id;$disposition.disposition='paragraph_member';$x.coverage.rawTextDispositions=@($disposition)
 $x
}
$x=Example '9.8 设备组：当潮湿时，应采用措施；其它措施或设备待明确。'
$v=ConvertTo-AutomaticDesignStatements $x
Check ($v.designStatements.Count -eq 2 -and $v.designStatements[0].applicabilityConditions.Count -eq 1 -and $v.designStatements[1].applicabilityConditions.Count -eq 0) 'condition never leaks to adjacent atomic'
Check (@($v.designStatements|ForEach-Object alternativeClauses).Count -eq 0) 'bare or remains signal'
Check (@($v.reviewItems|Where-Object type -EQ alternative_signal_without_bounded_options).Count -eq 1) 'bare or reviewed'
$v=ConvertTo-AutomaticDesignStatements (Example '9.8 设备组：除注明外，应安装设备。')
Check ($v.designStatements[0].exceptionConditions.Count -eq 1 -and $v.designStatements[0].exceptionConditions[0].appliesToStatement -eq $v.designStatements[0].statementId) 'exception points to statement, not whole paragraph'
$v=ConvertTo-AutomaticDesignStatements (Example '9.8 设备组：除特殊情形外；其它内容应保持候选。')
Check (@($v.designStatements|ForEach-Object exceptionConditions).Count -eq 0) 'exception without default host not attached to another atomic'
$v=ConvertTo-AutomaticDesignStatements (Example '9.8 设备组：详见另一系统图。')
Check ($v.designStatements[0].crossDrawingReferences[0].resolutionStatus -eq 'unresolved') 'reference navigation never resolves a document'
$v=ConvertTo-AutomaticDesignStatements (Example '9.8 相关专业提供的工程设计资料；')
Check ($v.designStatements[0].statementStatus -eq 'unresolved') 'design word alone does not validate a requirement'
$v=ConvertTo-AutomaticDesignStatements (Example '9.8 本期设备总容量为：120kVA。')
Check ($v.designStatements[0].applicabilityScope.subjectScopeCandidate -eq 'unresolved') 'predicate ending is not a nominal scope label'
$v=ConvertTo-AutomaticDesignStatements (Example '9.8 建设单位资料（如：设计图纸）。')
Check ($v.designStatements[0].applicabilityScope.subjectScopeCandidate -eq 'unresolved' -and $v.designStatements[0].statementType -eq 'unknown') 'parenthesized colon is not title scope; construction word is not requirement'
$x=Example '9.8 设备组：当潮湿时，应采用措施。';$x.after.paragraphs[0].readingOrderCandidate.confidence='low'
$v=ConvertTo-AutomaticDesignStatements $x
Check ($v.designStatements.Count -eq 0 -and $v.paragraphProcessing[0].status -eq 'blocked') 'low reading order not upgraded'
Check (@($r.designStatements|Where-Object {$_.statementStatus -eq 'supported'}).Count -eq 0) 'recognized type alone cannot yield supported'
$module=Get-Content (Join-Path $PSScriptRoot '../DesignStatementBridge.psm1') -Raw
Check ($module -notmatch '23428|23401|23402|非消防负荷|4\.12\.1|DesignStatementFixture') 'no golden adapter, handles or exact subject in general bridge'
Write-Host "PASS: $script:n automatic statement bridge checks"
