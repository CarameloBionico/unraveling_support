"""Experimental 3D accordion support. Coordinates and STL units: millimetres."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path

import manifold3d as m3d
import numpy as np
import trimesh


@dataclass(frozen=True)
class Config:
    nozzle: float = 0.4
    layer: float = 0.2
    cord_width: float = 0.9
    cord_height: float = 0.8
    pitch: float = 8.0
    rise: float = 3.2
    lateral: float = 0.65
    rows: int = 4
    row_pitch: float = 3.0
    levels: int = 4
    periods: int = 3
    neck_gap: float = 0.4
    base_height: float = 0.4
    roof_gap: float = 0.2
    roof_height: float = 1.2

    def validate(self):
        for key, value in asdict(self).items():
            if not np.isfinite(value) or value <= 0:
                raise ValueError(f"{key} must be positive and finite")
        if self.cord_width < self.nozzle:
            raise ValueError("Cord width cannot be smaller than the nozzle")
        if self.row_pitch <= self.cord_width + 2 * self.lateral:
            raise ValueError("Rows need lateral access clearance")
        if self.rise > self.pitch * 0.42:
            raise ValueError("Vertical ramps exceed the initial 45 degree limit")
        for key in ("cord_height", "neck_gap", "base_height", "roof_gap", "roof_height", "rise"):
            n = getattr(self, key) / self.layer
            if abs(n - round(n)) > 1e-6:
                raise ValueError(f"{key} must be a multiple of layer height")


def solid_mesh(solid):
    # 20 microns removes boolean slivers that older slicers merge into duplicate faces.
    mesh = solid.simplify(0.02).simplify(0.00001).to_mesh64()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3],
                           faces=np.asarray(mesh.tri_verts), process=True)


def box(size, origin):
    return m3d.Manifold.cube(size).translate(origin)


def cord(c: Config, row: int, level: int):
    """Closed sweep with a constant YZ rectangular section; no nonplanar G-code."""
    xs = np.linspace(0, c.periods * c.pitch, c.periods * 80 + 1)
    phase = (xs / c.pitch) % 1
    wave = np.clip(((1 - np.abs(2 * phase - 1)) - 0.08) / 0.84, 0, 1)
    if level % 2:
        wave = 1 - wave
    ys = row * c.row_pitch + c.lateral * np.cos(2 * np.pi * xs / c.pitch)
    zs = (c.base_height + c.cord_height / 2 +
          level * (c.rise + c.cord_height + c.neck_gap) + c.rise * wave)
    vertices = []
    for x, y, z in zip(xs, ys, zs):
        vertices.extend([[x, y-c.cord_width/2, z-c.cord_height/2],
                         [x, y+c.cord_width/2, z-c.cord_height/2],
                         [x, y+c.cord_width/2, z+c.cord_height/2],
                         [x, y-c.cord_width/2, z+c.cord_height/2]])
    faces = [[0, 2, 1], [0, 3, 2]]
    for i in range(len(xs)-1):
        for j in range(4):
            a, b = 4*i+j, 4*i+(j+1) % 4
            faces.extend([[a, b, b+4], [a, b+4, a+4]])
    k = 4*(len(xs)-1)
    faces.extend([[k, k+1, k+2], [k, k+2, k+3]])
    result = m3d.Manifold(m3d.Mesh64(np.asarray(vertices, dtype=np.float64),
                                   np.asarray(faces, dtype=np.uint64)))
    if result.status() != m3d.Error.NoError:
        raise ValueError(f"Invalid cord: {result.status()}")
    return result


def build(c: Config, neck_width: float):
    c.validate()
    if not c.nozzle <= neck_width <= c.cord_width:
        raise ValueError("Neck width must be between nozzle and cord width")
    length = c.periods * c.pitch
    ymin = -c.lateral - c.cord_width/2 - 0.8
    ymax = (c.rows-1)*c.row_pitch - ymin
    base = box([length+1.6, ymax-ymin, c.base_height], [-0.8, ymin, 0])
    parts = [("base", base)]
    for level in range(c.levels):
        for row in range(c.rows):
            parts.append((f"cord_{level}", cord(c, row, level)))
        if level == 0:
            # Small overlaps anchor lowest valleys to the base with real volume.
            for row in range(c.rows):
                for i in range(c.periods+1):
                    x = i*c.pitch
                    parts.append(("anchor", box([0.8, c.cord_width, 0.4],
                                 [x-0.4, row*c.row_pitch+c.lateral-c.cord_width/2, c.base_height-0.2])))
            continue
        # Upper valleys coincide with the peaks of the level below.
        offset = 0.5 if level % 2 else 0.0
        positions = np.arange(offset, c.periods+0.01, 1.0)*c.pitch
        bottom = c.base_height + c.cord_height + (level-1)*(c.rise+c.cord_height+c.neck_gap)+c.rise
        for row in range(c.rows):
            for x in positions:
                # Overlap both cords; only the exposed middle is the weak neck.
                parts.append(("neck", box([neck_width, neck_width, c.neck_gap+1.0],
                             [x-neck_width/2, row*c.row_pitch+c.lateral*np.cos(2*np.pi*x/c.pitch)-neck_width/2, bottom-0.5])))
    support = m3d.Manifold.batch_boolean([s for _, s in parts], m3d.OpType.Add)
    top = c.base_height+c.cord_height+(c.levels-1)*(c.rise+c.cord_height+c.neck_gap)+c.rise
    roof_z = top+c.roof_gap
    # Separate U-shaped specimen, with its own feet on the bed. No floating STL part.
    left = box([1.2, ymax-ymin, roof_z+c.roof_height], [-2.4, ymin, 0])
    right = box([1.2, ymax-ymin, roof_z+c.roof_height], [length+1.2, ymin, 0])
    roof = box([length+4.8, ymax-ymin, c.roof_height], [-2.4, ymin, roof_z])
    specimen = left + right + roof
    return support, specimen, parts, {"top_z": top, "roof_z": roof_z, "neck_count": sum(k == "neck" for k, _ in parts)}


def audit(mesh, expected_components):
    components = mesh.split(only_watertight=False)
    result = dict(watertight=bool(mesh.is_watertight), winding_consistent=bool(mesh.is_winding_consistent),
                  positive_volume=bool(mesh.volume > 0), components=len(components),
                  degenerate_faces=int(np.count_nonzero(mesh.area_faces < 1e-10)),
                  bounds_mm=np.round(mesh.bounds, 5).tolist(), volume_mm3=round(float(mesh.volume), 3),
                  triangles=len(mesh.faces))
    if not (result["watertight"] and result["winding_consistent"] and result["positive_volume"]
            and result["components"] == expected_components and result["degenerate_faces"] == 0):
        raise ValueError(f"Mesh audit failed: {result}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("output"))
    parser.add_argument("--config", type=Path, help="JSON overrides of Config fields")
    args = parser.parse_args()
    c = Config(**(json.loads(args.config.read_text()) if args.config else {}))
    c.validate()
    args.out.mkdir(parents=True, exist_ok=True)
    report = {"config": asdict(c), "status": "Geometry validated; physical printing and unraveling NOT validated.", "variants": {}}
    preview = {"config": asdict(c), "variants": {}}
    for name, width in [("A_fina", 0.45), ("B_media", 0.60), ("C_forte", 0.80)]:
        support, specimen, parts, meta = build(c, width)
        sm, pm = solid_mesh(support), solid_mesh(specimen)
        combined = trimesh.util.concatenate([sm, pm])
        entry = {"neck_width_mm": width, **meta,
                 "support": audit(sm, 1), "specimen": audit(pm, 1), "assembled": audit(combined, 2),
                 "support_specimen_intersection_mm3": float((support ^ specimen).volume())}
        if entry["support_specimen_intersection_mm3"] > 1e-8:
            raise ValueError("Support intersects specimen")
        for suffix, mesh in [("suporte", sm), ("peca", pm), ("conjunto", combined)]:
            path = args.out/f"{name}_{suffix}.stl"
            mesh.export(path)
            audit(trimesh.load_mesh(path), 2 if suffix == "conjunto" else 1)
        report["variants"][name] = entry
        view_parts = []
        for kind, solid in parts + [("specimen", specimen)]:
            mesh = solid_mesh(solid)
            view_parts.append({"kind": kind, "v": np.round(mesh.vertices, 4).tolist(), "f": mesh.faces.tolist()})
        preview["variants"][name] = {"neck": width, "parts": view_parts}
        print(f"{name}: {len(sm.faces)} triangles, 1 closed support, {meta['neck_count']} necks")
    (args.out/"validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (args.out/"preview-data.js").write_text("window.MODEL = "+json.dumps(preview, separators=(",", ":"))+";", encoding="utf-8")
    (args.out/"config.json").write_text(json.dumps(asdict(c), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
