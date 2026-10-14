"""Raw style evidence only. Never consumed by discovery admission."""
import json
import math
import re

EXPORTER = '2.5-line-style-evidence-v1'
ENTITY = ('entity_color_mode entity_aci entity_truecolor_rgb entity_colorbook_name '
          'entity_linetype entity_linetype_mode entity_linetype_scale '
          'entity_lineweight entity_lineweight_mode entity_visibility').split()
LAYER = ('layer_name layer_color_mode layer_aci layer_truecolor_rgb layer_colorbook_name '
         'layer_linetype layer_lineweight layer_on layer_frozen layer_locked '
         'layer_plottable layer_transparency').split()


def values(text, key):
    return [x.strip() for x in re.findall(r'^'+re.escape(key)+r'=(.*?)\r?$',text,re.M)]


def one(text, key):
    v=values(text,key)
    return v[0].strip('"') if len(v)==1 else None


def item(status='missing', value=None, source=None, reason=None):
    return dict(status=status,value=value,source=source,reason=reason)


def valid(key,value):
    if key.endswith('truecolor_rgb'):
        return isinstance(value,list) and len(value)==3 and all(type(v)==int and 0<=v<=255 for v in value)
    if key in ('entity_visibility','layer_on','layer_frozen','layer_locked','layer_plottable'):
        return type(value)==bool
    if key.endswith('color_mode'):
        return value in ('explicit_aci','explicit_truecolor','colorbook','ByLayer','ByBlock')
    if key.endswith('linetype_mode'):return value in ('explicit','ByLayer','ByBlock')
    if key.endswith('lineweight_mode'):return value in ('explicit','ByLayer','ByBlock','default')
    if key.endswith('_aci'):return type(value)==int and 0<=value<=256
    if key.endswith('lineweight'):return type(value)==int and -3<=value<=211
    if key.endswith('linetype_scale'):return type(value) in (float,int) and math.isfinite(value) and value>0
    return isinstance(value,str) and bool(value.strip())


def read_field(rec,key):
    prefix='Style.'+key
    status=one(rec,prefix+'.Status');source=one(rec,prefix+'.Source')
    if status is None:
        return item('unavailable' if values(rec,prefix+'.Status') else 'missing',reason='absent or duplicate status')
    if status not in ('read','missing','unavailable','unsupported'):return item('unavailable',reason='invalid status')
    if status!='read':return item(status,source=source)
    vals=values(rec,prefix+'.Value')
    if len(vals)!=1 or not source:return item('unavailable',reason='missing/duplicate value or source')
    try:
        raw=vals[0]
        # Exporter uses native LISP lists for RGB, JSON-compatible scalar strings/numbers.
        value=[int(x) for x in raw.strip('()').split()] if raw.startswith('(') else json.loads(raw)
        if value in ('true','false') and key in ('entity_visibility','layer_on','layer_frozen','layer_locked','layer_plottable'):
            value=value=='true'
        if not valid(key,value):raise ValueError('invalid value')
    except (ValueError,TypeError):return item('unavailable',source=source,reason='invalid value')
    return item('read',value,source)


def number(raw,source):
    if raw in (None,'nil'):return item()
    try:
        v=float(raw)
        if not math.isfinite(v) or v<0:raise ValueError()
        return item('read',v,source)
    except ValueError:return item('unavailable',source=source,reason='invalid width')


def polyline(rec,typ):
    if typ not in ('POLYLINE','LWPOLYLINE'):return None
    # Old POLYLINE exporter defaulted missing flags to zero: do not bless that fallback.
    flags=one(rec,'StylePolylineFlags') if typ=='POLYLINE' else one(rec,'Flags_DXF70')
    f=item();gen=item()
    if flags and flags.isdecimal():
        n=int(flags);f=item('read',n,'object DXF:70')
        gen=item('unsupported',source='object DXF:70',reason='3D/mesh/polyface') if typ=='POLYLINE' and n&88 else item('read','continuous_through_vertices' if n&128 else 'restart_at_each_segment','object DXF:70 bit128')
    widths=re.findall(r'Width_or_bulge_DXF=\(43 \. ([^)]+)\)',rec)
    constant=number(widths[0] if len(widths)==1 else None,'DXF:43') if typ=='LWPOLYLINE' else item('unsupported',reason='old POLYLINE has header default widths, not constant-width field')
    vertices=[]
    if typ=='LWPOLYLINE':
        for chunk in re.split(r'(?m)(?=^Vertex_OCS=)',rec)[1:]:
            get=lambda c:re.findall(r'Width_or_bulge_DXF=\('+str(c)+r' \. ([^)]+)\)',chunk)
            a,b=get(40),get(41)
            vertices.append({'vertex_index':len(vertices),'vertex_start_width':number(a[0] if len(a)==1 else None,'vertex DXF:40'),'vertex_end_width':number(b[0] if len(b)==1 else None,'vertex DXF:41')})
    else:
        for raw in values(rec,'Subentity_DXF'):
            if '(0 . "VERTEX")' not in raw:continue
            def get(c):
                m=re.search(r'\('+str(c)+r' \. ([^)]+)\)',raw);return m[1] if m else None
            vertices.append({'vertex_index':len(vertices),'raw_vertex_dxf':raw,'vertex_start_width':number(get(40),'vertex DXF:40'),'vertex_end_width':number(get(41),'vertex DXF:41')})
    return {'constant_width':constant,'vertices':vertices,'polyline_flags':f,'linetype_generation_mode':gen,
            'default_start_width':number(one(rec,'StylePolylineDefaultStartWidth'),'header DXF:40'),
            'default_end_width':number(one(rec,'StylePolylineDefaultEndWidth'),'header DXF:41')}


