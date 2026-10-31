"""Meshes for the engine: the designer STLs and the tessellated STEPs (model/build/steps), subdivided once so no
edge is longer than MAX_EDGE_MM, posed by rigid transform, and the pairwise judgement check.py makes in Fusion:
minimum distance (scipy cKDTree vertex screen, then exact point-to-triangle on the near candidates, both ways:
ADR 0006) and contact vs penetration: a vertex behind the other mesh's surface by more than DEPTH_MM is inside it
(sign against the angle-weighted pseudo-normal of the closest face, edge or vertex, Baerentzen & Aanaes 2005, the
deepest few confirmed by ray parity). A pair that measures 0 mm with nothing inside is a designed contact."""
import numpy as np
import trimesh
from scipy.spatial import cKDTree

MAX_EDGE_MM = 2.0   # the exact pass only needs vertices within (vertex-vertex bound + longest edge) of each other
NEAR_MM = 10.0      # pairs whose boxes are further apart are not measured (check.py NEAR_MM)
EXACT_MM = 5.0      # the exact pass runs when the vertex screen is under this; above, the screen (at most ~1.5 mm high) is reported
DEPTH_MM = 0.02     # a vertex counts as inside only this deep: coincident faces are a contact, not a collision
CONFIRM = 3         # deepest candidates confirmed by ray parity per direction
_RAY = np.array([0.5773, 0.6113, 0.5410])   # off-axis so edges and vertices are not hit


def load(stage, names=None):
    """{part name: trimesh.Trimesh in its local frame} for the Stage's parts (or just `names`)."""
    out = {}
    for name, part in stage.parts.items():
        if names is not None and name not in names:
            continue
        mesh = trimesh.load(part.file, force="mesh")
        v, f = mesh.vertices, mesh.faces
        if part.clip:   # shortcut: faces past the cut are dropped, no cap (the battery lead; the pack is grounded context)
            axis, cut = part.clip
            f = f[(v[f][:, :, "xyz".index(axis)] <= cut + 0.1).all(axis=1)]
        mesh = trimesh.Trimesh(*bisect(v, f, MAX_EDGE_MM))
        if mesh.volume < 0:   # inward winding: the depth sign below needs outward faces
            mesh.invert()
        out[name] = mesh
    return out


def bisect(v, f, max_edge):
    """Split every face at the midpoint of its longest edge until no edge is longer than max_edge (T-junctions are
    fine for distances; trimesh's subdivide_to_size quarters faces and makes a 120 x 160 base half a million faces)."""
    v, f = np.asarray(v, float), np.asarray(f)
    while True:
        tri = v[f]
        edges = np.linalg.norm(tri - np.roll(tri, -1, axis=1), axis=2)   # edge i: vertex i -> i+1
        longest = edges.argmax(axis=1)
        split = np.flatnonzero(edges.max(axis=1) > max_edge)
        if not len(split):
            return v, f
        i = longest[split]
        a, b, c = f[split, i], f[split, (i + 1) % 3], f[split, (i + 2) % 3]
        mid = np.arange(len(v), len(v) + len(split))
        v = np.vstack([v, (v[a] + v[b]) / 2])
        f = np.vstack([np.delete(f, split, axis=0), np.column_stack([a, mid, c]), np.column_stack([mid, b, c])])


class Placed:
    """A mesh at a world transform; vertices, box and KD-tree computed once per pose."""

    def __init__(self, mesh, matrix):
        self.faces = mesh.faces
        self.vertices = trimesh.transform_points(mesh.vertices, matrix)
        self.lo, self.hi = self.vertices.min(axis=0), self.vertices.max(axis=0)
        tri = self.vertices[self.faces]
        self.centroids = tri.mean(axis=1)
        self.reach = float(np.linalg.norm(tri - self.centroids[:, None], axis=2).max())   # every point of a face is this close to its centroid
        self._ctree = None
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        self.normals = n / np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
        # pseudo-normals for the inside test: angle-weighted at vertices, the two faces' sum on edges
        self.vertex_normals = trimesh.geometry.weighted_vertex_normals(len(self.vertices), self.faces, self.normals, trimesh.triangles.angles(tri))
        self.face_edges = mesh.faces_unique_edges          # (faces, 3): edge k joins face vertices k and k+1
        self.edge_normals = np.zeros((len(mesh.edges_unique), 3))
        np.add.at(self.edge_normals, self.face_edges.ravel(), np.repeat(self.normals, 3, axis=0))
        self._tree = None

    @property
    def ctree(self):
        if self._ctree is None:
            self._ctree = cKDTree(self.centroids)
        return self._ctree

    @property
    def tree(self):
        if self._tree is None:
            self._tree = cKDTree(self.vertices)
        return self._tree


