Set-StrictMode -Version Latest

Import-Module (Join-Path $PSScriptRoot 'SpatialRelations.psm1')

function Read-AnnotationRegion {
 [CmdletBinding()]
 param([Parameter(Mandatory)][string]$Report,[Parameter(Mandatory)]$Geometry,[double]$Margin=6000)
 if($Margin -le 0){throw 'Positive explicit local margin required'}
 $text=Get-Content -LiteralPath $Report -Raw -Encoding UTF8
 if($text -notmatch '(?m)^END_OF_REPORT:'){throw 'Incomplete report'}
 $hash=(Get-FileHash -LiteralPath $Report -Algorithm SHA256).Hash
 $points=@($Geometry.geometryEdges | ForEach-Object {foreach($p in $_.points){,$p}})
 $min=@(0..2 | ForEach-Object {$k=$_;($points | ForEach-Object {$_[$k]} | Measure-Object -Minimum).Minimum-$Margin})
 $max=@(0..2 | ForEach-Object {$k=$_;($points | ForEach-Object {$_[$k]} | Measure-Object -Maximum).Maximum+$Margin})
 foreach($m in [regex]::Matches($text,'(?ms)^EntityHandle="([^"]+)"\r?\n(.*?)(?=^EntityHandle=|^LayerEntityCount=|\z)')){
  $body=$m.Groups[2].Value;$type=[regex]::Match($body,'DXF_Type="([^"]+)"').Groups[1].Value
  if($type -notin @('TEXT','LINE','LWPOLYLINE','CIRCLE')){continue}
  $ps=@(foreach($p in [regex]::Matches($body,'(?m)^(?:Insertion|Alignment|Vertex|Start|End)_WCS=\(([^)]+)\)')){,@($p.Groups[1].Value.Split(' ')|ForEach-Object {[double]::Parse($_,[cultureinfo]::InvariantCulture)})})
  $radius=$null
  if($type -eq 'CIRCLE'){
   $pm=[regex]::Match($body,'Raw_DXF=\(10 ([^)]+)\)');$rm=[regex]::Match($body,'Raw_DXF=\(40 \. ([^)]+)\)')
   if(-not $pm.Success -or -not $rm.Success){continue}
   $ps=@(,@($pm.Groups[1].Value.Split(' ')|ForEach-Object {[double]::Parse($_,[cultureinfo]::InvariantCulture)}))
   $radius=[double]::Parse($rm.Groups[1].Value,[cultureinfo]::InvariantCulture)
  }
  if($ps.Count -eq 0){continue}
  $inside=$true;for($k=0;$k -lt 3;$k++){
   $extent=$ps | ForEach-Object {$_[$k]} | Measure-Object -Minimum -Maximum
   if($extent.Maximum -lt $min[$k] -or $extent.Minimum -gt $max[$k]){$inside=$false}
  }
  if(-not $inside){continue}
  if($body -match 'DETAIL_ERROR|TRANSFORM_ERROR|ENTITY_UNREADABLE'){throw "Incomplete local annotation geometry: $($m.Groups[1].Value)"}
  $rawText=[regex]::Match($body,'(?m)^Text_RAW="(.*)"\r?$').Groups[1].Value
  $insert=$null;$align=$null
  if($type -eq 'TEXT'){
   $insert=$ps[0]
   $am=[regex]::Match($body,'(?m)^Alignment_WCS=\(([^)]+)\)')
   if($am.Success){$align=@($am.Groups[1].Value.Split(' ')|ForEach-Object {[double]::Parse($_,[cultureinfo]::InvariantCulture)})}
  }
  $bulges=@(foreach($bm in [regex]::Matches($body,'Width_or_bulge_DXF=\(42 \. ([^)]+)\)')){[double]::Parse($bm.Groups[1].Value,[cultureinfo]::InvariantCulture)})
  [pscustomobject]@{handle=$m.Groups[1].Value;type=$type;layer=[regex]::Match($body,'(?m)^Layer="([^"]+)"').Groups[1].Value;
   text=$rawText;insertion=$insert;alignment=$align;points=$ps;radius=$radius;bulges=$bulges;
   closed=($body -match '(?m)^Closed=T\s*$');rawRecord=$m.Value;reportSHA256=$hash;
   reportLine=1+[regex]::Matches($text.Substring(0,$m.Index),'\n').Count;colorStatus='not_exported'}
 }
}

