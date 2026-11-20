"""Build the editable set. Run with Blender 5.3 in background/factory-startup mode."""
from pathlib import Path
from tempfile import TemporaryDirectory
from math import atan2, cos, pi, radians, sin
import bpy
import numpy as np
from mathutils import Quaternion, Vector

HERE = Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0


def linear(hex_color):
    rgb = [int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return [n / 12.92 if n < .04045 else ((n + .055) / 1.055) ** 2.4 for n in rgb]


def finish(name, color, rough=.3, metal=0, coat=.25):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*linear(color), 1)
    mat.use_nodes = True
    bs = mat.node_tree.nodes.get('Principled BSDF').inputs
    for key, value in [('Base Color', mat.diffuse_color), ('Roughness', rough), ('Metallic', metal),
                       ('Coat Weight', coat), ('Coat Roughness', .13)]:
        bs[key].default_value = value
    return mat


def bevel(obj, width):
    if width:
        mod = obj.modifiers.new('Mould radius', 'BEVEL')
        mod.width, mod.segments = width, 5
        mod.harden_normals = True
        normal = obj.modifiers.new('Face normals', 'WEIGHTED_NORMAL')
        normal.keep_sharp = True
    return obj


def link(name, data):
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def mesh(name, vertices, faces, mat, radius=0):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = link(name, data)
    data.materials.append(mat)
    return bevel(obj, radius)


