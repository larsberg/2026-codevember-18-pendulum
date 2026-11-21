import { Color, MathUtils, RectAreaLight, Spherical, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { RectAreaLightUniformsLib } from 'three/addons/lights/RectAreaLightUniformsLib.js';
import { applyMaterialSettings, defaultMaterials } from './material-settings.js';
import { createFloorReflection } from './floor-reflection.js';
import { instrumentSightline } from './camera.js';
import { cameraCut } from './beat-clock.js';
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

function wireTelevision(channels) {
  const dark = channels[0].lamp.color.clone().multiplyScalar(.16);
  const bright = channels[1].lamp.color.clone().multiplyScalar(.85);
  const wave = new Vector3();
  for (const { screen } of channels) {
    screen.onBeforeCompile = shader => {
      Object.assign(shader.uniforms, { wave: { value: wave }, darkField: { value: dark }, brightField: { value: bright } });
      shader.fragmentShader = 'uniform vec3 wave, darkField, brightField;\n' + shader.fragmentShader.replace(
        '#include <emissivemap_fragment>', `
          float edge = 0.5 - wave.x * sin(wave.y * vEmissiveMapUv.x + wave.z);
          float d = edge - vEmissiveMapUv.y;
          float aa = max(fwidth(d), 0.0001);
          totalEmissiveRadiance *= mix(darkField, brightField, smoothstep(-aa, aa, d));
        `);
    };
  }
  return ({ bass, cycles, phase }) => {
    wave.set(.10 + Math.min(.29, .41 * bass), 2 * Math.PI * cycles, phase);
    // Integrate the bright field over each half so its light follows the glass.
    channels.forEach(({ lamp }, side) => {
      const left = phase + side * wave.y / 2;
      const averageSine = (Math.cos(left) - Math.cos(left + wave.y / 2)) / (wave.y / 2);
      lamp.color.copy(dark).lerp(bright, .5 - wave.x * averageSine).multiplyScalar(1.7);
    });
  };
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
  const stageMeshes = stage.getObjectsByProperty('isMesh', true);
  const floor = stageMeshes.find(mesh => mesh.material.userData.stageFloor);
  const cone = stageMeshes.find(mesh => mesh.userData.role === 'wooferCone');
  const excursion = cone.morphTargetDictionary.Excursion;
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
        tvChannels[source.tvChannel] = { lamp };
      }
    }
    const blockers = [...stageMeshes];
    group.traverse(object => {
      if (object.isMesh) blockers.push(object);
      if (!object.isMesh || object.userData.tvChannel === undefined) return;
      const channel = tvChannels[object.userData.tvChannel];
      channel.screen = object.material;
    });
    group.visible = false;
    scene.add(group);
    const cameras = spec.cameras.map(camera => ({ ...camera,
      view: new Spherical().setFromVector3(toVector(camera.eye).sub(toVector(camera.target))),
    }));
    return { ...spec, group, keyDirection, sun, cameras, blockers, updateScreen: wireTelevision(tvChannels) };
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
  scene.updateMatrixWorld(true);
  const visible = instrumentSightline(instrument, pivot, amplitude);
  let active, angleIndex;
  return {
    pivot,
    get current() { return active; },
    get angle() { return active.cameras[angleIndex]; },
    get angleNumber() { return angleIndex + 1; },
    seesInstrument(camera) { return visible(camera, active.blockers); },
    select(take) {
      if (active) active.group.visible = false;
      ({ shot: active, angle: angleIndex } = cameraCut(take, shots));
      active.group.visible = true;
    },
    updateInstruments(signal) {
      active.updateScreen(signal);
      cone.morphTargetInfluences[excursion] = MathUtils.clamp(2.6 * signal.kick, -.40, 1);
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
      const angle = active.cameras[angleIndex];
      const sign = inverse ? -1 : 1;
      const yaw = view.yaw + sign * (MathUtils.radToDeg(angle.view.theta) - DEFAULT_CAMERA.yaw);
      const elevation = view.elevation + sign * (90 - MathUtils.radToDeg(angle.view.phi) - DEFAULT_CAMERA.elevation);
      return { ...view, yaw: MathUtils.euclideanModulo(yaw + 180, 360) - 180,
        elevation: MathUtils.clamp(elevation, -85, 85),
        distance: view.distance * Math.pow(angle.view.radius / DEFAULT_CAMERA.distance, sign) };
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
