"""Morty's Skin, cut from his Sculpt (GLOSSARY Skin, Shell; docs/adr/0027, #850). shells() is every Shell in the head's
frame at rest, mm, which `just ours` writes beside our parts (write()). No document wears them yet (g.SKINS, #850).

The Sculpt is placed on the Mech's eyes (morty.placed()) and cut at the base plane, the documents' z 0. Its outer
skin's own triangles stay the Skin's outside. The outer skin is what the open air reaches (outer()): behind each brow
this Sculpt has a pocket, a slab of empty space deep in its head joined to its surface by cracks, and none of a
pocket's walls is the Skin's. The inside is the surface skin.WALL under the outer skin, measured on a grid of PITCH:
each point's distance to it, meshed where that is WALL (scikit-image's marching cubes), then made lighter within FLAT.
The wall has no floor at the base. It is open inside each eye white's cut, the Sculpt's own dome's edge and no
larger (#893): the eyeballs, the mechanism's own, are the eye whites. Then it is split along skin.cuts(): the shirt under the collar, the hair above
and behind the hairline, the chin under the mouth line, each brow's ridge inside its outline, and the face. The hair
is cut again, level, into its crown and its back (LEVEL). Solids are cut with manifold3d.

Every seam is a gap of SEAM (docs/adr/0029): at rest the face steps back from the hair and the chin, the shirt from
the collar, and the hair's two pieces half of it each from their level; and where Shells move against each other the one that stands still gives way (cleared()):
the shirt to the head through tilt, pan and the jaw's range together, the face to the opening chin. A brow is laid
on the face and glued there (skin.GLUED): BROW thick, keyed by its own outline, FIT off the face, in a bed cut into
the outside of the face's wall, which runs on under it.

Last, each Shell gets its half of its Seats (seated(), model/skin.py SEATS)."""

import os

import manifold3d as m3
import numpy as np
import trimesh
from scipy import ndimage, sparse
from scipy.sparse import csgraph
from scipy.spatial import cKDTree
from skimage import measure

from model import geometry as g
from model import gimbal as gm
from model import morty, neck, skin, stages

PITCH = 0.8  # the grid the inside is measured on and meshed at, mm: twice it, and a sharp crease's wall thinned to 0.3
# the inside's mesh is then made lighter, within this of itself (manifold3d's simplify): 0.9 M triangles to 0.1 M, so
# each Shell is under the 200,000 faces MuJoCo reads from an STL
FLAT = 0.05
UNDER = 12.0  # the Sculpt is kept this far under the base while the inside is measured, so the wall has no floor
# A pocket (outer()) is empty space the open air does not reach on the grid, more than DEEP grid steps from it at its
# deepest: a crease's bottom is nearer. A face fronts what lies FRONT grid steps off its middle, along its normal
DEEP, FRONT = 5.0, (1.0, 1.5, 2.0, 2.5)
KEEP = 0.01  # a crumb a cut leaves, of its Shell's volume, under which it is dropped
# The gap at a seam, mm (inferred): two Shells never nearer than the room a worn Shell keeps from any part it does not
# sit on (gm.LID_CLEAR_MM, model/printed/test_skin.py), with what that gate's sampling can misread. At rest the face
# steps back this far from the hair and the chin, and the shirt from the collar; where the head's Shells turn into the
# shirt, the shirt gives way (cleared())
SEAM = 0.8
# Morty's hair is two Shells (Cansin, 2026-11-28, #893): a hood no straight way takes off the skull whole, cut on a
# level seam at this height in the head's frame, mm. The crown, above, lifts straight up; the back, below, slides
# straight back (skin.DIRECTIONS). Cansin picked "about eye level, z 0 to 20"; 10 is the highest there at which the
# back comes no nearer the worn skull on its way off than where it rests (2.5 mm; at 20 it passes 0.4 mm from it:
# measured, model/morty/test_shells.py holds it)
LEVEL = 10.0
# A brow is laid on the face and glued there (skin.GLUED; Cansin, 2026-11-28, #893), so it takes no seam's gap: its
# outline locates it, FIT off the face all round (inferred, as a pupil's play in its cap). It is BROW thick, the
# Sculpt's own surface outside, and lies in a bed cut into the outside of the face's wall, GLUE under it (the glue's
# room, and what two surfaces meshed on a PITCH grid can misread: at 0.2 they met in places). BROW, GLUE and the face
# left under the bed make skin.WALL, so the face's inside under a brow is its wall's own and a brow asks nothing of
# what stands behind it: the lids stow under it over the eye (#967) and the skull stands 1.5 mm behind the wall at
# its nose end (#874)
FIT, GLUE, BROW = 0.2, 0.4, 0.6
FINE = 0.4  # the grid a brow's and its bed's depths are measured on, mm: at PITCH a 0.6 mm brow thinned to 0.3
BROWS = ((-90.0, -30.0, 15.0), (90.0, 30.0, 65.0))  # the box a brow's depths are measured in: both brows, 12 mm round
REACH, PAD = 0.5, 4.0  # the grid a Shell's reach into another is measured on, and how far from it, mm
TURN = 0.1  # the jaw and the tilt are sampled every so many degrees of what they turn
LIFT = (
    60.0  # the head's Shells are measured to this far above the shirt's top, mm: cleared() holds the rest clear of it
)


