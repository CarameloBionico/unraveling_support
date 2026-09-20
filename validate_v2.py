"""Validate the spatial returns and compare cord connectivity against V1.

Run validate_slicing.py --out output_v2 first. No physical stability is inferred.
"""
import json
from pathlib import Path
import numpy as np
import manifold3d as m3d
from generate import Config, build as build_v1, solid_mesh
from generate_v2 import build
from validate_slicing import segments


def main():
    root=Path('output_v2')
    c=Config(**json.loads((root/'config.json').read_text()))
    _,_,old_parts,_=build_v1(c,.6)
    old_main=m3d.Manifold.batch_boolean([s for k,s in old_parts if k.startswith('cord_')],m3d.OpType.Add)
    old_count=len(solid_mesh(old_main).split())
    _,_,parts,meta,_=build(c,.6)
    assert old_count==c.rows*c.levels
    assert meta['main_cord']['components']==1
    report={'v1_cord_components_without_base_or_necks':old_count,
        'v2_cord_components_without_base_or_necks':1,'chain':meta['chain'],
        'scope':'Nearby extrusion on each sampled return centerline; not a tensile or stability test.',
        'maximum_distance_to_extrusion_center_mm':.30,'variants':{}}
    for name in ('A_fina','B_media','C_forte'):
        paths=segments(root/'audit'/f'{name}_NAO_IMPRIMIR.gcode')
        by_z={}
        for z,a,b in paths:
            by_z.setdefault(round(z,4),[]).append((a,b))
        missing=[]
        worst=0.
        count=0
        for part in parts:
            if part['kind'] not in ('horizontal','vertical'):
                continue
            for point in part['path']:
                # Cura layer output Z is 0.1 above the midpoint slice plane.
                z=round((round((point[2]-c.layer/2)/c.layer)+1)*c.layer,4)
                pairs=np.asarray(by_z.get(z,[]))
                target=point[:2]+110
                distance=float('inf')
                if len(pairs):
                    a,b=pairs[:,0],pairs[:,1]
                    d=b-a
                    t=np.clip(np.einsum('ij,ij->i',target-a,d)/np.einsum('ij,ij->i',d,d),0,1)
                    distance=float(np.linalg.norm(target-a-t[:,None]*d,axis=1).min())
                count+=1
                worst=max(worst,distance)
                if distance>.30:
                    missing.append({'kind':part['kind'],'point':point.tolist(),'z':z,'distance':distance})
        report['variants'][name]={'return_samples':count,'missing_samples':missing,
                                 'worst_distance_mm':round(worst,4)}
        print(name,count,'return samples,',len(missing),'missing; maximum distance',round(worst,4))
    (root/'audit'/'return_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if any(v['missing_samples'] for v in report['variants'].values()):
        raise SystemExit('Missing return extrusion samples; inspect report')


if __name__=='__main__':
    main()
