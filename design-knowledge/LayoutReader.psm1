Set-StrictMode -Version 2
Import-Module (Join-Path $PSScriptRoot 'BBoxContinuity.psm1')
function Convert-MTextCandidate([string]$Raw) {
 $tokens=@([regex]::Matches($Raw,'\\(?:[A-Za-z][^;\\{}]*;|[PLlOoKk~{}\\])|[{}]|%<.*?>%')|ForEach-Object {$_.Value})
 $plain=$Raw -replace '\\P',"`n" -replace '\\~',' '
 # Only simple display switches are normalized. Stacks, fields, unknown escapes remain visible.
 $plain=$plain -replace '\\[LlOoKk]','' -replace '\\[CHWFATQcf][^;\\{}]*;',''
 $unresolved=($plain -match '\\|%<|[{}]')
 [pscustomobject]@{rawMText=$Raw;normalizedPlainTextCandidate=$plain;formattingTokens=$tokens;status=if($unresolved){'partial'}else{'candidate'};automaticBodyAdmission=$false}
}
function Get-LayoutRotation($Record) {
 if($Record.PSObject.Properties['rotationRadians']){$a=$Record.rotationRadians}
 else{$m=[regex]::Match($Record.rawRecord,'(?m)^Rotation(?:_Radians)?=([-\d.]+)');$a=if($m.Success){[double]$m.Groups[1].Value}else{$null}}
 if($null -eq $a){return 'unknown'}
 $d=(([double]$a*180/[math]::PI)%360+360)%360
 if($d -le 1 -or $d -ge 359){return 'horizontal'}
 if([math]::Abs($d-90) -le 1 -or [math]::Abs($d-270) -le 1){return 'vertical'}
 return 'other'
}
function Read-LayoutGeometry([string]$Text,[string]$Snapshot) {
 foreach($m in [regex]::Matches($Text,'(?ms)^EntityHandle=.*?(?=^EntityHandle=|^LayerEntityCount=|^LAYER_END|\z)')){
  $r=$m.Value;$type=[regex]::Match($r,'DXF_Type="([^"]+)"').Groups[1].Value
  if($type -notin @('LINE','LWPOLYLINE')){continue}
  $h=[regex]::Match($r,'EntityHandle="([^"]+)"').Groups[1].Value
  $key=if($type -eq 'LINE'){'(?:Start|End)_WCS'}else{'Vertex_WCS'}
  $points=@([regex]::Matches($r,'(?m)^'+$key+'=\(([-\d.]+) ([-\d.]+) ([-\d.]+)\)')|ForEach-Object {,@([double]$_.Groups[1].Value,[double]$_.Groups[2].Value,[double]$_.Groups[3].Value)})
  $bulges=@([regex]::Matches($r,'\(42 \. ([-\d.]+)\)')|Where-Object {[double]$_.Groups[1].Value -ne 0})
  $closed=($r -match '(?m)^Closed=T\r?$')
  [pscustomobject]@{id=($Snapshot+':'+$h);handle=$h;sourceSnapshot=$Snapshot;entityType=$type;points=$points;closed=$closed;linearSupported=($bulges.Count -eq 0);rawRecord=$r;layer=[regex]::Match($r,'Layer="([^"]+)"').Groups[1].Value}
 }
}
function Get-LayoutBoundaries($Geometry,[double]$Pitch) {
 foreach($g in $Geometry){
  if(!$g.linearSupported -or $g.points.Count -lt 2){continue}
  $n=$g.points.Count-1;if($g.closed){$n++}
  for($i=0;$i -lt $n;$i++){
   $a=$g.points[$i];$b=$g.points[($i+1)%$g.points.Count];$dx=[math]::Abs($a[0]-$b[0]);$dy=[math]::Abs($a[1]-$b[1])
   $axis=if($dy -le $Pitch*.001 -and $dx -ge $Pitch*2){'horizontal'}elseif($dx -le $Pitch*.001 -and $dy -ge $Pitch*2){'vertical'}else{'unsupported'}
   if($axis -eq 'unsupported'){continue}
   [pscustomobject]@{id=($g.id+':segment:'+ $i);sourceRef=$g.id;sourceSnapshot=$g.sourceSnapshot;axis=$axis;minX=[math]::Min($a[0],$b[0]);maxX=[math]::Max($a[0],$b[0]);minY=[math]::Min($a[1],$b[1]);maxY=[math]::Max($a[1],$b[1]);roleCandidate=if($g.closed){'frame_edge'}else{$axis+'_separator'};status='candidate'}
  }
 }
}
function Test-LayoutSeparation($A,$B,$Boundaries) {
 foreach($s in $Boundaries){
  if($s.sourceSnapshot -ne $A.sourceSnapshot){continue}
  # Intersection of anchor-to-anchor segment with separator, not proximity.
  if($s.axis -eq 'horizontal' -and ($A.y-$s.minY)*($B.y-$s.minY) -lt 0){
   $x=$A.x+($B.x-$A.x)*($s.minY-$A.y)/($B.y-$A.y)
   if($x -ge $s.minX -and $x -le $s.maxX){return $true}
  }
  if($s.axis -eq 'vertical' -and ($A.x-$s.minX)*($B.x-$s.minX) -lt 0){
   $y=$A.y+($B.y-$A.y)*($s.minX-$A.x)/($B.x-$A.x)
   if($y -ge $s.minY -and $y -le $s.maxY){return $true}
  }
 }
 return $false
}
function Complete-LayoutResult($Result,$Records,$Boundaries) {
 $columns=@(foreach($r in $Result.regions){
  $ps=@($Result.paragraphs|Where-Object regionId -EQ $r.regionId);$fs=@($ps|ForEach-Object {$_.textFragments})
  $xmin=($fs.x|Measure-Object -Minimum).Minimum;$xmax=($fs.x|Measure-Object -Maximum).Maximum
  $edges=@($Boundaries|Where-Object {$_.sourceSnapshot -eq $r.sourceSnapshot -and $_.maxX -ge $xmin-$Result.linePitch -and $_.minX -le $xmax+$Result.linePitch -and $_.maxY -ge $r.bottomY-$Result.linePitch -and $_.minY -le $r.topY+$Result.linePitch})
  $boxes=@($fs|ForEach-Object {Get-TextLayoutBox $_}|Where-Object {$null -ne $_})
  [pscustomobject]@{modelType='TextColumnCandidate';id=($r.regionId+':column');sourceSnapshot=$r.sourceSnapshot;bounds=@{minX=$xmin;maxX=$xmax;minY=$r.bottomY;maxY=$r.topY;basis='text_anchor_extent_not_glyph_bounds'};bboxXMin=if($boxes.Count){($boxes|Measure-Object minX -Minimum).Minimum}else{$null};bboxXMax=if($boxes.Count){($boxes|Measure-Object maxX -Maximum).Maximum}else{$null};bboxEvidenceRefs=@($boxes|ForEach-Object {$_.sourceRef});continuationEvidence=@($ps|ForEach-Object {$_.continuationEvidence});dominantX=$r.referenceX;dominantTextRotation='horizontal_or_unknown';lineSpacingCandidate=$Result.linePitch;textEntityIds=@($fs.id);boundaryEvidence=$edges;confidence=$r.confidence}
 })
 $metadata=@($Records|Where-Object {$_.entityType -eq 'ATTRIB'})
 $layout=@(foreach($c in $columns){[pscustomobject]@{modelType='LayoutRegionCandidate';id=$c.id;roleCandidate='text_column';bounds=$c.bounds;evidence=$c.boundaryEvidence;confidence=$c.confidence;engineeringMeaning='unresolved'}})
 foreach($g in @($Boundaries|Where-Object roleCandidate -EQ frame_edge|Group-Object sourceRef)){
  if($g.Count -eq 4 -and @($g.Group|Where-Object axis -EQ horizontal).Count -eq 2){
   $layout+=,[pscustomobject]@{modelType='LayoutRegionCandidate';id=('frame:'+ $g.Name);roleCandidate='frame_candidate';bounds=@{minX=($g.Group.minX|Measure-Object -Minimum).Minimum;maxX=($g.Group.maxX|Measure-Object -Maximum).Maximum;minY=($g.Group.minY|Measure-Object -Minimum).Minimum;maxY=($g.Group.maxY|Measure-Object -Maximum).Maximum};evidence=$g.Group;confidence='medium';engineeringMeaning='unresolved'}
  }
 }
 foreach($g in @($Boundaries|Where-Object axis -EQ horizontal|Group-Object { $_.sourceSnapshot+':'+[math]::Round($_.minX/$Result.linePitch,2)+':'+[math]::Round($_.maxX/$Result.linePitch,2)})){
  if($g.Count -lt 3){continue}
  $ys=@($g.Group.minY|Sort-Object -Unique);if($ys.Count -lt 3){continue}
  $first=$g.Group[0];$lo=$ys[0];$hi=$ys[-1]
  $vs=@($Boundaries|Where-Object {$_.sourceSnapshot -eq $first.sourceSnapshot -and $_.axis -eq 'vertical' -and $_.minX -ge $first.minX -and $_.maxX -le $first.maxX -and $_.minY -le $lo -and $_.maxY -ge $hi})
  if($vs.Count -lt 2){continue}
  $layout+=,[pscustomobject]@{modelType='LayoutRegionCandidate';id=('grid:'+ $first.id);roleCandidate='table_grid_candidate';bounds=@{minX=$first.minX;maxX=$first.maxX;minY=$lo;maxY=$hi};evidence=@($g.Group)+$vs;confidence='medium';engineeringMeaning='unresolved'}
 }
 foreach($g in @($metadata|Group-Object parentHandle)){$layout+=,[pscustomobject]@{modelType='LayoutRegionCandidate';id=('metadata:'+ $g.Name);roleCandidate='drawing_metadata_candidate';sourceEntities=@($g.Group.id);evidence='attached_attributes_excluded_from_body';confidence='low';engineeringMeaning='unresolved'}}
 foreach($r in $Records|Where-Object {$_.rawText -match '(设计|施工).*说明'}){$layout+=,[pscustomobject]@{modelType='LayoutRegionCandidate';id=('title:'+ $r.id);roleCandidate='title_candidate';sourceEntities=@($r.id);evidence='title_text_pattern_only';confidence='low';engineeringMeaning='unresolved'}}
 $mt=@(foreach($r in $Records|Where-Object entityType -EQ MTEXT){[pscustomobject]@{sourceRef=$r.id;normalization=(Convert-MTextCandidate $r.rawText)}})
 $Result|Add-Member textColumns $columns
 $Result|Add-Member layoutRegions $layout
 $Result|Add-Member layoutBoundaries @($Boundaries)
 $Result|Add-Member mtextCandidates $mt
 $Result|Add-Member rotationEvidence @($Records|ForEach-Object {[pscustomobject]@{sourceRef=$_.id;classification=(Get-LayoutRotation $_)}})
 $Result.version='0.3-text-bbox-continuity'
 return $Result
}
Export-ModuleMember -Function Convert-MTextCandidate,Get-LayoutRotation,Read-LayoutGeometry,Get-LayoutBoundaries,Test-LayoutSeparation,Complete-LayoutResult
