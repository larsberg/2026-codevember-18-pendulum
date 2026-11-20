import { Color, MathUtils, RectAreaLight, Spherical, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { RectAreaLightUniformsLib } from 'three/addons/lights/RectAreaLightUniformsLib.js';
import { applyMaterialSettings, defaultMaterials } from './material-settings.js';
import { createFloorReflection } from './floor-reflection.js';
import { DEFAULT_CAMERA } from './settings.js';

const modelDir = `${import.meta.env.BASE_URL}models/`;
const toVector = values => new Vector3().fromArray(values);
const amplitude = Math.PI * .154;
const armAngle = position => amplitude * Math.cos(Math.PI * position);

export function createEscapement(simulation, pivot, tempo, strike) {
  // The motor operates in the dial's local coordinates, independent of which
  // pedestal holds the instrument. A beat is one traverse between extremes.
  const { body } = simulation.addBody({ body: { type: 'kinematic' } });
  const origin = { x: 0, y: 0, z: 0 };
  const velocity = { ...origin };
  let position = 0;
  function pose() { pivot.quaternion.copy(body.getRotation()); }
  function reset(value) {
    position = value;
    const half = armAngle(position) / 2;
    body.setTransform(origin, { x: 0, y: Math.sin(half), z: 0, w: Math.cos(half) });
    body.setAngularVelocity(origin);
    pose();
  }
  simulation.onBeforeStep(dt => {
    const previousBeat = Math.floor(position);
    position += dt * tempo() / 60;
    if (Math.abs(position - Math.round(position)) < 1e-10) position = Math.round(position);
    const current = body.getRotation();
    velocity.y = (armAngle(position) - 2 * Math.atan2(current.y, current.w)) / dt;
    body.setAngularVelocity(velocity);
    if (Math.floor(position) !== previousBeat) strike(Math.floor(position));
  });
  simulation.onSync(pose);
  reset(0);
  return { reset, get position() { return position; } };
}

function makeAreaLight(spec) {
  const radiance = spec.power / (Math.PI * spec.width * spec.height);
  const lamp = new RectAreaLight(new Color(...spec.color), radiance, spec.width, spec.height);
  lamp.position.fromArray(spec.position);
  lamp.up.fromArray(spec.up);
  lamp.lookAt(toVector(spec.target));
  return lamp;
}

const neutralMaterial = defaultMaterials().panels;
const neutralGround = new Color(neutralMaterial.color);
const neutralBackdrop = new Color('#eee9df');

export async function loadSet(scene) {
  RectAreaLightUniformsLib.init();
  const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  const load = async name => (await loader.loadAsync(`${modelDir}${name}.glb`)).scene;
  const [specs, instrument] = await Promise.all([
    fetch(`${modelDir}shots.json`).then(response => {
      if (!response.ok) throw Error(`Could not load the Blender shot list (${response.status}).`);
      return response.json();
    }),
    load('metronome'),
  ]);
  const groundMaterials = new Map();
  const shots = await Promise.all(specs.map(async spec => {
    const group = await load(spec.name);
    const sun = spec.lights.find(source => source.kind === 'SUN');
    const keyDirection = toVector(sun.position).sub(toVector(sun.target)).normalize();
    for (const source of spec.lights.filter(source => source.kind === 'AREA')) group.add(makeAreaLight(source));
    group.visible = false;
    scene.add(group);
    let floor;
    group.traverse(object => {
      const m = object.material;
      if (m?.userData.stageFloor) {
        floor = object;
        groundMaterials.set(m, { color: m.color.clone(), roughness: m.roughness });
      }
    });
    const view = new Spherical().setFromVector3(toVector(spec.eye).sub(toVector(spec.target)));
    return { ...spec, group, keyDirection, sun, view, floor };
  }));
  scene.add(instrument);
  let pivot;
  for (const root of [instrument, ...shots.map(s => s.group)]) root.traverse(object => {
    if (object.userData.role === 'pendulum') pivot = object;
    if (!object.isMesh) return;
    object.castShadow = !object.material.userData.stageFloor;
    object.receiveShadow = true;
    object.layers.enable(1);
  });
  if (!pivot) throw Error('The metronome GLB is missing its escapement pivot.');
  const reflection = createFloorReflection();
  scene.add(reflection.mesh);
  let active;
  return {
    pivot,
    get current() { return active; },
    select(beat) {
      if (active) active.group.visible = false;
      active = shots[beat % shots.length];
      active.group.visible = true;
      reflection.select(active.floor);
      instrument.position.fromArray(active.position);
      instrument.rotation.y = active.yaw;
    },
    setFloor(settings) {
      const material = settings.materials.panels;
      const tint = new Color(material.color).multiply(new Color(settings.studio.background));
      const neutral = neutralGround.clone().multiply(neutralBackdrop);
      tint.setRGB(tint.r / neutral.r, tint.g / neutral.g, tint.b / neutral.b);
      for (const [surface, baked] of groundMaterials) {
        applyMaterialSettings(surface, material, 'panels');
        surface.color.copy(baked.color).multiply(tint);
        surface.roughness = MathUtils.clamp(baked.roughness * material.roughness / neutralMaterial.roughness, .015, 1);
      }
      reflection.configure(settings);
    },
    // The saved camera is a framing adjustment shared by all four Blender lenses.
    cameraView(view, inverse = false) {
      const sign = inverse ? -1 : 1;
      const yaw = view.yaw + sign * (MathUtils.radToDeg(active.view.theta) - DEFAULT_CAMERA.yaw);
      const elevation = view.elevation + sign * (90 - MathUtils.radToDeg(active.view.phi) - DEFAULT_CAMERA.elevation);
      return { ...view, yaw: MathUtils.euclideanModulo(yaw + 180, 360) - 180,
        elevation: MathUtils.clamp(elevation, -85, 85),
        distance: view.distance * Math.pow(active.view.radius / DEFAULT_CAMERA.distance, sign) };
    },
    dispose() {
      reflection.dispose();
      const geometries = new Set(), materials = new Set(), textures = new Set();
      for (const root of [instrument, ...shots.map(s => s.group)]) {
        root.traverse(object => {
          if (object.geometry) geometries.add(object.geometry);
          if (object.material) materials.add(object.material);
        });
        root.removeFromParent();
      }
      for (const material of materials) {
        for (const value of Object.values(material)) if (value?.isTexture) textures.add(value);
        material.dispose();
      }
      for (const texture of textures) { texture.dispose(); texture.source.data?.close?.(); }
      for (const geometry of geometries) geometry.dispose();
    },
  };
}
