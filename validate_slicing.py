"""Geometric layer-start and Cura toolpath audits; NOT a machine print profile."""
import argparse
import json
from pathlib import Path
import re
import subprocess

import numpy as np
import manifold3d as m3d
import trimesh
from generate import Config, build, solid_mesh


def layer_audit(solid, c):
    """Detect disconnected islands born without any overlap below.

    A whole island overlapping below does not prove every extrusion is supported.
    Overhang cooling, bridge quality and stability require a physical test.
    """
    previous = None
    failures = []
    count = 0
    for z in np.arange(c.layer/2, solid.bounding_box()[5], c.layer):
        section = solid.slice(float(z))
        islands = section.decompose()
        if previous is not None:
            for island in islands:
                if (island ^ previous).area() < 1e-8:
                    failures.append(round(float(z), 4))
        previous = section
        count += 1
    return {"sampled_layers": count, "unsupported_island_birth_z_mm": failures,
            "scope": "Each island overlaps the preceding layer; not a full overhang or toolpath simulation."}


def segments(path):
    x=y=z=e=0.0
    result=[]
    for line in path.read_text().splitlines():
        command=line.split(';')[0].strip()
        if not command:
            continue
        fields={k:float(v) for k,v in re.findall(r'([XYZE])(-?\d+(?:\.\d+)?)', command)}
        if command.startswith('G92'):
            e=fields.get('E',e)
        elif command.split()[0] in ('G0','G1'):
            nx,ny,nz,ne=[fields.get(k,v) for k,v in zip('XYZE',[x,y,z,e])]
            if ne>e+1e-8 and np.hypot(nx-x,ny-y)>1e-6:
                result.append((nz,(x,y),(nx,ny)))
            x,y,z,e=nx,ny,nz,ne
    return result


def neck_coverage(paths, c):
    missing=[]
    checked=0
    # Cura default machine origin translates the uncentered STL by half bed size.
    shift=np.array([110.0,110.0])
    for level in range(1,c.levels):
        bottom=c.base_height+c.cord_height+(level-1)*(c.rise+c.cord_height+c.neck_gap)+c.rise
        offset=.5 if level%2 else 0
        for z in np.arange(bottom+c.layer,bottom+c.neck_gap+1e-5,c.layer):
            candidates=[(np.array(a),np.array(b)) for pz,a,b in paths if abs(pz-z)<1e-5]
            for row in range(c.rows):
                for x in np.arange(offset,c.periods+.01,1)*c.pitch:
                    point=np.array([x,row*c.row_pitch+c.lateral*np.cos(2*np.pi*x/c.pitch)])+shift
                    distance=float('inf')
                    for a,b in candidates:
                        d=b-a
                        t=np.clip(np.dot(point-a,d)/np.dot(d,d),0,1)
                        distance=min(distance,float(np.linalg.norm(point-a-t*d)))
                    checked+=1
                    if distance>c.nozzle/2+.02:
                        missing.append([round(float(x),3),row*c.row_pitch,round(float(z),3)])
    return {"neck_layer_samples": checked, "missing_neck_layer_samples": missing}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cura',type=Path,default=Path(r'C:\Program Files\Ultimaker Cura 4.13.1\CuraEngine.exe'))
    p.add_argument('--out',type=Path,default=Path('output'))
    args=p.parse_args()
    c=Config(**json.loads((args.out/'config.json').read_text()))
    out=args.out/'audit'
    out.mkdir(exist_ok=True)
    report={"note":"Generic Cura geometry audit, not validated printer G-code.","variants":{}}
    settings={"machine_width":220,"machine_depth":220,"machine_height":250,
              "machine_nozzle_size":c.nozzle,"material_diameter":1.75,
              "layer_height":c.layer,"layer_height_0":c.layer,
              "line_width":c.nozzle,"wall_line_width":c.nozzle,
              "wall_line_width_0":c.nozzle,"wall_line_width_x":c.nozzle,
              "skin_line_width":c.nozzle,"infill_line_width":c.nozzle,
              "wall_line_count":2,"fill_perimeter_gaps":"everywhere",
              "fill_outline_gaps":"true","filter_out_tiny_gaps":"false",
              "minimum_polygon_circumference":0,"meshfix_maximum_resolution":0.05,
              "infill_sparse_density":100,"infill_line_distance":c.nozzle,
              "top_layers":4,"bottom_layers":4,"support_enable":"false","adhesion_type":"none",
              "machine_start_gcode":"","machine_end_gcode":""}
    report['settings']=settings
    for name,width in [('A_fina',.45),('B_media',.6),('C_forte',.8)]:
        support,_,_,_=build(c,width)
        # Audit exactly the exported, simplified mesh, not merely the ideal construction.
        mesh=trimesh.load_mesh(args.out/f'{name}_suporte.stl')
        solid=m3d.Manifold(m3d.Mesh64(np.asarray(mesh.vertices),np.asarray(mesh.faces,dtype=np.uint64)))
        entry={'layer_geometry':layer_audit(solid,c)}
        if args.cura.exists():
            code=out/f'{name}_NAO_IMPRIMIR.gcode'
            command=[str(args.cura),'slice','-j',str(args.cura.parent/'resources/definitions/fdmprinter.def.json')]
            for k,v in settings.items():
                command.extend(['-s',f'{k}={v}'])
            command.extend(['-l',str(args.out/f'{name}_suporte.stl'),'-o',str(code)])
            run=subprocess.run(command,capture_output=True,text=True)
            log=run.stdout+run.stderr
            (out/f'{name}_cura.log').write_text(log,encoding='utf-8')
            if run.returncode:
                raise RuntimeError(f'Cura failed: {name}')
            toolpaths=segments(code)
            entry['cura']={'extruding_segments':len(toolpaths),**neck_coverage(toolpaths,c),
                'overlapping_face_warning':'Mesh has overlapping faces!' in log,
                'empty_layer_warnings':re.findall(r'Layer \d+ is empty',log)}
            assembly_code=out/f'{name}_conjunto_NAO_IMPRIMIR.gcode'
            assembly_command=command[:-4]+['-l',str(args.out/f'{name}_conjunto.stl'),'-o',str(assembly_code)]
            assembly_run=subprocess.run(assembly_command,capture_output=True,text=True)
            assembly_log=assembly_run.stdout+assembly_run.stderr
            (out/f'{name}_conjunto_cura.log').write_text(assembly_log,encoding='utf-8')
            if assembly_run.returncode:
                raise RuntimeError(f'Cura assembly failed: {name}')
            entry['cura_assembly']={'extruding_segments':len(segments(assembly_code)),
                'overlapping_face_warning':'Mesh has overlapping faces!' in assembly_log,
                'empty_layer_warnings':re.findall(r'Layer \d+ is empty',assembly_log)}
        report['variants'][name]=entry
        print(name,json.dumps(entry))
    (out/'slicing_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    failed=any(e['layer_geometry']['unsupported_island_birth_z_mm'] or
               e.get('cura',{}).get('missing_neck_layer_samples') or
               e.get('cura',{}).get('overlapping_face_warning') or
               e.get('cura',{}).get('empty_layer_warnings') or
               e.get('cura_assembly',{}).get('overlapping_face_warning') or
               e.get('cura_assembly',{}).get('empty_layer_warnings') for e in report['variants'].values())
    if failed:
        raise SystemExit('Audit failed; inspect slicing_validation.json')


if __name__=='__main__':
    main()
