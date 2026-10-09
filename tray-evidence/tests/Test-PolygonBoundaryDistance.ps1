$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../SpatialRelations.psm1') -Force
Add-Type -Path (Join-Path $PSScriptRoot '../../design-knowledge/SheetGeometry.cs')
$script:n=0
function Check($ok,$message){if(!$ok){throw $message};$script:n++}
function Near($actual,$expected,$message){Check ([math]::Abs($actual-$expected) -lt 0.000002) $message}
# Reproduce the historical PowerShell overload error, not a C# geometry defect.
$legacyT=[Math]::Max(0,[Math]::Min(1,0.25))
Check ($legacyT -ne 0.25) 'Historical integer clamp reproduction'
$square=[double[][]]@(@(0,0),@(10,0),@(10,10),@(0,10))
Near (Get-PolygonBoundaryDistanceXY @(2.5,-2) $square) 2 'Interior perpendicular foot'
Near (Get-PolygonBoundaryDistanceXY @(-3,-4) $square) 5 'Projection outside segment clamps to vertex'
Near (Get-PolygonBoundaryDistanceXY @(13,14) $square) 5 'Projection beyond other endpoint'
Near (Get-PolygonBoundaryDistanceXY @(-2,5) $square) 2 'Closing edge included'
Near (Get-PolygonBoundaryDistanceXY @(0,0) $square) 0 'Vertex hit'
Near (Get-PolygonBoundaryDistanceXY @(5,0) $square) 0 'Segment hit'
Near (Get-PolygonBoundaryDistanceXY @(1,1) ([double[][]]@(@(0,0),@(0,0),@(10,0),@(0,10)))) 1 'Repeated vertex safe'
$concave=[double[][]]@(@(0,0),@(10,0),@(10,4),@(4,4),@(4,10),@(0,10))
Near (Get-PolygonBoundaryDistanceXY @(8,8) $concave) 4 'Real concave boundary not bounds'
$root=Join-Path $PSScriptRoot '../..'
$raw=[IO.File]::ReadAllText((Join-Path $root 'local_test_data/architecture-fire-compartment-zone1-block-probe-20260926/block-definition-probe.txt'))
$block=@([regex]::Split($raw,'(?m)^SourceInternalHandle=')|Where-Object {$_ -match '^"55DF5"'})[0]
$poly=[double[][]]@([regex]::Matches($block,'(?m)^DXF:10=\(([^)]+)\)')|ForEach-Object {
 $v=$_.Groups[1].Value -split '\s+'
 ,@(([double]$v[0]+555932139.9856748),([double]$v[1]+553155197.1740737),0.0)
})
Check ($poly.Count -eq 52) 'Real 52 vertices'
$expectedInside=@('13955','13962','13974','1397C','13984','1398C','13994','1399C','139A4','139AC')
$expectedDistances=@{'13974'=100.152895;'139B4'=150.006002;'139CC'=150.031224;'139C4'=2850.006000;'13A4B'=3304.591668;'13A2B'=5449.165052;'13955'=4256.588567;'13962'=5250.006005;'1397C'=7142.168122;'13984'=13173.810405;'1398C'=4100.207127;'13994'=1389.589111;'1399C'=10749.351176;'139A4'=7949.053466;'139AC'=5168.416592}
$raw=[IO.File]::ReadAllText((Join-Path $root 'local_test_data/fire-alarm-full-snapshot-20260923/MEP-full-entity-report.txt'))
$count=0;$inside=0
foreach($b in [regex]::Split($raw,'(?m)^EntityHandle=')){
 if($b -notmatch '^"([^"]+)"'){continue};$h=$Matches[1]
 if($b -notmatch '(?m)^DXF_Type="INSERT"' -or $b -notmatch 'AttributeText_RAW="带火警电话插孔的手动报警按钮"'){continue}
 $m=[regex]::Match($b,'(?m)^Insertion_WCS=\(([^)]+)\)');$v=$m.Groups[1].Value -split '\s+'
 $p=[double[]]@([double]$v[0],[double]$v[1],0.0) # Explicit plan XY, not storey inference.
 $before=[MepSheet.Geometry]::Point($poly,$p,0.001)
 $distance=Get-PolygonBoundaryDistanceXY $p $poly
 $after=[MepSheet.Geometry]::Point($poly,$p,0.001)
 Check ($before -eq $after) "$h classifier unchanged"
 Check ($after -eq $(if($h -in $expectedInside){1}else{-1})) "$h frozen membership"
 Check ($distance -gt 0.001) "$h not on boundary"
 if($expectedDistances.ContainsKey($h)){Near $distance $expectedDistances[$h] "$h real distance"}
 if($after -eq 1){$inside++};$count++
}
Check ($count -eq 74 -and $inside -eq 10) '74 classifications: 10 inside / 64 outside'
Write-Output "PASS polygon boundary distance: $script:n checks; 13974=100.152895; 139B4=150.006002; 74 classifications unchanged"
