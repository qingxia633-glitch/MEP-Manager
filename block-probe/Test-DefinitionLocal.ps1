$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'Test-Anchor.ps1')
$n=0
$method=Read-Function 'blp:coordinate-method'
foreach($case in @(
 @('TEXT',@(0,0,1),'identity_ocs_to_definition'),
 @('TEXT',@(0,1,0),'trans_normal_to_definition'),
 @('TEXT',$null,'missing_normal'),
 @('CIRCLE',@(0,0,1),'trans_normal_to_definition'),
 @('LINE',$null,'identity_definition_coordinates'),
 @('MTEXT',@(0,1,0),'identity_definition_coordinates'),
 @('ACAD_PROXY_ENTITY',@(0,0,1),'unsupported_coordinate_semantics')
)){
 Check ((Eval-Form $method[3] @{typ=$case[0];normal=$case[1]}) -eq $case[2]) "coordinate policy $($case[2])"
}
$frame=Read-Function 'blp:frame-status'
$outcome=Read-Function 'blp:transform-outcome'
$failure=Eval-Form $outcome[3] @{valid=$false;exception='bad argument type: enamep (original diagnostic)';result=$null}
Check ($failure[0] -eq 'coordinate_transform_error') 'transform exception status'
Check ($failure[2] -ceq 'bad argument type: enamep (original diagnostic)') 'exception returned verbatim'
Check (!$failure[1]) 'no coordinate fallback on exception'
$success=Eval-Form $outcome[3] @{valid=$true;exception=$false;result=@(10,20,30)}
Check ($success[0] -eq 'resolved' -and ($success[1] -join ',') -eq '10,20,30') 'successful transformed point preserved'
$invalid=Eval-Form $outcome[3] @{valid=$false;exception=$false;result=@(10,20)}
Check ($invalid[0] -eq 'invalid_transform_result' -and !$invalid[1]) 'invalid return rejected without fallback'
foreach($case in @(@($true,$false,'verified_definition_line_extents'),@($false,$false,'unverified_no_control_geometry'),@($true,$true,'coordinate_frame_mismatch'),@($false,$true,'coordinate_frame_mismatch'))){
 Check ((Eval-Form $frame[3] @{hasControls=$case[0];hasMismatch=$case[1]}) -eq $case[2]) 'frame gate'
}
$match=Read-Function 'blp:frame-bounds-match'
$wanted=@(@(10.0,20.0,0.0),@(30.0,40.0,0.0))
foreach($case in @(
 @{Actual=$wanted;Owner=$true;Expected=$true},
 @{Actual=@(@(10.000001,20.0,0.0),@(30.0,40.0,0.0));Owner=$true;Expected=$true},
 @{Actual=@(@(1010.0,20.0,0.0),@(1030.0,40.0,0.0));Owner=$true;Expected=$false},
 @{Actual=@(@(20.0,40.0,0.0),@(60.0,80.0,0.0));Owner=$true;Expected=$false},
 @{Actual=$wanted;Owner=$false;Expected=$false}
)){
 Check ((Eval-Form $match[3] @{wanted=$wanted;actual=$case.Actual;ownerOK=$case.Owner;tolerance=0.00001}) -eq $case.Expected) 'definition bounds match, translated/scaled/foreign-owner rejection'
}
foreach($key in @('DXF210_RAW','RawCoordinateSystem','AnchorPoint_DefinitionLocal','CoordinateResolutionMethod','CoordinateResolutionStatus','CoordinateException_RAW','CoordinateInput','Trans.FromType','Trans.FromValue','Trans.ToType','Trans.ToValue','Trans.Return_RAW','InstanceWCS','not_computed','BoundingBoxFrameStatus')){Check ($code.Contains($key)) "coordinate diagnostic $key"}
Check ($code.Contains("'trans (list input normal 0)")) 'explicit OCS normal conversion'
Check ($code.Contains('(vl-catch-all-error-message result)')) 'original exception retained'
Check ($code.Contains('(equal (blp:owner d) expected)')) 'frame witnesses belong to requested definition'
Check ($code.Contains('(blp:verify-frame block)')) 'frame check precedes filtering'
Check ($code.IndexOf('(blp:verify-frame block)') -lt $code.IndexOf('(initget 7)')) 'no window comparison before frame gate'
Check ($code -notmatch 'vla-get-BlockTransform|nentselp?\b') 'no instance WCS transform'
"PASS: $n DefinitionLocal policy/frame and diagnostics checks; AutoCAD runtime pending"