def head():
    """4x4 taking the Sculpt's own frame to the head's: his eyes on the Mech's (morty.placed()), at rest."""
    return np.linalg.inv(stages.align(*stages.DOCS[morty.DOC]["eyes"])) @ morty.placed()


def base():
    """The base plane's height in the head's frame: the documents' z 0, the Torso's foot."""
    return float(np.linalg.inv(stages.align(*stages.DOCS[morty.DOC]["eyes"]))[2, 3])


def _solid(vertices, faces):
    out = m3.Manifold(m3.Mesh(np.asarray(vertices, np.float32), np.asarray(faces, np.uint32)))
    assert out.status() == m3.Error.NoError, out.status()  # a mesh that is no closed surface would cut to nothing
    return out


def _mesh(solid):
    """The solid as a trimesh, without the facets whose corners its 32-bit coordinates bring together: two of a
    Shell's 65,000, each an open edge to a reader that merges vertices (as model/ours.py printable() drops OCCT's)."""
    mesh = solid.to_mesh()
    mesh = trimesh.Trimesh(mesh.vert_properties[:, :3], mesh.tri_verts)
    mesh.update_faces(mesh.nondegenerate_faces())
    return mesh


def _points(triangles, spacing):
    """Points on the triangles, none further than `spacing` from the next: each triangle's own lattice."""
    edge = np.linalg.norm(triangles - np.roll(triangles, 1, axis=1), axis=2).max(axis=1)
    steps = np.ceil(edge / spacing).astype(int)
    out = []
    for k in np.unique(steps):
        i, j = np.meshgrid(np.arange(k + 1), np.arange(k + 1))
        keep = i + j <= k
        weights = np.stack([i[keep], j[keep], k - i[keep] - j[keep]], axis=1) / k
        out.append(np.einsum("wk,fkd->fwd", weights, triangles[steps == k]).reshape(-1, 3))
    return np.vstack(out)


def _spaces(surface, pitch=PITCH):
    """(the low corner of a grid of `pitch` round a surface's points, the grid): 0 where a point falls, and elsewhere
    each empty space's number, one space where a step along the grid joins two cells. The corner's is the open air."""
    low, high = surface.min(axis=0) - 3 * pitch, surface.max(axis=0) + 3 * pitch
    empty = np.ones(np.ceil((high - low) / pitch).astype(int) + 1, bool)
    empty[tuple(np.round((surface - low) / pitch).astype(int).T)] = False
    return low, ndimage.label(empty)[0]


