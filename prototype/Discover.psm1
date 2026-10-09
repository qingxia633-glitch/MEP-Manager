Set-StrictMode -Version Latest
function Vec($a,$b){,@(($b[0]-$a[0]),($b[1]-$a[1]),($b[2]-$a[2]))}
function Dot($a,$b){$a[0]*$b[0]+$a[1]*$b[1]+$a[2]*$b[2]}
function Dist($a,$b){$v=Vec $a $b;[math]::Sqrt((Dot $v $v))}
function Cross2($a,$b){$a[0]*$b[1]-$a[1]*$b[0]}
function Clip-Hit($p,$q,$config){
 $lo=0.0;$hi=1.0
 for($k=0;$k -lt 3;$k++){$d=$q[$k]-$p[$k]
  if([math]::Abs($d) -lt 1e-12){if($p[$k] -lt $config.min[$k] -or $p[$k] -gt $config.max[$k]){return $false}}
  else{$a=($config.min[$k]-$p[$k])/$d;$b=($config.max[$k]-$p[$k])/$d;$lo=[math]::Max($lo,[math]::Min($a,$b));$hi=[math]::Min($hi,[math]::Max($a,$b));if($lo -gt $hi){return $false}}
 };return $true
}
function Walk-Contour($path,$points,$directions,$turns){
 $last=$path[-1];$end=$points[-1];$turnTotal=0.0;foreach($t in $turns){$turnTotal+=$t}
 if([math]::Abs([math]::Abs($turnTotal)-90) -le $script:cfg.angleToleranceDegrees){
  $kind=if($turns.Count -eq 1){'rightAngle'}else{'chamfer'}
  $names=@($path | ForEach-Object {$script:edges[$_].handle});$forward=$names -join ',';$reverse=@($names);[array]::Reverse($reverse);$back=$reverse -join ',';$key=if([string]::CompareOrdinal($forward,$back) -lt 0){$forward}else{$back}
  if(-not $script:found.ContainsKey($key)){$script:found[$key]=[pscustomobject]@{kind=$kind;handles=$names;points=$points;turns=$turns}}
 }
 if($path.Count -ge $script:cfg.maxEdgesPerChain){$script:depthLimitHits++;return}
 foreach($link in $script:links){
  $other=-1;$entry=-1
  if($link.a -eq $last -and (Dist $end $script:edges[$last].vertices[$link.aEnd]) -le $script:cfg.endpointTolerance){$other=$link.b;$entry=$link.bEnd}
  if($link.b -eq $last -and (Dist $end $script:edges[$last].vertices[$link.bEnd]) -le $script:cfg.endpointTolerance){$other=$link.a;$entry=$link.aEnd}
  if($other -lt 0 -or $other -in $path){continue}
  $edge=$script:edges[$other];$next=$edge.vertices[1-$entry]
  # Do not extend via an endpoint outside the configured region.
  $inside=$true;for($k=0;$k -lt 3;$k++){if($end[$k] -lt $script:cfg.min[$k] -or $end[$k] -gt $script:cfg.max[$k]){$inside=$false}}
  if(-not $inside){continue}
  $d=Vec $edge.vertices[$entry] $next;$len=Dist $edge.vertices[$entry] $next;$d=@($d | ForEach-Object {$_/$len})
  $prev=$directions[-1];$angle=[math]::Atan2((Cross2 $prev $d),(Dot $prev $d))*180/[math]::PI
  $newTurns=@($turns)
  if([math]::Abs($angle) -gt $script:cfg.angleToleranceDegrees){
   if([math]::Abs([math]::Abs($angle)-45) -gt $script:cfg.angleToleranceDegrees -and [math]::Abs([math]::Abs($angle)-90) -gt $script:cfg.angleToleranceDegrees){continue}
   if($turns.Count -gt 0 -and $angle*$turnTotal -le 0){continue}
   if([math]::Abs($turnTotal+$angle) -gt 90+$script:cfg.angleToleranceDegrees){continue}
   $newTurns+= $angle
  }
  Walk-Contour @($path+$other) @($points+,(,@($next[0],$next[1],$next[2]))[0]) @($directions+,$d) $newTurns
 }
}
function Pair-Metrics($a,$b,$tol,$angleTol){
 $a=Clip-Run $a;$b=Clip-Run $b
 if($null -eq $a -or $null -eq $b){return $null}
 $u=Vec $a[0] $a[1];$v=Vec $b[0] $b[1];$len=Dist $a[0] $a[1];$otherLen=Dist $b[0] $b[1]
 $u=@($u | ForEach-Object {$_/$len});$v=@($v | ForEach-Object {$_/$otherLen})
 if((Dot $u $v) -lt [math]::Cos($angleTol*[math]::PI/180)){return $null}
 if([math]::Abs($a[0][2]-$b[0][2]) -gt $tol){return $null}
 $delta=Vec $a[0] $b[0];$start=Dot $delta $u;$finish=$start+$otherLen
 $overlap=[math]::Min($len,$finish)-[math]::Max(0,$start)
 if($overlap -le $tol){return $null}
 $gap=Cross2 $u $delta
 if([math]::Abs($gap) -le $tol){return $null}
 [pscustomobject]@{signedGap=$gap;overlap=$overlap}
}
function Clip-Run($points){
 $p=$points[0];$q=$points[1];$lo=0.0;$hi=1.0
 for($k=0;$k -lt 3;$k++){$d=$q[$k]-$p[$k]
 if([math]::Abs($d) -lt 1e-12){if($p[$k] -lt $script:cfg.min[$k] -or $p[$k] -gt $script:cfg.max[$k]){return $null}}
 else{$a=($script:cfg.min[$k]-$p[$k])/$d;$b=($script:cfg.max[$k]-$p[$k])/$d;$lo=[math]::Max($lo,[math]::Min($a,$b));$hi=[math]::Min($hi,[math]::Max($a,$b))}}
 if($hi -le $lo){return $null}
 $start=@(0..2 | ForEach-Object {$p[$_]+$lo*($q[$_]-$p[$_])})
 $end=@(0..2 | ForEach-Object {$p[$_]+$hi*($q[$_]-$p[$_])})
 ,@($start,$end)
}
function End-Runs($points,$angleTol){
 $first=Vec $points[0] $points[1];$last=Vec $points[-2] $points[-1];$i=1
 while($i -lt $points.Count-1){$d=Vec $points[$i] $points[$i+1];if([math]::Abs([math]::Atan2((Cross2 $first $d),(Dot $first $d))*180/[math]::PI) -gt $angleTol){break};$i++}
 $j=$points.Count-2
 while($j -gt 0){$d=Vec $points[$j-1] $points[$j];if([math]::Abs([math]::Atan2((Cross2 $last $d),(Dot $last $d))*180/[math]::PI) -gt $angleTol){break};$j--}
 [pscustomobject]@{first=@($points[0],$points[$i]);last=@($points[$j],$points[-1])}
}
function Find-LocalContours {
 param([string]$Report,[object]$Config,[string]$Text)
 if($Config.endpointTolerance -le 0 -or $Config.maxEdgesPerChain -lt 3){throw 'Invalid discovery configuration'}
 if(-not $Text){$Text=Get-Content -LiteralPath $Report -Raw -Encoding UTF8}
 if($Text -notmatch '(?m)^END_OF_REPORT:'){throw 'Incomplete report'}
 $layer=[regex]::Match($Text,'(?ms)^LAYER_BEGIN="'+[regex]::Escape($Config.layer)+'"\r?\n(.*?)^LAYER_END')
 if(-not $layer.Success){throw 'Configured layer not found'}
 $candidates=@();$unsupported=@()
 foreach($r in [regex]::Matches($layer.Groups[1].Value,'(?ms)^EntityHandle="([^"]+)"\r?\n(.*?)(?=^EntityHandle=|^LayerEntityCount=|\z)')){
  $body=$r.Groups[2].Value;$type=[regex]::Match($body,'DXF_Type="([^"]+)"').Groups[1].Value
  $pts=@(foreach($m in [regex]::Matches($body,'(?m)^(?:Vertex_WCS|Start_WCS|End_WCS)=\(([^)]+)\)')){,@($m.Groups[1].Value.Split(' ') | ForEach-Object {[double]::Parse($_,[cultureinfo]::InvariantCulture)})})
  $bulges=@(foreach($m in [regex]::Matches($body,'Width_or_bulge_DXF=\(42 \. ([^)]+)\)')){[double]::Parse($m.Groups[1].Value,[cultureinfo]::InvariantCulture)})
  $closed=$body -match '(?m)^Closed=T\s*$'
  if($pts.Count -ne 2 -or $closed -or @($bulges | Where-Object {$_ -ne 0}).Count -or $type -notin @('LINE','LWPOLYLINE') -or $body -match 'ERROR|UNAVAILABLE'){$unsupported+=@{handle=$r.Groups[1].Value;reason='Unsupported/incomplete geometry; window membership not established'};continue}
  if(-not (Clip-Hit $pts[0] $pts[1] $Config)){continue}
  $len=Dist $pts[0] $pts[1]
  if($len -le $Config.endpointTolerance -or [math]::Abs($pts[0][2]-$pts[1][2]) -gt $Config.endpointTolerance){$unsupported+=@{handle=$r.Groups[1].Value;reason='Degenerate or non-XY segment'};continue}
  $d=Vec $pts[0] $pts[1]
  $candidates+=[pscustomobject]@{handle=$r.Groups[1].Value;type=$type;layer=$Config.layer;vertices=$pts;endpoints=$pts;direction=@($d | ForEach-Object {$_/$len});length=$len;bulges=$bulges;closed=$closed}
 }
 $script:cfg=$Config;$script:edges=$candidates;$script:links=@();$duplicates=@()
 for($i=0;$i -lt $candidates.Count;$i++){for($j=$i+1;$j -lt $candidates.Count;$j++){$hits=0
  for($a=0;$a -lt 2;$a++){for($b=0;$b -lt 2;$b++){$gap=Dist $candidates[$i].vertices[$a] $candidates[$j].vertices[$b]
   if($gap -le $Config.endpointTolerance){$script:links+=[pscustomobject]@{a=$i;b=$j;aEnd=$a;bEnd=$b;handles=@($candidates[$i].handle,$candidates[$j].handle);gap=$gap};$hits++}}}
  if($hits -eq 2){$duplicates+=,@($candidates[$i].handle,$candidates[$j].handle)}
 }}
 $script:found=@{};$script:depthLimitHits=0
 for($i=0;$i -lt $candidates.Count;$i++){foreach($start in @(0,1)){$p=$candidates[$i].vertices[$start];$q=$candidates[$i].vertices[1-$start];$d=Vec $p $q;$d=@($d | ForEach-Object {$_/$candidates[$i].length});Walk-Contour @($i) @($p,$q) @(,$d) @()}}
 $chains=@($script:found.Values | Sort-Object kind,@{e={$_.handles -join ','}})
 # Keep maximal chains of the SAME turn pattern; reversal is geometrically equivalent.
 $maximal=@(foreach($c in $chains){$contained=$false;$s=','+($c.handles -join ',')+',';$rev=@($c.handles);[array]::Reverse($rev);$rs=','+($rev -join ',')+','
 foreach($other in $chains){if($other.kind -eq $c.kind -and $other.handles.Count -gt $c.handles.Count){$os=','+($other.handles -join ',')+',';if($os.Contains($s) -or $os.Contains($rs)){$contained=$true;break}}}
 if(-not $contained){$c}})
 $id=0;foreach($c in $maximal){$c | Add-Member id ('C'+(++$id));$c | Add-Member ambiguity 'Geometric candidate only: endpoint branches, end caps and overlaps are not semantically resolved'}
 $pairs=@()
 foreach($inner in @($maximal | Where-Object kind -eq 'chamfer')){foreach($outer in @($maximal | Where-Object kind -eq 'rightAngle')){
  if(@($inner.handles | Where-Object {$_ -in $outer.handles}).Count){continue}
  $a=End-Runs $inner.points $Config.angleToleranceDegrees
  foreach($reverse in @($false,$true)){$op=@($outer.points);if($reverse){[array]::Reverse($op)};$b=End-Runs $op $Config.angleToleranceDegrees
   $m=Pair-Metrics $a.first $b.first $Config.endpointTolerance $Config.angleToleranceDegrees
   $n=Pair-Metrics $a.last $b.last $Config.endpointTolerance $Config.angleToleranceDegrees
   if($null -ne $m -and $null -ne $n -and [math]::Abs($m.signedGap-$n.signedGap) -le $Config.endpointTolerance){
    $pairs+=[pscustomobject]@{inner=$inner.id;outer=$outer.id;width=[math]::Abs($m.signedGap);overlapFirst=$m.overlap;overlapLast=$n.overlap;confidence='geometrically_supported_not_confirmed';reason='Two parallel overlapping end runs, same signed spacing, continuous 45+45 versus 90 turn; caps/other networks remain unresolved'}
   }
  }
 }}
 # Materialize plain arrays so PowerShell pipeline metadata cannot alter JSON shape.
 foreach($c in $candidates){for($i=0;$i -lt $c.vertices.Count;$i++){$p=$c.vertices[$i];$c.vertices[$i]=@([double]$p[0],[double]$p[1],[double]$p[2])};$c.endpoints=$c.vertices}
 foreach($c in $maximal){for($i=0;$i -lt $c.points.Count;$i++){$p=$c.points[$i];$c.points[$i]=@([double]$p[0],[double]$p[1],[double]$p[2])}}
 $duplicateRecords=@(foreach($d in $duplicates){[pscustomobject]@{handles=@([string]$d[0],[string]$d[1]);reason='Both endpoint positions coincide within tolerance'}})
 [pscustomobject]@{config=$Config;candidates=$candidates;connections=$script:links;chains=$maximal;pairs=$pairs;duplicates=$duplicateRecords;unsupported=$unsupported;depthLimitHits=$script:depthLimitHits;scope='Segments intersecting window retained whole for provenance; no traversal through outside endpoints. No interior intersections imply connectivity.'}
}
Export-ModuleMember -Function Find-LocalContours