def bbox_gap(a, b):
    return float(np.linalg.norm(np.maximum(0.0, np.maximum(b.lo - a.hi, a.lo - b.hi))))


def to_surface(pts, b, bounds):
    """(distance, depth) of each point to b's surface, given per-point upper bounds (vertex distances): the closest
    triangle's centroid is within bound + b.reach of the point. depth > 0 where the point lies behind its closest
    face, i.e. inside b."""
    out = np.array(bounds, float)
    depth = np.zeros(len(pts))
    hits = b.ctree.query_ball_point(pts, out + b.reach)
    counts = np.fromiter((len(h) for h in hits), int, len(hits))
    fi = np.concatenate(hits).astype(int) if counts.any() else np.zeros(0, int)
    pi = np.repeat(np.arange(len(pts)), counts)
    if len(pi):
        away = pts[pi] - trimesh.triangles.closest_point(b.vertices[b.faces[fi]], pts[pi])
        d = np.linalg.norm(away, axis=1)
        best = np.full(len(pts), -1)
        order = np.argsort(d)[::-1]
        best[pi[order]] = order                      # last write wins: the closest pair of each point
        k = np.flatnonzero(best >= 0); best = best[k]
        out[k] = np.minimum(out[k], d[best])
        depth[k] = np.where((away[best] * pseudo_normal(b, fi[best], pts[k])).sum(axis=1) < 0, d[best], 0.0)
    return out, depth


def inside(pts, b):
    """Ray-parity containment of points in b."""
    tri = b.vertices[b.faces]
    e1, e2 = tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]
    pv = np.cross(_RAY, e2)
    det = (e1 * pv).sum(axis=1)
    ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    out = np.zeros(len(pts), bool)
    for i, pt in enumerate(pts):
        tv = pt - tri[:, 0]
        u = (tv * pv).sum(axis=1) * inv
        q = np.cross(tv, e1)
        v = (q * _RAY).sum(axis=1) * inv
        t = (e2 * q).sum(axis=1) * inv
        out[i] = (ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-9)).sum() % 2 == 1
    return out


def pseudo_normal(b, faces, pts):
    """Outward pseudo-normal of b at each point's closest feature on `faces`: the face's own normal inside it, the
    two faces' sum on an edge, the angle-weighted vertex normal at a corner."""
    tri = b.vertices[b.faces[faces]]
    bary = trimesh.triangles.points_to_barycentric(tri, trimesh.triangles.closest_point(tri, pts))
    on = bary > 1e-6
    n = b.normals[faces].copy()
    corner = on.sum(axis=1) == 1
    n[corner] = b.vertex_normals[b.faces[faces[corner]][np.arange(corner.sum()), on[corner].argmax(axis=1)]]
    edge = on.sum(axis=1) == 2
    off = (~on[edge]).argmax(axis=1)                 # the vertex not on the edge: edge (off+1, off+2) is face edge index off+1
    n[edge] = b.edge_normals[b.face_edges[faces[edge], (off + 1) % 3]]
    return n


def _one_way(a, b, bound):
    """(min distance, confirmed penetration) from a's vertices to b, complete below `bound`."""
    d, _ = b.tree.query(a.vertices, distance_upper_bound=bound + b.reach)
    near = np.flatnonzero(np.isfinite(d))
    if not len(near):
        return bound, False
    pts = a.vertices[near]
    dist, depth = to_surface(pts, b, np.minimum(d[near], bound))
    deep = np.flatnonzero(depth > DEPTH_MM)
    deep = deep[np.argsort(-depth[deep])][:CONFIRM]
    return min(bound, float(dist.min())), bool(len(deep)) and bool(inside(pts[deep], b).any())


def judge(a, b):
    """(minimum distance mm, penetrates) for two Placed meshes: 0 mm when they touch or overlap; penetrating when
    a vertex of either sits inside the other (else a 0 is a designed contact)."""
    bound = float(b.tree.query(a.vertices)[0].min())
    if bound > EXACT_MM:
        return bound, False
    d_ab, in_ab = _one_way(a, b, bound)
    d_ba, in_ba = _one_way(b, a, d_ab)
    deep = in_ab or in_ba
    return (0.0 if deep else d_ba), deep


def distance(a, b):
    return judge(a, b)[0]


def penetrates(a, b):
    return judge(a, b)[1]