def cube(name, at, dims, mat, radius=.035, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.object
    obj.name, obj.dimensions = name, dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.parent, obj.location = parent, at
    obj.data.materials.append(mat)
    return bevel(obj, radius)


def cyl(name, at, radius, depth, mat, edge=.025, rot=(0, 0, 0), parent=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=radius, depth=depth)
    obj = bpy.context.object
    obj.name, obj.parent, obj.location, obj.rotation_euler = name, parent, at, rot
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    obj.data.materials.append(mat)
    return bevel(obj, edge)


def empty(name, at, parent=None, role=None):
    obj = link(name, None)
    obj.parent, obj.location, obj.empty_display_size = parent, at, .18
    if role:
        obj['role'] = role
    return obj


def shell(name, levels, mat, radius):
    vertices = [(x * w, y * d + cy, z) for z, w, d, cy in levels for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    faces = [(3, 2, 1, 0)] + [(4*i+j, 4*i+(j+1)%4, 4*i+4+(j+1)%4, 4*i+4+j) for i in range(len(levels)-1) for j in range(4)]
    faces.append(tuple(range(len(vertices)-4, len(vertices))))
    return mesh(name, vertices, faces, mat, radius)


def ring(name, at, inner, outer, depth, material, rot=(0,0,0), arc=2*pi, parent=None):
    n = 112
    full = abs(arc - 2*pi) < .0001
    verts = [(r*cos(i*arc/n), r*sin(i*arc/n), z) for i in range(n if full else n+1)
             for r,z in [(inner,-depth/2),(outer,-depth/2),(outer,depth/2),(inner,depth/2)]]
    faces = [(4*i+j, 4*((i+1)%(len(verts)//4))+j, 4*((i+1)%(len(verts)//4))+(j+1)%4, 4*i+(j+1)%4)
             for i in range(n) for j in range(4)]
    if not full:
        faces.extend([(0,1,2,3), tuple(range(len(verts)-1,len(verts)-5,-1))])
    obj = mesh(name, verts, faces, material, .012)
    for i, p in enumerate(obj.data.polygons):
        p.use_smooth = i < 4*n and i % 4 in (1,3)
    obj.parent, obj.location, obj.rotation_euler = parent, at, rot
    return obj


def ink_mesh(name, rectangles, mat, parent=None, z=.004):
    verts, faces = [], []
    for x,y,dx,dy,angle in rectangles:
        n = len(verts)
        for a,b in [(-dx/2,-dy/2),(dx/2,-dy/2),(dx/2,dy/2),(-dx/2,dy/2)]:
            verts.append((x+a*cos(angle)-b*sin(angle),y+a*sin(angle)+b*cos(angle),z))
        faces.append((n,n+1,n+2,n+3))
    obj = mesh(name, verts, faces, mat)
    obj.parent = parent
    return obj


def text_on_scale(value, x, y, parent, mat, size=.072):
    data = bpy.data.curves.new('Tempo engraving', 'FONT')
    data.body, data.size, data.align_x, data.align_y = value, size, 'CENTER', 'CENTER'
    data.resolution_u = 4
    o = link('Tempo ' + value, data)
    o.parent, o.location = parent, (x, y, .015)
    data.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target='MESH')


porcelain = finish('Ivory-white injection moulding', 'eee9e4', .235, 0, .53)
dial_white = finish('Warm white scale', 'e9e4df', .34, 0, .18)
nickel = finish('Satin nickel', 'b9b8b3', .255, .86, .1)
ink = finish('Printed graphite', '221e20', .49, 0, 0)
black = finish('Ebony rubber', '16191a', .56, 0, 0)
brass = finish('Spun brass', 'ac8653', .29, .72)
ivory = finish('Parchment', 'e4d2ad', .64, 0, .03)
red = finish('Vermilion enamel', 'c24d32', .27)
teal = finish('Petrol enamel', '2c6162', .32)
mustard = finish('Ochre enamel', 'be953f', .32)

master = bpy.context.scene
master.name = 'Instrument'
for x in [-.74,.74]:
    for y in [-.47,.47]:
        cyl('Rubber foot',(x,y,.038),.105,.076,black,.019)
shell('One-piece tapered housing', [(.063,.955,.692,0),(3.83,.372,.29,.081),(3.94,.345,.267,.083)], porcelain,.094)
# The raised lower apron conceals the escapement. Only the polished reed
# emerges from its slot, as on the mechanical reference.
shell('Lower apron',[(.07,.962,.707,-.006),(.16,.956,.735,-.030),(1.09,.812,.657,-.063)],porcelain,.067)
face = empty('Scale plane',(0,-.612,.82))
face.rotation_euler.x = atan2(3.60,.455)

def plate(name, lo, hi, length, mat):
    verts = [(x*w,y,z) for z in [0,.014] for y,w in [(0,lo),(length,hi)] for x in [-1,1]]
    faces = [(0,2,3,1),(4,5,7,6),(0,1,5,4),(1,3,7,5),(3,2,6,7),(2,0,4,6)]
    obj=mesh(name,verts,faces,mat,.012)
    obj.parent=face
    return obj

plate('Inlaid scale',.645,.24,2.93,dial_white)
dial=empty('Tempo scale',(0,0,.018),face)
ticks=[]
left=[208,192,176,160,144,132,120,112,104,96,88,80,72,66,60,56,52,48,44,40]
right=[200,184,168,152,138,126,116,108,100,92,84,76,69,63,58,54,50,46,42]
names={0:'PRESTISSIMO',3:'PRESTO',6:'VIVACE',9:'ALLEGRO',11:'MODERATO',13:'ANDANTE',15:'ADAGIO',17:'LENTO',19:'LARGO'}
for i,num in enumerate(left):
    t=i/(len(left)-1)
    y=.41+2.30*(1-(1-t)**1.48)
    reach=.435-.219*t
    for side in [-1,1]:
        if side==1 and i>=len(right): continue
        yc=y+(.019+.047*(1-t) if side==1 else 0)
        ticks.append((side*(reach+.08)/2,yc,reach-.08,.011,0))
        text_on_scale(str(num if side==-1 else right[i]),side*(reach+.058),yc,dial,ink)
    if i in names:
        text_on_scale(names[i],0,y+.057,dial,ink,size=.050)
ink_mesh('Printed graduations',ticks,ink,dial,z=.005)
arm = empty('Escapement pivot',(0,.004,.073),face,'pendulum')
cube('Satin steel reed',(0,1.46,0),(.068,2.94,.039),nickel,.015,arm)
# Nickel friction weight with three shallow grooves across its lower half.
cube('Sliding weight',(0,1.56,.051),(.276,.36,.134),nickel,.065,arm)
for dy in [-.075,-.031,.013]:
    cube('Rider groove',(0,1.56+dy,.116),(.249,.012,.006),ink,.003,arm)
cube('Reed keeper',(0,2.881,.069),(.194,.234,.10),porcelain,.037,face)
cube('Escapement opening',(0,.265,.049),(.78,.046,.022),black,.013,face)
cyl('Winding bushing',(.873,.03,.73),.121,.13,nickel,rot=(0,pi/2,0))
cyl('Winding stem',(.986,.03,.73),.059,.20,nickel,rot=(0,pi/2,0))
key=ring('Nickel winding key',(1.155,.03,.73),.107,.181,.063,nickel,(pi/2,0,0))
key.scale=(1.18,1,1)

# Collection instances in the numbered Blender scenes refer back to this editable instrument.
instrument = bpy.data.collections.new('Mechanical metronome')
master.collection.children.link(instrument)
for o in list(master.collection.objects):
    instrument.objects.link(o)
    master.collection.objects.unlink(o)
for o in list(master.objects):
    for coll in list(o.users_collection):
        if coll != instrument:
            if o.name not in instrument.objects: instrument.objects.link(o)
            coll.objects.unlink(o)


def at_target(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


UNITS_PER_METRE = 4
METRONOME_HEIGHT_M = .21
stage_scene = bpy.data.scenes.new('Stage')
bpy.context.window.scene = stage_scene
stage = bpy.data.collections.new('Shared petrol cyclorama')
stage_scene.collection.children.link(stage)
ground = finish('Petrol cyclorama', '17494d', .48, 0, .035)
ground['stageFloor'] = True
path = [(-120,0),(8.2,0)] + [(8.2+3*sin(i*pi/64),3-3*cos(i*pi/64)) for i in range(1,33)] + [(11.2,160)]
cove = mesh('Seamless sweep',[(x,y,z) for y,z in path for x in [-110,110]],
            [(2*i,2*i+1,2*i+3,2*i+2) for i in range(len(path)-1)],ground)
for poly in cove.data.polygons: poly.use_smooth = True
stage.objects.link(cove)
stage_scene.collection.objects.unlink(cove)


def shot(name, eye, target, lens, sun, warm, softboxes, *, wide=False):
    sc = bpy.data.scenes.new(name)
    bpy.context.window.scene = sc
    sc['shot'] = name.split(' ',1)[1].lower()
    sc['wide'] = wide
    sc.unit_settings.system, sc.unit_settings.scale_length = 'METRIC', 1/UNITS_PER_METRE
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1600,900,100
    sc.world = bpy.data.worlds.new(name)
    sc.world.use_nodes = True
    sc.world.node_tree.nodes.get('Background').inputs['Color'].default_value = (.48,.48,.48,1)
    sc.world.node_tree.nodes.get('Background').inputs['Strength'].default_value = .32
    sc.collection.children.link(stage)
    socket = empty('Instrument position',(0,0,0),role='instrument')
    socket.instance_type, socket.instance_collection = 'COLLECTION', instrument
    socket.scale = [METRONOME_HEIGHT_M * UNITS_PER_METRE / 3.94] * 3
    focus = empty('Camera focus',target,role='focus')
    cam = link('Camera / '+name,bpy.data.cameras.new(name))
    cam.location, cam.data.lens = eye,lens
    cam.data.sensor_fit = 'HORIZONTAL'
    aim = cam.constraints.new('TRACK_TO')
    aim.target, aim.track_axis, aim.up_axis = focus, 'TRACK_NEGATIVE_Z', 'UP_Y'
    sc.camera = cam
    key = link('Key / '+name,bpy.data.lights.new('Hard key','SUN'))
    key.location = sun
    key.data.energy, key.data.color, key.data.angle = warm[0],linear(warm[1]),radians(4)
    at_target(key,target)
    for i,(at,size,power,color) in enumerate(softboxes):
        a = link('Softbox '+str(i+1),bpy.data.lights.new('Softbox','AREA'))
        a.location = at
        a.data.shape, a.data.size, a.data.size_y = 'RECTANGLE',*size
        a.data.energy, a.data.color = power, linear(color)
        at_target(a,(0,0,1.1))
    return sc


prop_cache = {}

def prop(name, xy, bottom=0, angle=0, tilt=(0, 0)):
    if name in prop_cache:
        obj = prop_cache[name].copy()
        bpy.context.scene.collection.objects.link(obj)
    else:
        bpy.ops.import_scene.gltf(filepath=str(HERE/'sources'/f'{name}.glb'))
        obj, = [o for o in bpy.context.selected_objects if o.type == 'MESH']
        prop_cache[name] = obj
    # Place the rotated bounds. The same bottom coordinate works for a chair
    # on its feet, a chair on its side and a sofa suspended upside down.
    pivot = empty(name+' / placement', (0, 0, 0), role='prop')
    obj.parent = pivot
    pivot.rotation_euler = tuple(radians(a) for a in (*tilt, angle))
    bpy.context.view_layer.update()
    corners = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
    low = Vector([min(c[k] for c in corners) for k in range(3)])
    high = Vector([max(c[k] for c in corners) for k in range(3)])
    pivot.location = (xy[0]-(low.x+high.x)/2, xy[1]-(low.y+high.y)/2, bottom-low.z)
    obj.name = name.capitalize()
    if name in ('clock','cups','vase'):
        bs = obj.data.materials[0].node_tree.nodes.get('Principled BSDF').inputs
        bs['Roughness'].default_value = .29
        bs['Coat Weight'].default_value = .30
    bpy.context.view_layer.update()
    return obj


def surface_height(obj, x, y, below=20):
    """Find the actual supporting face under a prop, including inside a bookcase."""
    inv = obj.matrix_world.inverted()
    hit, point, _, _ = obj.ray_cast(inv @ Vector((x, y, below)), inv.to_3x3() @ Vector((0, 0, -1)))
    if not hit:
        raise ValueError(f'No supporting surface on {obj.name} at {(x, y, below)}')
    return (obj.matrix_world @ point).z + .001


def side_lamp(x, y, bottom):
    lamp = empty('Table lamp', (x, y, bottom), role='prop')
    cyl('Lamp foot', (0,0,.062), .36, .124, brass, .035, parent=lamp)
    cyl('Lamp stem', (0,0,.55), .042, .98, brass, .015, parent=lamp)
    bpy.ops.mesh.primitive_cone_add(vertices=80, radius1=.59, radius2=.40, depth=.60)
    shade = bpy.context.object
    shade.name, shade.parent, shade.location = 'Ivory lamp shade', lamp, (0,0,1.02)
    shade.data.materials.append(ivory)
    for polygon in shade.data.polygons: polygon.use_smooth = len(polygon.vertices)==4
    bevel(shade,.016)


def book(at, angles, cloth):
    volume = empty('Clothbound book', at, role='prop')
    volume.rotation_euler = tuple(radians(a) for a in angles)
    for z in [-.077, .077]:
        cube('Linen board', (0,0,z), (.70,.92,.028), cloth, .012, volume)
    cube('Page block', (.014,0,0), (.64,.865,.126), ivory, .006, volume)
    cube('Cloth spine', (-.327,0,0), (.043,.917,.154), cloth, .015, volume)


def dish(name, profile, material, parent, at=(0,0,0)):
    vertices = [(0,0,profile[0][1])]
    faces = []
    count = 64
    for radius, height in profile:
        vertices.extend((radius*cos(i*2*pi/count), radius*sin(i*2*pi/count), height) for i in range(count))
    vertices.append((0,0,profile[-1][1]))
    for i in range(count):
        j = (i+1) % count
        faces.append((0,1+j,1+i))
        for row in range(len(profile)-1):
            k = 1 + row*count
            faces.append((k+i,k+j,k+count+j,k+count+i))
        k = 1 + (len(profile)-1)*count
        faces.append((k+i,k+j,len(vertices)-1))
    obj = mesh(name,vertices,faces,material)
    obj.parent, obj.location = parent, at
    for face in obj.data.polygons:
        face.use_smooth = True


def place_setting(table, x, y, cup=False):
    place = empty('Melamine place setting', (x,y,surface_height(table,x,y)), role='prop')
    dish('Side plate', [(.28,0),(.30,.012),(.46,.055),(.48,.073),(.47,.083),(.31,.040),(.27,.037)], porcelain, place)
    if cup:
        dish('Espresso cup', [(.105,0),(.13,.017),(.17,.24),(.168,.264),(.151,.264),(.114,.05)],
             teal, place, (0,0,.037))
        ring('Cup handle', (.203,0,.182), .055, .087, .05, teal, (pi/2,0,0), parent=place)


def speaker(at, angles):
    cabinet = empty('Studio monitor', at, role='prop')
    cabinet.rotation_euler = tuple(radians(a) for a in angles)
    cube('Monitor cabinet', (0,0,0), (.98,.85,1.64), black, .07, cabinet)
    for radius, z in [(.31,-.26),(.153,.40)]:
        for name, y, r, depth, mat in [
            ('Driver surround', -.42, radius, .046, ink),
            ('Driver cone', -.455, radius*.78, .023, black),
            ('Dust cap', -.473, radius*.30, .025, nickel),
        ]:
            cyl(name, (0,y,z), r, depth, mat, .012, (pi/2,0,0), cabinet)


def record(at, angles, label):
    disc = empty('LP', at, role='prop')
    disc.rotation_euler = tuple(radians(a) for a in angles)
    ring('Vinyl', (0,0,0), .028, .60, .021, black, parent=disc)
    for side in [-1,1]:
        ring('Centre label', (0,0,side*.012), .028, .19, .004, label, parent=disc)


# One 55-inch television. The two halves of the panel also serve as area
# emitters, so its picture casts different colors from the two sides.
tv_width = 4.87
tv_height = tv_width * 9 / 16
tv_trim = finish('Television / graphite edge', '262932', .23, .52)
tv_case = finish('Television / moulded back', '191c22', .39, .06)
tv_glass = finish('Television / glass border', '101322', .14, .20)


def broadcast_image(name, colors):
    w, h = 512, 288
    y, x = np.mgrid[:h, :w]
    u, v = (x + .5) / w, (y + .5) / h
    # A split-field station ident. The ruled lower half of the disc recalls
    # an analog test card and remains legible when seen obliquely.
    radius = np.hypot((u - .50) * 16/9, v - .53)
    disc = np.clip((.381 - radius) * h, 0, 1)
    stripe = np.clip(((v * 17) % 1 - .35) * 14, 0, 1)
    level = .105 + .16*v + disc*(.72 - .54*(v < .46)*(1-stripe))
    image = bpy.data.images.new(name + ' / broadcast', width=w, height=h)
    pixels = np.ones((h, w, 4), dtype=np.float32)
    for i, color in enumerate(colors):
        zone = slice(i*w//2, (i+1)*w//2)
        # Blender byte images store sRGB pixels. Light colors use linear RGB.
        rgb = level[:, zone, None] * np.array(linear(color))
        pixels[:, zone, :3] = np.where(rgb < .0031308, rgb*12.92, 1.055*rgb**(1/2.4)-.055)
    image.pixels.foreach_set(pixels.ravel())
    image.pack()
    return image


def television(at, aim, roll, colors, power):
    scene_name = bpy.context.scene['shot']
    tv = empty('Floating television', at, role='prop')
    tv['television'] = True
    tv.rotation_mode = 'QUATERNION'
    tv.rotation_quaternion = (Vector(aim) - tv.location).to_track_quat('Z','Y') @ Quaternion((0,0,1), radians(roll))
    w, h = tv_width, tv_height
    cube('TV / graphite frame', (0, -.018, -.080), (w+.16, h+.195, .16), tv_trim, .055, tv)
    cube('TV / rear enclosure', (0, -.17, -.168), (w*.80, h*.69, .11), tv_case, .05, tv)
    cube('TV / glass surround', (0, 0, -.007), (w+.085, h+.085, .025), tv_glass, .029, tv)
    image = broadcast_image(scene_name, colors)
    for channel, color in enumerate(colors):
        x0, x1 = (channel-1)*w/2, channel*w/2
        material = finish(scene_name + ' / phosphor ' + str(channel), '10131b', .27, .05, .12)
        bs = material.node_tree.nodes.get('Principled BSDF')
        tex = material.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = image
        material.node_tree.links.new(tex.outputs['Color'], bs.inputs['Emission Color'])
        bs.inputs['Emission Strength'].default_value = 2.25
        face = mesh('TV / active picture', [(x0,-h/2,.009),(x1,-h/2,.009),(x1,h/2,.009),(x0,h/2,.009)],
                    [(0,1,2,3)], material)
        face.parent = tv
        face['tvChannel'] = channel
        uv = face.data.uv_layers.new()
        for corner, coord in enumerate([(0,0),(1,0),(1,1),(0,1)]):
            uv.data[corner].uv = ((channel+coord[0])/2, coord[1])
        lamp = link('TV / panel light', bpy.data.lights.new('TV / panel light','AREA'))
        lamp.parent, lamp.location = tv, ((x0+x1)/2,0,.012)
        lamp.rotation_euler.x = pi
        lamp['tvChannel'] = channel
        lamp.data.shape, lamp.data.size, lamp.data.size_y = 'RECTANGLE', w/2, h
        lamp.data.color, lamp.data.energy = linear(color), power/2


# The lamp and clock share the end table. The television tilts down towards
# the seat of the sofa, leaving the glossy floor clear around the metronome.
shot('01 Parlor', (1.18,-3.95,1.05), (-.32,2.7,1.95), 16.5,
     (-4.7,-6,7.4),(1.55,'ffe0ae'),[((-3,-2,5),(2.6,4.7),145,'ffebcf')], wide=True)
prop('sofa', (-1.58,5.25), angle=6)
table = prop('side-table', (3.48,3.85), angle=-14)
side_lamp(3.76,4.02, surface_height(table,3.76,4.02))
prop('clock', (2.97,3.53), bottom=surface_height(table,2.97,3.53), angle=-8)
television((-1.47,5.57,5.30), (-.45,.60,.90), -7, ('2ce1f3','6779ff'), 2300)

# Cups stand on the tabletop. Two chairs are planted on the floor and the
# inverted third chair forms a counterweight to the floating television.
shot('02 Breakfast', (-2.5,-4.10,6.60), (-.12,2.58,2.38), 14.1,
     (4,-3,7.5),(1.65,'ffcb99'),[((-.5,-4,6),(1,3.5),155,'fff6e9')])
table = prop('dining-table', (0,3.45))
prop('dining-chair', (-4.02,2.56), angle=52)
prop('dining-chair', (4.03,2.53), angle=-53)
prop('dining-chair', (2.59,7.90), bottom=3.58, angle=-20, tilt=(162,0))
prop('cups', (-.55,3.00), bottom=surface_height(table,-.55,3.00), angle=-18)
place_setting(table,-1.40,3.43, cup=True)
place_setting(table,1.32,2.98)
television((-3.70,5.97,4.88), (.48,2.00,2.28), 13, ('ff674c','ffb446'), 2100)

# Closed volumes stand on one shelf and lie in an offset stack on the next.
shot('03 Library', (2.0,-4.56,1.14), (-.60,2.17,2.02), 21.5,
     (-4,-2,6.3),(1.55,'c9e5ff'),[((3,-3,5),(2.4,3.8),165,'f5ecce')])
case = prop('bookcase', (-5.68,5.66))
prop('reading-chair', (2.38,6.25), angle=-28)
prop('floor-lamp', (4.98,6.66), angle=-36)
for i, cloth in enumerate([teal, ivory, red, mustard, teal, red]):
    x, y = -6.77 + i*.193, 5.55 - .04*(i%3)
    book((x, y, surface_height(case,x,y,3.12)+.46), (90,0,90), cloth)
x, y = -5.48, 5.50
top = surface_height(case,x,y,4.42)
for i, cloth in enumerate([red, ivory, mustard, teal]):
    book((x+.032*i, y-.018*i, top+.091+.183*i), (0,0,82+4*(i%3)), cloth)
television((-.80,3.35,3.60), (-4.70,.85,1.85), 8, ('af72ff','68bbe4'), 2300)

# A playable record and a vase sit on the sideboard. The television hangs
# low to the left of the deck, sending a green highlight across its finish.
shot('04 Listening', (-2.7,-4.7,5.00), (.10,2.75,1.63), 24.5,
     (4.7,-.8,5.8),(1.5,'ffba91'),[((3,2,4.7),(3.5,1),190,'f99cb9')])
console = prop('sideboard', (.98,5.88))
prop('vase', (2.67,5.87), bottom=surface_height(console,2.67,5.87), angle=13)
speaker((-1.09,5.83,surface_height(console,-1.09,5.83)+.82), (0,0,-6))
speaker((4.79,4.84,.82), (0,0,-22))
deck = empty('Record deck', (.91,5.83,surface_height(console,.91,5.83)+.11), role='prop')
cube('Turntable plinth', (0,0,0), (1.83,1.36,.22), teal, .062, deck)
cyl('Aluminium platter', (-.13,0,.151), .60, .082, nickel, .015, parent=deck)
cyl('Spindle', (-.13,0,.217), .023, .082, brass, .006, parent=deck)
tonearm = cube('Pickup arm', (.64,.06,.22), (.043,.73,.047), nickel, .012, deck)
tonearm.rotation_euler.z = radians(-16)
record((deck.location.x-.13, deck.location.y, deck.location.z+.192+.015), (0,0,0), mustard)
television((-3.55,4.10,2.20), (.55,2.53,1.20), 8, ('52d5aa','dcf57c'), 2200)

def ellipsoid(name, at, radii, mat, parent, exponent=1):
    """A smooth sphere or a boxy, upholstered superellipsoid."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16)
    obj = bpy.context.object
    obj.name, obj.parent, obj.location = name, parent, at
    for vertex in obj.data.vertices:
        for axis, radius in enumerate(radii):
            value = vertex.co[axis]
            vertex.co[axis] = np.sign(value) * abs(value)**exponent * radius
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj.data.materials.append(mat)
    return obj


def tube(name, points, radius, mat, parent, *, sampled=False):
    path = bpy.data.curves.new(name, 'CURVE')
    path.dimensions, path.resolution_u = '3D', 5
    path.bevel_depth, path.bevel_resolution, path.use_fill_caps = radius, 2, True
    spline = path.splines.new('BEZIER')
    spline.bezier_points.add(len(points)-1)
    for point, position in zip(spline.bezier_points, points):
        point.co = position
        point.handle_left_type = point.handle_right_type = 'VECTOR' if sampled else 'AUTO'
    obj = link(name,path)
    obj.parent = parent
    path.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target='MESH')
    return obj


def rod(name, a, b, r1, r2, mat, parent):
    axis = Vector(b) - Vector(a)
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=r1, radius2=r2, depth=axis.length)
    obj = bpy.context.object
    obj.name, obj.parent, obj.location = name, parent, (Vector(a)+Vector(b))/2
    obj.rotation_euler = axis.to_track_quat('Z','Y').to_euler()
    obj.data.materials.append(mat)
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices)==4
    return obj


mint = finish('Celadon ABS', '78aa95', .22, 0, .48)
orange = finish('Persimmon ABS', 'e46c3e', .23, 0, .45)
plum = finish('Oxblood vinyl', '793644', .34, 0, .25)
steel = finish('Brushed chrome', 'ccd0d2', .22, .85)
linen = finish('Unbleached cotton', 'e6d5bb', .83, 0, 0)


walnut = finish('Walnut lacquer','61362b',.28,0,.30)

def telephone(x, y, z, yaw, enamel):
    phone = empty('Rotary telephone',(x,y,z),role='prop')
    phone.rotation_euler.z = radians(yaw)
    shell_body = shell('Bakelite bell housing',
                       [(0,.48,.40,0),(.09,.52,.43,0),(.25,.45,.35,.04),(.35,.34,.21,.14)], enamel,.066)
    shell_body.parent = phone
    dial = empty('Sloped dial',(0,-.15,.276),phone)
    dial.rotation_euler.x = radians(15)
    cyl('Finger plate',(0,0,0),.28,.045,brass,parent=dial)
    cyl('Number card',(0,0,.027),.112,.012,porcelain,parent=dial)
    for i in range(10):
        a = radians(38 + i*29)
        cyl('Dial recess',(.207*cos(a),.207*sin(a),.024),.039,.012,ink,.003,parent=dial)
    tube('Receiver grip',[(-.49,.21,.38),(-.39,.23,.51),(-.22,.23,.55),(.22,.23,.55),(.39,.23,.51),(.49,.21,.38)],
         .104,enamel,phone)
    for xend in [-.485,.485]:
        ellipsoid('Receiver cap',(xend,.198,.39),(.152,.172,.118),enamel,phone,.75)
    points = [(-.51,.23,.41),(-.70,.17,.21),(-.74,.06,.10)]
    for i in range(73):
        a = i*pi/4
        points.append((-.74+i*.006, -.03-.12*i/72+.040*cos(a), .074+.037*sin(a)))
    tube('Curled handset lead',points,.017,ink,phone)


shot('05 Exchange', (3.15,-4.38,4.18), (-.15,3.03,2.32), 22.5,
     (-3.2,-3,6.6),(1.35,'ffe1c0'),[((1.2,-2,6),(3,3),155,'d5e5ff')])
desk = empty('Switchboard desk',(-.90,4.65,0),role='prop')
cube('Lacquered counter',(0,0,2.80),(6.90,1.90,.22),ivory,.105,desk)
cube('Edge band',(0,0,2.66),(6.78,1.80,.09),orange,.038,desk)
for x in [-2.85,2.85]:
    path = [(x,-.70,2.68)]
    for side in [-1,1]:
        angles = np.linspace(0,pi/2,10) if side < 0 else np.linspace(pi/2,0,10)
        path.extend((x,side*(.52+.18*cos(a)),.28-.18*sin(a)) for a in angles)
    path.append((x,.70,2.68))
    tube('Bent tubular trestle',path,.10,red,desk,sampled=True)
for x, yaw, mat in [(-3.00,-12,mint),(-.91,0,orange),(1.20,12,porcelain)]:
    telephone(x,4.53,2.911,yaw,mat)
stool = empty('Operator stool',(-4.72,3.28,0),role='prop')
cyl('Weighted foot',(0,0,.07),.68,.14,ink,parent=stool)
cyl('Adjustable post',(0,0,.82),.11,1.50,steel,parent=stool)
ring('Footrest',(0,0,.60),.42,.47,.06,steel,parent=stool)
for k in range(3):
    a = k*2*pi/3
    rod('Footrest spoke',(0,0,.60),(.45*cos(a),.45*sin(a),.60),.029,.029,steel,stool)
ellipsoid('Vinyl seat',(0,0,1.64),(.77,.77,.16),plum,stool,.65)
television((4.03,5.52,3.83),(-.95,1.25,2.15), -71, ('ef608f','708aff'), 2350)


# A scalloped playing surface leaves real openings between the cushion ends.
shot('06 Billiards', (4.55,-4.10,6.85), (0,3.25,2.10), 25,
     (2.2,0,8.7),(1.5,'e6fff4'),[((-4,-1,5.8),(3,2),215,'fcdbab')], wide=True)
table = empty('Billiard table',(-.60,4.66,0),role='prop')
table.rotation_euler.z = radians(-6)
felt = finish('Tournament baize','16654f',.91,0,0)
for x in [-2.85,2.85]:
    for y in [-1.28,1.28]:
        rod('Tapered table leg',(x,y,.05),(x*.97,y*.95,2.65),.18,.32,walnut,table)
        cyl('Brass foot',(x,y,.07),.19,.14,brass,parent=table)
cube('Table apron',(0,0,2.67),(8.34,4.20,.53),walnut,.16,table)
hx, hy, pocket, bed_z = 4.01, 1.96, .235, 3.05
outline = []
def pocket_arc(x,y,start,end):
    for angle in np.linspace(radians(start),radians(end),13):
        outline.append((x+pocket*cos(angle),y+pocket*sin(angle),bed_z))
pocket_arc(0,-hy,180,0)
pocket_arc(hx,-hy,180,90)
pocket_arc(hx,hy,270,180)
pocket_arc(0,hy,0,-180)
pocket_arc(-hx,hy,0,-90)
pocket_arc(-hx,-hy,90,0)
cloth = mesh('Pocket-cut baize',outline,[tuple(range(len(outline)))],felt)
cloth.parent = table
for y in [-hy,hy]:
    for x in [-hx,0,hx]:
        cyl('Pocket well',(x,y,2.949),.238,.026,black,.005,parent=table)
    for x in [-hx/2,hx/2]:
        cube('Long cushion',(x,y,bed_z+.007),(hx-.53,.28,.20),felt,.066,table)
        cube('Rail cap',(x,y*1.10,bed_z-.005),(hx-.43,.20,.27),walnut,.070,table)
        for offset in [-.78,.78]:
            cyl('Ivory sight',(x+offset,y*1.10,bed_z+.134),.037,.010,porcelain,.003,parent=table)
for x in [-hx,hx]:
    cube('End cushion',(x,0,bed_z+.007),(.28,hy*2-.53,.20),felt,.066,table)
    cube('End rail',(x*1.05,0,bed_z-.005),(.20,hy*2-.43,.27),walnut,.065,table)
ball_mats = [mustard,teal,red,plum,orange,mint,ink]
for row in range(5):
    for col in range(row+1):
        mat = ball_mats[(row*3+col)%len(ball_mats)]
        ball = ellipsoid('Racked ball',(1.04+row*.203,(col-row/2)*.234,bed_z+.115),(.115,)*3,mat,table)
        if row >= 3:
            ball.data.materials.append(porcelain)
            for face in ball.data.polygons:
                if abs(face.center.z)>.063: face.material_index=1
ellipsoid('Cue ball',(-1.88,.16,bed_z+.115),(.115,)*3,porcelain,table)
rod('Maple cue',(-3.41,-1.13,bed_z+.062),(2.65,-1.40,bed_z+.026),.062,.026,ivory,table)
television((-4.55,5.95,4.97),(-1.65,2.55,2.25), 8, ('39d2a2','ffe97c'), 1850)


def rubber_plant(at, scale, pot, leaf_mats, twist):
    plant = empty('Potted rubber plant',at,role='prop')
    plant.scale = (scale,)*3
    plant.rotation_euler.z = radians(twist)
    dish('Stoneware planter',[(.48,0),(.52,.045),(.68,.93),(.70,1.02),(.69,1.055),(.62,1.055),(.61,.89)],pot,plant)
    cyl('Potting soil',(0,0,.95),.625,.048,walnut,.01,parent=plant)
    tube('Central stem',[(0,0,.94),(-.09,.06,1.78),(.08,0,2.52),(.01,.06,3.35)],.043,leaf_rib,plant)
    for i in range(10):
        a = i*2.40 + .40
        direction = Vector((cos(a),sin(a),0))
        side = Vector((-sin(a),cos(a),.75*cos(a+.29))).normalized()
        base = Vector((.025*sin(i),.03,1.40+i*.199))
        tip = .99 + .31*sin(i*.51)
        start = base + direction*.24 + Vector((0,0,.17))
        tube('Petiole',[base,base+direction*.14+Vector((0,0,.05)),start],.025,leaf_rib,plant)
        vertices, faces, vein = [], [], []
        for row in range(13):
            t = row/12
            shape = sin(pi*t)**.76
            middle = start + direction*(tip*t) + Vector((0,0,.33*sin(pi*t) + (.19+.38*cos(i*.77))*t))
            width = .37*shape+.006
            for transverse in [-1,-.52,0,.52,1]:
                vertices.append(tuple(middle + side*width*transverse + Vector((0,0,-.105*shape*abs(transverse)**1.2))))
            vein.append(tuple(middle+Vector((0,0,.008))))
            if row:
                for j in range(4):
                    k=(row-1)*5+j
                    faces.append((k,k+5,k+6,k+1))
        leaf = mesh('Glazed rubber leaf',vertices,faces,leaf_mats[i%len(leaf_mats)])
        leaf.parent=plant
        for face in leaf.data.polygons: face.use_smooth=True
        tube('Midrib',vein[::3],.010,leaf_rib,plant)


shot('07 Conservatory', (-.95,-4.60,1.75), (-.48,3.12,2.22), 23.5,
     (-4.8,-1,6.9),(1.45,'ffe8c5'),[((3.8,1.7,5.7),(1.8,3.1),165,'e7ffd9')])
leaf_rib = finish('Leaf midrib','9caa68',.50,0,.1)
foliage = [finish('Bottle green leaf','22654c',.31),finish('New jade leaf','609358',.28)]
rubber_plant((-3.60,5.48,0),1.46,mustard,foliage,16)
for x,y,height,scale,color,angle in [(1.45,6.91,1.26,1.03,porcelain,152),(3.80,4.24,.58,.76,orange,78)]:
    stand = empty('Enamel plant stand',(x,y,0),role='prop')
    cyl('Round foot',(0,0,.06),.64,.12,teal,parent=stand)
    cyl('Pedestal',(0,0,height/2),.16,height-.10,teal,parent=stand)
    cyl('Plant saucer',(0,0,height-.055),.84,.11,teal,parent=stand)
    rubber_plant((x,y,height+.001),scale,color,foliage,angle)
can = empty('Watering can',(-.75,3.38,0),role='prop')
dish('Enamel can',[(.34,0),(.41,.05),(.46,.65),(.36,.77),(.29,.78),(.28,.69)],mint,can)
rod('Long spout',(.32,0,.23),(1.02,0,.81),.135,.075,mint,can)
tube('Can handle',[(-.35,0,.54),(-.69,0,.75),(-.65,0,1.10),(-.19,0,1.14),(.04,0,.73)],.059,mint,can)
television((-.48,3.14,5.44),(-.10,.74,.64), -17, ('ff9671','c2ff96'), 2300)


def washer(x,y,case):
    washer = empty('Front-loading washer',(x,y,0),role='prop')
    cube('Machine base',(0,0,.09),(2.18,2.24,.18),black,.055,washer)
    cube('Enamel cabinet',(0,0,1.75),(2.36,2.45,3.32),case,.105,washer)
    cube('Rolled top',(0,0,3.42),(2.38,2.47,.09),porcelain,.042,washer)
    axis=(pi/2,0,0)
    cyl('Door gasket',(0,-1.24,1.64),.883,.115,ink,rot=axis,parent=washer)
    ring('Chrome porthole',(0,-1.32,1.64),.679,.84,.14,steel,axis,parent=washer)
    ellipsoid('Smoked door glass',(0,-1.36,1.64),(.674,.107,.674),smoke,washer)
    ring('Drum reflection',(0,-1.451,1.62),.43,.454,.012,teal,axis,arc=pi*1.17,parent=washer)
    cube('Detergent drawer',(-.63,-1.237,2.96),(.74,.07,.32),porcelain,.041,washer)
    cube('Recessed pull',(-.63,-1.279,2.92),(.48,.024,.042),ink,.014,washer)
    cyl('Cycle selector',(.02,-1.29,2.95),.177,.14,nickel,rot=axis,parent=washer)
    cube('Dial index',(.02,-1.367,3.036),(.022,.014,.083),ink,.006,washer)
    cube('Timer display',(.70,-1.244,2.97),(.55,.042,.21),smoke,.030,washer)
    for j in range(3):
        cyl('Panel key',(.49+.18*j,-1.254,2.73),.036,.045,porcelain,.007,rot=axis,parent=washer)
    return 3.465


shot('08 Launderette', (-.56,-5.45,2.03), (-.12,3.47,1.87), 24,
     (3.6,-4.1,7.6),(1.65,'e7f8ff'),[((-3,-1.5,5),(3.3,1.5),215,'fff1e4')])
smoke = finish('Smoked acrylic','203948',.115,.32,.70)
wash_top = washer(-2.83,5.22,mint)
washer(-.30,5.22,porcelain)
for i, mat in enumerate([linen,red,linen]):
    towel = empty('Folded hand towel',(-2.89+.04*i,5.12,wash_top+.001+.177*i),role='prop')
    towel.rotation_euler.z=radians(4+i*3)
    ellipsoid('Terry fold',(0,0,.088),(.64,.44,.088),mat,towel,.39)
cart = empty('Rolling laundry basket',(2.02,2.72,0),role='prop')
for x in [-.60,.60]:
    for y in [-.36,.36]:
        cyl('Caster',(x,y,.14),.14,.10,black,.018,(pi/2,0,0),cart)
        rod('Caster fork',(x,y,.14),(x,y,.34),.043,.043,steel,cart)
cube('Basket bottom',(0,0,.37),(1.55,1.0,.13),mint,.065,cart)
# A continuous rectangular hoop with bowed corners follows the basket taper.
def basket_hoop(a,b,z):
    points = [(a*np.sign(cos(t))*abs(cos(t))**.42,
               b*np.sign(sin(t))*abs(sin(t))**.42,z) for t in np.linspace(0,2*pi,33)]
    tube('Wire rim',points,.030,steel,cart)
for z in [.50,.86,1.22,1.59]:
    t = (z-.37)/1.22
    basket_hoop(.75+.19*t,.48+.15*t,z)
for a in np.linspace(0,2*pi,20,endpoint=False):
    x,y=np.sign(cos(a))*abs(cos(a))**.42,np.sign(sin(a))*abs(sin(a))**.42
    rod('Basket upright',(.75*x,.48*y,.39),(.94*x,.63*y,1.59),.019,.022,steel,cart)
for i, mat in enumerate([linen,mustard,linen]):
    ellipsoid('Folded laundry',(0,.015*i,.54+.22*i),(.71,.43,.12),mat,cart,.52)
television((4.02,5.59,3.58),(.48,1.37,1.30), 24, ('75c9ff','ff759f'), 2120)


shot('09 Daybed', (2.65,-5.22,2.45), (.10,3.40,1.70), 23,
     (-4,2,5.9),(1.18,'ffbc90'),[((2,-2,4.5),(2,3.5),120,'e4c5e0')], wide=True)
bed = empty('Channel-stitched daybed',(.62,5.32,0),role='prop')
bed.rotation_euler.z = radians(-10)
for y in [-1.26,1.26]:
    for sign in [-1,1]:
        rod('Scissor rail',(sign*2.98,y,.105),(-sign*2.85,y,1.22),.090,.090,steel,bed)
        ellipsoid('Rubber glide',(sign*2.98,y,.065),(.16,.14,.065),black,bed,.66)
    cyl('Frame pivot',(0,y,.67),.137,.22,brass,.016,(pi/2,0,0),bed)
cube('Seat frame',(0,0,1.24),(7.55,3.04,.20),walnut,.09,bed)
ellipsoid('Welted cushion',(0,0,1.53),(3.86,1.60,.26),plum,bed,.38)
for i in range(9):
    ellipsoid('Upholstered channel',((i-4)*.83,0,1.75),(.425,1.55,.136),plum,bed,.53)
cyl('Loose bolster',(-2.99,0,2.25),.365,2.87,orange,.085,(pi/2,0,0),bed)
for y in [-1.16,1.16]:
    ring('Bolster piping',(-2.99,y,2.25),.361,.374,.041,ivory,(pi/2,0,0),parent=bed)
table = prop('side-table',(5.84,4.43),angle=-8)
side_lamp(6.18,4.77,surface_height(table,6.18,4.77))
book((5.39,4.04,surface_height(table,5.39,4.04)+.091),(0,0,13),teal)
television((-4.30,4.30,3.12),(1.22,1.90,1.54), 33, ('ffc177','db709b'), 2000)


bpy.context.window.scene = bpy.data.scenes['01 Parlor']
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.region_3d.view_perspective = 'CAMERA'
# Web and Blender share the same baked furniture textures. The untouched catalog
# originals live in sources/ for anyone who wants a higher-resolution edit.
for img in bpy.data.images:
    if img.type != 'IMAGE':
        continue
    w,h = img.size[:]
    if max(w,h) > 768:
        factor = 768 / max(w,h)
        img.scale(max(1,round(w*factor)), max(1,round(h*factor)))
        with TemporaryDirectory(prefix='pendulum-image-') as directory:
            path = Path(directory) / (Path(img.name).stem + '.png')
            img.filepath_raw = str(path)
            img.file_format = 'PNG'
            img.save()
            pixels = path.read_bytes()
            img.pack(data=pixels, data_len=len(pixels))
            img.filepath_raw = '//textures/' + path.name
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'18-pendulum.blend'),compress=True)
exec(compile((HERE/'export.py').read_text(),str(HERE/'export.py'),'exec'))