def outer(solid):
    """`solid` (manifold3d) less its pockets: its outer skin, its own triangles. A pocket is empty space outside the
    solid that the open air does not reach, a hole narrower than the grid being closed to it: a chamber behind a
    pinhole. The faces that front a pocket are its walls and those that front the open air are outside. The rest (a
    crease's sides, the pinhole's) fall to whichever they join by more: the walls end at the shortest loops of edges
    that part the two (a minimum cut, each edge its length), taken as near the outside as they come. The walls go,
    and each loop is capped by a fan about its middle."""
    mesh = _mesh(solid)
    low, space = _spaces(_points(mesh.triangles, 0.7 * PITCH))
    air = space == space[0, 0, 0]
    depth = ndimage.distance_transform_edt(~air)  # grid steps to the open air
    deepest = ndimage.maximum_position(depth, space, np.arange(1, space.max() + 1))
    cell = m3.Manifold.cube((PITCH / 2,) * 3, True)  # an empty cell's middle: none of it is the solid's, or all
    pocket = np.isin(
        space,
        [
            n
            for n, at in enumerate(deepest, 1)
            if depth[at] > DEEP and (solid ^ cell.translate(low + np.array(at) * PITCH)).is_empty()
        ],
    )

    def fronts(what):
        ahead = [mesh.triangles_center + k * PITCH * mesh.face_normals for k in FRONT]
        return np.any([what[tuple(np.round((p - low) / PITCH).astype(int).T)] for p in ahead], axis=0)

    wall, out = fronts(pocket), fronts(air)
    wall, out = np.flatnonzero(wall & ~out), np.flatnonzero(out & ~wall)
    if not len(wall):
        return solid
    # the faces, each joined to its neighbours by their edge's length (um), then one end the walls, the other outside.
    # An edge four faces share joins none (trimesh): a wall touches the outside along it, and each pair stays closed
    pairs, n = mesh.face_adjacency, len(mesh.faces)
    edges = mesh.vertices[mesh.face_adjacency_edges]
    width = np.maximum(np.rint(1000 * np.linalg.norm(edges[:, 0] - edges[:, 1], axis=1)), 1)
    held = np.full(len(wall) + len(out), 2**30)
    graph = sparse.csr_array(
        (
            np.concatenate([width, width, held]).astype(np.int32),
            (
                np.concatenate([pairs[:, 0], pairs[:, 1], np.full(len(wall), n), out]),
                np.concatenate([pairs[:, 1], pairs[:, 0], wall, np.full(len(out), n + 1)]),
            ),
        ),
        (n + 2, n + 2),
    )
    spare = (graph - csgraph.maximum_flow(graph, n, n + 1).flow).tocsr()  # what more each join could carry
    spare.data[spare.data < 0] = 0
    spare.eliminate_zeros()
    walls = np.ones(n + 2, bool)  # a face is a wall when nothing more can pass from it to the outside
    walls[csgraph.breadth_first_order(spare.T.tocsr(), n + 1, return_predecessors=False)] = False
    walls = walls[:n]
    rim = walls[pairs[:, 0]] != walls[pairs[:, 1]]
    ends = mesh.face_adjacency_edges[rim]
    kept = mesh.faces[np.where(walls[pairs[rim, 0]], pairs[rim, 1], pairs[rim, 0])]  # the outside's face at each
    runs = kept[np.arange(len(kept)), ((kept == ends[:, :1]).argmax(axis=1) + 1) % 3] == ends[:, 1]
    cap = np.where(runs[:, None], ends[:, ::-1], ends)  # against the way its face runs the edge
    joined = sparse.coo_array((np.ones(len(ends)), tuple(ends.T)), (len(mesh.vertices),) * 2)
    _, loop = np.unique(csgraph.connected_components(joined, directed=False)[1][ends[:, 0]], return_inverse=True)
    middle = np.stack([np.bincount(loop, edges[rim].mean(axis=1)[:, k]) for k in range(3)], axis=1)
    middle /= np.bincount(loop)[:, None]
    capped = _solid(
        np.vstack([mesh.vertices, middle]),
        np.vstack([mesh.faces[~walls], np.column_stack([cap, len(mesh.vertices) + loop])]),
    )
    return _whole("the outer skin", capped)


