Set-StrictMode -Version Latest
if(-not ('Mep.Spatial.Polygon' -as [type])){Add-Type -Path (Join-Path $PSScriptRoot 'SpatialRelations.cs')}
function Get-UnitSpatialRelations {
 param([Parameter(Mandatory)][double[]]$Point,[Parameter(Mandatory)]$Geometry,[double]$Tolerance=0.001)
 if($Tolerance -le 0 -or [double]::IsNaN($Tolerance) -or [double]::IsInfinity($Tolerance)){throw 'Invalid spatial tolerance'}
 foreach($u in $Geometry.units){
  $unsupportedHoles=$u.PSObject.Properties.Name -contains 'holes' -and @($u.holes).Count -gt 0
  $relation=if($unsupportedHoles){'unknown'}else{[Mep.Spatial.Polygon]::Classify($Point,[double[][]]$u.vertices,($u.closure -eq 'closed'),$Tolerance)}
  [pscustomobject]@{unitId=$u.id;relation=$relation;tolerance=$Tolerance;point=@($Point);
   reason=if($relation -eq 'unknown'){'open, invalid, noncoplanar or unsupported contour; no interior/outside assertion'}else{'validated contour/observed boundary test'};
   sourceHandles=@($u.sourceHandles);contourId=$u.contourId}
 }
}
function Get-PolygonBoundaryDistanceXY {
 param([Parameter(Mandatory)][double[]]$Point,[Parameter(Mandatory)][double[][]]$Vertices)
 # Explicit XY distance to a closed, straight-edged ring. Does not classify membership.
 if($Vertices.Count -lt 3){throw 'A polygon requires at least three vertices'}
 if($Point.Count -lt 2){throw 'Point requires XY'}
 foreach($coordinate in $Point){if([double]::IsNaN($coordinate) -or [double]::IsInfinity($coordinate)){throw 'Nonfinite point'}}
 foreach($v in $Vertices){
  if($v.Count -lt 2 -or [double]::IsNaN($v[0]) -or [double]::IsNaN($v[1]) -or [double]::IsInfinity($v[0]) -or [double]::IsInfinity($v[1])){throw 'Invalid polygon vertex'}
 }
 $p3=[double[]]@($Point[0],$Point[1],0.0)
 $minimum=[double]::PositiveInfinity
 for($i=0;$i -lt $Vertices.Count;$i++){
  $a=$Vertices[$i];$b=$Vertices[($i+1)%$Vertices.Count]
  # C# uses double arithmetic for the clamped projection; PowerShell integer overloads are avoided.
  $d=[Mep.Spatial.Polygon]::SegmentDistance($p3,[double[]]@($a[0],$a[1],0.0),[double[]]@($b[0],$b[1],0.0))
  if($d -lt $minimum){$minimum=$d}
 }
 return $minimum
}
Export-ModuleMember -Function Get-UnitSpatialRelations,Get-PolygonBoundaryDistanceXY
