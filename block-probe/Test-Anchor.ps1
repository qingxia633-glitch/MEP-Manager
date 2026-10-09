$ErrorActionPreference='Stop'
$code=Get-Content (Join-Path $PSScriptRoot 'BlockLocalGeometryProbe.lsp') -Raw
# Evaluate the actual pure Lisp normalization/decision forms, not a second copy
# of the decision table. This tiny test evaluator does NOT emulate CAD getters.
function Parse-Form($q){
 $token=$q.Dequeue()
 if($token -eq "'"){return ,@('quote',(Parse-Form $q))}
 if($token -eq '('){$items=[Collections.Generic.List[object]]::new();while($q.Peek() -ne ')'){$items.Add((Parse-Form $q))};$null=$q.Dequeue();return ,$items.ToArray()}
 return $token
}
function Read-Function($name){
 $start=$code.IndexOf('(defun '+$name+' ')
 if($start -lt 0){throw "missing $name"}
 $q=[Collections.Generic.Queue[string]]::new()
 foreach($m in [regex]::Matches($code.Substring($start),'"(?:\\.|[^"\\])*"|[()'']|[^\s()'']+')){$q.Enqueue($m.Value)}
 return ,(Parse-Form $q)
}
function Unquote($form){
 if($form -is [string]){if($form -match '^[-\d.]+$'){return [double]$form};if($form.StartsWith('"')){return [regex]::Unescape($form.Substring(1,$form.Length-2))};return $form}
 return ,@($form|ForEach-Object{Unquote $_})
}
function Equal-Value($a,$b,$fuzz){
 if($a -is [array] -or $b -is [array]){
  if($a -isnot [array] -or $b -isnot [array] -or $a.Count -ne $b.Count){return $false}
  for($i=0;$i -lt $a.Count;$i++){if(!(Equal-Value $a[$i] $b[$i] $fuzz)){return $false}};return $true
 }
 if($a -is [ValueType] -and $b -is [ValueType]){return [math]::Abs([double]$a-[double]$b) -le $fuzz}
 return $a -ceq $b
}
function Eval-Form($form,$env){
 if($form -is [string]){
  if($form.StartsWith('"')){return [regex]::Unescape($form.Substring(1,$form.Length-2))}
  if($form -eq 'T'){return $true};if($form -eq 'nil'){return $false}
  if(!$env.ContainsKey($form)){throw "unknown symbol $form"};return $env[$form]
 }
 switch($form[0]){
  'list' {$values=[Collections.Generic.List[object]]::new();foreach($v in $form[1..($form.Length-1)]){$values.Add((Eval-Form $v $env))};return ,$values.ToArray()}
  'quote' {return ,(Unquote $form[1])}
  'equal' {$a=Eval-Form $form[1] $env;$b=Eval-Form $form[2] $env;$fuzz=0;if($form.Count -gt 3){$fuzz=Eval-Form $form[3] $env};return Equal-Value $a $b $fuzz}
  'member' {$a=Eval-Form $form[1] $env;$b=Eval-Form $form[2] $env;return ($b -ccontains $a)}
  'cond' {foreach($clause in $form[1..($form.Length-1)]){if(Eval-Form $clause[0] $env){return Eval-Form $clause[1] $env}};return $false}
  'and' {foreach($v in $form[1..($form.Length-1)]){if(!(Eval-Form $v $env)){return $false}};return $true}
  'or' {foreach($v in $form[1..($form.Length-1)]){if(Eval-Form $v $env){return $true}};return $false}
  'not' {return !(Eval-Form $form[1] $env)}
  'strcase' {return (Eval-Form $form[1] $env).ToUpperInvariant()}
  'vl-string-trim' {return (Eval-Form $form[2] $env).Trim((Eval-Form $form[1] $env).ToCharArray())}
  default {throw "unsupported test evaluator operator $($form[0])"}
 }
}
$n=0
function Check($ok,$message){if(!$ok){throw $message};$script:n++}
$normalize=Read-Function 'blp:normalize-handle'
foreach($case in @(@('abC','ABC'),@(' ABC ','ABC'),@("`t836`r`n",'836'),@('836','836'),@('',''))){
 Check ((Eval-Form $normalize[3] @{value=$case[0]}) -ceq $case[1]) 'normalization of raw input'
}
$status=Read-Function 'blp:anchor-status'
$cases=@(
 @($false,$false,$true,$false,$false,$true,'handle_not_found'),
 @($false,$true,$false,$false,$true,$true,'owner_mismatch'),
 @($true,$true,$false,$true,$true,$true,'owner_mismatch'),
 @($true,$false,$true,$false,$true,$true,'traversal_handent_disagreement'),
 @($false,$true,$true,$false,$true,$true,'traversal_handent_disagreement'),
 @($true,$true,$true,$false,$true,$true,'traversal_handent_disagreement'),
 @($true,$true,$true,$true,$false,$true,'missing_dxf10'),
 @($true,$true,$true,$true,$true,$false,'coordinate_transform_error'),
 @($true,$true,$true,$true,$true,$true,'resolved')
)
foreach($case in $cases){$env=@{};for($i=0;$i -lt 6;$i++){$env[$status[2][$i]]=$case[$i]};Check ((Eval-Form $status[3] $env) -eq $case[6]) "status $($case[6])"}
foreach($key in @('AnchorInput_RAW','AnchorInput_Normalized','RequestedBlockDefinition','ResolvedBlockDefinition','BlockRecordHandle','Traversal.','Handent.','OwnerHandle','DXF10_RAW','DXF11_RAW','Text_RAW','AnchorTransformedLocalCoordinate','SnapshotComparisonStatus')){Check ($code.Contains($key)) "diagnostic $key"}
Check ($code.Contains('(handent handle)')) 'global lookup is cross-check'
Check ($code.Contains('(cdr (assoc 330 d))')) 'owner from raw DXF330'
Check ($code.Contains('(equal (blp:owner glob) expected)')) 'global owner mandatory'
Check ($code.Contains('(equal (blp:owner tr) expected)')) 'traversal owner mandatory'
Check ($code.Contains('(equal (cdr (assoc -1 tr)) (cdr (assoc -1 glob)))')) 'same entity mandatory'
Check ($code.Contains('(foreach item anchorDiagnostics')) 'diagnostics persisted on success'
Check ($code -notmatch 'Anchor missing from this definition or has no DXF10') 'split failure diagnostics'
Check ($code -notmatch "'trans \(list \(cdr \(assoc 11") 'no DXF11 fallback'
"PASS: $n anchor decision/normalization and integration contract checks; CAD getters not executed"