function Convert-TrayDeclaration {
 param([Parameter(Mandatory)][AllowEmptyString()][string]$Text)
 $normalized=$Text.Normalize([Text.NormalizationForm]::FormKC)
 $isTray=$normalized -match '桥架|槽盒|线槽'
 $type=$null;$width=$null;$height=$null;$installation=$null;$basis=@()
 if($isTray){
  $tm=[regex]::Match($normalized,'普通强电|消防强电|住宅强电|商业强电|高压强电|安防|弱电|消防|强电')
  if($tm.Success){$type=$tm.Value;$basis+='type phrase: '+$tm.Value}
  else {
   $generic=[regex]::Match($normalized,'(?<name>[\u4e00-\u9fff]{1,12})(?:桥架|槽盒|线槽)')
   if($generic.Success){$type=$generic.Groups['name'].Value;$basis+='unmapped literal type phrase: '+$type}
  }
  $size=[regex]::Match($normalized,'(?<w>\d+(?:\.\d+)?)\s*[xX×*＊]\s*(?<h>\d+(?:\.\d+)?)(?<unit>\s*mm)?')
  if($size.Success){$width=[double]::Parse($size.Groups['w'].Value,[cultureinfo]::InvariantCulture);$height=[double]::Parse($size.Groups['h'].Value,[cultureinfo]::InvariantCulture);$basis+='width-height expression: '+$size.Value}
 }
 $im=[regex]::Match($normalized,'(?<ref>梁下|板下|顶板下)\s*(?<offset>\d+(?:\.\d+)?)\s*(?:mm)?\s*(?<method>吊装|安装|敷设)')
 if($im.Success){$installation=[pscustomobject]@{reference=$im.Groups['ref'].Value;offset=[double]::Parse($im.Groups['offset'].Value,[cultureinfo]::InvariantCulture);method=$im.Groups['method'].Value;raw=$im.Value};$basis+='installation phrase: '+$im.Value}
 [pscustomobject]@{raw=$Text;normalized=$normalized;isTray=$isTray;type=$type;width=$width;height=$height;installation=$installation;parseBasis=$basis;lengthUnit=if($normalized -match '(?i)mm'){'mm'}else{'unspecified'}}
}

function Distance($a,$b){[math]::Sqrt([math]::Pow($a[0]-$b[0],2)+[math]::Pow($a[1]-$b[1],2)+[math]::Pow($a[2]-$b[2],2))}
function Projection($p,$a,$b){
 $d=@(0..2|ForEach-Object {$b[$_]-$a[$_]});$len=Distance $a $b
 if($len -le 0){return $null}
 $t=0.0;for($i=0;$i -lt 3;$i++){$t+=($p[$i]-$a[$i])*$d[$i]/$len}
 $q=@(0..2|ForEach-Object {$a[$_]+$t*$d[$_]/$len})
 $clamped=[math]::Max(0.0,[math]::Min($len,$t));$nearest=@(0..2|ForEach-Object {$a[$_]+$clamped*$d[$_]/$len})
 [pscustomobject]@{along=$t;offLine=(Distance $p $q);distance=(Distance $p $nearest);length=$len}
}
function Targets($p,$geometry,$tol){
 $hit=@($geometry.geometryEdges | Where-Object {(Projection $p $_.points[0] $_.points[1]).distance -le $tol})
 $ids=@($hit|ForEach-Object {$_.id})
 $relations=@(Get-UnitSpatialRelations -Point $p -Geometry $geometry -Tolerance $tol)
 $supported=@($relations|Where-Object {$_.relation -in @('vertex_hit','boundary_hit','interior_hit')})
 [pscustomobject]@{edgeIds=$ids;unitIds=@($supported|ForEach-Object {$_.unitId}|Sort-Object -Unique);relations=$relations;interfaceIds=@($geometry.interfaces|Where-Object {$_.geometryEdgeId -in $ids}|ForEach-Object {$_.id})}
}

