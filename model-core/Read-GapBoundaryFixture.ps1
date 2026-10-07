# Source selection is confined to the manifest. No CAD calls or recursive expansion.
function Read-GapBoundaryFixture {
 param($Root,$Spec,$TopRecord)
 $path=Join-Path $Root $Spec.path
 if((Get-FileHash $path).Hash-cne $Spec.sha256){throw 'Boundary probe hash mismatch'}
 $s=[IO.File]::ReadAllText($path)
 function F($r,$k){[regex]::Match($r,'(?m)^'+[regex]::Escape($k)+'=(.*?)\r?$').Groups[1].Value.Trim('"')}
 function P($r,$k){,@([regex]::Matches($r,'(?m)^'+[regex]::Escape($k)+'=\(([^)]+)\)')|ForEach-Object {,@($_.Groups[1].Value.Split(' ')|ForEach-Object {[double]::Parse($_,[cultureinfo]::InvariantCulture)})})}
 if($s-notmatch '(?m)^END_OF_REPORT' -or (F $s Block_BEGIN)-cne (F $TopRecord BlockName)){throw 'Boundary definition mismatch'}
 if((F $TopRecord Normal_DXF210)-ne '(0.000000 0.000000 1.000000)'){throw 'Unsupported instance normal'}
 $base=(P $s 'DefinitionDXF:10')[0];$ins=(P $TopRecord Insertion_WCS)[0]
 $scale=@(41..43|ForEach-Object {[double]::Parse([regex]::Match($TopRecord,'BlockTransform_or_Array_DXF=\('+$_+' \. ([^)]+)').Groups[1].Value,[cultureinfo]::InvariantCulture)})
 $angle=[double]::Parse([regex]::Match($TopRecord,'BlockTransform_or_Array_DXF=\(50 \. ([^)]+)').Groups[1].Value,[cultureinfo]::InvariantCulture)
 function World($p){$x=($p[0]-$base[0])*$scale[0];$y=($p[1]-$base[1])*$scale[1];$z=if($p.Count-ge 3){$p[2]}else{0};,@(($ins[0]+$x*[math]::Cos($angle)-$y*[math]::Sin($angle)),($ins[1]+$x*[math]::Sin($angle)+$y*[math]::Cos($angle)),($ins[2]+($z-$base[2])*$scale[2]))}
 $references=@();$markers=@();$poly=@();$bboxErrors=@();$nameRefs=@()
 foreach($m in [regex]::Matches($s,'(?ms)^SourceDefinitionPath=.*?^Entity_END\r?$')){
  $r=$m.Value;$h=F $r EntityHandle;if(!$h){continue};$type=F $r DXF_Type;$id=$Spec.sha256+':'+$h
  $references+=,[pscustomobject]@{id=$id;resolved=$true;sourceSnapshot=$Spec.sha256;sourcePath=$Spec.path;sourceDocument=(F $s DWG);handle=$h;entityType=$type;definitionName=(F $s Block_BEGIN);sourceSpan=[pscustomobject]@{offset=$m.Index;length=$m.Length;unit='utf16_code_units'}}
  if($r-match 'BoundsError='){$bboxErrors+=@($h)}
  if($h-ceq $Spec.boundaryHandle){
   $vertices=P $r 'DXF:10'
   if($type-ne 'LWPOLYLINE' -or (F $r Closed_RAW)-ne 'T' -or (F $r 'DXF:210')-ne '(0.000000000000 0.000000000000 1.000000000000)' -or $vertices.Count-ne 4){throw 'Unsupported boundary'}
   foreach($bulge in [regex]::Matches($r,'(?m)^DXF:42=(.*)$')){if([double]::Parse($bulge.Groups[1].Value,[cultureinfo]::InvariantCulture)-ne 0){throw 'Curved boundary unsupported'}}
   $poly=@($vertices|ForEach-Object {World $_})
  }
  if($type-eq 'POINT'){$markers+=,[pscustomobject]@{reference=$id;position=(World (P $r 'DXF:10')[0]);meaning='unresolved'}}
  if($type-eq 'ATTDEF'){$nameRefs+=@($id)}
 }
 if($poly.Count-ne 4 -or $references.Count-ne [int](F $s DirectEntityCount)){throw 'Incomplete boundary evidence'}
 [pscustomobject]@{objectHandle=$Spec.object;closed=$true;worldPolygon=$poly;pointMarkers=$markers;roleCandidate=$Spec.reviewedRole;roleBasis='reviewed name/code plus independently computed boundary contacts';nameRefs=$nameRefs;evidenceRefs=@($references.id);references=$references;definitionRead=$true;readErrorCount=[int](F $s ReadErrorCount);bboxUnavailableRefs=$bboxErrors;transform=[pscustomobject]@{insertion=$ins;scale=$scale;rotation=$angle;normal=@(0,0,1);basePoint=$base};internalContinuity='unresolved'}
}
