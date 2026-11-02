// The web viewer (docs/adr/0008): every element of class noggin-viewer on a page draws one Stage, data-stage, from
// Blender's glTF in style B with the look numbers Blender writes into the GLB's extras, and one bar of controls under
// it: the page's buttons (src/pages/viewer.astro: a Stage switch and a look switch, #720), the Tour and a chip per gesture, Explode;
// under the bar, a line on what plays and the Claude Code event that plays it. Any page, a doc's Markdown too, drops a
// small one in with
//   <div class="noggin-viewer" data-stage="stage1"></div>
// and the footer (src/components/Footer.astro) loads this module there, which Vite bundles with three.js from npm. A
// <figure> inside is its poster until the Stage has loaded (the landing page's hero, #468), and a deep link,
// ?stage=<n>&look=plain&gesture=<g>, opens the viewer on its nth Stage button's Stage in that look playing that gesture;
// each click on a button rewrites the address to the deep link of what it plays. Explode moves a Stage's parts apart by the offsets
// macros.json has for it (the next Mech's, model/render/pictures.py EXPLODE, #482, #664) and back, &explode=1 opens it so. Only a
// viewer with data-zoom (the /viewer page) zooms; one in a page turns, and the wheel scrolls past it (#598).
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { mergeVertices } from "three/addons/utils/BufferGeometryUtils.js";
import { LineSegments2 } from "three/addons/lines/LineSegments2.js";
import { LineSegmentsGeometry } from "three/addons/lines/LineSegmentsGeometry.js";
import { LineMaterial } from "three/addons/lines/LineMaterial.js";
import { fit, lineWidth, radiusPx } from "./frame.mjs";
import { address, bony, caption as captionFor, look as lookOf, offsets as offsetsFor, opened, title } from "./state.mjs";

// the GLBs (just site copies web/build there) and the Draco decoder from npm (package.json prebuild) sit at viewer/
const here = (f) => `${import.meta.env.BASE_URL.replace(/\/$/, "")}/viewer/${f}`;
const loader = new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath(here("draco/")));
const FOV = 20;
// the hero GIF's view (model/render/pictures.py HERO): 15 deg to the Mech's right, 15 deg up, in glTF's Y-up; framed
// as the GIFs are on load and Stage switch (MARGIN x the tightest fit), and lines line_px wide when the Stage fills a
// 4:3 frame line_at wide, as in the hero GIF (640 x 480)
const VIEW = new THREE.Vector3(-0.25, 0.259, 0.933), MARGIN = 1.06, GIF_ASPECT = 4 / 3;
const APART_S = 1;  // the seconds Explode takes to move the parts apart, or back
const press = (b, on) => b.setAttribute("aria-pressed", on);

