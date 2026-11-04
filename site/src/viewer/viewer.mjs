// The web viewer (docs/adr/0008): every element of class noggin-viewer on a page draws one Stage, data-stage, from
// Blender's glTF in style B with the look numbers Blender writes into the GLB's extras; the /viewer page's alone has a
// bar of controls under it (#883): the page's buttons (src/pages/viewer.astro: a Stage switch, #720), a chip per clip,
// Explode's levels, the mix; under it, a line on what plays (and the Claude Code event that plays a gesture). Any page
// drops one in with macros.py embed:
//   <div class="noggin-viewer" data-stage="next-stage1" data-link="gesture=wink&view=front&part=next+jaw">
//     <figure>its still</figure><p class="noggin-open"><a href="…/viewer/?stage=1&gesture=wink">Open …</a></p></div>
// whose link GitHub shows and this replaces; the footer (src/components/Footer.astro) loads this module there, which
// Vite bundles with three.js from npm. A page may hold several (#839): one WebGL renderer draws them all, each into
// its own canvas, each GLB is loaded once, and a viewer loads its Stage only once scrolled into view (the home's on a
// phone, data-tap, once tapped), its still until then; of those on screen the three that came into view or were
// touched last animate (state.mjs touched), the rest hold their last frame. Every viewer plays its Stage's hero loop
// (state.mjs looped: Rest where there is none, #889) unless its link names a gesture, which it repeats; it opens from
// its link's view= (front, side, isometric; else the default framing) and, with part=, shows that part alone at full
// look, the rest ghosted. The viewer with Stage buttons (the /viewer page) keeps the address its deep link:
// ?stage=<n>&gesture=<g> opens it on its nth Stage button's Stage playing that gesture once, and each click rewrites
// the address to the deep link of what it plays. It draws the Stage in the Preset the header's bar picks
// (src/theme.mjs, #806, #819: on <html>) unless its link names one, and again in the next one the bar picks; with none
// picked, in the Default build (state.mjs mixed, #889); or in any Shape and Palette (a select per axis, kept in its
// link: ?skeleton-palette=black): Blender's GLB of the Skeleton shape, each Colour group's material painted in its
// Palette's colour (state.mjs paint). Explode moves a Stage's parts from level to level, Assembled, Sub-assemblies,
// Parts, by the offsets each part's node carries (web/build.py explode, model/render/pictures.py offsets, #482, #664,
// #811), &explode=<level> opens it so. Only the /viewer page's (data-zoom) zooms and pans; every other only turns, the
// wheel and a pinch left to the page (state.mjs moves, #598, #889), and once turned shows its one control, a reset.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { mergeVertices } from "three/addons/utils/BufferGeometryUtils.js";
import { LineSegments2 } from "three/addons/lines/LineSegments2.js";
import { LineSegmentsGeometry } from "three/addons/lines/LineSegmentsGeometry.js";
import { LineMaterial } from "three/addons/lines/LineMaterial.js";
import { fit, lineWidth, radiusPx } from "./frame.mjs";
import {
  ANIMATING, LEVELS, address, between, caption as captionFor, glb, looped, mixed, moves, opened, paint, partOf,
  shows, title, touched,
} from "./state.mjs";
import { AXES, picked } from "../theme.mjs";

// the GLBs (just site copies web/build there) and the Draco decoder from npm (package.json prebuild) sit at viewer/
const here = (f) => `${import.meta.env.BASE_URL.replace(/\/$/, "")}/viewer/${f}`;
const loader = new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath(here("draco/")));
const glbs = {};  // each GLB's load, once a page: every viewer of it draws its own clone (its geometry shared)
const fetched = (file) => (glbs[file] ??= loader.loadAsync(here(`${file}.glb`)));
// the one WebGL renderer of the page (#839): it draws a viewer in the bottom-left of its own canvas, which grows to the
// largest viewer, and the viewer copies that corner into its canvas; see-through, the page's own background behind
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(devicePixelRatio);
renderer.shadowMap.enabled = true;
renderer.setScissorTest(true);
const frames = new Map();  // each viewer's frame (its root: its step of dt seconds and its draw)
let seen = [];  // the viewers on screen, by when they came into view or were touched (state.mjs touched)
const watch = new IntersectionObserver((entries) => {
  for (const e of entries) {
    seen = touched(seen, e.target, e.isIntersecting);
    if (e.isIntersecting) e.target.dispatchEvent(new Event("noggin-seen"));
  }
});