def style_evidence(rec,header,identity,provenance):
    version=one(rec,'StyleEvidenceVersion');exporter=one(header,'ExtractorVersion')
    supported=version=='1' and exporter==EXPORTER
    status='unsupported' if version is not None else 'missing'
    entity={k:read_field(rec,k) if supported else item(status) for k in ENTITY}
    layer={k:read_field(rec,k) if supported else item(status) for k in LAYER}
    layer_name=one(rec,'Layer');layer_handle=one(rec,'StyleLayerHandle') if supported else None
    layer_ok=bool(layer_handle and re.fullmatch('[0-9A-Fa-f]+',layer_handle) and layer['layer_name']['status']=='read' and layer['layer_name']['value']==layer_name)
    resolution={}
    def read(d,k):return d[k]['value'] if d[k]['status']=='read' else None
    for prop,key,raw in [('color','entity_color_mode',None),('linetype','entity_linetype_mode','entity_linetype'),('lineweight','entity_lineweight_mode','entity_lineweight')]:
        mode=read(entity,key);hint='unresolved'
        if mode=='ByBlock':hint='unresolved_byblock'
        elif identity['parent_path']!=[]:hint='unresolved'
        elif mode=='ByLayer' and layer_ok and layer_name!='0':
            lk='layer_'+prop
            complete=(read(layer,'layer_color_mode')=='explicit_aci' and read(layer,'layer_aci') is not None or read(layer,'layer_color_mode')=='explicit_truecolor' and read(layer,'layer_truecolor_rgb') is not None) if prop=='color' else read(layer,lk) is not None
            if prop=='linetype':complete=complete and read(layer,lk).upper() not in ('BYLAYER','BYBLOCK')
            if prop=='lineweight':complete=complete and read(layer,lk)>=0
            if prop=='color' and read(layer,'layer_color_mode')=='explicit_aci':complete=complete and 1<=read(layer,'layer_aci')<=255
            if complete:hint='bylayer_candidate'
        elif mode and mode.startswith('explicit'):
            rk={'explicit_aci':'entity_aci','explicit_truecolor':'entity_truecolor_rgb'}.get(mode,raw)
            if rk and read(entity,rk) is not None:
                v=read(entity,rk)
                coherent=(1<=v<=255) if mode=='explicit_aci' else (v>=0 if prop=='lineweight' else v.upper() not in ('BYLAYER','BYBLOCK') if prop=='linetype' else True)
                if coherent:hint='direct'
        if one(rec,'StyleAcquisitionStatus')=='unavailable':hint='unresolved'
        resolution[prop]=hint
    typ=one(rec,'DXF_Type');cls=one(rec,'ObjectName')
    standard={'LINE','LWPOLYLINE','POLYLINE','ARC','SPLINE','MLINE','TEXT','MTEXT','INSERT','CIRCLE','ATTDEF','POINT','HATCH','ELLIPSE','ACAD_TABLE','OLE2FRAME','LEADER','MLEADER','MULTILEADER','DIMENSION'}
    proxy=typ=='ACAD_PROXY_ENTITY' or cls in ('AcDbZombieEntity','AcDbProxyEntity')
    custom=bool(typ not in standard and not proxy)
    return {'contract_version':version,'contract_status':'read' if supported else status,'identity':identity,
            'acquisition_status':one(rec,'StyleAcquisitionStatus') or 'missing','entity_type':typ,'entity_class':cls,'raw_entity_style':entity,
            'raw_entity_dxf':values(rec,'StyleRawEntityDXF'),
            'layer_raw_style':{'layer_name':layer_name,'layer_handle':layer_handle,'identity_status':'read' if layer_ok else 'unresolved','fields':layer,'raw_layer_dxf':values(rec,'StyleRawLayerDXF'),'provenance':provenance},
            'polyline':polyline(rec,typ),'style_resolution_status':resolution,
            'viewport_effective_style':'unresolved_out_of_scope','plot_effective_style':'unresolved_out_of_scope',
            'proxy_marker':proxy,'custom_marker':custom,'host_dependent_visual_evidence_unresolved':proxy or custom,
            'provenance':provenance,'use_restriction':'raw contextual evidence only; not used by discovery admission'}