def under(solid, level, pitch=PITCH):
    """The solid `level` mm under the surface of `solid` (manifold3d, with no pocket: outer()), closed, measured on a
    grid of `pitch`."""
    surface = _points(_mesh(solid).triangles, 0.7 * pitch)
    low, space = _spaces(surface, pitch)
    air = space == space[0, 0, 0]
    cap = level + 3 * pitch
    near = np.argwhere(~air & (ndimage.distance_transform_edt(space > 0) <= cap / pitch + 1))
    field = np.where(air, 0.0, -cap).astype(np.float32)
    field[tuple(near.T)] = -np.minimum(cKDTree(surface).query(near * pitch + low, workers=-1)[0], cap)
    v, f, _, _ = measure.marching_cubes(field, level=-level, spacing=(pitch,) * 3)
    out = _solid(v + low, f)
    assert out.volume() > 0  # the field falls inward, so marching cubes winds its faces outward
    return out.simplify(FLAT)


def _swept(view, region, grow=0.0):
    """The region a cut bounds (skin.cuts()), swept through the head along its view's axis: a side view's along x; a
    front view's from the eyes' plane forward, as the review's ahead(), turned about z with its view (skin.TURNED).
    `grow` mm larger all round (smaller, negative): a seam's gap."""
    section, far = m3.CrossSection([np.asarray(region)], m3.FillRule.EvenOdd), skin.FAR
    if grow:
        section = section.offset(grow, m3.JoinType.Round)
    if view == "side":  # (y, z), swept along x
        return m3.Manifold.extrude(section, 2 * far).transform([[0, 0, 1, -far], [1, 0, 0, 0], [0, 1, 0, 0]])
    ahead = m3.Manifold.extrude(section, far).transform([[1, 0, 0, 0], [0, 0, -1, grow], [0, 1, 0, 0]])  # (x, z), -y
    return ahead.rotate((0.0, 0.0, skin.TURNED[view]))


def _angle(a, b):
    """Radians between two 4x4s' turns."""
    return float(np.arccos(np.clip((np.trace(a[:3, :3].T @ b[:3, :3]) - 1) / 2, -1, 1)))


def moves(horn, region, step):
    """The 4x4s the Motion region `region` (skin.MOTION) moves by, in the head's frame, over `horn`'s range, both ends
    among them, the region turning about `step` degrees from one to the next (model/stages.py pose)."""
    stage, eyes = stages.STAGES[morty.DOC], stages.align(*stages.DOCS[morty.DOC]["eyes"])
    part = f"{skin.MOTION[region]}:1"
    back = np.linalg.inv(stage.parts[part].matrix) @ eyes

    def at(deg):
        return np.linalg.inv(eyes) @ stages.pose(stage, horn, deg).parts[part] @ back

    low, high = stage.horns[horn].limits
    n = int(np.ceil(np.degrees(_angle(at(low), at(high))) / step)) + 1
    return [at(deg) for deg in np.linspace(low, high, n)]


def _far(clouds):
    """(its low corner, a grid of REACH: mm from each cell to the nearest point of `clouds`, out to PAD past them)."""
    low = np.min([p.min(axis=0) for p in clouds], axis=0) - PAD
    high = np.max([p.max(axis=0) for p in clouds], axis=0) + PAD
    free = np.ones(np.ceil((high - low) / REACH).astype(int) + 1, bool)
    for points in clouds:
        free[tuple(np.rint((points - low) / REACH).astype(int).T)] = False
    return low, ndimage.distance_transform_edt(free).astype(np.float32) * REACH


def _turned(points, move):
    return points @ move[:3, :3].T + move[:3, 3]


