Set-StrictMode -Version 2

# These adapters read frozen reports only. Selection belongs to the caller.
function Get-ReportValue($body,[string]$key) {
 $m=[regex]::Match($body,'(?m)^'+[regex]::Escape($key)+'=(.*)\r?$')
 if($m.Success){return $m.Groups[1].Value.TrimEnd("`r")};return $null
}
function Unquote($s) {if($null -eq $s){return $null};$s.Trim('"')}
function Numbers($s) {
 @([regex]::Matches([string]$s,'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?')|ForEach-Object {[double]::Parse($_.Value,[cultureinfo]::InvariantCulture)})
}
function Read-DiagramSnapshot {
 param([string]$Path)
 $text=Get-Content -LiteralPath $Path -Raw -Encoding UTF8
 if($text -notmatch '(?m)^END_OF_REPORT:' -or $text -notmatch '(?m)^ReadErrorCount=0\s*$' -or $text -match 'TRANSFORM_ERROR|DETAIL_ERROR|ENTITY_UNREADABLE'){throw 'Incomplete/error diagram snapshot'}
 $source=[pscustomobject]@{path=(Resolve-Path $Path).Path;sha256=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash;dwg=(Unquote (Get-ReportValue $text 'DWG'))}
 $entities=@();$statements=@()
 foreach($m in [regex]::Matches($text,'(?ms)^EntityHandle="([^"]+)"\r?\n(.*?)(?=^EntityHandle=|^LayerEntityCount=|\z)')){
  $b=$m.Groups[2].Value;$h=$m.Groups[1].Value;$type=Unquote (Get-ReportValue $b 'DXF_Type')
  if($type -notin @('TEXT','MTEXT','INSERT')){continue}
  $e=[pscustomobject]@{handle=$h;type=$type;layer=(Unquote (Get-ReportValue $b 'Layer'));insertion=@(Numbers (Get-ReportValue $b 'Insertion_WCS'));alignment=@(Numbers (Get-ReportValue $b 'Alignment_WCS'));blockName=(Unquote (Get-ReportValue $b 'BlockName'));effectiveName_RAW=(Unquote (Get-ReportValue $b 'EffectiveName_RAW'));sourceSnapshot=$source;rawRecord=$m.Value;dynamicMetadata=$null}
  if($type -eq 'INSERT'){
   $properties=@(foreach($pm in [regex]::Matches($b,'(?ms)^DynamicProperty_BEGIN=.*?^DynamicProperty_END')){
    $p=$pm.Value;$fields=[ordered]@{}
    foreach($line in ($p -split '\r?\n')){if($line -match '^([^=]+)=(.*)$'){$fields[$matches[1]]=$matches[2]}}
    [pscustomobject]@{propertyName_RAW=(Unquote (Get-ReportValue $p 'PROPERTYNAME'));value_RAW=(Get-ReportValue $p 'VALUE');allowedValues_RAW=(Get-ReportValue $p 'ALLOWEDVALUES');readStatus=@{name=(Unquote (Get-ReportValue $p 'PROPERTYNAME_Status'));value=(Unquote (Get-ReportValue $p 'VALUE_Status'));allowedValues=(Unquote (Get-ReportValue $p 'ALLOWEDVALUES_Status'))};rawFields=$fields}
   })
   $e.dynamicMetadata=[pscustomobject]@{evidenceType='DynamicBlockMetadataEvidence';outerInsertHandle=$h;sourceSnapshot=$source;blockName=$e.blockName;effectiveName_RAW=$e.effectiveName_RAW;isDynamicBlock=(Get-ReportValue $b 'IsDynamicBlock');properties=$properties;readStatus=(Unquote (Get-ReportValue $b 'DynamicMetadataStatus'));semanticInterpretation='not_assigned'}
   foreach($am in [regex]::Matches($b,'(?ms)^AttributeTag="(.*?)"\r?\nAttributeText_RAW="(.*?)"\r?\nAttributeLayer="(.*?)"\r?\nAttribute_DXF=(.*?)\r?$')){
    $d=$am.Groups[4].Value;$ah=[regex]::Match($d,'\(5 \. "([^"]+)"\)').Groups[1].Value
    $statements+=,[pscustomobject]@{handle=$ah;parentHandle=$h;type='ATTRIB';rawText=$am.Groups[2].Value;layer=$am.Groups[3].Value;insertion=@(Numbers ([regex]::Match($d,'\(10 ([^)]+)\)').Groups[1].Value));alignment=@(Numbers ([regex]::Match($d,'\(11 ([^)]+)\)').Groups[1].Value));sourceSnapshot=$source;rawRecord=$am.Value;coordinateStatus='raw_attribute_OCS_not_general_WCS';referencePointType='parent_INSERT_WCS';referencePoint=$e.insertion}
   }
  } else {
   $statements+=,[pscustomobject]@{handle=$h;parentHandle=$null;type=$type;rawText=(Unquote (Get-ReportValue $b 'Text_RAW'));layer=$e.layer;insertion=$e.insertion;alignment=$e.alignment;sourceSnapshot=$source;rawRecord=$m.Value;coordinateStatus='WCS';referencePointType='Insertion_WCS';referencePoint=$e.insertion}
  }
  $entities+=,$e
 }
 [pscustomobject]@{sourceSnapshot=$source;entities=$entities;statements=$statements}
}

