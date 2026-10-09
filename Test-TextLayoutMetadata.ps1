$ErrorActionPreference='Stop'
# Reuse the existing restricted evaluator; no CAD runtime/getters are emulated.
. (Join-Path $PSScriptRoot 'block-probe/Test-Anchor.ps1')
$code=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'Test-AutoCADEntities.lsp'))
$n=0
$spec=Read-Function 'mep2:layout-spec'
function Map-Fields($type,$dxf){
 $map=Eval-Form $spec[3] @{typ=$type};$output=@{}
 foreach($field in $map){$output[$field[0]]=$dxf[[int]$field[1]]}
 return $output
}
foreach($angle in @(0,([math]::PI/2),0.371)){
 foreach($align in @(0,1,2)){
  $d=@{50=$angle;40=250;41=.85;51=.12;7='fixture-style';72=$align;73=2;11=@(12,23,0);210=@(0,0,1)}
  $v=Map-Fields 'TEXT' $d
  Check ($v.Rotation -eq $angle -and $v.HorizontalAlignment -eq $align -and $v.VerticalAlignment -eq 2) 'TEXT angle/alignment preserved'
  Check ($v.TextHeight -eq 250 -and $v.WidthFactor -eq .85 -and $v.ObliqueAngle -eq .12 -and $v.TextStyle -eq 'fixture-style') 'TEXT size/style preserved'
  Check (($v.AlignmentPoint_OCS_RAW -join ',') -eq '12,23,0' -and ($v.Normal -join ',') -eq '0,0,1') 'TEXT points/normals raw'
 }
}
$v=Map-Fields 'ATTRIB' @{50=.7;40=20;41=1.2;72=2;73=99;74=3;11=@(5,6,7);210=@(0,1,0)}
Check ($v.VerticalAlignment -eq 3 -and $v.HorizontalAlignment -eq 2 -and $v.Rotation -eq .7) 'ATTRIB uses DXF74 not field-length DXF73'
$v=Map-Fields 'MTEXT' @{50=999;11=@(0,1,0);40=100;41=500;71=5;210=@(0,0,1)}
Check (!$v.ContainsKey('Rotation') -and ($v.Direction_WCS_RAW -join ',') -eq '0,1,0') 'MTEXT direction retained; column-height DXF50 not guessed angle'
Check ($v.ReferenceWidth -eq 500 -and $v.AttachmentPoint -eq 5 -and $v.TextHeight -eq 100) 'MTEXT width attachment height'
$v=Map-Fields 'TEXT' @{}
Check ($null -eq $v.Rotation -and $null -eq $v.Normal) 'missing optional raw fields not invented'
$status=Read-Function 'mep2:bbox-status'
foreach($case in @(@($true,$true,'read'),@($false,$false,'unavailable'),@($true,$false,'invalid_result'))){
 Check ((Eval-Form $status[3] @{getterSucceeded=$case[0];validPoints=$case[1]}) -ceq $case[2]) 'bbox independent status decision'
}
function Function-Source($name){
 $start=$code.IndexOf('(defun '+$name+' ');$end=$code.IndexOf('(defun ',$start+7)
 if($end -lt 0){$end=$code.Length};$code.Substring($start,$end-$start)
}
$bbox=Function-Source 'mep2:bbox'
Check ($bbox.Contains("'mep2:bbox-body") -and $bbox.Contains('vl-catch-all-apply') -and !$bbox.Contains('setq errors')) 'bbox exception cannot increment entity errors'
Check ($bbox.Contains('bboxError_RAW') -and $bbox.Contains('vlax-release-object')) 'bbox error provenance and COM release'
$enrichment=Function-Source 'mep2:text-layout'
Check ($enrichment.Contains("'mep2:layout-body") -and !$enrichment.Contains('setq errors')) 'metadata failure isolated'
Check ($code.Contains('(if full (mep2:text-layout e d nil ""))') -and $code.Contains('(if full (mep2:text-layout sub sd (cdr (assoc 5 d)) "AttributeLayout."))')) 'new metadata full mode only and explicit attribute parent'
foreach($key in @('Text_RAW','Insertion_WCS','Insertion','Alignment','AttributeTag','AttributeText_RAW','AttributeLayer','Attribute_DXF','ConstantAttributeDefinition_BLOCK_LOCAL','EffectiveName_RAW','DynamicPropertyCount')){
 Check ($code.Contains('"'+$key+'"')) "legacy field $key retained"
}
foreach($key in @('positionFrame','InsertionRawFrame','bboxFrame','bboxMin','bboxMax','bboxStatus','TextLayout_DXF','VisibilityEvidence','AttributeFlags_DXF70','rawMText','2.3-text-layout-metadata')){
 Check ($code.Contains('"'+$key+'"')) "new field $key"
}
Check ($code -notmatch 'vla-put-|vla-Explode|vla-TransformBy|entmod|entmake') 'read-only getters'
Write-Host "PASS: $n text layout checks (actual Lisp field maps/status decisions; COM calls await AutoCAD acceptance)"