def _given_way(solid, reach, pivot, turn, box):
    """`solid` less wherever what moves against it comes within SEAM: `reach(points)` is the least mm from each point
    to it over its poses, read at each point of a grid of REACH by the solid's wall inside `box` (low, high). The level
    cut to allows the move between two poses (a point's distance from `pivot` times half the `turn` between them,
    radians) and the grids' rounding (inferred: model/morty/test_shells.py holds the gap that is left)."""
    wall = _points(_mesh(solid).triangles, 0.5 * REACH)
    wall = wall[((wall > box[0]) & (wall < box[1])).all(axis=1)]
    corner = wall.min(axis=0) - 4 * REACH
    by = np.zeros(np.ceil((wall.max(axis=0) - corner) / REACH).astype(int) + 5, bool)
    by[tuple(np.rint((wall - corner) / REACH).astype(int).T)] = True
    nodes = np.argwhere(ndimage.binary_dilation(by, iterations=2))
    points = nodes * REACH + corner
    level = SEAM + np.linalg.norm(points - pivot, axis=1).max() * turn / 2 + REACH
    assert level < PAD
    least = np.full(by.shape, np.float32(PAD))
    least[tuple(nodes.T)] = reach(points)
    if not (least < level).any():
        return solid
    v, f, _, _ = measure.marching_cubes(least, level=level, spacing=(REACH,) * 3)
    return solid - _solid(v + corner, f)


def cleared(face, shirt, hair, chin):
    """(the face, the shirt), each less wherever a Shell that moves against it comes within SEAM (_given_way()): the
    chin against the face as the jaw opens, and the hair, the face and the chin (wherever the jaw has it) against the
    shirt as tilt and pan turn the head.

    The pan turns the head about an upright axis under the tilt (model/neck.py HEAD_PARENTS). So the head's reach is
    read in two steps: on a grid round the pan's axis, each point's least distance to the head's Shells along its own
    circle, as far each way as the pan swings; then each point by the shirt's wall, turned back by the tilt every TURN,
    reads that grid."""
    jaw, tilt, pan = moves("jaw horn", "jaw", TURN), moves("tilt horn", "head", TURN), moves("pan horn", "head", TURN)
    hinge, pivot = (np.array(neck.HEAD_AXES[k][0]) for k in ("jaw", "tilt"))  # the pivot is on the pan's axis too
    for point, turns in ((hinge, jaw), (pivot, (*tilt, *pan))):  # each turn leaves its axis where it is
        assert all(np.allclose(_turned(point, m), point, atol=1e-6) for m in turns)
    assert all(np.allclose(m[2, :3], (0, 0, 1), atol=1e-9) for m in pan)  # about an upright axis

    def read(grid, cells):
        """The grid at each cell (n, 3), PAD outside it."""
        ok = ((cells >= 0) & (cells < grid.shape)).all(axis=1)
        out = np.full(len(cells), np.float32(PAD))
        out[ok] = grid[tuple(cells[ok].T)]
        return out

    rest = _points(_mesh(chin).triangles, REACH).astype(np.float32)  # the jaw's poses are closer than the grid
    opened = [_turned(rest, m.astype(np.float32)) for m in jaw]
    low, far = _far([rest])

    def by_the_chin(points):
        return np.min(
            [read(far, np.rint((_turned(points, np.linalg.inv(m)) - low) / REACH).astype(int)) for m in jaw], 0
        )

    box = np.min([p.min(axis=0) for p in opened], axis=0) - PAD, np.max([p.max(axis=0) for p in opened], axis=0) + PAD
    face = _given_way(face, by_the_chin, hinge, max(map(_angle, jaw, jaw[1:], strict=False)), box)

    top, head = _mesh(shirt).bounds[1][2], _mesh(hair + face)
    # what stands higher than LIFT over the shirt never comes down to it: a point moves at most its turn's chord
    drop = 2 * np.sin(max(_angle(np.eye(4), m) for m in tilt) / 2) * np.linalg.norm(head.vertices - pivot, axis=1)
    assert (head.vertices[:, 2] - drop)[head.vertices[:, 2] > top + LIFT].min() > top + PAD
    head = head.triangles[head.triangles[:, :, 2].min(axis=1) < top + LIFT]
    low, far = _far([_points(head, 0.5 * REACH), *opened])  # the head's frame

    def by_the_head(points):
        step = REACH / np.linalg.norm(points - pivot, axis=1).max()  # radians: REACH at the furthest point
        r, n = np.arange(0, REACH / step + REACH, REACH), int(np.ceil(2 * np.pi / step))
        angle = np.arange(n) * (2 * np.pi / n)
        x = np.rint((pivot[0] + np.outer(r, np.cos(angle)) - low[0]) / REACH).astype(int)
        y = np.rint((pivot[1] + np.outer(r, np.sin(angle)) - low[1]) / REACH).astype(int)
        inside = (x >= 0) & (x < far.shape[0]) & (y >= 0) & (y < far.shape[1])
        round_ = far[np.where(inside, x, 0), np.where(inside, y, 0)]
        round_[~inside] = PAD
        # each point's least over the pan: along its circle, the swing each way and a step more
        swing = max(abs(np.arctan2(m[1, 0], m[0, 0])) for m in pan)
        round_ = ndimage.minimum_filter1d(round_, 2 * int(np.ceil(swing / (2 * np.pi / n))) + 3, axis=1, mode="wrap")
        least = np.full(len(points), np.float32(PAD))
        for m in tilt:
            q = _turned(points, np.linalg.inv(m))
            i = np.rint(np.hypot(q[:, 0] - pivot[0], q[:, 1] - pivot[1]) / REACH).astype(int)
            j = np.rint(np.arctan2(q[:, 1] - pivot[1], q[:, 0] - pivot[0]) / (2 * np.pi / n)).astype(int) % n
            k = np.rint((q[:, 2] - low[2]) / REACH).astype(int)
            np.minimum(least, read(round_, np.stack([np.minimum(i, len(r)), j, k], axis=1)), out=least)
        return least

    box = (-skin.FAR,) * 3, (skin.FAR,) * 3
    return face, _given_way(shirt, by_the_head, pivot, max(map(_angle, tilt, tilt[1:], strict=False)), box)


