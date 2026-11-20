import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { Box3, Matrix4, PerspectiveCamera, Quaternion, Vector3 } from 'three';

import { applyShotLens } from '../src/camera.js';

function glb(file) {
  const bytes = readFileSync(new URL(file, import.meta.url));
  return JSON.parse(bytes.toString('utf8', 20, 20 + bytes.readUInt32LE(12)));
}

function geometry(file, name, transform = new Matrix4()) {
  const model = glb(file);
  const bounds = new Box3();
  function visit(id, parent, inside) {
    const node = model.nodes[id];
    const local = node.matrix ? new Matrix4().fromArray(node.matrix) : new Matrix4().compose(
      new Vector3(...(node.translation ?? [0, 0, 0])), new Quaternion(...(node.rotation ?? [0, 0, 0, 1])),
      new Vector3(...(node.scale ?? [1, 1, 1])));
    const world = parent.clone().multiply(local);
    const selected = inside || !name || node.name === name;
    if (node.mesh !== undefined && selected) {
      for (const part of model.meshes[node.mesh].primitives) {
        const position = model.accessors[part.attributes.POSITION];
        const box = new Box3(new Vector3(...position.min), new Vector3(...position.max));
        if (position.normalized) {
          // The source GLBs use signed 16-bit normalized positions.
          assert.equal(position.componentType, 5122);
          box.min.divideScalar(32767);
          box.max.divideScalar(32767);
        }
        bounds.union(box.applyMatrix4(world));
      }
    }
    node.children?.forEach(child => visit(child, world, selected));
  }
  model.scenes[model.scene ?? 0].nodes.forEach(id => visit(id, transform, false));
  assert.ok(!bounds.isEmpty(), 'Expected geometry in ' + file);
  return bounds;
}

test('the exported furniture and the 21 cm metronome share one physical scale', () => {
  const layout = JSON.parse(readFileSync(new URL('../public/models/shots.json', import.meta.url)));
  const unitsPerMetre = 4;
  for (const [asset, shot, mesh] of [
    ['sofa', 'parlor', 'Sofa'], ['dining-table', 'breakfast', 'Dining-table'],
    ['reading-chair', 'library', 'Reading-chair'], ['sideboard', 'listening', 'Sideboard'],
  ]) {
    const source = geometry('../blender/sources/' + asset + '.glb').getSize(new Vector3()).y;
    const staged = geometry('../public/models/' + shot + '.glb', mesh).getSize(new Vector3()).y;
    assert.ok(Math.abs(source - staged / unitsPerMetre) < .002, asset + ' height differs from catalog');
  }
  const body = geometry('../public/models/metronome.glb');
  const height = body.getSize(new Vector3()).y * layout.instrument.scale[1] / unitsPerMetre;
  assert.ok(Math.abs(height - .21) < .002);
  assert.ok(layout.instrument.position.every(n => n === 0));
  assert.equal(layout.instrument.yaw, 0);
});

test('each dining chair clears the tabletop and the other chairs', () => {
  const file = '../public/models/breakfast.glb';
  const roots = glb(file).nodes.filter(node => node.extras?.role === 'prop');
  const chairs = roots.filter(node => node.name.startsWith('dining-chair / placement'));
  assert.equal(chairs.length, 3);
  const placed = [geometry(file, 'dining-table / placement')];
  for (const chair of chairs) {
    const bounds = geometry(file, chair.name);
    for (const other of placed) assert.ok(!bounds.intersectsBox(other), chair.name);
    placed.push(bounds);
  }
});

test('each TV emitter sits just in front of its corresponding half of the picture', () => {
  const { shots } = JSON.parse(readFileSync(new URL('../public/models/shots.json', import.meta.url)));
  for (const shot of shots) {
    const file = '../public/models/' + shot.name + '.glb';
    const model = glb(file);
    const lights = shot.lights.filter(source => source.tvChannel !== undefined);
    assert.deepEqual(lights.map(light => light.tvChannel).sort(), [0, 1]);
    for (const light of lights) {
      const face = model.nodes.find(node => node.extras?.tvChannel === light.tvChannel);
      const material = model.materials[model.meshes[face.mesh].primitives[0].material];
      assert.ok(material.emissiveTexture && light.kind === 'AREA' && light.power > 0);
      const center = geometry(file, face.name).getCenter(new Vector3());
      const origin = new Vector3(...light.position);
      const normal = new Vector3(...light.target).sub(origin).normalize();
      const gap = origin.clone().sub(center);
      assert.ok(gap.length() < .01 && gap.normalize().dot(normal) > .98, shot.name);
    }
  }
});

test('every cut frames the instrument and TV, and the wide shots frame their furniture', () => {
  const { instrument, shots } = JSON.parse(readFileSync(new URL('../public/models/shots.json', import.meta.url)));
  const instance = new Matrix4().makeScale(...instrument.scale).setPosition(...instrument.position);
  for (const aspect of [16/9, 1, 9/16]) for (const shot of shots) {
    const camera = new PerspectiveCamera(shot.fov, aspect, .1, 900);
    camera.position.fromArray(shot.eye);
    camera.lookAt(new Vector3(...shot.target));
    camera.updateMatrixWorld();
    applyShotLens(camera, shot);
    const clip = new Matrix4().multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    const subject = geometry('../public/models/metronome.glb', undefined, clip.clone().multiply(instance));
    const visible = [subject];
    const file = '../public/models/' + shot.name + '.glb';
    const tv = glb(file).nodes.find(node => node.extras?.television);
    const wide = ['parlor', 'billiards', 'daybed'].includes(shot.name);
    visible.push(geometry(file, wide ? undefined : tv.name, clip));
    for (const bounds of visible) {
      for (const axis of ['x','y','z']) {
        assert.ok(bounds.min[axis] > -1 && bounds.max[axis] < 1, shot.name + ' cropped on ' + axis);
      }
    }
    assert.ok(subject.max.y - subject.min.y < 1, shot.name + ' should give the metronome breathing room');
  }
});
