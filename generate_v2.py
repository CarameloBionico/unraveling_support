"""Continuous XY/XZ accordion. V1 generator and output remain unchanged."""
from dataclasses import asdict
import argparse
import json
from pathlib import Path
import manifold3d as m3d
import networkx as nx
import numpy as np
import trimesh
from generate import Config, audit, box, build as build_v1, cord, solid_mesh


def sweep(points, c, plane):
    points = np.asarray(points, dtype=float)
    tangent = np.gradient(points, axis=0)
    tangent /= np.linalg.norm(tangent, axis=1)[:, None]
    if plane == 'xy':
        u = np.column_stack([-tangent[:,1], tangent[:,0], np.zeros(len(points))])
        v = np.tile([0.,0.,1.], (len(points),1))
    else:
        u = np.tile([0.,1.,0.], (len(points),1))
        v = np.cross(tangent,u)
    vertices = np.stack([points-u*c.cord_width/2-v*c.cord_height/2,
        points+u*c.cord_width/2-v*c.cord_height/2,
        points+u*c.cord_width/2+v*c.cord_height/2,
        points-u*c.cord_width/2+v*c.cord_height/2],axis=1).reshape(-1,3)
    faces = [[0,2,1],[0,3,2]]
    for i in range(len(points)-1):
        for j in range(4):
            a,b = 4*i+j,4*i+(j+1)%4
            faces += [[a,b,b+4],[a,b+4,a+4]]
    k=4*(len(points)-1)
    faces += [[k,k+1,k+2],[k,k+2,k+3]]
    result=m3d.Manifold(m3d.Mesh64(vertices,np.asarray(faces,dtype=np.uint64)))
    if result.status()!=m3d.Error.NoError:
        raise ValueError(f'Invalid return sweep: {result.status()}')
    return result


def cord_path(c,row,level):
    x=np.linspace(0,c.periods*c.pitch,c.periods*80+1)
    wave=np.clip((1-np.abs(2*((x/c.pitch)%1)-1)-.08)/.84,0,1)
    if level%2:
        wave=1-wave
    return np.column_stack([x,row*c.row_pitch+c.lateral*np.cos(2*np.pi*x/c.pitch),
        c.base_height+c.cord_height/2+level*(c.rise+c.cord_height+c.neck_gap)+c.rise*wave])


def horizontal_return(c,row_a,row_b,level,side):
    radius=c.row_pitch/2
    y0=min(row_a,row_b)*c.row_pitch+c.lateral
    z=cord_path(c,min(row_a,row_b),level)[0,2]
    x0=c.periods*c.pitch if side==1 else 0
    theta=np.linspace(0,np.pi,41)
    points=np.column_stack([x0+side*radius*np.sin(theta),
        y0+radius*(1-np.cos(theta)),np.full_like(theta,z)])
    # Real volume overlap at both endpoints, rather than touching caps.
    points=np.vstack([[x0-side*.15,y0,z],points,[x0-side*.15,y0+c.row_pitch,z]])
    return sweep(points,c,'xy'), points[1:-1] if row_a<row_b else points[-2:0:-1]


def vertical_return(c,row,level):
    y=row*c.row_pitch+c.lateral
    z0=cord_path(c,row,level)[0,2]
    z1=cord_path(c,row,level+1)[0,2]
    radius=min(.8,(z1-z0)/2)
    if radius<=c.cord_height/2:
        raise ValueError('Vertical return radius too small for cord height')
    theta=np.linspace(0,np.pi,65)
    points=np.column_stack([-radius*np.sin(theta),np.full_like(theta,y),
        z0+(z1-z0)/2*(1-np.cos(theta))])
    points=np.vstack([[.15,y,z0],points,[.15,y,z1]])
    return sweep(points,c,'xz'),points[1:-1]


def audit_chain(chunks):
    # Construct adjacency from actual volume intersections, not intended order.
    graph=nx.Graph()
    graph.add_nodes_from(range(len(chunks)))
    for i,a in enumerate(chunks):
        amin,amax=np.asarray(a['solid'].bounding_box()).reshape(2,3)
        for j in range(i+1,len(chunks)):
            b=chunks[j]['solid']
            bmin,bmax=np.asarray(b.bounding_box()).reshape(2,3)
            if np.any(amax<=bmin) or np.any(bmax<=amin):
                continue
            if (a['solid']^b).volume()>1e-7:
                graph.add_edge(i,j)
    actual={tuple(sorted(e)) for e in graph.edges}
    expected={(i,i+1) for i in range(len(chunks)-1)}
    report={'chunks':len(chunks),'connected_components':nx.number_connected_components(graph),
        'endpoints':sum(d==1 for _,d in graph.degree()),
        'unexpected_contacts':[list(e) for e in sorted(actual-expected)],
        'missing_contacts':[list(e) for e in sorted(expected-actual)],
        'scope':'Full-section cord only, without base, anchors or weak necks.'}
    if actual!=expected or report['connected_components']!=1 or report['endpoints']!=2:
        raise ValueError(f'Cord is not an unbranched continuous path: {report}')
    return report


