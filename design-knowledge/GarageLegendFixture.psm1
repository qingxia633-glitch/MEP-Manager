Set-StrictMode -Version 2
Import-Module (Join-Path $PSScriptRoot 'ProjectDesignKnowledge.psm1')
Import-Module (Join-Path $PSScriptRoot '../model-core/ModelCore.psm1')

# This is a pinned, reviewed sample adapter, not a production legend discovery algorithm.
function Read-GarageLegendFixture {
 param([string]$Root=(Join-Path $PSScriptRoot '..'))
 $f=Get-Content (Join-Path $PSScriptRoot 'tests/garage-legend.json') -Encoding UTF8 -Raw|ConvertFrom-Json
 function Field($r,$k){[regex]::Match($r,'(?m)^'+[regex]::Escape($k)+'=(.*?)\r?$').Groups[1].Value.Trim('"')}
 function Point($raw){@([regex]::Matches($raw,'-?\d+(?:\.\d+)?')|ForEach-Object {[double]::Parse($_.Value,[cultureinfo]::InvariantCulture)})}
 function ReadSource($path,$hash,$document){
  $file=Join-Path $Root $path
  if((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -cne $hash){throw 'Pinned design source changed'}
  $text=[IO.File]::ReadAllText($file)
  if(!(Field $text DWG).EndsWith($document) -or $text -notmatch '(?m)^END_OF_REPORT' -or (Field $text ReadErrorCount) -ne '0'){throw 'Design source not accepted'}
  $map=@{}
  foreach($m in [regex]::Matches($text,'(?ms)^EntityHandle=.*?(?=^EntityHandle=|^LayerEntityCount=|^LAYER_END|\z)')){
   $r=$m.Value;$h=Field $r EntityHandle
   $attrs=@(foreach($am in [regex]::Matches($r,'(?m)^Attribute_DXF=(.*)')){
    $a=$am.Groups[1].Value;$flags=[regex]::Match($a,'\(70 \. (\d+)\)').Groups[1].Value
    [pscustomobject]@{handle=[regex]::Match($a,'\(5 \. "([^"]*)"\)').Groups[1].Value;parentHandle=$h;tag=[regex]::Match($a,'\(2 \. "([^"]*)"\)').Groups[1].Value;rawText=[regex]::Match($a,'\(1 \. "([^"]*)"\)').Groups[1].Value;layer=[regex]::Match($a,'\(8 \. "([^"]*)"\)').Groups[1].Value;coordinateRaw=[regex]::Match($a,'\(10 ([^)]+)\)').Groups[1].Value;flags_RAW=$flags;visibility=if($flags -ne '' -and ([int]$flags -band 1)){'hidden_attribute'}else{'not_flagged_hidden'};rawDXF=$a;sourceSnapshot=$hash;sourceDocument=$document}
   })
   $location=Field $r Insertion_WCS
   if(!$location){$location=[regex]::Match($r,'(?m)^(?:Start_WCS|Center_WCS|Vertex_WCS)=([^\r\n]+)').Groups[1].Value}
   $map[$h]=[pscustomobject]@{handle=$h;entityType=(Field $r DXF_Type);layer=(Field $r Layer);rawText=(Field $r Text_RAW);coordinateRaw=$location;alignmentPoint_RAW=(Field $r Alignment_WCS);blockName=(Field $r BlockName);effectiveName=(Field $r EffectiveName_RAW);attributes=$attrs;rawRecord=$r;sourceDocument=$document;sourceSnapshot=$hash;evaluatedVisibility='unknown'}
  }
  return $map
 }
 $map=ReadSource $f.source.path $f.source.sha256 $f.source.document
 $scope=New-DesignScope $f.projectId $f.source.document $f.source.sha256
 $source=New-DesignKnowledgeSource 'garage-system-legend' $scope $f.source.path DrawingFact $f.source.sha256
 $bounds=$f.region;$x=$bounds.xColumns
 $regionRecords=@(foreach($r in $map.Values){
  $points=@([regex]::Matches($r.rawRecord,'(?m)^(?:Insertion_WCS|Start_WCS|End_WCS|Center_WCS|Vertex_WCS)=([^\r\n]+)')|ForEach-Object {,$(Point $_.Groups[1].Value)})
  if(@($points|Where-Object {$_.Count -eq 3 -and $_[0] -ge $x[0] -and $_[0] -le $x[-1] -and $_[1] -ge $bounds.bottom -and $_[1] -le $bounds.top}).Count){$r}
 })
 $lines=@($regionRecords|Where-Object {$_.entityType -in @('LINE','LWPOLYLINE')})
 $horizontal=@(foreach($r in $lines){
  $a=@(Point (Field $r.rawRecord Start_WCS));$b=@(Point (Field $r.rawRecord End_WCS))
  if($a.Count -eq 3 -and $b.Count -eq 3 -and [math]::Abs($a[1]-$b[1]) -lt 0.00001 -and [math]::Abs($a[0]-$x[0]) -lt 0.00001 -and [math]::Abs($b[0]-$x[-1]) -lt 0.00001){[pscustomobject]@{y=$a[1];handle=$r.handle}}
 })
 foreach($n in 0..$bounds.rowCount){$y=$bounds.bodyTop-$n*$bounds.rowHeight;if(!@($horizontal|Where-Object {[math]::Abs($_.y-$y) -lt 0.00001}).Count){throw "Reviewed row boundary missing: $n"}}
 $region=New-LegendRegion $f.fixtureId $source @($f.region.titleHandles|ForEach-Object {$map[$_]}) @($f.region.headerHandles|ForEach-Object {$map[$_]}) $lines @{grid=$bounds;basis=$bounds.basis;horizontalBoundaries=$horizontal;coordinateFrame='snapshot_WCS_drawing_units'}
 $entries=@();$symbols=@()
 foreach($n in 1..$bounds.rowCount){
  $upper=$bounds.bodyTop-($n-1)*$bounds.rowHeight;$lower=$upper-$bounds.rowHeight
  $members=@($regionRecords|Where-Object {$p=@(Point $_.coordinateRaw);$p.Count -eq 3 -and $p[1] -ge $lower -and $p[1] -lt $upper}|Sort-Object handle)
  $texts=@($members|Where-Object entityType -CEQ TEXT)
  function Cell([int]$col){@($texts|Where-Object {$p=@(Point $_.coordinateRaw);$p[0] -ge $x[$col] -and $p[0] -lt $x[$col+1]})}
  $nameRecords=@(Cell 2|Where-Object {$f.fragmentReview.handles -cnotcontains $_.handle})
  $reading=$null
  if($n -eq $f.fragmentReview.row){
   $nameRecords+=@($f.fragmentReview.handles|ForEach-Object {$map[$_]})
   $fragments=@($nameRecords|ForEach-Object {New-TextFragmentCandidate $source $_})
   $reading=New-ReadingOrderCandidate $fragments @{basis=$f.fragmentReview.basis;status='boundary_spillover_unresolved'} $f.fragmentReview.normalizedCandidate
  }
  $names=@($nameRecords|ForEach-Object {New-TextFragmentCandidate $source $_})
  $models=@(Cell 3|ForEach-Object {New-TextFragmentCandidate $source $_})
  $installation=@(Cell 5|ForEach-Object {New-TextFragmentCandidate $source $_})
  $notes=@(Cell 4|ForEach-Object {New-TextFragmentCandidate $source $_})
  $sym=@($members|Where-Object {
   if($_.entityType -notin @('INSERT','LINE','LWPOLYLINE','CIRCLE','ARC')){return $false}
   $ps=@([regex]::Matches($_.rawRecord,'(?m)^(?:Insertion_WCS|Start_WCS|End_WCS|Center_WCS|Vertex_WCS)=([^\r\n]+)')|ForEach-Object {,$(Point $_.Groups[1].Value)})
   # Direct symbol geometry only; full-width table lines are not symbol members.
   return ($ps.Count -gt 0 -and !@($ps|Where-Object {$_[0] -lt $x[1] -or $_[0] -ge $x[2] -or $_[1] -lt $lower -or $_[1] -ge $upper}).Count)
  })
  $layout=@{upperY=$upper;lowerY=$lower;boundaryHandles=@($horizontal|Where-Object {[math]::Abs($_.y-$upper) -lt 0.00001 -or [math]::Abs($_.y-$lower) -lt 0.00001}|ForEach-Object {$_.handle});sequenceRepresentations=@(Cell 0);columnBoundaries=$x;membership='grid_cells_not_nearest_text';fragmentExceptions=@($reading|Where-Object {$null -ne $_})}
  $entry=New-DesignLegendEntry $region ([string]$n) $sym $names $models $notes $installation $members $layout $reading
  $entries+=,$entry
  $inserts=@($sym|Where-Object entityType -EQ INSERT)
  if($inserts.Count){$symbols+=,(New-SymbolDefinitionCandidate ($entry.entryId+':symbols') @($inserts.blockName|Select-Object -Unique) $sym $scope)}
 }
 $otherScope=New-DesignScope $f.projectId $f.otherSource.document '' $f.otherSource.building
 $other=New-DesignKnowledgeSource 'building-4-human-legend' $otherScope $f.otherSource.provenance HumanConfirmation
 $comparisons=@();$evidence=@()
 foreach($c in $f.comparisons){
  $entry=$entries|Where-Object rowId -EQ ([string]$c.row)
  $comparisons+=,(New-CrossDrawingLegendComparison $entry $other $c.token $c.meaning $c.status)
  $ss=New-SystemScope $f.projectId (New-SystemIdentity $c.system)
  $evidence+=,(ConvertTo-DesignEvidence $entry ('legend_meaning:'+$c.token) $ss)
 }
 $ff=Get-Content (Join-Path $Root $f.fireSourceFixture) -Encoding UTF8 -Raw|ConvertFrom-Json
 $fire=ReadSource $ff.source.path $ff.source.sha256 $ff.source.dwgName
 $fireSource=New-DesignKnowledgeSource 'garage-fire-instance-facts' (New-DesignScope $f.projectId $ff.source.dwgName $ff.source.sha256) $ff.source.path DrawingFact $ff.source.sha256
 $conflicts=@();$reviews=@();$alarm=New-SystemScope $f.projectId (New-SystemIdentity fire_alarm)
 foreach($h in $f.conflictInstances){
  $r=$fire[$h];$name=@($r.attributes|Where-Object tag -CEQ A);$code=@($r.attributes|Where-Object tag -CEQ '$TEXT$')
  if($name.Count -ne 1 -or $code.Count -ne 1 -or $code[0].rawText -cne 'I'){throw 'Reviewed conflict representation changed'}
  $claims=@(@{id=($ff.source.sha256+':'+$h);kind='DrawingFact';semanticClaim=$name[0].rawText;sourceDocument=$ff.source.dwgName;sourceSnapshot=$ff.source.sha256;representation=$r;name=$name[0];code=$code[0]})
  $entry=$entries|Where-Object rowId -EQ '23'
  $conflict=New-DesignConflict ('design-conflict:'+$h) $entry $claims $alarm
  $conflicts+=,$conflict
  $reviews+=,(New-LegendConflictReview $conflict.conflictId $conflict.claims @($r,$name[0],$code[0]) @($source,$fireSource) $alarm $conflict.invalidationDependencies)
  $es=@{projectId=$f.projectId;snapshotIds=@($source.sourceSnapshot,$ff.source.sha256);subjectIds=@($entry.entryId,$claims[0].id)}
  $evidence+=,(New-SystemEvidence $conflict.conflictId ('instance_semantics:'+$h) DerivedInference conflicting $es $alarm -Claim $conflict -Provenance @{sources=@($source,$fireSource);status='unresolved_comparison_not_instance_typing'})
 }
 $coverage=@((Get-Content (Join-Path $Root 'model-core/capabilities.json') -Encoding UTF8 -Raw|ConvertFrom-Json)|Where-Object {$_.id -in @('design_knowledge_source','legend_region_parsing','legend_entry_extraction','cross_drawing_legend_comparison','design_conflict_detection')}|ForEach-Object {New-CapabilityCoverage $_.id $_.domain $_.objectType $_.type $_.status $_.samples $_.scope $_.limitations $_.unresolved $_.evidence})
 New-ProjectDesignKnowledge $f.projectId @($source,$other,$fireSource) @($region) $entries $symbols $comparisons $conflicts $evidence $reviews $coverage
}
Export-ModuleMember -Function Read-GarageLegendFixture
