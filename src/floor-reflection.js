import { LinearMipmapLinearFilter, PlaneGeometry } from 'three';
import { Reflector } from 'three/addons/objects/Reflector.js';

// The cyclorama supplies the lit surface and its shadows. This second pass adds
// only the objects reflected in the flat deck, with a roughness-dependent blur.
export function createFloorReflection(sweep) {
  const mirror = new Reflector(new PlaneGeometry(110, 110), {
    textureWidth: 512, textureHeight: 512, multisample: 0, clipBias: .001,
    shader: {
      uniforms: { ...Reflector.ReflectorShader.uniforms, strength: { value: .18 }, blur: { value: 2.5 } },
      vertexShader: Reflector.ReflectorShader.vertexShader,
      fragmentShader: `
        uniform sampler2D tDiffuse;
        uniform float strength, blur;
        varying vec4 vUv;
        void main() {
          vec4 reflected = textureLod(tDiffuse, vUv.xy / vUv.w, blur);
          gl_FragColor = vec4(reflected.rgb / max(reflected.a, .001), reflected.a * strength);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }
      `,
    },
  });
  mirror.rotation.x = -Math.PI / 2;
  mirror.position.y = .002;
  mirror.material.transparent = true;
  mirror.material.depthWrite = false;
  const map = mirror.getRenderTarget().texture;
  map.generateMipmaps = true;
  map.minFilter = LinearMipmapLinearFilter;
  const capture = mirror.onBeforeRender;
  mirror.onBeforeRender = function (renderer, scene, camera) {
    const background = scene.background, alpha = renderer.getClearAlpha();
    scene.background = null;
    sweep.visible = false;
    renderer.setClearAlpha(0);
    try { capture.call(mirror, renderer, scene, camera); }
    finally {
      renderer.setClearAlpha(alpha);
      scene.background = background;
      sweep.visible = true;
    }
  };
  return {
    mesh: mirror,
    configure(settings) {
      const surface = settings.materials.panels, env = settings.lighting.environment;
      const roughness = sweep.material.roughness;
      mirror.visible = env.enabled && env.intensity > 0 && surface.opacity > 0 && !surface.wireframe;
      mirror.material.uniforms.strength.value = Math.min(.5, .35 * (1 - roughness) * env.intensity * surface.envMapIntensity * surface.opacity);
      mirror.material.uniforms.blur.value = 5 * roughness + env.blur * 12;
    },
    dispose() { mirror.removeFromParent(); mirror.geometry.dispose(); mirror.dispose(); },
  };
}