def build(c,neck_width):
    c.validate()
    if c.rows<2 or c.rows%2:
        raise ValueError('V2 requires an even number of rows, at least two')
    _,_,old_parts,_=build_v1(c,neck_width)
    chunks=[]
    for level in range(c.levels):
        rows=list(range(c.rows)) if level%2==0 else list(range(c.rows-1,-1,-1))
        for position,row in enumerate(rows):
            path=cord_path(c,row,level)
            if position%2:
                path=path[::-1]
            chunks.append({'kind':f'cord_{level}','level':level,'solid':cord(c,row,level),'path':path})
            if position<len(rows)-1:
                solid,path=horizontal_return(c,row,rows[position+1],level,1 if position%2==0 else -1)
                chunks.append({'kind':'horizontal','level':level,'solid':solid,'path':path})
        if level<c.levels-1:
            solid,path=vertical_return(c,rows[-1],level)
            chunks.append({'kind':'vertical','level':level+1,'solid':solid,'path':path})
    chain_audit=audit_chain(chunks)
    main=m3d.Manifold.batch_boolean([p['solid'] for p in chunks],m3d.OpType.Add)
    main_audit=audit(solid_mesh(main),1)
    margin=c.row_pitch/2+c.cord_width/2+.4
    length=c.periods*c.pitch
    ymin=-c.lateral-c.cord_width/2-.8
    ymax=(c.rows-1)*c.row_pitch-ymin
    base=box([length+2*margin,ymax-ymin,c.base_height],[-margin,ymin,0])
    parts=[{'kind':'base','level':0,'solid':base}]+chunks
    for kind,solid in old_parts:
        if kind not in ('anchor','neck'):
            continue
        level=0 if kind=='anchor' else int(round((solid.bounding_box()[2]+.5-c.base_height-c.cord_height-c.rise)/
              (c.rise+c.cord_height+c.neck_gap)))+1
        parts.append({'kind':kind,'level':level,'solid':solid})
    support=m3d.Manifold.batch_boolean([p['solid'] for p in parts],m3d.OpType.Add)
    top=c.base_height+c.cord_height+(c.levels-1)*(c.rise+c.cord_height+c.neck_gap)+c.rise
    roof_z=top+c.roof_gap
    left_x=-margin-.4-1.2
    right_x=length+margin+.4
    specimen=box([1.2,ymax-ymin,roof_z+c.roof_height],[left_x,ymin,0]) + box(
        [1.2,ymax-ymin,roof_z+c.roof_height],[right_x,ymin,0]) + box(
        [right_x+1.2-left_x,ymax-ymin,c.roof_height],[left_x,ymin,roof_z])
    route=np.vstack([p['path'] for p in chunks])
    meta={'chain':chain_audit,'main_cord':main_audit,
        'horizontal_returns':sum(p['kind']=='horizontal' for p in chunks),
        'vertical_returns':sum(p['kind']=='vertical' for p in chunks),
        'route_length_mm':round(float(np.linalg.norm(np.diff(route,axis=0),axis=1).sum()),2),
        'neck_count':sum(p['kind']=='neck' for p in parts),'top_z':top,'roof_z':roof_z}
    return support,specimen,parts,meta,main


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=Path('output_v2'))
    parser.add_argument('--config',type=Path)
    args=parser.parse_args()
    c=Config(**(json.loads(args.config.read_text()) if args.config else {}))
    args.out.mkdir(parents=True,exist_ok=True)
    report={'version':2,'config':asdict(c),'variants':{},'physical_validation':False}
    preview={'version':2,'config':asdict(c),'variants':{}}
    for name,width in [('A_fina',.45),('B_media',.6),('C_forte',.8)]:
        support,specimen,parts,meta,main_cord=build(c,width)
        sm,pm,cm=map(solid_mesh,[support,specimen,main_cord])
        combined=trimesh.util.concatenate([sm,pm])
        entry={'neck_width_mm':width,**meta,'support':audit(sm,1),'specimen':audit(pm,1),
            'assembled':audit(combined,2),'support_specimen_intersection_mm3':float((support^specimen).volume())}
        if entry['support_specimen_intersection_mm3']>1e-8:
            raise ValueError('Specimen intersects support')
        for suffix,mesh in [('suporte',sm),('peca',pm),('conjunto',combined),('cordao_sem_ligacoes',cm)]:
            path=args.out/f'{name}_{suffix}.stl'
            mesh.export(path)
            audit(trimesh.load_mesh(path),2 if suffix=='conjunto' else 1)
        view_parts=[]
        route=[]
        for part in parts+[{'kind':'specimen','level':0,'solid':specimen}]:
            mesh=solid_mesh(part['solid'])
            view_parts.append({'kind':part['kind'],'level':part['level'],
                'v':np.round(mesh.vertices,4).tolist(),'f':mesh.faces.tolist()})
            if 'path' in part:
                route.append({'level':part['level'],'kind':part['kind'],
                    'points':np.round(part['path'],4).tolist()})
        preview['variants'][name]={'neck':width,'parts':view_parts,'route':route,'meta':meta}
        report['variants'][name]=entry
        print(f'{name}: continuous cord, {meta["horizontal_returns"]} XY returns, '
              f'{meta["vertical_returns"]} XZ returns, {meta["route_length_mm"]} mm',flush=True)
    (args.out/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (args.out/'config.json').write_text(json.dumps(asdict(c),indent=2),encoding='utf-8')
    (args.out/'preview-data.js').write_text('window.MODEL = '+json.dumps(preview,separators=(',',':'))+';',encoding='utf-8')


if __name__=='__main__':
    main()
