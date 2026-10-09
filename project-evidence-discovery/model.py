"""Deterministic evidence identities; no probability or approval fields."""
import hashlib,json
def identity(*parts):
 return hashlib.sha256(json.dumps(parts,ensure_ascii=False,sort_keys=True).encode('utf-8')).hexdigest()[:24]
EXPORTER_FIELDS=['annotation handle and owner path','leader to annotation handle association',
 'leader type and all WCS vertices','arrowhead presence and explicit arrow endpoint WCS',
 'landing WCS and MLeader branch ids','OCS normal and complete parent transform chain',
 'object attachment references','scope boundary handles and termination evidence']
