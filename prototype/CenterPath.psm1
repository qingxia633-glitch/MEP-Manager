Set-StrictMode -Version Latest
function Sub($a,$b) { ,@(($a[0]-$b[0]),($a[1]-$b[1]),($a[2]-$b[2])) }
function Dot($a,$b) { $a[0]*$b[0]+$a[1]*$b[1]+$a[2]*$b[2] }
function Distance($a,$b) { $v=Sub $a $b; [math]::Sqrt((Dot $v $v)) }
function Mid($a,$b) { ,@(($a[0]+($b[0]-$a[0])/2),($a[1]+($b[1]-$a[1])/2),($a[2]+($b[2]-$a[2])/2)) }
function Read-SampleReport($Path,$Config) {
 $raw=Get-Content -LiteralPath $Path -Raw -Encoding UTF8
 if(-not $raw.Contains($Config.drawingName)){throw 'Report drawing does not match configured drawing'}
 if($raw -notmatch '(?m)^INSUNITS=0\s*$'){throw 'Unexpected INSUNITS; review calibration'}
 if($raw -notmatch '(?m)^END_OF_REPORT:'){throw 'Incomplete report'}
 $handles=@($Config.straight)+@($Config.turn.innerChain)+@($Config.turn.outerChain)
 $entities=@{}
 foreach($h in $handles){
  $matches=[regex]::Matches($raw,'(?ms)^EntityHandle="'+[regex]::Escape($h)+'"\r?\n(.*?)(?=^EntityHandle=|^LayerEntityCount=|\z)')
  if($matches.Count -ne 1){throw "Missing or duplicate handle: $h"}
  $body=$matches[0].Groups[1].Value
  if($body -match 'ERROR|UNAVAILABLE|UNREADABLE'){throw "Read error in $h"}
  $vertices=@(foreach($m in [regex]::Matches($body,'(?m)^Vertex_WCS=\(([^)]+)\)')){
   $tokens=$m.Groups[1].Value.Split(' ')
   if($tokens.Count -ne 3){throw "Invalid coordinate in $h"}
   ,@($tokens | ForEach-Object {[double]::Parse($_,[cultureinfo]::InvariantCulture)})
  })
  $bulges=@(foreach($m in [regex]::Matches($body,'Width_or_bulge_DXF=\(42 \. ([^)]+)\)')){[double]::Parse($m.Groups[1].Value,[cultureinfo]::InvariantCulture)})
  $type=[regex]::Match($body,'DXF_Type="([^"]+)"').Groups[1].Value
  if($type -ne 'LWPOLYLINE' -or $vertices.Count -ne 2 -or $bulges.Count -ne 2 -or @($bulges | Where-Object {$_ -ne 0}).Count -gt 0 -or $body -notmatch '(?m)^Closed=nil\s*$'){throw "Unsupported geometry at $h; only open two-vertex straight polylines are supported"}
  $entities[$h]=[pscustomobject]@{handle=$h;layer=[regex]::Match($body,'(?m)^Layer="([^"]+)"').Groups[1].Value;type=$type;vertices=$vertices;bulges=$bulges;closed=$false;reportSHA256=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash;drawing=$Config.drawingName}
 }
 return $entities
}
function Center-Pair($a,$b,$tol) {
 $p=$a.vertices[0];$q=$a.vertices[1];$r=$b.vertices[0];$s=$b.vertices[1]
 $u=Sub $q $p;$v=Sub $s $r
 if((Dot $u $v) -lt 0){$temp=$r;$r=$s;$s=$temp}
 # Canonical direction makes reversal of either input deterministic.
 $u=Sub $q $p
 $axis=0;while($axis -lt 2 -and [math]::Abs($u[$axis]) -le $tol){$axis++}
 if($u[$axis] -lt 0){$temp=$p;$p=$q;$q=$temp;$temp=$r;$r=$s;$s=$temp}
 $len=Distance $p $q
 if($len -le $tol -or (Distance $r $s) -le $tol){throw 'Degenerate edge'}
 $u=Sub $q $p;$u=@($u | ForEach-Object {$_/$len})
 $v=Sub $s $r;$projection=Dot $v $u
 $residual=@(0..2 | ForEach-Object {$v[$_]-$projection*$u[$_]})
 if((Distance $residual @(0,0,0)) -gt $tol){throw 'Nonparallel edges'}
 if([math]::Abs($p[2]-$q[2]) -gt $tol -or [math]::Abs($p[2]-$r[2]) -gt $tol -or [math]::Abs($p[2]-$s[2]) -gt $tol){throw 'Only coplanar XY samples supported'}
 $t0=Dot (Sub $r $p) $u;$t1=Dot (Sub $s $p) $u
 $lo=[math]::Max(0,$t0);$hi=[math]::Min($len,$t1)
 if($hi-$lo -le $tol){throw 'No supported overlap'}
 $offset=Sub $r $p;$offset=@(0..2 | ForEach-Object {$offset[$_]-$t0*$u[$_]})
 $width=Distance $offset @(0,0,0)
 if($width -le $tol){throw 'Coincident sides'}
 $start=@(0..2 | ForEach-Object {$p[$_]+$lo*$u[$_]+$offset[$_]/2})
 $end=@(0..2 | ForEach-Object {$p[$_]+$hi*$u[$_]+$offset[$_]/2})
 [pscustomobject]@{points=@($start,$end);width=$width;sourceHandles=@($a.handle,$b.handle)}
}
function Connections($handles,$entities,$tol) {
 $links=@()
 for($i=0;$i -lt $handles.Count-1;$i++){
  $a=$entities[$handles[$i]];$b=$entities[$handles[$i+1]];$hits=@()
  foreach($p in $a.vertices){foreach($q in $b.vertices){if((Distance $p $q) -le $tol){$hits+=,[pscustomobject]@{point=(Mid $p $q);gap=(Distance $p $q)}}}}
  if($hits.Count -ne 1){throw "Ambiguous or disconnected chain: $($a.handle), $($b.handle)"}
  $links+=[pscustomobject]@{sourceHandles=@($a.handle,$b.handle);point=$hits[0].point;gap=$hits[0].gap}
 }
 ,$links
}
function Geometry($points,$handles,$config,$strategy) {
 $length=0.0;for($i=1;$i -lt $points.Count;$i++){$length+=Distance $points[$i-1] $points[$i]}
 [pscustomobject]@{strategy=$strategy;points=$points;sourceHandles=$handles;length=[pscustomobject]@{drawingUnits=$length;mm=$length*$config.units.mmPerDrawingUnit;m=$length*$config.units.mmPerDrawingUnit/1000}}
}
function Build-Samples($entities,$config) {
 $tol=[double]$config.tolerance
 if($tol -le 0 -or $config.units.mmPerDrawingUnit -le 0 -or $config.units.source -ne 'manual_calibration'){throw 'Explicit positive tolerance and manual unit calibration required'}
 $straight=Center-Pair $entities[$config.straight[0]] $entities[$config.straight[1]] $tol
 $inner=Connections $config.turn.innerChain $entities $tol
 $outer=Connections $config.turn.outerChain $entities $tol
 $h=Center-Pair $entities[$config.turn.horizontalPair[0]] $entities[$config.turn.horizontalPair[1]] $tol
 $v=Center-Pair $entities[$config.turn.verticalPair[0]] $entities[$config.turn.verticalPair[1]] $tol
 $a=$h.points[0];$b=$v.points[0];$u=Sub $h.points[1] $a;$w=Sub $v.points[1] $b
 if([math]::Abs((Dot $u $w)/((Distance $h.points[0] $h.points[1])*(Distance $v.points[0] $v.points[1]))) -gt 0.000001){throw 'Expected perpendicular turn'}
 if([math]::Abs($a[2]-$b[2]) -gt $tol){throw 'Turn elevations differ'}
 $det=$u[0]*$w[1]-$u[1]*$w[0];$delta=Sub $b $a
 $t=($delta[0]*$w[1]-$delta[1]*$w[0])/$det
 $node=@(0..2 | ForEach-Object {$a[$_]+$t*$u[$_]})
 $hs=@($h.points | Sort-Object {Distance $_ $node} -Descending)
 $vs=@($v.points | Sort-Object {Distance $_ $node} -Descending)
 # Copy sorted arrays to plain arrays (PowerShell pipeline wrappers affect JSON).
 $hs=@(@([double]$hs[0][0],[double]$hs[0][1],[double]$hs[0][2]),@([double]$hs[1][0],[double]$hs[1][1],[double]$hs[1][2]))
 $vs=@(@([double]$vs[0][0],[double]$vs[0][1],[double]$vs[0][2]),@([double]$vs[1][0],[double]$vs[1][1],[double]$vs[1][2]))
 $sources=@($config.turn.innerChain)+@($config.turn.outerChain)
 $topology=[pscustomobject]@{nodes=@(@{id='H';point=$hs[0]},@{id='N';point=$node;kind='logical_turn';sourceHandles=$sources},@{id='V';point=$vs[0]});edges=@(@{from='H';to='N';geometryId='turn-A'},@{from='N';to='V';geometryId='turn-A'});connectionBasis=$config.pairingSource}
 [pscustomobject]@{schemaVersion=1;units=$config.units;pairingSource=$config.pairingSource;tolerance=$tol;rawEntities=@($entities.Values | Sort-Object handle);straight=@{topology=@{nodes=@('S0','S1');edge=@{from='S0';to='S1';geometryId='straight'}};geometry=(Geometry $straight.points $config.straight $config 'straight');width=$straight.width};turn=@{supportedSegments=@($h,$v);connections=@{inner=$inner;outer=$outer};topology=$topology;geometry=(Geometry @($hs[0],$node,$vs[0]) $sources $config 'A-theoretical-90');geometryId='turn-A';unpairedContinuation='52905 beyond supported vertical overlap is excluded';status='derived_geometry_pending_review'}}
}
Export-ModuleMember -Function Read-SampleReport,Build-Samples
