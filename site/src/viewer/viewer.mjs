// The web viewer (docs/adr/0008): every element of class noggin-viewer on a page draws one Stage, data-stage, from
// Blender's glTF in style B with the look numbers Blender writes into the GLB's extras, a button per clip under it. The
// viewer's page (src/pages/viewer.astro) adds Stage buttons and imports this module, which Vite bundles with three.js
// from npm; a page can drop a small one in with
//   <div class="noggin-viewer" data-stage="stage1"></div>
// and a <script>import "../viewer/viewer.mjs";</script>.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { mergeVertices } from "three/addons/utils/BufferGeometryUtils.js";
import { LineSegments2 } from "three/addons/lines/LineSegments2.js";
import { LineSegmentsGeometry } from "three/addons/lines/LineSegmentsGeometry.js";
import { LineMaterial } from "three/addons/lines/LineMaterial.js";
import { fit, lineWidth, radiusPx } from "./frame.mjs";

// the GLBs (make site copies web/build there) and the Draco decoder from npm (package.json prebuild) sit at viewer/
const here = (f) => `${import.meta.env.BASE_URL.replace(/\/$/, "")}/viewer/${f}`;
const loader = new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath(here("draco/")));
const FOV = 20;
// the hero GIF's view (model/render/pictures.py HERO): 15 deg to the Mech's right, 15 deg up, in glTF's Y-up; framed
// as the GIFs are on load and Stage switch (MARGIN x the tightest fit), and lines line_px wide when the Stage fills a
// 4:3 frame line_at wide, as in the hero GIF (640 x 480)
const VIEW = new THREE.Vector3(-0.25, 0.259, 0.933), MARGIN = 1.06, GIF_ASPECT = 4 / 3;
const press = (b, on) => b.setAttribute("aria-pressed", on);

function mount(root) {
  const stages = root.querySelectorAll("[data-stage]");
  const canvas = root.appendChild(document.createElement("canvas"));
  canvas.setAttribute("role", "img");
  canvas.setAttribute("aria-label", "The noggin Mech, rendered from its model; drag to turn it, scroll or pinch to zoom");
  const bar = root.appendChild(document.createElement("nav"));
  bar.setAttribute("aria-label", "Gesture");
  // see-through: the page's own background behind the Mech, in either theme
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(devicePixelRatio);
  renderer.shadowMap.enabled = true;
  const camera = new THREE.PerspectiveCamera(FOV);
  const controls = new OrbitControls(camera, canvas);
  // the key light rides at the camera's upper right and casts shadows; intensity PI makes a part colour x ramp (RE_Direct_Toon
  // divides by PI) and the ambient is the ramp's floor, so a shadowed point gets the N.L <= 0 light as in Eevee
  const key = new THREE.DirectionalLight(0xffffff, Math.PI);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  const ambient = new THREE.AmbientLight(0xffffff);
  const outline = { value: new THREE.Vector2() };  // the hull's push in clip units, per pixel of line
  const band = { value: new THREE.Vector2() };  // the highlight: from N.H, amount toward white
  let scene, sphere, refPx, mixer, clips, creases, look, loading = 0;

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
    const r = radiusPx(sphere.radius, camera.position.distanceTo(sphere.center), FOV, h);
    creases.linewidth = lineWidth(look.line_px, r, refPx);
    outline.value.set(2 * creases.linewidth / w, 2 * creases.linewidth / h);
  }

  // a gesture plays once, then the hero loops again; Stage 1 has no neck, so no hero: it rests until a gesture
  function play(name) {
    mixer.stopAllAction();
    if (name) {
      const a = mixer.clipAction(clips[name]).reset();
      a.setLoop(name === "hero" ? THREE.LoopRepeat : THREE.LoopOnce, Infinity).clampWhenFinished = true;
      a.play();
    }
    for (const b of bar.children) press(b, b.textContent === name);
  }

  async function load(stage) {
    const mine = ++loading;
    for (const b of stages) press(b, b.dataset.stage === stage);
    for (const b of bar.children) b.disabled = true;
    const gltf = await loader.loadAsync(here(`${stage}.glb`));
    if (mine !== loading) return;  // a later Stage click won
    stylise(gltf.scene);
    scene?.traverse((o) => { o.geometry?.dispose(); o.material?.dispose(); });  // the last Stage's GPU buffers
    scene = new THREE.Scene();
    scene.add(gltf.scene, camera, key, key.target, ambient);
    sphere = new THREE.Box3().setFromObject(gltf.scene).getBoundingSphere(new THREE.Sphere());
    const box = key.shadow.camera;  // the shadow map covers the Stage, seen from the key light 2 radii out
    [box.left, box.right, box.bottom, box.top, box.near, box.far] = [-1, 1, -1, 1, 1, 3].map((x) => x * sphere.radius);
    box.updateProjectionMatrix();
    key.shadow.normalBias = sphere.radius / 1000;
    key.target.position.copy(sphere.center);
    // shortcut: fits the Stage at rest, not every pose of its hero loop as the GIF does; fit the clips' frames if a
    // pose leaves the view
    const v = new THREE.Vector3(), points = [];  // every vertex of the Stage at rest, from its centre
    gltf.scene.traverse((o) => {
      if (!o.material?.isMeshToonMaterial) return;  // the parts, not their hulls and lines
      const p = o.geometry.attributes.position;
      for (let i = 0; i < p.count; i++)
        points.push(v.fromBufferAttribute(p, i).applyMatrix4(o.matrixWorld).sub(sphere.center).toArray());
    });
    const frame = (aspect) => fit(points, VIEW.toArray(), [0, 1, 0], FOV, aspect, MARGIN);
    const fitted = frame(canvas.clientWidth / canvas.clientHeight), gif = frame(GIF_ASPECT);
    controls.target.copy(sphere.center).add(v.fromArray(fitted.target));
    camera.position.copy(controls.target).addScaledVector(VIEW, fitted.distance);
    refPx = radiusPx(sphere.radius, Math.hypot(...gif.target, gif.distance), FOV, look.line_at / GIF_ASPECT);
    camera.near = sphere.radius / 100;
    camera.far = sphere.radius * 100;
    resize();
    clips = Object.fromEntries(gltf.animations.map((c) => [c.name, c]));
    mixer = new THREE.AnimationMixer(gltf.scene);
    mixer.addEventListener("finished", () => play(clips.hero && "hero"));
    bar.replaceChildren(...Object.keys(clips).map((name) => {  // a button per clip: each gesture, and the hero
      const b = document.createElement("button");
      b.textContent = name;
      b.addEventListener("click", () => play(name));
      return b;
    }));
    play(clips.hero && "hero");
  }

  for (const b of stages) b.addEventListener("click", () => load(b.dataset.stage));
  addEventListener("resize", () => scene && resize());
  const timer = new THREE.Timer();
  renderer.setAnimationLoop((t) => {
    timer.update(t);
    if (!scene) return;
    mixer.update(timer.getDelta());
    controls.update();
    lineWidths();
    key.position.fromArray(look.key).normalize().applyQuaternion(camera.quaternion);
    key.position.multiplyScalar(2 * sphere.radius).add(sphere.center);
    renderer.render(scene, camera);
  });
  load(root.dataset.stage);
}

document.querySelectorAll(".noggin-viewer").forEach(mount);
