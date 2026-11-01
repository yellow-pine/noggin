// The viewer's framing (web/viewer.mjs): plain numbers, no three.js, so node tests them (frame.test.mjs)
const tan = (deg) => Math.tan((deg * Math.PI) / 360);  // of half the angle
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const unit = (a) => a.map((x) => x / Math.hypot(...a));

// The camera along `view` (from the scene toward the camera) of vertical angle fovY and width/height `aspect` that holds
// every point, `margin` x the tightest fit, as the pictures' cameras (model/render/camera.py fit): each frame edge is a
// plane through the camera, which sits where the binding pair of opposite edges both touch a point, centred between
// them on the other axis. Returns where it aims (in the points' frame, on the plane through their origin) and how far
// back from there it sits.
export function fit(points, view, up, fovY, aspect, margin) {
  const back = unit(view), right = unit(cross(up, back)), top = cross(back, right);
  const ty = tan(fovY) / margin, tx = ty * aspect;
  let [a, b, c, d] = [-Infinity, -Infinity, -Infinity, -Infinity];
  for (const p of points) {  // a loop, not Math.max(...): a Stage has more vertices than a call takes arguments
    const x = dot(p, right), y = dot(p, top), z = -dot(p, back);  // z: depth along the view
    [a, b, c, d] = [Math.max(a, x - tx * z), Math.max(b, -x - tx * z), Math.max(c, y - ty * z), Math.max(d, -y - ty * z)];
  }
  const s = (a - b) / 2, t = (c - d) / 2;
  return { target: right.map((r, i) => s * r + t * top[i]), distance: Math.max((a + b) / (2 * tx), (c + d) / (2 * ty)) };
}

// A sphere's radius in pixels on a canvas `height` pixels high, seen from `distance` with vertical angle fovY
export function radiusPx(radius, distance, fovY, height) {
  return (radius / distance / tan(fovY)) * height / 2;
}

// The line width that keeps linePx at the reference size on screen (refPx): one pixel at least, twice linePx at most
export function lineWidth(linePx, rPx, refPx) {
  return Math.min(Math.max((linePx * rPx) / refPx, 1), 2 * linePx);
}
