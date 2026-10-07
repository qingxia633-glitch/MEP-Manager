$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../BlockTextIndex.psm1') -Force
$script:n=0
function Check($v,$message){if(!$v){throw $message};$script:n++}
function Reject($action,$message){$failed=$false;try{& $action|Out-Null}catch{$failed=$true};Check $failed $message}
function TextRecord($block,$h,$type,$raw){
 @('Text_BEGIN',"SourceBlock=`"$block`"","InternalHandle=`"$h`"","EntityType=`"$type`"",'Layer="arbitrary layer"',
   ('Text_RAW='+$raw),'Tag_RAW="TAG"','Prompt_RAW="Prompt"',('Default_RAW='+$raw),'LocalPoint_DXF10=(1.250000000000 -2.000000000000 0.000000000000)',
   'Alignment_DXF11=(0.0 0.0 0.0)','Normal_DXF210=(0.0 0.0 1.0)','DXF60_RAW=1','AttributeFlags_DXF70_RAW=3',
   'VisibilityStatus="definition_only_not_evaluated"','DXF:3="prefix"','DXF:1="suffix"','ReadStatus="read"','Text_END')
}
function Reference($parent,$target,$h,$kind='block_definition'){
 @('Reference_BEGIN',"ParentBlock=`"$parent`"","SourceKind=`"$kind`"","InternalHandle=`"$h`"","ReferencedBlockName=`"$target`"",'Reference_END')
}
function Block($name,$body,$count,$kind='block_definition',$status='read'){
 @('Block_BEGIN',"BlockName=`"$name`"","Kind=`"$kind`"",'Flags_RAW=0','XrefPath_RAW=nil')+@($body)+@("BlockTextCount=$count","ReadStatus=`"$status`"",'Block_END')
}
$header=@('IndexVersion="1.0"','AcquisitionMode="BlockTableDirectTextAndReferences"','DWG="fixture.dwg"','Limitations="no evaluated visibility or binding"')
$fixture=$header+
 (Block 'A' ((TextRecord 'A' 'T1' 'TEXT' '"QWB1"')+(TextRecord 'A' 'T2' 'MTEXT' '"前缀\\P中文\"引号\"\nQWB1"')+(Reference 'A' 'B' 'AB')) 2)+
 (Block 'B' ((TextRecord 'B' 'D1' 'ATTDEF' '"QWB1"')+(Reference 'B' 'A' 'BA')) 1)+
 (Block 'Unused' ((TextRecord 'Unused' 'T3' 'TEXT' '"QWB1"')+(TextRecord 'Unused' 'T4' 'TEXT' '"QWB1"')) 2)+
 (Block '*Model_Space' ((Reference '*Model_Space' 'B' 'M1' 'modelspace_top_level')+(Reference '*Model_Space' 'B' 'M2' 'modelspace_top_level')) 0 'modelspace_top_level')+
 (Block '*Paper_Space' (Reference '*Paper_Space' 'A' 'P1' 'paperspace_top_level') 0 'paperspace_top_level')+
 (Block 'External' @() 0 'block_definition' 'not_scanned_external')+
 @('BlockTableRecordCount=6','BlockDefinitionCount=4','TextBearingBlockCount=3','TextRecordCount=5','TEXTCount=3','MTEXTCount=1','ATTDEFCount=1',
 'ReferenceCount=5','ExternalSkippedCount=1','ProxyEntityCount=1','ReadErrorCount=0','END_OF_REPORT')
$tmp=Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString()+'.txt')
try {
 $fixture|Set-Content -LiteralPath $tmp -Encoding UTF8
 $i=Read-BlockTextIndex $tmp
 Check ($i.Blocks.Count -eq 6) 'all definitions and layout containers retained'
 Check ($i.Texts.Count -eq 5) 'duplicates retained'
 Check ($i.References.Count -eq 5) 'all independent reference entities retained'
 Check ($i.SourceSnapshot.SHA256.Length -eq 64) 'snapshot fingerprint'
 Check ($i.SourceSnapshot.DWG -eq 'fixture.dwg') 'DWG provenance'
 Check ($i.Metadata.BlockDefinitionCount -eq 4) 'layout containers excluded from definition count'
 Check ($i.Metadata.TextBearingBlockCount -eq 3) 'text bearing definition count'
 Check ($i.Texts[0].Layer -eq 'arbitrary layer') 'no layer filtering'
 Check ($i.Texts[0].LocalPoint_DXF10 -eq '(1.250000000000 -2.000000000000 0.000000000000)') 'raw coordinate precision'
 Check ($i.Texts[1].Text_RAW.Contains('\P中文"引号"')) 'CAD formatting quotes and Chinese retained'
 Check ($i.Texts[1].Text_RAW.Contains("`nQWB1")) 'escaped newline decoded'
 Check ($i.Texts[1].RawDXF.Count -eq 2) 'ordered raw text chunks retained'
 Check ($i.Texts[2].Default_RAW -eq 'QWB1' -and $i.Texts[2].Tag_RAW -eq 'TAG') 'ATTDEF default and tag'
 Check ($i.Texts[2].Prompt_RAW -eq 'Prompt') 'ATTDEF prompt'
 Check ($i.Texts[2].DXF60_RAW -eq 1 -and $i.Texts[2].AttributeFlags_DXF70_RAW -eq 3) 'hidden attribute flags retained'
 Check ($i.Texts[0].SourceSnapshot.SHA256 -eq $i.SourceSnapshot.SHA256) 'text source identity'
 $q=Find-BlockDefinitionText $i 'qwb1'
 Check ($q.Hits.Count -eq 5) 'generic literal case insensitive query includes duplicates and defaults'
 Check ($q.Hits[0].DirectReferences.Count -eq 2) 'direct nested and layout parents'
 Check ($q.Hits[0].ReachableTopLevelReferences.Count -eq 3) 'cycle-safe reverse reachability retains M1 M2 P1'
 Check ($q.Hits[3].ReachableTopLevelReferences.Count -eq 0) 'unreferenced definition text retained'
 Check ($q.Hits[0].RelationStatus -eq 'reference_reachability_only_not_instance_binding') 'no instance binding'
 Check ($q.Hits[2].VisibilityStatus -eq 'not_evaluated') 'hidden ATTDEF not declared visible'
 Check ($q.EngineeringBindings.Count -eq 0) 'no engineering objects'
 Check ((Find-BlockDefinitionText $i 'QWB.').Hits.Count -eq 0) 'query is not regex'
 Check ((Find-BlockDefinitionText $i 'absent').Status -eq 'not_found_in_readable_block_definition_text') 'absence scoped to readable text'
 Check ($q.ExternalSkippedCount -eq 1) 'external coverage gap survives search'
 $json=& (Join-Path $PSScriptRoot '../Search-BlockText.ps1') -Report $tmp -Query @('QWB1','absent')
 Check (($json|ConvertFrom-Json).Results.Count -eq 2) 'generic multiquery entrypoint'
 $renamed=$fixture -replace 'QWB1','OTHER_PANEL' -replace 'InternalHandle="T1"','InternalHandle="REPLACED"'
 $renamed|Set-Content -LiteralPath $tmp -Encoding UTF8
 Check ((Find-BlockDefinitionText (Read-BlockTextIndex $tmp) 'OTHER_PANEL').Hits.Count -eq 5) 'identifiers and handles not hardcoded'
 foreach($mutation in @(
   @($fixture|Where-Object{$_ -ne 'END_OF_REPORT'}),
   @($fixture -replace '^ReadErrorCount=0$','ReadErrorCount=1'),
   @($fixture -replace '^TextRecordCount=5$','TextRecordCount=6'),
   @($fixture -replace '^SourceBlock="A"$','SourceBlock="Wrong"'),
   @($fixture -replace '^ReadStatus="read"$','ReadStatus="partial"'),
   @($fixture -replace '^IndexVersion="1.0"$','IndexVersion="future"')
 )){
   $mutation|Set-Content -LiteralPath $tmp -Encoding UTF8
   Reject {Read-BlockTextIndex $tmp} 'reject incomplete/corrupt/provenance-inconsistent index'
 }
 $empty=$header+(Block 'empty' @() 0)+@('BlockTableRecordCount=1','BlockDefinitionCount=1','TextBearingBlockCount=0','TextRecordCount=0',
 'TEXTCount=0','MTEXTCount=0','ATTDEFCount=0','ReferenceCount=0','ExternalSkippedCount=0','ReadErrorCount=0','END_OF_REPORT')
 $empty|Set-Content -LiteralPath $tmp -Encoding UTF8
 Check ((Read-BlockTextIndex $tmp).Texts.Count -eq 0) 'empty index supported'
} finally {Remove-Item -LiteralPath $tmp -ErrorAction SilentlyContinue}

$lsp=Get-Content (Join-Path $PSScriptRoot '../BlockTextIndex.lsp') -Raw -Encoding UTF8
$clean=[regex]::Replace($lsp,'"(?:\\.|[^"\\])*"|;[^\r\n]*','')
$depth=0;foreach($c in $clean.ToCharArray()){if($c -eq '('){$depth++};if($c -eq ')'){$depth--;if($depth -lt 0){throw 'Lisp unbalanced'}}}
Check ($depth -eq 0) 'Lisp balanced'
$depth=0
foreach($line in ($clean -split "`r?`n")) {
 if($line -match '^\(defun (bti:|c:)'){Check ($depth -eq 0) 'public/helper definition at top level'}
 foreach($c in $line.ToCharArray()){if($c -eq '('){$depth++};if($c -eq ')'){$depth--}}
}
Check ($clean -notmatch '\(error\s') 'no unsupported error function'
Check ($lsp.Contains('(substr outputPath 2 1)') -and $lsp.Contains('(substr outputPath 3 1)')) 'absolute path validation'
Check ($clean -notmatch '(?i)\((entmod|entmake|entdel|command|command-s|setvar|vla-put-\S*|vla-explode|vla-resetblock|vla-save\S*|vla-transformby)\b') 'no DWG mutation operations'
Check ($lsp.Contains('(vlax-for block blocks')) 'enumerate BlockTable'
Check ($lsp.Contains('(vlax-for obj block')) 'direct entities only'
Check ([regex]::Matches($lsp,"'bti:block").Count -eq 1) 'no recursive definition traversal'
Check ($lsp.Contains('vla-get-IsXRef') -and $lsp.Contains('vla-get-IsLayout')) 'explicit layout and external scope'
Check ($lsp -notmatch 'QWB[0-9]|1D433|E1DB') 'no project answer or sample handles in acquisition'
Check (!$lsp.Contains('MEPFULLREAD') -and !$lsp.Contains('MEP-entity-report.txt')) 'independent command and output'
Check ($lsp.Contains('(findfile outputPath)')) 'protect existing snapshot'
Check ([regex]::Matches($lsp,'\(setq outputPath\b').Count -eq 1) 'chosen full path never rebuilt'
Check ($lsp.Contains('(vl-filename-base outputPath)') -and !$lsp.Contains('vl-filename-nondirectory')) 'supported filename functions'
Check ($lsp.Contains("(member (car p) '(1 3))")) 'MTEXT concatenates chunks in DXF order'
foreach($field in @('Flags_RAW','XrefPath_RAW','LocalPoint_DXF10','DXF60_RAW','AttributeFlags_DXF70_RAW','Default_RAW','Prompt_RAW','Tag_RAW',
 'ReadErrorCount','ExternalSkippedCount','TextBearingBlockCount','TEXTCount','MTEXTCount','ATTDEFCount','ReferencedBlockName','SourceKind','Encoding')){
 Check ($lsp.Contains('"'+$field+'"')) "acquisition contract $field"
}
"PASS: $script:n block text index checks; AutoCAD runtime not exercised"