def _whole(name, solid):
    """The Shell's one piece, less what a cut left under KEEP of it: a crumb, or a closed pocket in its wall (a piece
    of negative volume), which prints filled. ValueError when nothing falls in it, or a cut split it or left more."""
    pieces = sorted(solid.decompose(), key=lambda p: -abs(p.volume()))
    if not pieces or pieces[0].volume() <= 0:
        raise ValueError(f"{name}: nothing of the wall falls in it")
    if len(pieces) > 1 and abs(pieces[1].volume()) > KEEP * pieces[0].volume():
        raise ValueError(f"{name}: cut into {[round(p.volume()) for p in pieces[:4]]} mm3, not one piece")
    return pieces[0]


def _disc(r, z0, z1):
    return m3.Manifold.cylinder(z1 - z0, r, circular_segments=96).translate((0, 0, z0))


def _clear(boss, other, turns):
    """`boss` less wherever `other`, a Shell that moves against it, comes within SEAM of it: `turns` are the 4x4s
    `other` is seen through from the boss's own Shell, TURN apart. A boss is no skin, so it gives way where a skin
    would not. Exact solids: the piece of `other` that ever comes near, grown by SEAM (a Minkowski sum with a
    ball), at each turn."""
    box = np.reshape(boss.bounding_box(), (2, 3))
    corners = np.array([(x, y, z) for x in box[:, 0] for y in box[:, 1] for z in box[:, 2]])
    seen = np.vstack([_turned(corners, np.linalg.inv(m)) for m in turns])  # the boss as `other` sees it
    low, high = seen.min(axis=0) - 2 * SEAM, seen.max(axis=0) + 2 * SEAM
    near = other ^ m3.Manifold.cube(high - low).translate(low)
    if near.is_empty():
        return boss
    grown = near.minkowski_sum(m3.Manifold.sphere(SEAM, 24))
    return boss - m3.Manifold.batch_boolean([grown.transform(m[:3]) for m in turns], m3.OpType.Add)


