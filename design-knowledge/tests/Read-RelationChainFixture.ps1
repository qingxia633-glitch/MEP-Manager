. (Join-Path $PSScriptRoot 'Read-RoleFixture.ps1')
function Read-RelationChainFixture {
 $root=Resolve-Path (Join-Path $PSScriptRoot '../..')
 $m=Get-Content (Join-Path $PSScriptRoot 'relation-chain-sample.json') -Raw -Encoding UTF8|ConvertFrom-Json
 $b=Read-RoleAdmissionFixture;$role=Get-RoleEvidenceAdmission $b
 $file=Join-Path $root $m.source.path
 if((Get-FileHash $file).Hash-cne $m.source.sha256){throw 'Speaker source changed'}
 $s=[IO.File]::ReadAllText($file)
 if($s-notmatch '(?m)^END_OF_REPORT'){throw 'Incomplete speaker probe'}
 function Field($s,$k){[regex]::Match($s,'(?m)^'+[regex]::Escape($k)+'=(.*?)\r?$').Groups[1].Value.Trim('"')}
 function Record($s,$h){[regex]::Match($s,'(?ms)^EntityHandle="'+[regex]::Escape($h)+'".*?(?=^EntityHandle=|^Entity_END|\z)').Value}
 function Points($s,$k){,@([regex]::Matches($s,'(?m)^'+[regex]::Escape($k)+'=\(([^)]+)\)')|ForEach-Object {,@($_.Groups[1].Value.Split(' ')|ForEach-Object {[double]::Parse($_,[cultureinfo]::InvariantCulture)})})}
 $raw=@{}
 foreach($p in $m.references.PSObject.Properties){
  $record=Record $s $p.Value;if(!$record){throw 'Missing speaker reference'};$raw[$p.Name]=$record
  $b.references|Add-Member $p.Name ([pscustomobject]@{resolved=$true;handle=$p.Value;sourceSnapshot=$m.source.sha256;sourcePath=$m.source.path;sourceDocument=(Field $s DWG);definitionName=(Field $s Block_BEGIN)})
 }
 $top=[IO.File]::ReadAllText((Join-Path $root $b.references.speaker.sourcePath))
 $speaker=Record $top $b.references.speaker.handle;$line=Record $top $b.references.lowerLine.handle
 if((Field $speaker BlockName)-cne (Field $s Block_BEGIN)){throw 'Speaker definition mismatch'}
 if((Field $speaker Normal_DXF210)-ne '(0.000000 0.000000 1.000000)' -or (Field $raw.speakerBoundary 'DXF:210')-ne '(0.000000000000 0.000000000000 1.000000000000)'){throw 'Unsupported fixture normal'}
 $base=(Points $s 'DefinitionDXF:10')[0]
 $ins=(Points $speaker Insertion_WCS)[0];$center=(Points $raw.speakerBoundary 'DXF:10')[0]
 $scale=@(41..43|ForEach-Object {[double]::Parse([regex]::Match($speaker,'BlockTransform_or_Array_DXF=\('+$_+' \. ([^)]+)').Groups[1].Value,[cultureinfo]::InvariantCulture)})
 $angle=[double]::Parse([regex]::Match($speaker,'BlockTransform_or_Array_DXF=\(50 \. ([^)]+)').Groups[1].Value,[cultureinfo]::InvariantCulture)
 if($scale[0]-le 0 -or $scale[0]-ne $scale[1] -or (Field $raw.speakerBoundary 'DXF_Type')-ne 'CIRCLE'){throw 'Unsupported circle transform'}
 $lx=($center[0]-$base[0])*$scale[0];$ly=($center[1]-$base[1])*$scale[1]
 $cx=$ins[0]+$lx*[math]::Cos($angle)-$ly*[math]::Sin($angle);$cy=$ins[1]+$lx*[math]::Sin($angle)+$ly*[math]::Cos($angle)
 $radius=[double]::Parse((Field $raw.speakerBoundary 'DXF:40'),[cultureinfo]::InvariantCulture)*$scale[0]
 $pts=Points $line Vertex_WCS
 if($pts.Count-ne 2 -or $line-notmatch 'Width_or_bulge_DXF=\(42 \. 0.000000\)'){throw 'Fixture must be straight segment'}
 # Segment/circle intersection, not proximity to insertion point.
 $dx=$pts[1][0]-$pts[0][0];$dy=$pts[1][1]-$pts[0][1];$fx=$pts[0][0]-$cx;$fy=$pts[0][1]-$cy
 $aa=$dx*$dx+$dy*$dy;$bb=2*($fx*$dx+$fy*$dy);$cc=$fx*$fx+$fy*$fy-$radius*$radius
 $disc=$bb*$bb-4*$aa*$cc;$hits=@()
 if($aa-gt 0 -and $disc-ge 0){foreach($t in @(((-$bb-[math]::Sqrt($disc))/(2*$aa)),((-$bb+[math]::Sqrt($disc))/(2*$aa)))){if($t-ge 0 -and $t-le 1){$hits+=,@(($pts[0][0]+$t*$dx),($pts[0][1]+$t*$dy))}}}
 $inside=([math]::Pow($pts[1][0]-$cx,2)+[math]::Pow($pts[1][1]-$cy,2))-lt ($radius*$radius)
 $refs=@('speaker','lowerLine','speakerBoundary')
 $contactA=@($role.lineRelations|Where-Object fromRef -CEQ $m.pathRepresentation)[0]
 $contacts=@(
  [pscustomobject]@{fromRef=$m.pathRepresentation;toRef=$m.endpointA;geometryType='crosses_boundary';status=$contactA.status;sourceRefs=$contactA.sourceRefs},
  [pscustomobject]@{fromRef=$m.pathRepresentation;toRef=$m.endpointB;geometryType='crosses_boundary';status=if($hits.Count-eq 1 -and $inside){'supported'}else{'unresolved'};sourceRefs=$refs}
 )
 [pscustomobject]@{
  chainId='reviewed-local-relation-chain';scopeId=$b.scopeId;endpointA=$m.endpointA;pathRepresentation=$m.pathRepresentation;endpointB=$m.endpointB;references=$b.references
  contacts=$contacts;context=$m.reviewedContext
  endpointRoles=@(
   [pscustomobject]@{subjectRef=$m.endpointA;roleCandidate=$role.deviceRole.roleCandidate;status=$role.deviceRole.status;systemScopeCandidate=$m.reviewedContext.systemScopeCandidate;sourceRefs=$role.deviceRole.sourceRefs},
   [pscustomobject]@{subjectRef=$m.endpointB;roleCandidate=(Field $raw.speakerName 'DXF:1');status='candidate';systemScopeCandidate=$m.reviewedContext.systemScopeCandidate;sourceRefs=@('speaker','speakerName')}
  )
  reviewItems=$role.reviewItems;requirements=$b.requirements
  geometryAudit=[pscustomobject]@{center=@($cx,$cy);radius=$radius;intersections=$hits;endsInside=$inside;sourceRefs=$refs}
 }
}