function Get-StatementKind([string]$text){
 if($text -match '^\d+(?:\.\d+)?\s*[kK][wW]$'){return 'power-like'}
 if($text -match '^L[123].*N.*PE$'){return 'phase-neutral-PE-like'}
 if($text -match '^[A-Za-z]+\d+(?:[,，][A-Za-z]+\d+)*$'){return 'identifier-like'}
 return 'unclassified'
}
function New-DiagramLocalView {
 param($Snapshot,[object[]]$RowInserts,[object[]]$Statements,[string]$LocalViewId,[double]$RowBand=600,[double]$Tolerance=0.00001)
 if($RowBand -le 0 -or $Tolerance -le 0 -or [double]::IsNaN($RowBand) -or [double]::IsInfinity($RowBand) -or [double]::IsNaN($Tolerance) -or [double]::IsInfinity($Tolerance)){throw 'Positive finite row band/tolerance required'}
 $rows=@();$alignments=@();$claims=@();$metadata=@()
 $ordered=@($RowInserts|Sort-Object @{Expression={$_.insertion[1]};Descending=$true},handle)
 foreach($e in $ordered){
  if($e.sourceSnapshot.sha256 -ne $Snapshot.sha256 -or $e.type -ne 'INSERT' -or $e.insertion.Count -ne 3){throw 'Row basis must be an INSERT with WCS point from this snapshot'}
  $id='R'+($rows.Count+1)
  $rows+=,[pscustomobject]@{rowId=$id;localViewId=$LocalViewId;sourceSnapshot=$Snapshot;rowBasis=@{kind='caller_selected_INSERT_layout_anchor';handle=$e.handle;rawRecord=$e.rawRecord};rowBaselineY=$e.insertion[1];baselinePoint=$e.insertion;memberRepresentations=@($e.handle);statementCandidateIds=@();rowSpacingEvidence=@();status='candidate';conflicts=@();humanConfirmations=@()}
  $metadata+=,$e.dynamicMetadata
 }
 for($i=0;$i -lt $rows.Count;$i++){
  for($j=$i+1;$j -lt $rows.Count;$j++){
   $gap=[math]::Abs($rows[$i].rowBaselineY-$rows[$j].rowBaselineY)
   if($j -eq $i+1){$rows[$i].rowSpacingEvidence+=,@{otherRow=$rows[$j].rowId;drawingUnitSpacing=$gap;basis='INSERT_WCS_Y_difference';tolerance=$Tolerance}}
   if($gap -le $Tolerance){foreach($r in @($rows[$i],$rows[$j])){$r.status='ambiguous';$r.conflicts+=,'indistinguishable_row_baselines'}}
  }
 }
 foreach($s in $Statements){
  if($s.sourceSnapshot.sha256 -ne $Snapshot.sha256){throw 'Statement snapshot mismatch'}
  $cid='S'+($claims.Count+1);$hits=@()
  if($s.referencePoint.Count -eq 3){foreach($r in $rows){
   $dx=$s.referencePoint[0]-$r.baselinePoint[0];$dy=$s.referencePoint[1]-$r.rowBaselineY
   if([math]::Abs($dy) -le $RowBand){
    $hits+=,$r.rowId;$r.statementCandidateIds+=,$cid;$r.memberRepresentations+=,$s.handle
    $alignments+=,[pscustomobject]@{id='A'+($alignments.Count+1);evidenceType='AlignmentEvidence';sourceSnapshot=$Snapshot;sourceA=$r.rowBasis.handle;sourceB=$s.handle;referencePointType=@('INSERT_WCS',$s.referencePointType);deltaX=$dx;deltaY=$dy;rowId=$r.rowId;rowBaselineRelation=if([math]::Abs($dy) -le $Tolerance){'on_baseline'}else{'within_explicit_layout_band'};tolerance=$Tolerance;layoutBand=$RowBand;residual=[math]::Abs($dy);meaning='layout_only_not_connection'}
   }
  }}
  $claims+=,[pscustomobject]@{id=$cid;evidenceType='StatementCandidate';handle=$s.handle;parentHandle=$s.parentHandle;rawText=$s.rawText;layer=$s.layer;insertion=$s.insertion;alignment=$s.alignment;coordinateStatus=$s.coordinateStatus;candidateKind=(Get-StatementKind $s.rawText);sourceSnapshot=$s.sourceSnapshot;rawRecord=$s.rawRecord;candidateRowIds=$hits;bindingStatus=if($hits.Count -gt 1){'ambiguous'}else{'unbound'};rowAssociationStatus=if($hits.Count -eq 1){'candidate'}elseif($hits.Count -gt 1){'ambiguous'}else{'insufficient'}}
 }
 [pscustomobject]@{schemaVersion='1.0';modelType='SystemDiagramLocalView';localViewId=$LocalViewId;sourceSnapshot=$Snapshot;scope='explicit_local_fixture_not_discovery';coordinateContext=@{units='drawing_units';engineeringScale='unknown';cadZMeaning='raw_coordinate_not_elevation'};rows=$rows;statements=$claims;alignmentEvidence=$alignments;dynamicBlockMetadataEvidence=$metadata;deviceCandidates=@();representationEquivalences=@();humanConfirmations=@();snapshotCorrespondences=@();conflicts=@();limitations=@('row membership is layout only','no evaluated dynamic visibility','no electrical connections or quantities')}
}