def seated(name, solid, whole, other=None, turns=()):
    """The Shell `name` (`solid`) with its half of each of its Seats (skin.SEATS, model/skin.py), as
    model/printed/skin.py shell() draws a CadQuery Shell's: a boss in from its wall to a face skin.GAP off its
    carrier's, three balls standing out of that face, and its magnet's pocket open from it. The boss is cut at the
    Sculpt's surface (`whole`, its outer skin's solid), so the outside stays the Sculpt's, and gives way to `other`,
    a Shell that moves against this one through `turns` (_clear()); ValueError when the pocket
    would leave under skin.SKIN of it over the magnet."""
    bore, gap, depth = skin.MAGNET[0] / 2 + skin.FIT, skin.GAP, skin.MAGNET[1]
    for seat in (s for s in skin.SEATS if s.shell == name):
        to = np.array(skin.frame(seat))[:3]
        over = _disc(bore, gap + depth, gap + depth + skin.SKIN).transform(to)
        if (over ^ whole).volume() < 0.999 * over.volume():
            raise ValueError(f"{name} at {seat.at}: under {skin.SKIN} mm of it would be left over its magnet")
        add = _disc(skin.PAD_R, gap, gap + seat.boss).transform(to) ^ whole
        if other is not None:
            add = _clear(add, other, turns)
        for deg in (0, 120, 240):
            a = np.radians(deg)
            ball = m3.Manifold.sphere(skin.BALL_R, 48).translate((skin.RING * np.cos(a), skin.RING * np.sin(a), gap))
            add += ball.transform(to)
        solid = solid + add - _disc(bore, gap - 1.0, gap + depth).transform(to)
    return solid


def sculpt():
    """The Sculpt (a manifold3d solid) in the head's frame at rest, from UNDER below the base plane up."""
    mesh = trimesh.load(os.path.join(stages.REPO, morty.SCULPT), process=False).apply_transform(head())
    return _solid(mesh.vertices, mesh.faces).trim_by_plane((0, 0, 1), base() - UNDER)


def outside():
    """The Sculpt's outer skin (outer()), as sculpt() has it: what the Skin's outside is cut from."""
    return outer(sculpt())


def shells():
    """{Shell: its mesh (trimesh), one closed solid in the head's frame at rest}: g.SHELLS["morty"]."""
    whole = outside()
    wall = (whole - under(whole, skin.WALL)).trim_by_plane((0, 0, 1), base())
    cuts = {name: _swept(*cut) for name, cut in skin.cuts().items() if "pupil" not in name}  # the caps carry those
    for side in gm.EYE:
        wall -= cuts[f"{side} eye white"]
    # a seam's gap (SEAM): the face steps back from the hair and the chin, the shirt from the collar

    def grown(name, by):
        return _swept(*skin.cuts()[name], grow=by)

    moving = wall - cuts["collar"]
    hairs = grown("hairline", SEAM)  # the hair's, and its seam's gap
    skinned = moving - hairs
    hair = moving ^ cuts["hairline"]
    out = {
        "hair crown": hair.trim_by_plane((0, 0, 1), LEVEL + SEAM / 2),
        "hair back": hair.trim_by_plane((0, 0, -1), SEAM / 2 - LEVEL),
        "chin": skinned ^ cuts["mouth"],
        "face": skinned - grown("mouth", SEAM),
    }
    # each brow laid on the face, BROW thick, in a bed GLUE under it, keyed by its outline (FIT): the depths are
    # measured round the brows alone
    low, high = np.array(BROWS)
    near = whole ^ m3.Manifold.cube(high - low).translate(low)
    under_a_brow, under_its_bed = under(near, BROW, FINE), under(near, BROW + GLUE, FINE)
    for brow in (f"{side} brow" for side in gm.EYE):
        out[brow] = (skinned ^ cuts[brow]) - under_a_brow
        out["face"] -= grown(brow, FIT) - under_its_bed
    out["face"], out["shirt"] = cleared(out["face"], wall ^ grown("collar", -SEAM), hair, out["chin"])
    assert set(out) == set(g.SHELLS["morty"]), sorted(out)
    # the chin's boss gives way to the face's edge under the jaw, which the opening jaw brings up behind its wall
    away = {"chin": (out["face"], [np.linalg.inv(m) for m in moves("jaw horn", "jaw", TURN)])}
    return {
        f"morty {name}": _mesh(_whole(name, seated(f"morty {name}", solid, whole, *away.get(name, ()))))
        for name, solid in out.items()
    }


def write():
    """Each Shell's STL beside our parts (stages.stl)."""
    os.makedirs(stages.OURS, exist_ok=True)
    for name, mesh in shells().items():
        mesh.export(stages.stl(name))
