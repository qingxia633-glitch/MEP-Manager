$ErrorActionPreference='Stop'
$root=Resolve-Path (Join-Path $PSScriptRoot '../..')
$tests=@(
 'model-core/tests/Test-RoutePath.ps1',
 'model-core/tests/Test-PlanLogicalRelation.ps1',
 'model-core/tests/Test-VisualContinuity.ps1',
 'model-core/tests/Test-RoutingCorrespondence.ps1',
 'model-core/tests/Test-DeviceAttachment.ps1',
 'model-core/tests/Test-AlarmRouting.ps1',
 'model-core/tests/Test-AlarmMembership.ps1',
 'design-knowledge/tests/Test-FunctionalControl.ps1',
 'design-knowledge/tests/Test-LegendSemantics.ps1',
 'model-core/tests/Test-RoleInheritance.ps1',
 'model-core/tests/Test-CategoryMapping.ps1',
 'tray-evidence/tests/Test-PolygonBoundaryDistance.ps1',
 'model-core/tests/Test-LocalLogicalNetwork.ps1',
 'design-knowledge/tests/Test-RelationChainAdmission.ps1',
 'design-knowledge/tests/Test-RoleEvidenceAdmission.ps1',
 'design-knowledge/tests/Test-DocumentTargets.ps1',
 'design-knowledge/tests/Test-SystemScopePropagation.ps1',
 'design-knowledge/tests/Test-InvestigationAdapter.ps1',
 'design-knowledge/tests/Test-EvidenceAdmission.ps1',
 'design-knowledge/tests/Test-StatementBridge.ps1',
 'design-knowledge/tests/Test-HierarchyBridge.ps1',
 'design-knowledge/tests/Test-Coverage.ps1',
 'design-knowledge/tests/Test-SheetScope.ps1',
 'design-knowledge/tests/Test-LayoutReader.ps1',
 'design-knowledge/tests/Test-BBoxContinuity.ps1',
 'design-knowledge/tests/Test-Hierarchy.ps1',
 'design-knowledge/tests/Test-Reader.ps1',
 'design-knowledge/tests/Test-DesignStatements.ps1',
 'design-knowledge/tests/Test-DesignKnowledge.ps1',
 'model-core/tests/Test-Model.ps1',
 'model-core/tests/Test-SystemIsolation.ps1',
 'Test-Acquisition.ps1',
 'Test-TextLayoutMetadata.ps1',
 'block-text-index/tests/Test-BlockTextIndex.ps1',
 'block-probe/Test-Anchor.ps1',
 'block-probe/Test-DefinitionLocal.ps1',
 'block-probe/Test-LocalProbe.ps1',
 'block-probe/Test-ParentPath.ps1',
 'block-probe/Test-OneLevel.ps1',
 'block-probe/Test-Probe.ps1',
 'block-probe/Test-RealProbe.ps1',
 'geometry-units/tests/Test-Units.ps1',
 'tray-evidence/tests/Test-Evidence.ps1',
 'view-context/tests/Test-Context.ps1',
 'prototype/Test-Prototype.ps1',
 'prototype/Test-Discovery.ps1',
 'system-diagram/tests/Test-Diagram.ps1',
 'system-diagram/tests/Test-Fields.ps1',
 'system-diagram/tests/Test-PanelConfiguration.ps1',
 'system-diagram/tests/Test-OutgoingRows.ps1',
 'drainage/tests/Test-Pit.ps1'
)
# The legacy discovery test writes this historical artifact. Restore exact bytes.
$artifact=Join-Path $root 'local_test_data/discovery-result.json'
$existed=Test-Path -LiteralPath $artifact
$before=if($existed){[IO.File]::ReadAllBytes($artifact)}else{$null}
Push-Location $root
try {
 foreach($test in $tests){
  Write-Host "RUN $test"
  & pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root $test)
  if($LASTEXITCODE -ne 0){throw "Regression failed: $test"}
 }
 Write-Host "PASS: $($tests.Count) offline test suites; no AutoCAD invoked"
} finally {
 if($existed){[IO.File]::WriteAllBytes($artifact,$before)}
 elseif(Test-Path -LiteralPath $artifact){Remove-Item -LiteralPath $artifact}
 Pop-Location
}