function draw(canvas, scene, camera) {
  const w = canvas.clientWidth, h = canvas.clientHeight, size = renderer.getSize(new THREE.Vector2());
  if (!w || !h) return;
  if (size.x < w || size.y < h) renderer.setSize(Math.max(size.x, w), Math.max(size.y, h), false);
  renderer.setViewport(0, 0, w, h);
  renderer.setScissor(0, 0, w, h);
  renderer.render(scene, camera);
  const r = renderer.getPixelRatio(), [W, H] = [Math.floor(w * r), Math.floor(h * r)], from = renderer.domElement;
  if (canvas.width !== W || canvas.height !== H) [canvas.width, canvas.height] = [W, H];
  const out = canvas.getContext("2d");
  out.clearRect(0, 0, W, H);
  out.drawImage(from, 0, from.height - H, W, H, 0, 0, W, H);
}
const FOV = 20;
// framed from its view (state.mjs VIEWS) as the GIFs are on load and Stage switch (MARGIN x the tightest fit), and
// lines line_px wide when the Stage fills a 4:3 frame line_at wide, as in the hero GIF (640 x 480)
const MARGIN = 1.06, GIF_ASPECT = 4 / 3, GHOST = 0.12;  // GHOST: a ghosted part's opacity (part=)
const APART_S = 1;  // the seconds each Explode step takes
const press = (b, on) => b.setAttribute("aria-pressed", on);

