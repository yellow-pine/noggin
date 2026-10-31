"""The camera for a picture: looking back along eye_dir with `up` up, fitted so the given points fill the frame
(Blender's camera conventions: it looks down its local -Z, local +Y is up; sensor 36 mm fitted to the width)."""

from collections import namedtuple

import numpy as np

SENSOR_MM = 36.0
Camera = namedtuple("Camera", "matrix lens ortho_scale")  # lens None: orthographic


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def three_quarter(front, side, up, elevation_deg):
    """Unit direction toward the corner between `front` and `side`, raised elevation_deg toward `up`."""
    e = np.radians(elevation_deg)
    return np.cos(e) * _unit(np.add(_unit(front), _unit(side))) + np.sin(e) * _unit(up)


def fit(points, eye_dir, up, aspect, lens=None, margin=1.0):
    """Camera whose frame (width/height = aspect >= 1) holds every point, `margin` x the tightest fit."""
    back = _unit(eye_dir)
    right = _unit(np.cross(up, back))
    top = np.cross(back, right)
    pts = np.asarray(points, float)
    x, y, z = pts @ right, pts @ top, pts @ -back  # z: depth along the view
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2] = right, top, back
    if lens is None:
        cx, cy = (x.max() + x.min()) / 2, (y.max() + y.min()) / 2
        scale = max(x.max() - x.min(), (y.max() - y.min()) * aspect) * margin
        depth = z.min() - (z.max() - z.min()) - scale  # well clear of the nearest point
        m[:3, 3] = cx * right + cy * top + depth * -back
        return Camera(m, None, scale)
    # perspective: each frame edge is a plane through the camera; the camera sits where the binding pair of opposite
    # edges both touch a point, centred between them on the other axis
    tx = SENSOR_MM / 2 / lens / margin
    ty = tx / aspect
    a, b = (x - tx * z).max(), (-x - tx * z).max()
    c, d = (y - ty * z).max(), (-y - ty * z).max()
    depth = min(-(a + b) / (2 * tx), -(c + d) / (2 * ty))
    m[:3, 3] = (a - b) / 2 * right + (c - d) / 2 * top + depth * -back
    return Camera(m, lens, None)


def stand(cam, points, scale, aspect, gap=0.05):
    """An orthographic camera at `scale` with the lowest point `gap` x the frame height above the frame bottom, same
    view and horizontal centre: Stage panels side by side share one scale and one ground line."""
    m = cam.matrix.copy()
    top = m[:3, 1]
    height = scale / aspect
    low = (np.asarray(points, float) @ top).min()
    m[:3, 3] += (low + height * (0.5 - gap) - m[:3, 3] @ top) * top
    return Camera(m, None, scale)
