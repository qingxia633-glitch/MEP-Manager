# Fire alarm logical membership (experimental)

`Read-AlarmMembership.ps1` composes the existing real local-network adapter with
six previously reviewed category mapping artifacts. Artifact hashes are pinned
in `tests/alarm-membership-sources.json`. This is composition of reviewed evidence,
not automatic extraction of new connections. Source category references are joined
by snapshot path and Handle, never by Handle alone.

`Join-LogicalNetworkMembership` accepts only the requested alarm region and
compartment. Category, representation and plan instance nodes remain distinct.
Membership is a separate `NetworkMembershipCandidate`, not a wiring edge.
Explicit and inherited role tiers survive, and actual loop membership stays
unresolved. The quantity is never used to choose members.

The source branch-to-bus edges retain their evidence. Unexpanded branch-to-device
associations remain unresolved and are not inserted into the admitted edge list.
Thus bus -> branch is supported while branch -> detector category is unresolved;
category -> reviewed spatial set is a partial logical membership. The diagram
does not become a complete connected graph merely because the spatial set exists.

DZX and isolator gaps remain, with `bridgeAllowed=false`. Cross-system interface
references are retained without importing phone or broadcast nodes. Existing
reviews (including other-system quantity mismatches) are carried as an unchanged
review ledger, not as members of the alarm graph. No Routing, Circuit, lengths,
installation heights, quantities or Requirement status changes are produced.

Run `pwsh -NoProfile -File model-core/tests/Test-AlarmMembership.ps1`, or the full
offline runner. `Read-AlarmMembership.ps1 -OutputPath ...` exports the traceable
candidate report. Unresolved category connections and non-membership candidate
nodes are reported rather than silently completed.