# Probe records are retained verbatim as DXF fields; never merge by text/Handle.
function Read-DiagramProbe {
 param([string]$Path)
 Import-Module (Join-Path $PSScriptRoot '../block-probe/BlockProbe.psm1')
 $p=Read-BlockProbe $Path
 # Get-Content strings can carry PSDrive/PSProvider metadata. Copy only CAD
 # values, so JSON cannot traverse PowerShell's provider/session object graph.
 foreach($b in $p.Blocks){
  $b.Definition=@(foreach($f in $b.Definition){@{Code=[int]$f.Code;Value=('{0}' -f $f.Value)}})
  foreach($e in $b.Entities){$e.Fields=@(foreach($f in $e.Fields){@{Code=[int]$f.Code;Value=('{0}' -f $f.Value)}})}
 }
 $p
}
function Get-ProbeField($e,[int]$code,$default=$null){$v=@($e.Fields|Where-Object Code -eq $code);if($v.Count){return $v[0].Value};return $default}
function Get-Unique($items,[string]$field,[string]$value){$v=@($items|Where-Object {$_.$field -ceq $value});if($v.Count -ne 1){throw "Expected exactly one $field=$value"};$v[0]}
function New-DeviceCandidate {
 param($OuterInsert,$OuterProbe,$ChildProbe,$Link,$HumanConfirmation=$null,[string]$LocalViewId,[string]$CandidateRole='unclassified')
 $b=Get-Unique $OuterProbe.Blocks Name $Link.outerBlock
 if($OuterInsert.blockName -cne $b.Name){throw 'Outer definition correspondence mismatch'}
 $ref=Get-Unique $b.Entities Handle $Link.symbolInsertHandle
 if((Unquote (Get-ProbeField $ref 2)) -cne $Link.symbolBlock){throw 'Child reference mismatch'}
 $child=Get-Unique $ChildProbe.Blocks Name $Link.symbolBlock
 $geometry=@($child.Entities|Where-Object {(Unquote (Get-ProbeField $_ 0)) -in @('LINE','LWPOLYLINE')})
 $attributes=@($child.Entities|Where-Object {(Unquote (Get-ProbeField $_ 0)) -in @('ATTDEF','ATTRIB')})
 $attached=@();$fields=$null
 foreach($field in $ref.Fields){
  if($field.Code -eq -999 -and $field.Value -eq 'Subentity_BEGIN'){$fields=@()}
  elseif($field.Code -eq -999 -and $field.Value -eq 'Subentity_END'){
   $record=[pscustomobject]@{Fields=$fields}
   if((Unquote (Get-ProbeField $record 0)) -eq 'ATTRIB'){
    $attached+=,[pscustomobject]@{handle=(Unquote (Get-ProbeField $record 5));sourceSnapshot=$OuterProbe.Snapshot;parentDefinition=$b.Name;parentInsert=$ref.Handle;fields=$fields}
   }
   $fields=$null
  }elseif($null -ne $fields){$fields+=,$field}
 }
 $hc=@();if($null -ne $HumanConfirmation){
  if($HumanConfirmation.outerHandle -ne $OuterInsert.handle -or $HumanConfirmation.sourceSnapshot.sha256 -ne $OuterInsert.sourceSnapshot.sha256 -or $HumanConfirmation.localViewId -ne $LocalViewId){throw 'Human confirmation scope mismatch'}
  $hc+=,$HumanConfirmation
 }
 [pscustomobject]@{id='D-'+$OuterInsert.handle;modelType='DeviceCandidate';localViewId=$LocalViewId;sourceSnapshot=$OuterInsert.sourceSnapshot;sourceInstancePath=@($OuterInsert.sourceSnapshot.sha256,$OuterInsert.handle,$OuterProbe.Snapshot,$b.Name,$ref.Handle,$ChildProbe.Snapshot,$child.Name);outerInsertHandle=$OuterInsert.handle;referencedSubblock=$child.Name;effectiveName=$OuterInsert.effectiveName_RAW;blockName=$OuterInsert.blockName;dynamicPropertyRaw=$OuterInsert.dynamicMetadata.properties;geometryMembers=$geometry;attributeEvidence=$attributes;instanceAttributeEvidence=$attached;humanConfirmations=$hc;candidateRole=$CandidateRole;semanticStatus='candidate';roleBasis='caller_supplied_local_symbol_hypothesis_with_raw_attribute_evidence';definitionCorrespondence=$Link;sourceTransforms=@{outerRaw=$OuterInsert.rawRecord;childInsertFields=$ref.Fields;childBase=$child.Definition};visibilityStatus='DXF_only_not_evaluated';conflicts=@()}
}

