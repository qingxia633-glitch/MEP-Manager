# Geometry support only; never returns a network edge or terminal identity.
function Get-GapBoundaryContact {
 param($Point,$Boundary,[double]$Tolerance=0.00001)
 if($Tolerance-le 0 -or [double]::IsNaN($Tolerance) -or [double]::IsInfinity($Tolerance)){throw 'Invalid tolerance'}
 $hits=@();$markers=@();$poly=@($Boundary.worldPolygon)
 foreach($p in @($Point)+@()){if([double]::IsNaN([double]$p)-or [double]::IsInfinity([double]$p)){throw 'Invalid point'}}
 if($Point.Count-ne 3 -or !$Boundary.closed -or $poly.Count-lt 3){throw 'Closed 3D boundary required'}
 for($i=0;$i-lt $poly.Count;$i++){
  $a=$poly[$i];$z=$poly[($i+1)%$poly.Count];$l2=0.;$dot=0.
  for($k=0;$k-lt 3;$k++){$d=[double]$z[$k]-[double]$a[$k];$l2+=$d*$d;$dot+=([double]$Point[$k]-[double]$a[$k])*$d}
  if($l2-eq 0){continue};$t=[math]::Max(0.0,[math]::Min(1.0,$dot/$l2));$d2=0.
  for($k=0;$k-lt 3;$k++){$d2+=[math]::Pow([double]$Point[$k]-($a[$k]+$t*($z[$k]-$a[$k])),2)}
  if($d2-le $Tolerance*$Tolerance){$hits+=,[pscustomobject]@{segmentIndex=$i;residual=[math]::Sqrt($d2)}}
 }
 foreach($marker in $Boundary.pointMarkers){$d2=0.;for($k=0;$k-lt 3;$k++){$d2+=[math]::Pow($Point[$k]-$marker.position[$k],2)};if($d2-le $Tolerance*$Tolerance){$markers+=@($marker.reference)}}
 [pscustomobject]@{status=if($hits.Count){'supported_candidate'}else{'unresolved'};geometryType=if($hits.Count){'touches_boundary'}else{'no_boundary_contact'};point=@($Point);coordinateFrame='WCS';tolerance=$Tolerance;boundarySegments=$hits;pointMarkerMatches=$markers;pointMeaning='unresolved';portRole='unresolved'}
}