function mount(root) {
  const stages = root.querySelectorAll("[data-stage]");
  root.querySelector(":scope > .noggin-open")?.remove();  // the link GitHub shows in the viewer's place
  const poster = root.querySelector(":scope > figure");
  const names = [...stages].map((b) => b.dataset.stage), linked = names.length > 0;
  let own = root.dataset.link ?? "";  // a viewer in a page: its link, its mix kept in it
  const search = () => (linked ? location.search : `?${own}`);
  const link = opened(search(), names, root.dataset.stage), VIEW = new THREE.Vector3(...link.view).normalize();
  const canvas = document.createElement("canvas");
  if (!poster) root.appendChild(canvas);
  canvas.setAttribute("role", "img");
  const zoom = "zoom" in root.dataset;
  const how = zoom ? "drag to turn it, scroll or pinch to zoom" : "drag to turn it";
  canvas.setAttribute("aria-label", `The noggin Mech, rendered from its model; ${how}`);
  // the bar (not-content: no Starlight Markdown spacing in it): the page's Stage buttons, the gestures, Explode's levels
  const tools = document.createElement("div");
  if (linked) root.append(tools);  // the /viewer page's alone: one in a page shows its Mech and motion, no control (#883)
  tools.className = "noggin-controls not-content";
  const bar = document.createElement("nav"), explode = document.createElement("nav");
  bar.setAttribute("aria-label", "Gesture");
  explode.setAttribute("aria-label", "Explode");
  explode.append(document.createElement("span"), ...LEVELS.map(() => document.createElement("button")));
  explode.firstChild.textContent = "Explode";
  tools.append(...root.querySelectorAll(":scope > nav"), explode, bar);
  const levels = [...explode.querySelectorAll("button")];
  // the mix (#819): a select per axis, its Preset's values unless the address names others
  const preset = () => picked(search(), document.documentElement.dataset.preset);  // none: the viewer's own (#883)
  let mix = mixed(search(), preset());
  const mixing = document.createElement("nav");
  mixing.setAttribute("aria-label", "Mix");
  const picks = Object.entries(AXES).map(([axis, values]) => {
    const label = mixing.appendChild(document.createElement("label")), s = document.createElement("select");
    label.append(title(axis.replace("-", " ")), s);
    s.append(...values.map((v) => new Option(title(v), v)));
    s.dataset.axis = axis;
    s.addEventListener("change", () => {
      const link = new URLSearchParams(search());
      link.set(axis, s.value);
      if (linked) history.replaceState(null, "", `${location.pathname}?${link}${location.hash}`);
      else own = `${link}`;
      remix();
    });
    return s;
  });
  tools.append(mixing);
  // the mix the address and the Preset give: a new Skeleton shape is another GLB, Skin shape none too (#876), a new
  // Palette a repaint
  function remix() {
    mix = mixed(search(), preset());
    for (const s of picks) s.value = mix[s.dataset.axis];
    if (!current) return;  // not scrolled into view yet: it loads in this mix
    if (glb(current, mix["skeleton-shape"], mix["skin-shape"]) !== file) load(current, linked ? undefined : link.gesture), share();
    else repaint();
  }
  const caption = root.appendChild(document.createElement("p"));
  caption.className = "noggin-caption";
  const camera = new THREE.PerspectiveCamera(FOV);
  const controls = Object.assign(new OrbitControls(camera, canvas), moves(zoom));
  // the one control an embed carries: once the reader turned it, a reset back to the view it opened on
  const reset = root.appendChild(document.createElement("button"));
  reset.className = "noggin-reset";
  reset.setAttribute("aria-label", "Reset the view");
  reset.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12a8 8 0 1 0 2.3-5.6M4 4v4h4"/></svg>';
  reset.hidden = true;
  controls.addEventListener("start", () => (reset.hidden = false));
  reset.addEventListener("click", () => (scene && spread(), reset.hidden = true));  // a drag may beat the load
  // the key light rides at the camera's upper right and casts shadows; intensity PI makes a part colour x ramp (RE_Direct_Toon
  // divides by PI) and the ambient is the ramp's floor, so a shadowed point gets the N.L <= 0 light as in Eevee
  const key = new THREE.DirectionalLight(0xffffff, Math.PI);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  const ambient = new THREE.AmbientLight(0xffffff);
  const outline = { value: new THREE.Vector2() };  // the hull's push in clip units, per pixel of line
  const band = { value: new THREE.Vector2() };  // the highlight: from N.H, amount toward white
  explode.hidden = true;  // until a Stage with offsets loads
  levels.forEach((b, i) => {
    b.textContent = LEVELS[i];
    b.addEventListener("click", () => (goal = i, pressLevel(), share(gesture)));
  });
  const pressLevel = () => levels.forEach((b, i) => press(b, i === goal));
  let scene, sphere, reach, refPx, mixer, clips, loop, creases, look, current, file, loading = 0;
  // how far apart the parts are (0 together, 1 each sub-assembly apart, 2 each part), the level they are headed to,
  // each part's group with its offset at each level, the camera's framing at each level, and the gesture in the address
  let apart = 0, goal = 0, parts = [], framings, gesture = link.gesture;

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
      o.material = new THREE.MeshToonMaterial({  // named by its Colour group (web/glb.py), which repaint reads
        name: o.material.name, color: o.material.color, gradientMap: gradient,
        polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1,
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
      if (shows(link.part, partOf(o))) o.add(new THREE.Mesh(h, hull), new LineSegments2(lines, creases));
      else Object.assign(o.material, { transparent: true, opacity: GHOST, depthWrite: false }), o.castShadow = false;
    }
  }

  // each part's Colour group in the mix's Palette (the hardware keeps the GLB's grey)
  function repaint() {
    const colours = paint(mix);
    scene?.traverse((o) => o.material?.isMeshToonMaterial && colours[o.material.name] && o.material.color.set(colours[o.material.name]));
  }

  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
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

  // a gesture (a clip's name) plays once, then the viewer's own goes on: its link's gesture again (a viewer in a
  // page), else (none) the Stage's loop (state.mjs looped: the hero, else Rest), round and round
  function play(name) {
    const clip = name ?? loop;
    run(clip);
    for (const b of bar.children) press(b, b.dataset.clip === clip);
    caption.textContent = captionFor(clip);
  }

  function run(clip) {
    mixer.stopAllAction();
    const a = mixer.clipAction(clips[clip]).reset();
    a.setLoop(THREE.LoopOnce, 1).clampWhenFinished = true;
    a.play();
  }

  const next = () => play(linked || !clips[link.gesture] ? undefined : link.gesture);

  // the parts `apart` of the way through the levels, eased, and the camera framing them as the hero GIF does: on load
  // from its view, later moved with the framing from `before`, the last step, so the reader's turn and zoom stay
  function spread(before) {
    const aim = (x) => new THREE.Vector3(...between(framings.map((f) => f.target), x)).add(sphere.center);
    const distance = (x) => between(framings.map((f) => [f.distance]), x)[0];
    for (const [group, offsets] of parts) group.position.fromArray(between(offsets, apart));
    if (before === undefined) {
      controls.target.copy(aim(apart));
      camera.position.copy(controls.target).addScaledVector(VIEW, distance(apart));
      return;
    }
    const back = camera.position.clone().sub(controls.target).multiplyScalar(distance(apart) / distance(before));
    camera.position.copy(controls.target.add(aim(apart).sub(aim(before)))).add(back);
  }

  // the address as the deep link to the Stage (by its button, where the page has them) and the gesture playing: the
  // viewer with Stage buttons alone
  function share(playing) {
    gesture = playing;
    if (!linked) return;
    const link = address(names, current, playing, goal, location.search);
    history.replaceState(null, "", `${location.pathname}${link}${location.hash}`);
  }

  async function load(stage, playing, level = 0) {
    const mine = ++loading;
    current = stage;
    file = glb(stage, mix["skeleton-shape"], mix["skin-shape"]);
    goal = level;  // a Stage switch puts it back together
    for (const b of stages) press(b, b.dataset.stage === stage);
    for (const b of [...bar.children, ...levels]) b.disabled = true;
    root.setAttribute("aria-busy", true);
    const gltf = await fetched(file);
    if (mine !== loading) return;  // a later Stage click won
    poster?.replaceWith(canvas);  // sized before the framing reads it, drawn before the page paints again
    const model = gltf.scene.clone();  // its own nodes and materials, the GLB's geometry
    stylise(model);
    // each part's offsets, assembled and at each level past it, from its node's extras (none: it stays)
    const home = [0, 0, 0], carried = (o, i) => o.userData.explode?.slice(3 * i, 3 * i + 3) ?? home;
    const offsetsOf = (o) => [home, ...LEVELS.slice(1).map((_, i) => carried(o, i))];
    const named = [];
    model.traverse((o) => o.userData.explode && named.push(o));
    parts = named.map((o) => {  // each part in a group that moves it apart, so the clips still pose it
      const group = new THREE.Group();
      o.parent.add(group);
      group.add(o);
      return [group, offsetsOf(o)];
    });
    if (!parts.length) goal = 0;  // a Stage that does not come apart
    // the last Stage's GPU buffers but the GLB's own geometry, which other viewers of it share
    scene?.traverse((o) => { if (!o.material?.isMeshToonMaterial) o.geometry?.dispose(); o.material?.dispose(); });
    scene = new THREE.Scene();
    scene.add(model, camera, key, key.target, ambient);
    repaint();
    sphere = new THREE.Box3().setFromObject(model).getBoundingSphere(new THREE.Sphere());
    reach = sphere.radius + Math.max(0, ...parts.flatMap(([, ds]) => ds.map((d) => Math.hypot(...d))));  // apart too
    const box = key.shadow.camera;  // the shadow map covers the Stage, seen from the key light 2 radii out
    [box.left, box.right, box.bottom, box.top, box.near, box.far] = [-1, 1, -1, 1, 1, 3].map((x) => x * reach);
    box.updateProjectionMatrix();
    key.shadow.normalBias = sphere.radius / 1000;
    key.target.position.copy(sphere.center);
    // shortcut: fits the Stage at rest, not every pose of its hero loop as the GIF does; fit the clips' frames if a
    // pose leaves the view
    const v = new THREE.Vector3(), at = LEVELS.map(() => []);  // every vertex of the Stage from its centre, at each level
    model.traverse((o) => {
      if (!o.material?.isMeshToonMaterial) return;  // the parts, not their hulls and lines
      const p = o.geometry.attributes.position, ds = offsetsOf(o);
      for (let i = 0; i < p.count; i++) {
        const x = v.fromBufferAttribute(p, i).applyMatrix4(o.matrixWorld).sub(sphere.center).toArray();
        ds.forEach((d, k) => at[k].push(x.map((c, j) => c + d[j])));
      }
    });
    camera.fov = FOV;
    const fitted = (aspect, points = at[0]) => fit(points, VIEW.toArray(), [0, 1, 0], camera.fov, aspect, MARGIN);
    const aspect = canvas.clientWidth / canvas.clientHeight, gif = fitted(GIF_ASPECT);
    framings = at.map((points) => fitted(aspect, points));
    apart = goal;
    spread();
    refPx = radiusPx(sphere.radius, Math.hypot(...gif.target, gif.distance), camera.fov, look.line_at / GIF_ASPECT);
    camera.near = sphere.radius / 100;
    camera.far = reach * 100;
    resize();
    clips = Object.fromEntries(gltf.animations.map((c) => [c.name, c]));
    mixer = new THREE.AnimationMixer(model);
    mixer.addEventListener("finished", next);
    loop = looped(Object.keys(clips));
    const others = Object.keys(clips).filter((c) => c !== loop);
    bar.replaceChildren(...[loop, ...others].map((clip) => {  // the loop, then a chip per gesture
      const b = document.createElement("button"), mine = clip === loop ? undefined : clip;
      b.textContent = title(clip.replace(/^next /, ""));
      b.dataset.clip = clip;
      b.addEventListener("click", () => (play(mine), share(mine)));
      return b;
    }));
    explode.hidden = !parts.length;
    for (const b of levels) b.disabled = false;
    pressLevel();
    bar.hidden = caption.hidden = !clips[loop];  // a GLB without clips plays nothing
    if (clips[loop]) play(clips[playing] ? playing : undefined);  // the link's, if the Stage has it
    frame(0);  // its first frame, though it may not animate
    root.setAttribute("aria-busy", false);
  }

  function frame(dt) {
    if (!scene) return;
    mixer.update(dt);
    if (apart !== goal) {
      const before = apart;
      apart = goal > apart ? Math.min(apart + dt / APART_S, goal) : Math.max(apart - dt / APART_S, goal);
      spread(before);
    }
    controls.update();
    lineWidths();
    key.position.fromArray(look.key).normalize().applyQuaternion(camera.quaternion);
    key.position.multiplyScalar(2 * reach).add(sphere.center);
    draw(canvas, scene, camera);
  }

  for (const b of stages) b.addEventListener("click", () => (load(b.dataset.stage), share()));
  document.addEventListener("noggin-theme", () => {  // the bar's new Preset: its own mix, none of the link's
    const link = new URLSearchParams(search());
    for (const axis in AXES) link.delete(axis);
    if (linked) history.replaceState(null, "", `${location.pathname}?${link}${location.hash}`);
    else own = `${link}`;
    remix();
  });
  for (const s of picks) s.value = mix[s.dataset.axis];
  addEventListener("resize", () => scene && (resize(), frame(0)));
  canvas.addEventListener("pointerdown", () => seen.includes(root) && (seen = touched(seen, root, true)));
  frames.set(root, frame);
  const start = () => load(link.stage, link.gesture, link.explode);
  // the home's on a phone (data-tap): its still until a tap, so it costs no GLB on mobile data unasked
  if ("tap" in root.dataset && matchMedia("(pointer: coarse)").matches) root.addEventListener("click", start, { once: true });
  else root.addEventListener("noggin-seen", start, { once: true });
  watch.observe(root);
}

document.querySelectorAll(".noggin-viewer").forEach(mount);
const timer = new THREE.Timer();
renderer.setAnimationLoop((t) => {
  timer.update(t);
  const dt = timer.getDelta();
  for (const root of seen.slice(-ANIMATING)) frames.get(root)(dt);
});