function Type-Compatibility($types){
 if($types.Count -le 1){return 'same_or_single'}
 if(@($types|Where-Object {$_ -ne '电力' -and $_ -notmatch '强电$'}).Count -eq 0 -and @($types|Where-Object {$_ -ne '电力'}).Count -le 1){return 'broad_specific_compatible'}
 if('安防' -in $types -and @($types|Where-Object {$_ -match '强电$'}).Count -gt 0){return 'conflicting'}
 if(@($types|Where-Object {$_ -match '强电$'}).Count -gt 1){return 'conflicting'}
 return 'unresolved_compatibility'
}

function Get-TrayEvidence {
 [CmdletBinding()]
 param([Parameter(Mandatory)]$Geometry,[Parameter(Mandatory)][AllowEmptyCollection()][object[]]$Records,$UnitContext=$null,
  [double]$AnchorTolerance=0.001,[double]$LayoutTolerance=0.01,[double]$MaxTextOffset=600,[double]$MaxMarkerRadius=200,[double]$WidthTolerance=0.01)
 if($AnchorTolerance -le 0 -or $LayoutTolerance -le 0 -or $MaxTextOffset -le 0 -or $MaxMarkerRadius -le 0 -or $WidthTolerance -le 0){throw 'Positive tolerances required'}
 if($null -ne $UnitContext){
  foreach($key in @('mmPerDrawingUnit','source','independent','annotationLengthUnit','evidence')){if($UnitContext.PSObject.Properties.Name -notcontains $key){throw "Unit context missing: $key"}}
  if($UnitContext.mmPerDrawingUnit -le 0 -or [double]::IsNaN($UnitContext.mmPerDrawingUnit) -or [double]::IsInfinity($UnitContext.mmPerDrawingUnit) -or $UnitContext.independent -isnot [bool]){throw 'Invalid unit context'}
 }
 if(@($Records|ForEach-Object {$_.handle}|Select-Object -Unique).Count -ne $Records.Count){throw 'Duplicate annotation Handles'}
 $texts=@(foreach($e in $Records){if($e.type -eq 'TEXT'){
  $p=Convert-TrayDeclaration $e.text
  if($p.isTray -or $null -ne $p.installation){[pscustomobject]@{entity=$e;parsed=$p}}
 }})
 $markers=@($Records | Where-Object {$_.type -eq 'CIRCLE' -and $_.radius -gt 0 -and $_.radius -le $MaxMarkerRadius})
 $leaders=@($Records | Where-Object {$_.type -in @('LINE','LWPOLYLINE') -and -not $_.closed -and $_.points.Count -ge 2 -and @($_.bulges | Where-Object {$_ -ne 0}).Count -eq 0})
 $associations=@()
 foreach($line in $leaders){foreach($end in @(0,1)){
  $anchor=if($end -eq 0){$line.points[0]}else{$line.points[-1]}
  $free=if($end -eq 0){$line.points[-1]}else{$line.points[0]}
  $base=if($end -eq 0){$line.points[-2]}else{$line.points[1]}
  if((Distance $free $base) -le $AnchorTolerance){continue}
  $circles=@($markers | Where-Object {(Distance $anchor $_.points[0]) -le $AnchorTolerance})
  $vx=$base[0]-$free[0];$vy=$base[1]-$free[1];$vz=$base[2]-$free[2]
  $baselineLength=[math]::Sqrt($vx*$vx+$vy*$vy+$vz*$vz)
  $matched=@(foreach($t in $texts){
   if($null -eq $t.entity.alignment -or $null -eq $t.entity.insertion){continue}
   $alignment=$t.entity.alignment
   $along=(($alignment[0]-$free[0])*$vx+($alignment[1]-$free[1])*$vy+($alignment[2]-$free[2])*$vz)/$baselineLength
   if([math]::Abs($along) -gt $LayoutTolerance){continue}
   $ap=Projection $t.entity.alignment $free $base;$ip=Projection $t.entity.insertion $free $base
   if([math]::Abs($ap.along) -le $LayoutTolerance -and $ap.offLine -le $MaxTextOffset -and $ip.offLine -le $MaxTextOffset -and $ip.along -ge (-$LayoutTolerance) -and $ip.along -le ($ip.length+$LayoutTolerance) -and [math]::Abs($t.entity.insertion[2]-$free[2]) -le $AnchorTolerance){
    [pscustomobject]@{text=$t;alignmentResidual=[math]::Abs($ap.along);baselineOffset=$ip.offLine}
   }
  })
  if(@($matched|Where-Object {$_.text.parsed.isTray}).Count -eq 0){continue}
  $landing=if($circles.Count -eq 1){$circles[0].points[0]}else{$anchor}
  $target=Targets $landing $Geometry $AnchorTolerance
  $otherHits=@()
  if($target.unitIds.Count -eq 0){
   $otherHits=@(foreach($candidate in $leaders){
    if($candidate.handle -eq $line.handle){continue}
    for($k=1;$k -lt $candidate.points.Count;$k++){
     $projection=Projection $landing $candidate.points[$k-1] $candidate.points[$k]
     if($null -ne $projection -and $projection.distance -le $AnchorTolerance){$candidate.handle;break}
    }
   })
  }
  $associationStatus=if($target.unitIds.Count -eq 0){'insufficient'}elseif($target.unitIds.Count -gt 1 -or $circles.Count -gt 1){'ambiguous'}else{'supported'}
  $spatialRelation='unknown'
  if($target.unitIds.Count -eq 1){$spatialRelation=@($target.relations|Where-Object {$_.unitId -eq $target.unitIds[0]})[0].relation}
  elseif($target.unitIds.Count -gt 1){$kinds=@($target.relations|Where-Object {$_.unitId -in $target.unitIds}|ForEach-Object {$_.relation}|Sort-Object -Unique);if($kinds.Count -eq 1){$spatialRelation=$kinds[0]}}
  elseif($target.relations.Count -gt 0 -and @($target.relations|Where-Object relation -ne 'outside').Count -eq 0){$spatialRelation='outside'}
  $status=if($associationStatus -eq 'supported'){'local_unit_supported'}elseif($associationStatus -eq 'ambiguous'){'ambiguous_target'}else{'no_supported_target'}
  $associations+= [pscustomobject]@{id='A'+($associations.Count+1);textHandles=@($matched|ForEach-Object {$_.text.entity.handle});
   leaderHandle=$line.handle;markerHandles=@($circles|ForEach-Object {$_.handle});anchor=@($landing);markerResidual=if($circles.Count -eq 1){Distance $anchor $landing}else{$null};
   targetEdgeIds=$target.edgeIds;targetUnitIds=$target.unitIds;targetInterfaceIds=$target.interfaceIds;
   spatialRelation=$spatialRelation;spatialRelations=$target.relations;associationStatus=$associationStatus;
   otherLandingHandles=$otherHits;
   status=$status;strength=if($circles.Count -eq 1){'strong_spatial'}else{'reduced_no_marker'};
   layout=@($matched|ForEach-Object {[pscustomobject]@{handle=$_.text.entity.handle;alignmentResidual=$_.alignmentResidual;baselineOffset=$_.baselineOffset}});
   basis='text alignment and baseline span -> terminal leader segment -> optional circle -> edge landing';
   scope='landing unit only; no propagation through interfaces';nativeAssociation='not_exported'}
 }}
 # A text that fits multiple leaders is explicitly ambiguous, never resolved by nearest distance.
 foreach($a in $associations){
  if(@($associations|Where-Object {$_.id -ne $a.id -and @($_.textHandles|Where-Object {$_ -in $a.textHandles}).Count -gt 0}).Count -gt 0){$a.status='ambiguous_layout';$a.associationStatus='ambiguous'}
 }
 $weak=@(foreach($t in $texts){if($t.parsed.isTray -and $t.entity.handle -notin @($associations|ForEach-Object {$_.textHandles})){
  [pscustomobject]@{handle=$t.entity.handle;rawText=$t.entity.text;parsed=$t.parsed;status='unassociated_weak_candidate';targetUnitIds=@();reason='No complete supported text-layout/leader relation; proximity is not ownership'}
 }})
 $evidence=New-Object 'System.Collections.Generic.List[object]';$conflicts=New-Object 'System.Collections.Generic.List[object]';$assessments=@()
 foreach($u in $Geometry.units){
  $id=$u.id;$sources=@($Geometry.rawEntities|Where-Object {$_.handle -in $u.sourceHandles})
  $ev=[pscustomobject]@{id='E'+($evidence.Count+1);unitId=$id;kind='geometry';value=[pscustomobject]@{kind=$u.kind;closure=$u.closure;width=$u.width;unit='drawing_units'};sourceHandles=@($u.sourceHandles);basis='phase-1 contour and interface structure';dependencies=@()};$evidence.Add($ev)
  $evidence.Add([pscustomobject]@{id='E'+($evidence.Count+1);unitId=$id;kind='color';value=[pscustomobject]@{status='not_exported'};sourceHandles=@($u.sourceHandles);basis='report has no entity/layer color fields for these sources';dependencies=@()})
  $layerClaims=@(foreach($group in ($sources|Group-Object layer)){
   $p=Convert-TrayDeclaration $group.Name
   $v=[pscustomobject]@{rawLayer=$group.Name;typeClue=$p.type;isTrayNameClue=$p.isTray}
   $e=[pscustomobject]@{id='E'+($evidence.Count+1);unitId=$id;kind='layer';value=$v;sourceHandles=@($group.Group.handle);basis='layer name clue, not authoritative classification';dependencies=@()};$evidence.Add($e);$e
  })
  $annotations=@();$comparisons=@()
  foreach($a in @($associations|Where-Object {$_.associationStatus -eq 'supported' -and $id -in $_.targetUnitIds})){
   foreach($t in @($texts|Where-Object {$_.entity.handle -in $a.textHandles})){
    $e=[pscustomobject]@{id='E'+($evidence.Count+1);unitId=$id;kind='annotation';value=$t.parsed;sourceHandles=@($t.entity.handle,$a.leaderHandle)+@($a.markerHandles);basis=$a.strength;dependencies=@($a.id)}
    $evidence.Add($e);$annotations+=,$e
    if($null -ne $t.parsed.width){
     $measured=@();if($null -ne $u.width){$measured=@([double]$u.width)}else{$measured=@($Geometry.interfaces|Where-Object {$_.id -in $u.interfaceIds}|ForEach-Object {[double]$_.width}|Select-Object -Unique)}
     if($measured.Count -eq 0 -and $Geometry.PSObject.Properties.Name -contains 'widthMeasurements'){$measured=@($Geometry.widthMeasurements|Where-Object {$_.unitId -eq $id}|ForEach-Object {$_.drawingUnitSpacing})}
     $status='units_unresolved';$scaled=@();$independent=$false
     $annotationUnit=if($t.parsed.lengthUnit -eq 'mm'){'mm'}elseif($null -ne $UnitContext){$UnitContext.annotationLengthUnit}else{'unspecified'}
     if($null -ne $UnitContext -and $UnitContext.mmPerDrawingUnit -gt 0 -and $annotationUnit -eq 'mm' -and $measured.Count -gt 0){
      $scaled=@($measured|ForEach-Object {$_*$UnitContext.mmPerDrawingUnit});$independent=[bool]$UnitContext.independent
      if(@($scaled|Where-Object {[math]::Abs($_-$t.parsed.width) -gt $WidthTolerance}).Count -gt 0){$status='inconsistent'}elseif($independent){$status='consistent'}else{$status='consistent_not_independent'}
     }
     $v=[pscustomobject]@{annotatedWidth=$t.parsed.width;measuredDrawingWidths=$measured;convertedWidths=$scaled;status=$status;independent=$independent;unitContext=$UnitContext;annotationUnit=$annotationUnit;numericValuesEqual=($measured.Count -gt 0 -and @($measured|Where-Object {[math]::Abs($_-$t.parsed.width) -gt $WidthTolerance}).Count -eq 0)}
     $ce=[pscustomobject]@{id='E'+($evidence.Count+1);unitId=$id;kind='width_comparison';value=$v;sourceHandles=@($u.sourceHandles)+@($t.entity.handle);basis='compare supplied scale; no scale inferred from annotation';dependencies=@($ev.id,$e.id)};$evidence.Add($ce);$comparisons+=,$ce
     if($status -eq 'inconsistent'){$conflicts.Add([pscustomobject]@{id='F'+($conflicts.Count+1);unitId=$id;field='width';claims=@($t.parsed.width,$scaled);evidenceIds=@($ev.id,$e.id,$ce.id);status='unresolved';unitContext=$UnitContext})}
    }
   }
  }
  $typed=@($annotations|Where-Object {$null -ne $_.value.type});$layerTyped=@($layerClaims|Where-Object {$null -ne $_.value.typeClue})
  $types=@(@($typed|ForEach-Object {$_.value.type})+@($layerTyped|ForEach-Object {$_.value.typeClue})|Sort-Object -Unique)
  $compatibility=Type-Compatibility $types
  if($compatibility -eq 'conflicting'){$conflicts.Add([pscustomobject]@{id='F'+($conflicts.Count+1);unitId=$id;field='type';claims=$types;evidenceIds=@($typed|ForEach-Object {$_.id})+@($layerTyped|ForEach-Object {$_.id});status='unresolved'})}
  $height=@($annotations|Where-Object {$null -ne $_.value.height}|ForEach-Object {$_.value.height}|Sort-Object -Unique)
  if($height.Count -gt 1){$conflicts.Add([pscustomobject]@{id='F'+($conflicts.Count+1);unitId=$id;field='height';claims=$height;evidenceIds=@($annotations|ForEach-Object {$_.id});status='unresolved'})}
  $installations=@($annotations|Where-Object {$null -ne $_.value.installation})
  $installationKeys=@($installations|ForEach-Object {"$($_.value.installation.reference)|$($_.value.installation.offset)|$($_.value.installation.method)"}|Sort-Object -Unique)
  if($installationKeys.Count -gt 1){$conflicts.Add([pscustomobject]@{id='F'+($conflicts.Count+1);unitId=$id;field='installation';claims=@($installations|ForEach-Object {$_.value.installation});evidenceIds=@($installations|ForEach-Object {$_.id});status='unresolved'})}
  $identity=if($u.kind -notin @('straight','bend')){'geometry_unresolved'}elseif(@($annotations|Where-Object {$_.value.isTray}).Count -gt 0){'geometry_and_annotation_supported'}else{'geometry_supported_only'}
  $assessments+= [pscustomobject]@{unitId=$id;identity=$identity;
   type=[pscustomobject]@{status=if($compatibility -eq 'conflicting'){'conflict_unresolved'}elseif($compatibility -eq 'unresolved_compatibility'){'compatibility_unresolved'}elseif($typed.Count -gt 0){'annotation_supported'}else{'layer_clue_only'};compatibility=$compatibility;claims=$types;resolved=$null};
   width=[pscustomobject]@{measuredDrawingUnits=$u.width;comparisonEvidenceIds=@($comparisons|ForEach-Object {$_.id})};
   height=[pscustomobject]@{values=$height;status=if($height.Count -eq 0){'unknown'}elseif($height.Count -eq 1){'annotation_only'}else{'conflict_unresolved'};geometryVerified=$false;evidenceIds=@($annotations|Where-Object {$null -ne $_.value.height}|ForEach-Object {$_.id})};
   installationClaims=@($annotations|Where-Object {$null -ne $_.value.installation}|ForEach-Object {$_.value.installation});
   color=[pscustomobject]@{status='not_exported'};evidenceIds=@($evidence|Where-Object unitId -eq $id|ForEach-Object {$_.id})}
 }
 [pscustomobject]@{schemaVersion=1;scope='phase-2 evidence on supplied local units';geometrySourceRefs=@($Geometry.rawEntities|Select-Object handle,entityKey,reportSHA256,reportLine);rawAnnotationRecords=$Records;associations=$associations;weakCandidates=$weak;evidence=$evidence.ToArray();conflicts=$conflicts.ToArray();unitAssessments=$assessments;
  parameters=[pscustomobject]@{anchorTolerance=$AnchorTolerance;layoutTolerance=$LayoutTolerance;maxTextOffset=$MaxTextOffset;maxMarkerRadius=$MaxMarkerRadius;widthTolerance=$WidthTolerance};unitContext=$UnitContext;
  limitations=@('TEXT alignment records required for strong layout evidence','Only straight LINE/open zero-bulge LWPOLYLINE leaders and CIRCLE markers','No native annotation association in report','No type propagation across interfaces','No unit scale inferred','No colors, center paths or quantities')}
}
Export-ModuleMember -Function Read-AnnotationRegion,Convert-TrayDeclaration,Get-TrayEvidence,Get-UnitSpatialRelations
