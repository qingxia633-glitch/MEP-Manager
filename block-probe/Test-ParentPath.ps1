$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'Test-Anchor.ps1')
$code=Get-Content (Join-Path $PSScriptRoot 'BlockDefinitionProbe.lsp') -Raw
$n=0
$status=Read-Function 'bp:parent-status'
foreach($case in @(
 @($true,'INSERT','child','child','53','53','resolved'),
 @($true,'INSERT','child','child','54','53','owner_mismatch'),
 @($true,'INSERT','child','child','OTHER','53','owner_mismatch'),
 @($true,'INSERT','wrong','child','53','53','referenced_block_mismatch'),
 @($false,$false,$false,'child',$false,'53','handle_not_found'),
 @($true,'TEXT','child','child','53','53','entity_type_mismatch'),
 @($true,'INSERT','child','child',$false,$false,'owner_mismatch')
)){
 $env=@{};for($i=0;$i -lt 6;$i++){$env[$status[2][$i]]=$case[$i]}
 Check ((Eval-Form $status[3] $env) -ceq $case[6]) "parent status $($case[6])"
}
Check (!$code.Contains('(tblobjname "BLOCK" parent)')) 'BlockBegin is not owner target'
Check ($code.Contains("'vla-item (list collection parent)")) 'actual Blocks collection record'
Check ($code.Contains("'vla-get-Handle (list record)")) 'expected record Handle'
Check ($code.Contains('(cdr (assoc 5 (entget owner)))')) 'actual owner Handle from DXF330 entity'
foreach($key in @('ParentInsertHandle','ActualEntityType','ActualReferencedBlockName','RequestedReferencedBlockName','ActualOwnerHandle','ExpectedParentBlockRecordHandle','ParentPathStatus')){Check ($code.Contains($key)) "diagnostic $key"}
Check (!$code.Contains('Parent INSERT owner/reference mismatch')) 'no merged error'
Check ($code.Contains('(equal onePathStatus "resolved")')) 'resolved gate'
"PASS: $n parent path checks; actual Lisp decision forms evaluated, CAD getters not executed"
