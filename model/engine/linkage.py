"""Planar four-bar solver (ADR 0006): every chain of the Mech is crank (horn) -> coupler (bar) -> rocker (lid, eyeball,
tilt arm, pan, jaw) about parallel pivots. Fed with the neutral pin positions from model/geometry.py, so the link
lengths are the ones the joints enforce (the joints meet at the world pins, not at the bars' holes).
Angles are degrees about the +axis, as the recorded sweeps hold them."""

import math

import numpy as np
import trimesh

# In-plane coordinates (u, v) per axis so that a positive angle is a right-handed rotation about the axis.
_PLANE = {(1, 0, 0): (1, 2), (0, 1, 0): (2, 0), (0, 0, 1): (0, 1)}


class Unreachable(ValueError):
    """The coupler cannot span the crank pin and the rocker circle at this crank angle."""


def rotation(axis, deg, about=(0.0, 0.0, 0.0)):
    """4x4 matrix: rotation by deg about the unit `axis` through the point `about` (mm)."""
    return trimesh.transformations.rotation_matrix(math.radians(deg), axis, about)


def four_bar(o2, a0, o4, b0, axis):
    """Four-bar from its neutral pins (mm): crank pivot o2 with pin a0, rocker pivot o4 with pin b0, all turning
    about `axis` (a unit X, Y or Z). Returns solve(crank_deg) -> (rocker_deg, A, B): the rocker's angle from neutral
    and the pins' world points, in the assembly mode that holds at neutral. Raises Unreachable when the loop
    cannot close."""
    u, v = _PLANE[tuple(axis)]
    o2, a0, o4, b0 = (np.asarray(p, float) for p in (o2, a0, o4, b0))
    coupler = float(np.linalg.norm(b0 - a0))
    r4 = math.hypot(b0[u] - o4[u], b0[v] - o4[v])
    phi_a0 = math.atan2(a0[v] - o2[v], a0[u] - o2[u])
    phi_b0 = math.atan2(b0[v] - o4[v], b0[u] - o4[u])
    r2 = math.hypot(a0[u] - o2[u], a0[v] - o2[v])
    # Out-of-plane parts stay as placed: the pins may sit in different planes (coupler squared length splits).
    d_perp = b0 - a0
    d_perp[[u, v]] = 0
    r3 = math.sqrt(max(coupler**2 - float(d_perp @ d_perp), 0.0))
    sign = None

    def solve(crank_deg):
        nonlocal sign
        phi = phi_a0 + math.radians(crank_deg)
        a = a0.copy()
        a[u], a[v] = o2[u] + r2 * math.cos(phi), o2[v] + r2 * math.sin(phi)
        du, dv = o4[u] - a[u], o4[v] - a[v]
        d = math.hypot(du, dv)
        if d > r3 + r4 or d < abs(r3 - r4) or d == 0:
            raise Unreachable(
                f"crank {crank_deg} deg: pin {d:.2f} mm from the rocker pivot, coupler {r3:.2f}, rocker {r4:.2f}"
            )
        along = (r3 * r3 - r4 * r4 + d * d) / (2 * d)
        h = math.sqrt(max(r3 * r3 - along * along, 0.0))
        eu, ev = du / d, dv / d
        modes = [(a[u] + along * eu - s * h * ev, a[v] + along * ev + s * h * eu, s) for s in (1, -1)]
        if sign is None:  # neutral call: the mode whose B lands on b0 holds for the sweep
            sign = min(modes, key=lambda m: math.hypot(m[0] - b0[u], m[1] - b0[v]))[2]
        bu, bv, _ = next(m for m in modes if m[2] == sign)
        b = b0.copy()
        b[u], b[v] = bu, bv
        rocker = math.degrees(math.atan2(bv - o4[v], bu - o4[u]) - phi_b0)
        return (rocker + 180) % 360 - 180, tuple(a), tuple(b)

    solve(0.0)  # fixes the assembly mode at neutral
    solve.o4, solve.axis = tuple(o4), tuple(axis)
    return solve


def rocker_angle(solve, crank_deg, absolute=False):
    """Rocker angle at crank_deg; absolute: from the +u axis of the plane instead of from neutral."""
    rocker, _, b = solve(crank_deg)
    if not absolute:
        return rocker
    u, v = _PLANE[tuple(solve.axis)]
    return math.degrees(math.atan2(b[v] - solve.o4[v], b[u] - solve.o4[u]))