function Get-StraightProbeLine($e){
 if((Unquote (Get-ProbeField $e 0)) -ne 'LWPOLYLINE' -or (Get-ProbeField $e 70 '0') -ne '0'){throw 'Only open straight two-vertex LWPOLYLINE supported'}
 if(@($e.Fields|Where-Object {$_.Code -eq 42 -and [double]$_.Value -ne 0}).Count){throw 'Bulged line unsupported'}
 $p=@(foreach($v in @($e.Fields|Where-Object Code -eq 10)){,@(Numbers $v.Value)})
 if($p.Count -ne 2 -or [double](Get-ProbeField $e 38 '0') -ne 0){throw 'Expected two vertices at zero elevation'}
 $normal=@(Numbers (Get-ProbeField $e 210 '(0 0 1)'))
 if($normal.Count -ne 3 -or $normal[0] -ne 0 -or $normal[1] -ne 0 -or $normal[2] -ne 1){throw 'Non-XY normal unsupported'}
 if($p[0].Count -ne 2 -or $p[1].Count -ne 2 -or ($p[0][0] -eq $p[1][0] -and $p[0][1] -eq $p[1][1])){throw 'Invalid/degenerate line'}
 $width=[double](Get-ProbeField $e 43 '0')
 if(@($e.Fields|Where-Object {$_.Code -in @(40,41) -and [double]$_.Value -ne $width -and [double]$_.Value -ne 0}).Count){throw 'Variable widths unsupported'}
 return ,$p
}
function New-RepresentationEquivalence {
 param($OuterProbe,$ChildProbe,$Selection,[double]$Tolerance=0.00001)
 if($Tolerance -le 0 -or [double]::IsNaN($Tolerance) -or [double]::IsInfinity($Tolerance)){throw 'Positive finite tolerance required'}
 $b=Get-Unique $OuterProbe.Blocks Name $Selection.outerBlock;$c=Get-Unique $ChildProbe.Blocks Name $Selection.childBlock
 $a=Get-Unique $b.Entities Handle $Selection.directHandle;$i=Get-Unique $b.Entities Handle $Selection.childInsertHandle;$line=Get-Unique $c.Entities Handle $Selection.childLineHandle
 if((Unquote (Get-ProbeField $i 0)) -ne 'INSERT' -or (Unquote (Get-ProbeField $i 2)) -cne $c.Name){throw 'Invalid equivalence reference'}
 $ap=Get-StraightProbeLine $a;$cp=Get-StraightProbeLine $line
 $base=@(Numbers (@($c.Definition|Where-Object Code -eq 10)[0].Value));$pos=@(Numbers (Get-ProbeField $i 10));$sx=[double](Get-ProbeField $i 41 '1');$sy=[double](Get-ProbeField $i 42 '1');$rot=[double](Get-ProbeField $i 50 '0')
 $normal=@(Numbers (Get-ProbeField $i 210 '(0 0 1)'))
 if($normal.Count -ne 3 -or $normal[0] -ne 0 -or $normal[1] -ne 0 -or $normal[2] -ne 1 -or $pos.Count -ne 3 -or $base.Count -ne 3 -or $pos[2] -ne 0 -or $base[2] -ne 0 -or $sx -eq 0 -or $sy -eq 0){throw 'Unsupported INSERT transform'}
 $bp=@(foreach($p in $cp){$x=($p[0]-$base[0])*$sx;$y=($p[1]-$base[1])*$sy;,@(($pos[0]+$x*[math]::Cos($rot)-$y*[math]::Sin($rot)),($pos[1]+$x*[math]::Sin($rot)+$y*[math]::Cos($rot)))})
 function Dist($x,$y){[math]::Sqrt([math]::Pow($x[0]-$y[0],2)+[math]::Pow($x[1]-$y[1],2))}
 $res=[math]::Min([math]::Max((Dist $ap[0] $bp[0]),(Dist $ap[1] $bp[1])),[math]::Max((Dist $ap[0] $bp[1]),(Dist $ap[1] $bp[0])))
 $styles=@(foreach($code in @(8,6,62,420,370,43)){[pscustomobject]@{dxfCode=$code;a=(Get-ProbeField $a $code);b=(Get-ProbeField $line $code);equal=((Get-ProbeField $a $code) -ceq (Get-ProbeField $line $code))}})
 $geometryEqual=$res -le $Tolerance;$styleEqual=@($styles|Where-Object {-not $_.equal}).Count -eq 0 -and [math]::Abs($sx) -eq 1 -and [math]::Abs($sy) -eq 1
 $ra=@{snapshot=$OuterProbe.Snapshot;block=$b.Name;handle=$a.Handle;rawFields=$a.Fields}
 $rb=@{snapshot=$ChildProbe.Snapshot;block=$c.Name;handle=$line.Handle;viaInsert=$i.Handle;rawFields=$line.Fields}
 [pscustomobject]@{modelType='RepresentationEquivalence';representationA=$ra;representationB=$rb;geometryComparison=@{equal=$geometryEqual;residual=$res;tolerance=$Tolerance;frame='outer_block_definition';pointsA=$ap;transformedPointsB=$bp};styleComparison=@{equal=$styleEqual;fields=$styles;scope='explicit_fields_only_no_general_ByLayer_resolution'};visibilityState=@{aDXF60=(Get-ProbeField $a 60 '0');bInsertDXF60=(Get-ProbeField $i 60 '0');bLineDXF60=(Get-ProbeField $line 60 '0');evaluatedVisibility='unknown'};transform=@{insertion=$pos;scale=@($sx,$sy);rotationRadians=$rot;definitionBase=$base;rawFields=$i.Fields};equivalenceScope=@{outerSnapshot=$OuterProbe.Snapshot;childSnapshot=$ChildProbe.Snapshot;outerBlock=$b.Name;scope='definition_pair_only_not_engineering_object';instanceApplication='requires_snapshot_correspondence_and_instance_path'};status=if($geometryEqual -and $styleEqual){'supported'}else{'ambiguous'};representationGroups=@($(if($geometryEqual -and $styleEqual){[pscustomobject]@{id='EQ1';members=@($ra,$rb)}}else{[pscustomobject]@{id='EQ1';members=@($ra)};[pscustomobject]@{id='EQ2';members=@($rb)}}));evidence=@('endpoint_comparison_after_explicit_transform','raw_style_comparison','DXF60_difference_retained');quantityStatus='not_computed'}
}
Export-ModuleMember -Function Read-DiagramSnapshot,Read-DiagramProbe,New-DiagramLocalView,New-DeviceCandidate,New-RepresentationEquivalence
