"""New project validation artifacts only. Frozen inputs are read-only."""
import json
from test_builder import ROOT, plan, synthetic, frozen
from builder import build, replay_validate, seal

def write(name,value):
    path=ROOT/'outputs/design-net-quantity-builder-v01'/name
    with path.open('x',encoding='utf-8') as f: json.dump(value,f,ensure_ascii=False,indent=2)

def main():
    replay={}
    for kind in ('conduit','wire'):
        source=frozen(kind)
        write(f'frozen-{kind}-adapter.json',source)
        replay[kind]=replay_validate(plan(kind),source)
        assert replay[kind]['status']=='replay_matched'
    write('golden-replay-results.json',replay)
    built={str(m):build(synthetic(m),[]) for m in (1,2)}
    built['mm_to_m']=build(synthetic(unit='mm'),[])
    assert all(r['status']=='built' for r in built.values())
    write('synthetic-build-results.json',built)
    blocked={}
    for edge in ('13CF0','13CE8','13CE9','14147'):
        p=plan();p['binding']['edge_handle']=edge;p['quantity_eligibility_status']='blocked';seal(p)
        blocked[edge]=build(p,[])
        assert blocked[edge]['status']=='blocked'
    write('blocked-results.json',blocked)
    write('duplicate-result.json',build(plan(),[frozen('conduit')]))

if __name__=='__main__':main()
