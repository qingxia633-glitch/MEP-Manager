Set-StrictMode -Version Latest
if(-not ('Mep.LocalUnits.Recognizer' -as [type])){Add-Type -Path (Join-Path $PSScriptRoot 'UnitGeometry.cs')}

function Read-LocalEntities {
 [CmdletBinding()]
 param([Parameter(Mandatory)][string]$Report,[Parameter(Mandatory)][string[]]$Handles)
 $raw=Get-Content -LiteralPath $Report -Raw -Encoding UTF8
 if($raw -notmatch '(?m)^END_OF_REPORT:'){throw 'Incomplete report'}
 if(@($Handles | Select-Object -Unique).Count -ne $Handles.Count){throw 'Duplicate selection handles'}
 $hash=(Get-FileHash -LiteralPath $Report -Algorithm SHA256).Hash
 $drawing=[regex]::Match($raw,'(?m)^DWG=(.*)').Groups[1].Value.Trim()
 foreach($h in $Handles){
  $matches=[regex]::Matches($raw,'(?ms)^EntityHandle="'+[regex]::Escape($h)+'"\r?\n(.*?)(?=^EntityHandle=|^LayerEntityCount=|\z)')
  if($matches.Count -ne 1){throw "Missing or nonunique entity: $h"}
  $body=$matches[0].Groups[1].Value
  if($body -match 'ERROR|UNREADABLE'){throw "Read error: $h"}
  $type=[regex]::Match($body,'(?m)^DXF_Type="([^"]+)"').Groups[1].Value
  $points=@(foreach($m in [regex]::Matches($body,'(?m)^(?:Vertex|Start|End)_WCS=\(([^)]+)\)')){
   ,@($m.Groups[1].Value.Split(' ') | ForEach-Object {[double]::Parse($_,[cultureinfo]::InvariantCulture)})
  })
  $bulges=@(foreach($m in [regex]::Matches($body,'Width_or_bulge_DXF=\(42 \. ([^)]+)\)')){[double]::Parse($m.Groups[1].Value,[cultureinfo]::InvariantCulture)})
  $closed=$body -match '(?m)^Closed=T\s*$'
  [pscustomobject]@{handle=$h;entityKey="$hash/$h";drawing=$drawing;reportSHA256=$hash;
   reportLine=1+([regex]::Matches($raw.Substring(0,$matches[0].Index),'\n').Count);
   type=$type;layer=[regex]::Match($body,'(?m)^Layer="([^"]+)"').Groups[1].Value;
   vertices=$points;bulges=$bulges;closed=$closed;rawRecord=$matches[0].Value;readStatus='read';
   units='drawing_units';colorStatus='not_exported'}
 }
}

function Get-LocalTrayUnits {
 [CmdletBinding()]
 param([Parameter(Mandatory)][object[]]$RawEntities,[double]$Tolerance=0.00001,[double]$AngularToleranceRadians=0.000001)
 $inputEdges=New-Object 'System.Collections.Generic.List[Mep.LocalUnits.InputEdge]'
 foreach($e in $RawEntities){
  if($e.type -notin @('LINE','LWPOLYLINE') -or $e.closed -or $e.vertices.Count -ne 2){throw "Unsupported local geometry: $($e.handle)"}
  if($e.type -eq 'LWPOLYLINE' -and ($e.bulges.Count -ne 2 -or @($e.bulges | Where-Object {$_ -ne 0}).Count -gt 0)){throw "Unverified or curved polyline: $($e.handle)"}
  $edge=New-Object Mep.LocalUnits.InputEdge
  $edge.handle=$e.handle;$edge.vertices=[double[][]]$e.vertices;$inputEdges.Add($edge)
 }
 $r=[Mep.LocalUnits.Recognizer]::Build($inputEdges.ToArray(),$Tolerance,[math]::Sin($AngularToleranceRadians))
 [pscustomobject]@{schemaVersion=1;scope='caller-supplied local straight-segment sample';
  tolerance=$Tolerance;angularToleranceRadians=$AngularToleranceRadians;unitsOfMeasure='drawing_units';
  rawEntities=$RawEntities;geometryEdges=$r.geometryEdges;contours=$r.contours;units=$r.units;interfaces=$r.interfaces;
  unassignedEdgeIds=$r.unassignedEdgeIds;diagnostics=$r.diagnostics;
  limitations=@('XY coplanar straight segments only','No interior intersection or partial overlap splitting',
   'Partial straights require one observed edge per side','No semantic tray identity, annotation, color, type or center path inference')}
}
Export-ModuleMember -Function Read-LocalEntities,Get-LocalTrayUnits
