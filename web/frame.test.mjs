// node --test web/frame.test.mjs (make check): the viewer's framing and line width, worked by hand
import { test } from "node:test";
import assert from "node:assert/strict";
import { fit, lineWidth, radiusPx } from "./frame.mjs";

const cube = [-1, 1].flatMap((x) => [-1, 1].flatMap((y) => [-1, 1].map((z) => [x, y, z])));
const front = [0, 0, 1], up = [0, 1, 0], fov90 = 90;
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} != ${b}`);

const distance = (...a) => fit(...a).distance;

test("the nearest corners touch the frame: 1 out of centre + 1 to the edge at 45 deg", () => {
  near(distance(cube, front, up, fov90, 1, 1), 2);
});

test("the margin widens the fit by its factor at the binding edge", () => {
  near(distance(cube, front, up, fov90, 1, 1.1), 2.1);
});

test("a wide frame binds on its height, a tall one on its width", () => {
  near(distance(cube, front, up, fov90, 2, 1), 2);
  near(distance(cube, front, up, fov90, 0.5, 1), 3);
});

test("the camera aims between the binding edges: points off centre move the target, not the distance", () => {
  const { target, distance } = fit(cube.map(([x, y, z]) => [x + 5, y - 3, z]), front, up, fov90, 1, 1);
  target.forEach((v, i) => near(v, [5, -3, 0][i]));
  near(distance, 2);
});

test("the radius on screen: half the height when it spans the half angle", () => {
  near(radiusPx(1, 1, fov90, 480), 240);
  near(radiusPx(1, 2, fov90, 480), 120);
});

test("lines keep their width at the reference size and scale with the Mech on screen", () => {
  assert.equal(lineWidth(2.5, 200, 200), 2.5);
  assert.equal(lineWidth(2.5, 300, 200), 3.75);
});

test("lines stay between one pixel and twice their width", () => {
  assert.equal(lineWidth(2.5, 20, 200), 1);
  assert.equal(lineWidth(2.5, 2000, 200), 5);
});
