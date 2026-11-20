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

export function createEscapement(simulation, pivot, clock) {
  // Drive the kinematic reed to the current beat, including after a dropped frame.
  // The transport owns time; integrating the animation would accumulate drift.
  const { body } = simulation.addBody({ body: { type: 'kinematic' } });
  const origin = { x: 0, y: 0, z: 0 }, velocity = { ...origin };
  function pose() { pivot.quaternion.copy(body.getRotation()); }
  simulation.onBeforeStep(dt => {
    const current = body.getRotation();
    velocity.y = (armAngle(clock.position()) - 2 * Math.atan2(current.y, current.w)) / dt;
    body.setAngularVelocity(velocity);
  });
  simulation.onSync(pose);
  return {
    reset(position) {
      const half = armAngle(position) / 2;
      body.setTransform(origin, { x: 0, y: Math.sin(half), z: 0, w: Math.cos(half) });
      body.setAngularVelocity(origin);
      pose();
    },
  };
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
  const [layout, instrument, stage] = await Promise.all([
    fetch(`${modelDir}shots.json`).then(response => {
      if (!response.ok) throw Error(`Could not load the Blender shot list (${response.status}).`);
      return response.json();
    }),
    load('metronome'), load('stage'),
  ]);
  const floor = stage.getObjectByProperty('isMesh', true);
  const ground = floor.material;
  const groundColor = ground.color.clone(), groundRoughness = ground.roughness;
  scene.add(stage);
  const shots = await Promise.all(layout.shots.map(async spec => {
    const group = await load(spec.name);
    const sun = spec.lights.find(source => source.kind === 'SUN');
    const keyDirection = toVector(sun.position).sub(toVector(sun.target)).normalize();
    const tvChannels = [];
    for (const source of spec.lights.filter(source => source.kind === 'AREA')) {
      const lamp = makeAreaLight(source);
      group.add(lamp);
      if (source.tvChannel !== undefined) {
        tvChannels[source.tvChannel] = { lamp, power: lamp.intensity };
      }
    }
    group.traverse(object => {
      if (!object.isMesh || object.userData.tvChannel === undefined) return;
      const channel = tvChannels[object.userData.tvChannel];
      channel.screen = object.material;
      channel.emission = object.material.emissiveIntensity;
    });
    group.visible = false;
    scene.add(group);
    const view = new Spherical().setFromVector3(toVector(spec.eye).sub(toVector(spec.target)));
    return { ...spec, group, keyDirection, sun, view, tvChannels };
  }));
  instrument.position.fromArray(layout.instrument.position);
  instrument.rotation.y = layout.instrument.yaw;
  instrument.scale.fromArray(layout.instrument.scale);
  scene.add(instrument);
  let pivot;
  for (const root of [stage, instrument, ...shots.map(s => s.group)]) root.traverse(object => {
    if (object.userData.role === 'pendulum') pivot = object;
    if (!object.isMesh) return;
    object.castShadow = !object.material.userData.stageFloor;
    object.receiveShadow = true;
    object.layers.enable(1);
  });
  if (!pivot) throw Error('The metronome GLB is missing its escapement pivot.');
  const reflection = createFloorReflection(floor);
  scene.add(reflection.mesh);
  let active;
  return {
    pivot,
    get current() { return active; },
    select(take) {
      if (active) active.group.visible = false;
      active = shots[take % shots.length];
      active.group.visible = true;
    },
    updateTelevision(position) {
      // A slow crossfade between the picture's two phosphor fields. Each field
      // illuminates the set with the same envelope as the glass above it.
      const balance = .26 * Math.cos(Math.PI * position);
      active.tvChannels.forEach(({ screen, emission, lamp, power }, side) => {
        const gain = .88 + (side === 0 ? balance : -balance);
        screen.emissiveIntensity = emission * gain;
        lamp.intensity = power * gain;
      });
    },
    setFloor(settings) {
      const material = settings.materials.panels;
      const tint = new Color(material.color).multiply(new Color(settings.studio.background));
      const neutral = neutralGround.clone().multiply(neutralBackdrop);
      tint.setRGB(tint.r / neutral.r, tint.g / neutral.g, tint.b / neutral.b);
      applyMaterialSettings(ground, material, 'panels');
      ground.color.copy(groundColor).multiply(tint);
      ground.roughness = MathUtils.clamp(groundRoughness * material.roughness / neutralMaterial.roughness, .015, 1);
      reflection.configure(settings);
    },
    // The saved camera is a framing adjustment shared by all Blender lenses.
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
      for (const root of [stage, instrument, ...shots.map(s => s.group)]) {
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
