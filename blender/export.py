"""Re-export the active Blender file after editing a set, camera or light."""
import json
from math import atan, degrees, pi
from pathlib import Path
import bpy
from mathutils import Vector

OUT = Path(bpy.data.filepath).parent.parent / 'public' / 'models'
OUT.mkdir(parents=True, exist_ok=True)


def vector(v):
    """Blender Z-up to glTF Y-up."""
    return [round(float(n), 7) for n in (v.x, v.z, -v.y)]


def export_meshes(scene, filename):
    bpy.context.window.scene = scene
    bpy.ops.object.select_all(action='DESELECT')
    for obj in scene.objects:
        if obj.type in ('MESH', 'EMPTY') and obj.instance_type != 'COLLECTION':
            obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT / (filename+'.glb')), use_selection=True,
                              use_active_scene=True, export_apply=True, export_extras=True,
                              export_meshopt_compression_enable=True, export_meshopt_extension='EXT_meshopt_compression',
                              export_animations=False, export_image_format='WEBP', export_image_quality=86)


export_meshes(bpy.data.scenes['Instrument'], 'metronome')
shots = []
for sc in sorted(bpy.data.scenes, key=lambda scene: scene.name):
    if 'shot' not in sc:
        continue
    export_meshes(sc, sc['shot'])
    socket = next(obj for obj in sc.objects if obj.get('role') == 'instrument')
    target = next(obj for obj in sc.objects if obj.get('role') == 'focus')
    lights = []
    for lamp in sc.objects:
        if lamp.type != 'LIGHT':
            continue
        data = lamp.data
        # Three's rectangular emitters and Blender's area lamps both face local -Z.
        forward = lamp.matrix_world.to_quaternion() @ Vector((0,0,-1))
        up = lamp.matrix_world.to_quaternion() @ Vector((0,1,0))
        light = dict(kind=data.type, position=vector(lamp.location), target=vector(lamp.location+forward),
                     up=vector(up), color=list(data.color), power=data.energy)
        if data.type == 'AREA':
            light.update(width=data.size, height=data.size_y)
        lights.append(light)
    camera = sc.camera
    frame = camera.data.view_frame(scene=sc)
    vfov = degrees(2 * atan(abs(frame[0].y / frame[0].z)))
    shots.append(dict(name=sc['shot'], eye=vector(camera.location), target=vector(target.location),
                      fov=round(vfov,5), position=vector(socket.location), yaw=socket.rotation_euler.z,
                      lights=lights))
(OUT/'shots.json').write_text(json.dumps(shots, indent=2)+'\n')
