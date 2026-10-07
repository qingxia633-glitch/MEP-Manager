# Fixture-only source resolver. Handles live in the manifest, never in admission policy.
function Read-RoleAdmissionFixture {
 $root=Resolve-Path (Join-Path $PSScriptRoot '../..')
 $m=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'role-admission-sample.json') -Raw -Encoding UTF8|ConvertFrom-Json
 $requirementFile=Join-Path $root $m.requirementSource.path
 if((Get-FileHash -LiteralPath $requirementFile).Hash-cne $m.requirementSource.sha256){throw 'Golden requirement source changed'}
 $existing=Get-Content -LiteralPath $requirementFile -Raw -Encoding UTF8|ConvertFrom-Json
 foreach($req in $m.requirements){
  $matches=@($existing.requirements|Where-Object requirementRef -CEQ $req.requirementId)
  if($matches.Count-ne 1){throw 'Golden requirement absent'}
  $req|Add-Member status $matches[0].statusUnchanged
  $req|Add-Member provenance $m.requirementSource
 }
 $sources=@{};$raw=@{};$refs=[ordered]@{}
 function Field($s,$k){[regex]::Match($s,'(?m)^'+[regex]::Escape($k)+'=(.*?)\r?$').Groups[1].Value.Trim('"')}
 function Points($s,$k){,@([regex]::Matches($s,'(?m)^'+[regex]::Escape($k)+'=\(([^)]+)\)')|ForEach-Object {,@($_.Groups[1].Value.Split(' ')|ForEach-Object {[double]::Parse($_,[cultureinfo]::InvariantCulture)})})}
 function Attribute($s,$tag){$a=[regex]::Match($s,'(?ms)^AttributeTag="'+[regex]::Escape($tag)+'".*?(?=^AttributeTag=|\z)').Value;Field $a AttributeText_RAW}
 foreach($p in $m.sources.PSObject.Properties){
  $file=Join-Path $root $p.Value.path
  if((Get-FileHash -LiteralPath $file).Hash -cne $p.Value.sha256){throw "Fixture source changed: $($p.Name)"}
  $sources[$p.Name]=[IO.File]::ReadAllText($file)
  if($sources[$p.Name]-notmatch '(?m)^END_OF_REPORT'){throw 'Incomplete source'}
 }
 foreach($p in $m.references.PSObject.Properties){
  $source=$m.sources.($p.Value.source);$s=$sources[$p.Value.source]
  $record=[regex]::Match($s,'(?ms)^EntityHandle="'+[regex]::Escape($p.Value.handle)+'".*?(?=^EntityHandle=|^Entity_END|\z)').Value
  if(!$record){throw "Missing source reference $($p.Name)"};$raw[$p.Name]=$record
  $refs[$p.Name]=[pscustomobject]@{sourceSnapshot=$source.sha256;sourcePath=$source.path;sourceDocument=(Field $s DWG);handle=$p.Value.handle;definitionName=(Field $s Block_BEGIN);referencedDefinition=(Field $record BlockName);resolved=$true}
 }
 foreach($pair in @(@('instance','systemDefinition'),@('legendSymbol','legendDefinition'))){
  if((Field $raw[$pair[0]] BlockName)-cne (Field $sources[$pair[1]] Block_BEGIN)){throw 'Definition reference mismatch'}
  if((Field $raw[$pair[0]] Normal_DXF210)-ne '(0.000000 0.000000 1.000000)'){throw 'Fixture transform assumption changed'}
 }
 # Validate the reviewed comparison from source geometry; preserve duplicate raw members.
 $compat=$true
 foreach($pair in @(@('legendBottom','bottom'),@('legendLeft','left'),@('legendTop','top'),@('legendRight','right'))){
  $a=(Points $raw[$pair[0]] 'DXF:10')[0];$b=(Points $raw[$pair[1]] 'DXF:10')[0]
  if([math]::Abs($a[0]-$b[0])-gt 1e-8 -or [math]::Abs($a[1]+.5-$b[1])-gt 1e-8){$compat=$false}
 }
 $lp=Points $raw.legendBoundary 'DXF:10';$sp=Points $raw.boundary 'DXF:10'
 foreach($a in $lp){if(!@($sp|Where-Object {[math]::Abs($_[0]-$a[0])-lt 1e-8 -and [math]::Abs($_[1]-($a[1]+.5))-lt 1e-8}).Count){$compat=$false}}
 $ins=(Points $raw.instance Insertion_WCS)[0]
 $sc=@(41..43|ForEach-Object {[double]::Parse([regex]::Match($raw.instance,'BlockTransform_or_Array_DXF=\('+$_+' \. ([^)]+)').Groups[1].Value,[cultureinfo]::InvariantCulture)})
 if($sc[0]-ne $sc[1] -or $sc[0]-le 0 -or $raw.instance-notmatch 'BlockTransform_or_Array_DXF=\(50 \. 0.000000\)'){throw 'Unsupported fixture transform'}
 $bounds=@((-.5*$sc[0]+$ins[0]),$ins[1],(.5*$sc[0]+$ins[0]),($ins[1]+$sc[0]));$tol=1e-5
 $boundaries=@();$specs=@(@('leftLine','left','fire_broadcast'),@('upperLine','top','fire_alarm'),@('lowerLine','bottom','fire_alarm'))
 foreach($spec in $specs){
  $pts=Points $raw[$spec[0]] Vertex_WCS;$a=$pts[0];$b=$pts[1];$hit=$false
  switch($spec[1]){
   left {$hit=$a[0]-gt $bounds[0] -and $a[0]-lt $bounds[2] -and $b[0]-lt $bounds[0] -and [math]::Abs($a[1]-$b[1])-lt $tol -and $a[1]-gt $bounds[1] -and $a[1]-lt $bounds[3]}
   top {$hit=[math]::Abs($a[1]-$bounds[3])-lt $tol -and $a[0]-gt $bounds[0] -and $a[0]-lt $bounds[2]}
   bottom {$hit=$a[1]-gt $bounds[1] -and $a[1]-lt $bounds[3] -and $b[1]-lt $bounds[1] -and [math]::Abs($a[0]-$b[0])-lt $tol -and $a[0]-gt $bounds[0] -and $a[0]-lt $bounds[2]}
  }
  $boundaries+=,[pscustomobject]@{fromRef=$spec[0];toRef='instance';side=$spec[1];systemIdentity=$spec[2];status=if($hit){'supported'}else{'unresolved'};sourceRefs=@($spec[0],'instance','boundary');evidenceMeaning='boundary geometry only; system context reviewed independently'}
 }
 [pscustomobject]@{
  evidenceId='reviewed-role-evidence';scopeId=$m.scopeId;subjectRef='instance';references=[pscustomobject]$refs
  legend=[pscustomobject]@{status=$m.reviewedLegendLayout.status;role=(Field $raw.legendName Text_RAW);code=(Attribute $raw.legendSymbol '$TEXT$');sourceRefs=$m.reviewedLegendLayout.sourceRefs}
  instanceCode=(Attribute $raw.instance '$TEXT$');instanceCodeRef='instance'
  compatibility=[pscustomobject]@{status=if($compat){'supported'}else{'unresolved'};sourceRefs=@('legendBoundary','boundary','legendBottom','bottom','legendLeft','left','legendTop','top','legendRight','right');sameDefinition=$false}
  context=$m.reviewedContext;boundaries=$boundaries;systemScopes=@('fire_alarm','fire_broadcast')
  semanticDeclarations=@([pscustomobject]@{sourceRef='legendHidden';meaning=(Field $raw.legendHidden 'DXF:1')},[pscustomobject]@{sourceRef='hidden';meaning=(Field $raw.hidden 'DXF:1')},[pscustomobject]@{sourceRef='legendName';meaning=(Field $raw.legendName Text_RAW)})
  reviewItems=@([pscustomobject]@{reviewId='dual-semantics';type='unresolved_dual_semantics';status='open';sourceRefs=@('legendHidden','hidden','legendName')})
  missingEvidence=@('port_mapping','direction','internal_conduction','control_logic','speaker_side_confirmation','physical_connection')
  searchRegionRefs=@('instance','lowerLine','speaker');requirements=$m.requirements
 }
}