function mount(root) {
  const stages = root.querySelectorAll("[data-stage]"), looks = root.querySelectorAll("[data-look]");
  const poster = root.querySelector("figure");
  const names = [...stages].map((b) => b.dataset.stage), link = opened(location.search, names, root.dataset.stage);
  const canvas = document.createElement("canvas");
  if (!poster) root.appendChild(canvas);
  else {  // the poster picture's box, so the swap keeps the Mech where it was (#597)
    const { width, height } = poster.querySelector("img").attributes;
    canvas.style.cssText = `max-width: ${width.value}px; aspect-ratio: ${width.value} / ${height.value}; margin-inline: auto`;
  }
  canvas.setAttribute("role", "img");
  const zoom = "zoom" in root.dataset;
  const how = zoom ? "drag to turn it, scroll or pinch to zoom" : "drag to turn it";
  canvas.setAttribute("aria-label", `The noggin Mech, rendered from its model; ${how}`);
  // the bar (not-content: no Starlight Markdown spacing in it): the page's Stage buttons, the gestures, Explode
  const tools = root.appendChild(document.createElement("div"));
  tools.className = "noggin-controls not-content";
  const bar = document.createElement("nav"), toggle = document.createElement("button");
  bar.setAttribute("aria-label", "Gesture");
  tools.append(...root.querySelectorAll(":scope > nav"), toggle, bar);
  const caption = root.appendChild(document.createElement("p"));
  caption.className = "noggin-caption";
  // see-through: the page's own background behind the Mech, in either theme
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(devicePixelRatio);
  renderer.shadowMap.enabled = true;
  const camera = new THREE.PerspectiveCamera(FOV);
  const controls = new OrbitControls(camera, canvas);
  controls.enableZoom = zoom;
  // the key light rides at the camera's upper right and casts shadows; intensity PI makes a part colour x ramp (RE_Direct_Toon
  // divides by PI) and the ambient is the ramp's floor, so a shadowed point gets the N.L <= 0 light as in Eevee
  const key = new THREE.DirectionalLight(0xffffff, Math.PI);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  const ambient = new THREE.AmbientLight(0xffffff);
  const outline = { value: new THREE.Vector2() };  // the hull's push in clip units, per pixel of line
  const band = { value: new THREE.Vector2() };  // the highlight: from N.H, amount toward white
  toggle.textContent = "Explode";
  toggle.hidden = true;  // until a Stage with offsets loads
  toggle.addEventListener("click", () => (goal = 1 - goal, press(toggle, goal === 1), share(linked)));
  let scene, sphere, reach, refPx, mixer, clips, tour, step, creases, look, current, loading = 0;
  // how far apart the parts are (0 together, 1 apart), where they are headed, each part's group with its offset, the
  // camera's framing together and apart, and the gesture in the address
  let apart = 0, goal = 0, parts = [], framings, linked = link.gesture;

  // style B from the GLB's look (web/glb.py writes it into the scene's extras): toon colour, a black inverted hull
  // for silhouettes, black crease lines
  function stylise(model) {
    look = model.userData;
    band.value.set(look.highlight_from, look.highlight);
    ambient.intensity = Math.PI * look.ramp[0];
    const ramp = new Uint8Array(look.ramp.map((x) => Math.round(255 * (x - look.ramp[0]))));
    const gradient = new THREE.DataTexture(ramp, ramp.length, 1, THREE.RedFormat);  // nearest filtering
    gradient.needsUpdate = true;
    const hull = new THREE.MeshBasicMaterial({ color: 0, side: THREE.BackSide });
    hull.onBeforeCompile = (s) => {
      s.uniforms.outline = outline;
      s.vertexShader = "uniform vec2 outline;\n" + s.vertexShader.replace("#include <project_vertex>",
        "#include <project_vertex>\ngl_Position.xy += normalize(normalMatrix * normal).xy * outline * gl_Position.w;");
    };
    creases = new LineMaterial({ color: 0 });
    const meshes = [];
    model.traverse((o) => o.isMesh && meshes.push(o));
    for (const o of meshes) {
      const g = o.geometry;
      o.castShadow = o.receiveShadow = true;
      o.material = new THREE.MeshToonMaterial({
        color: o.material.color, gradientMap: gradient, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1,
      });
      o.material.onBeforeCompile = (s) => {
        s.uniforms.band = band;
        s.fragmentShader = "uniform vec2 band;\n" + s.fragmentShader.replace("#include <opaque_fragment>",
          "outgoingLight = mix(outgoingLight, vec3(1.0), band.y * step(band.x, " +
          "dot(normal, normalize(directionalLights[0].direction + geometryViewDir))) * " +
          "step(1e-4, reflectedLight.directDiffuse.g));\n#include <opaque_fragment>");  // none in shadow, as in Eevee
      };
      // split normals at sharp edges would open the hull at every corner: it gets smooth ones
      const h = mergeVertices(new THREE.BufferGeometry().setAttribute("position", g.attributes.position).setIndex(g.index));
      h.computeVertexNormals();
      const lines = new LineSegmentsGeometry().fromEdgesGeometry(new THREE.EdgesGeometry(g, look.crease));
      o.add(new THREE.Mesh(h, hull), new LineSegments2(lines, creases));
    }
  }

  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    creases.resolution.set(w, h);
  }

  // lines follow the Stage's size on screen as the GIFs' do, through every zoom and resize
  function lineWidths() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    const r = radiusPx(sphere.radius, camera.position.distanceTo(sphere.center), camera.fov, h);
    creases.linewidth = lineWidth(look.line_px, r, refPx);
    outline.value.set(2 * creases.linewidth / w, 2 * creases.linewidth / h);
  }

  // a gesture (a clip's name) plays once, then the Tour (none) goes on: every clip in turn, round and round
  function play(name) {
    step = name ? -1 : 0;
    run(name ?? tour[0]);
    for (const b of bar.children) press(b, b.dataset.clip === (name ?? ""));
    caption.textContent = captionFor(name);
  }

  function run(clip) {
    mixer.stopAllAction();
    const a = mixer.clipAction(clips[clip]).reset();
    a.setLoop(THREE.LoopOnce, 1).clampWhenFinished = true;
    a.play();
  }

  function next() {
    if (step < 0) play();
    else run(tour[step = (step + 1) % tour.length]);
  }

  // the parts `apart` of the way out, eased, and the camera framing them as the hero GIF does: on load from its view,
  // later moved with the framing from `before`, the last eased step, so the reader's turn and zoom stay
  function spread(before) {
    const ease = (x) => THREE.MathUtils.smootherstep(x, 0, 1), e = ease(apart), [a, b] = framings;
    const aim = (x) => new THREE.Vector3(...a.target).lerp(new THREE.Vector3(...b.target), x).add(sphere.center);
    const distance = (x) => a.distance + (b.distance - a.distance) * x;
    for (const [group, offset] of parts) group.position.copy(offset).multiplyScalar(e);
    if (before === undefined) {
      controls.target.copy(aim(e));
      camera.position.copy(controls.target).addScaledVector(VIEW, distance(e));
      return;
    }
    const back = camera.position.clone().sub(controls.target).multiplyScalar(distance(e) / distance(ease(before)));
    camera.position.copy(controls.target.add(aim(e).sub(aim(ease(before))))).add(back);
  }

  // the address as the deep link to the Stage (by its button, where the page has them) and the gesture playing
  function share(gesture) {
    linked = gesture;
    history.replaceState(null, "", `${location.pathname}${address(names, current, gesture, goal === 1)}${location.hash}`);
  }

  async function load(stage, gesture, exploded) {
    const mine = ++loading, offsets = offsetsFor(stage);
    current = stage;
    goal = exploded ? 1 : 0;  // a Stage switch puts it back together
    for (const b of stages) press(b, b.dataset.stage === bony(stage));
    for (const b of looks) press(b, b.dataset.look === lookOf(stage));
    for (const b of [...bar.children, toggle]) b.disabled = true;
    root.setAttribute("aria-busy", true);
    const gltf = await loader.loadAsync(here(`${stage}.glb`));
    if (mine !== loading) return;  // a later Stage click won
    poster?.replaceWith(canvas);  // sized before the framing reads it, drawn before the page paints again
    stylise(gltf.scene);
    const named = [];
    gltf.scene.traverse((o) => o.userData.name in offsets && named.push(o));
    parts = named.map((o) => {  // each part in a group that moves it apart, so the clips still pose it
      const group = new THREE.Group();
      o.parent.add(group);
      group.add(o);
      return [group, new THREE.Vector3(...offsets[o.userData.name])];
    });
    scene?.traverse((o) => { o.geometry?.dispose(); o.material?.dispose(); });  // the last Stage's GPU buffers
    scene = new THREE.Scene();
    scene.add(gltf.scene, camera, key, key.target, ambient);
    sphere = new THREE.Box3().setFromObject(gltf.scene).getBoundingSphere(new THREE.Sphere());
    reach = sphere.radius + Math.max(0, ...parts.map(([, d]) => d.length()));  // the Stage's radius, apart too
    const box = key.shadow.camera;  // the shadow map covers the Stage, seen from the key light 2 radii out
    [box.left, box.right, box.bottom, box.top, box.near, box.far] = [-1, 1, -1, 1, 1, 3].map((x) => x * reach);
    box.updateProjectionMatrix();
    key.shadow.normalBias = sphere.radius / 1000;
    key.target.position.copy(sphere.center);
    // shortcut: fits the Stage at rest, not every pose of its hero loop as the GIF does; fit the clips' frames if a
    // pose leaves the view
    const v = new THREE.Vector3(), points = [], away = [];  // every vertex of the Stage at rest, from its centre; apart
    gltf.scene.traverse((o) => {
      if (!o.material?.isMeshToonMaterial) return;  // the parts, not their hulls and lines
      const p = o.geometry.attributes.position, d = new THREE.Vector3(...(offsets[o.userData.name] ?? [0, 0, 0]));
      for (let i = 0; i < p.count; i++) {
        points.push(v.fromBufferAttribute(p, i).applyMatrix4(o.matrixWorld).sub(sphere.center).toArray());
        away.push(v.add(d).toArray());
      }
    });
    // a poster's viewer starts from the poster picture's camera (web/glb.py exports the hero's), its lens too (#597)
    const shot = poster && gltf.cameras[0];
    camera.fov = shot?.fov ?? FOV;
    const frame = (aspect, at = points) => fit(at, VIEW.toArray(), [0, 1, 0], camera.fov, aspect, MARGIN);
    const aspect = canvas.clientWidth / canvas.clientHeight, gif = frame(GIF_ASPECT);
    framings = [frame(aspect), frame(aspect, away)];
    apart = goal;
    spread();
    if (shot) {  // turning about the point of its view line nearest the Stage's centre
      shot.updateWorldMatrix(true, false);
      const at = shot.getWorldPosition(camera.position), ahead = shot.getWorldDirection(new THREE.Vector3());
      controls.target.copy(ahead).multiplyScalar(ahead.dot(v.copy(sphere.center).sub(at))).add(at);
    }
    refPx = radiusPx(sphere.radius, Math.hypot(...gif.target, gif.distance), camera.fov, look.line_at / GIF_ASPECT);
    camera.near = sphere.radius / 100;
    camera.far = reach * 100;
    resize();
    clips = Object.fromEntries(gltf.animations.map((c) => [c.name, c]));
    mixer = new THREE.AnimationMixer(gltf.scene);
    mixer.addEventListener("finished", next);
    tour = Object.keys(clips).sort((a, b) => (b === "hero") - (a === "hero"));  // the hero first, where there is one
    const gestures = tour.filter((c) => c !== "hero");
    bar.replaceChildren(...["", ...gestures].map((clip) => {  // the Tour, then a chip per gesture
      const b = document.createElement("button");
      b.textContent = clip ? title(clip) : "Tour";
      b.dataset.clip = clip;
      b.addEventListener("click", () => (play(clip || undefined), share(clip || undefined)));
      return b;
    }));
    toggle.hidden = !parts.length;
    toggle.disabled = false;
    press(toggle, goal === 1);
    bar.hidden = caption.hidden = !tour.length;  // a GLB without clips plays nothing
    if (tour.length) play(gestures.includes(gesture) ? gesture : undefined);  // the link's, if the Stage has it
    root.setAttribute("aria-busy", false);
  }

  for (const b of stages) b.addEventListener("click", () => (load(b.dataset.stage + lookOf(current)), share()));
  for (const b of looks) b.addEventListener("click", () => (load(bony(current) + b.dataset.look), share()));
  addEventListener("resize", () => scene && resize());
  const timer = new THREE.Timer();
  renderer.setAnimationLoop((t) => {
    timer.update(t);
    if (!scene) return;
    const dt = timer.getDelta();
    mixer.update(dt);
    if (apart !== goal) {
      const before = apart;
      apart = goal ? Math.min(apart + dt / APART_S, 1) : Math.max(apart - dt / APART_S, 0);
      spread(before);
    }
    controls.update();
    lineWidths();
    key.position.fromArray(look.key).normalize().applyQuaternion(camera.quaternion);
    key.position.multiplyScalar(2 * reach).add(sphere.center);
    renderer.render(scene, camera);
  });
  load(link.stage, link.gesture, link.exploded);
}

document.querySelectorAll(".noggin-viewer").forEach(mount);
