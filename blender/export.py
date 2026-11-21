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
        if obj.get('role') == 'focus' or ('shot' in scene and obj.name in bpy.data.scenes['Stage'].objects):
            continue
        if obj.type in ('MESH', 'EMPTY') and obj.instance_type != 'COLLECTION':
            obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT / (filename+'.glb')), use_selection=True,
                              use_active_scene=True, export_apply=True, export_extras=True,
                              export_meshopt_compression_enable=True, export_meshopt_extension='EXT_meshopt_compression',
                              export_animations=False, export_image_format='WEBP', export_image_quality=86)


def protected_frame(scene, camera, socket, vertical_slope):
    """Projected subject bounds, measured in units of the frame's half-height."""
    protected = [(obj, socket.matrix_world @ obj.matrix_world)
                 for obj in socket.instance_collection.all_objects if obj.type == 'MESH']
    stage = bpy.data.scenes['Stage'].objects
    for obj in scene.objects:
        if obj.type != 'MESH' or obj.name in stage:
            continue
        root = obj
        while root.parent:
            root = root.parent
        if camera.get('wide', scene.get('wide')) or root.get('television') or root.get('frameSubject'):
            protected.append((obj, obj.matrix_world))
    view = camera.matrix_world.inverted()
    left, right, height = float('inf'), -float('inf'), 0
    for obj, transform in protected:
        local_to_camera = view @ transform
        for vertex in obj.data.vertices:
            x, y, z = local_to_camera @ vertex.co
            if z < 0:
                left = min(left, x / -z)
                right = max(right, x / -z)
                height = max(height, abs(y / z))
    # Leave air around the silhouette on tall screens as well as wide ones.
    fill = camera.get('horizontal_fill', scene.get('horizontal_fill', .90))
    margin = (right-left) * (1/fill-1) / 2
    return [round(n / vertical_slope, 6) for n in (left-margin, right+margin, height/.90)]


export_meshes(bpy.data.scenes['Instrument'], 'metronome')
export_meshes(bpy.data.scenes['Stage'], 'stage')
shots = []
anchor = None
for sc in sorted(bpy.data.scenes, key=lambda scene: scene.name):
    if 'shot' not in sc:
        continue
    export_meshes(sc, sc['shot'])
    socket = next(obj for obj in sc.objects if obj.get('role') == 'instrument')
    pose = dict(position=vector(socket.location), yaw=socket.rotation_euler.z)
    # The instrument is instantiated once by the player; all rooms must match.
    pose['scale'] = [round(s,7) for s in (socket.scale.x,socket.scale.z,socket.scale.y)]
    if anchor is not None and anchor != pose:
        raise ValueError('All rooms must share the same metronome transform')
    anchor = pose
    lights = []
    for lamp in sc.objects:
        if lamp.type != 'LIGHT':
            continue
        data = lamp.data
        # Three's rectangular emitters and Blender's area lamps both face local -Z.
        forward = lamp.matrix_world.to_quaternion() @ Vector((0,0,-1))
        up = lamp.matrix_world.to_quaternion() @ Vector((0,1,0))
        origin = lamp.matrix_world.translation
        light = dict(kind=data.type, position=vector(origin), target=vector(origin+forward),
                     up=vector(up), color=list(data.color), power=data.energy)
        if 'tvChannel' in lamp:
            light['tvChannel'] = lamp['tvChannel']
        if data.type == 'AREA':
            light.update(width=data.size, height=data.size_y)
        lights.append(light)
    cameras = []
    for camera in sorted((o for o in sc.objects if o.type == 'CAMERA'), key=lambda o: o.get('angle_index', 0)):
        target = next(c.target for c in camera.constraints if c.type == 'TRACK_TO' and c.target)
        frame = camera.data.view_frame(scene=sc)
        slope = abs(frame[0].y / frame[0].z)
        cameras.append(dict(label=camera.get('label', camera.name), eye=vector(camera.matrix_world.translation),
                            target=vector(target.matrix_world.translation), fov=round(degrees(2 * atan(slope)), 5),
                            wide=bool(camera.get('wide', sc.get('wide', False))),
                            framing=protected_frame(sc, camera, socket, slope)))
    ambient = sc.world.node_tree.nodes.get('Background').inputs['Strength'].default_value
    shots.append(dict(name=sc['shot'], cameras=cameras, lights=lights, ambient=round(ambient, 5)))
(OUT/'shots.json').write_text(json.dumps(dict(instrument=anchor, shots=shots), indent=2)+'\n')
