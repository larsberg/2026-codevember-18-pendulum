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


def rounded_rectangle(width, depth, corner):
    outline = []
    for sx,sy,angle in [(1,1,0),(-1,1,90),(-1,-1,180),(1,-1,270)]:
        for a in np.linspace(radians(angle),radians(angle+90),10):
            outline.append((sx*(width/2-corner)+corner*cos(a),sy*(depth/2-corner)+corner*sin(a)))
    return outline


stage_scene = bpy.data.scenes.new('Stage')
bpy.context.window.scene = stage_scene
stage = bpy.data.collections.new('Shared petrol cyclorama')
stage_scene.collection.children.link(stage)
ground = finish('Petrol cyclorama', '17494d', .48, 0, .035)
ground['stageFloor'] = True
# Continue the original three-unit cove around the wings and the camera end.
# The back of the flat deck still meets the original sweep at y = 8.2.
profile = [(-.10,0)] + [(3*sin(i*pi/64),3-3*cos(i*pi/64)) for i in range(33)] + [(3,160)]
vertices, faces = [], []
for row,(offset,z) in enumerate(profile):
    outline = rounded_rectangle(180+2*offset,110+2*offset,45+offset)
    n = len(outline)
    vertices.extend((x,y-46.8,z) for x,y in outline)
    if row==0:
        faces.append(tuple(range(n)))
    else:
        k = (row-1)*n
        faces.extend((k+(i+1)%n,k+i,k+n+i,k+n+(i+1)%n) for i in range(n))
cove = mesh('Seamless sweep',vertices,faces,ground)
for poly in cove.data.polygons: poly.use_smooth = poly.index!=0
stage.objects.link(cove)
stage_scene.collection.objects.unlink(cove)


def camera_angle(label, eye, target, lens, *, wide=False, horizontal_fill=.90):
    scene = bpy.context.scene
    index = sum(obj.type == 'CAMERA' for obj in scene.objects)
    name = f"{scene.name} / {chr(65+index)} / {label}"
    focus = empty('Focus / '+name, target, role='focus')
    cam = link(name,bpy.data.cameras.new(name))
    cam.location, cam.data.lens = eye,lens
    cam.data.sensor_fit = 'HORIZONTAL'
    cam['angle_index'], cam['label'] = index,label
    cam['wide'], cam['horizontal_fill'] = wide,horizontal_fill
    aim = cam.constraints.new('TRACK_TO')
    aim.target, aim.track_axis, aim.up_axis = focus, 'TRACK_NEGATIVE_Z', 'UP_Y'
    marker = scene.timeline_markers.new(label, frame=index+1)
    marker.camera = cam
    scene.frame_end = index+1
    if index == 0:
        scene.camera = cam
    return cam


def softbox(name, at, size, power, color, target=(0,0,1.1)):
    lamp = link(name, bpy.data.lights.new(name, 'AREA'))
    lamp.location = at
    lamp.data.shape, lamp.data.size, lamp.data.size_y = 'RECTANGLE', *size
    lamp.data.energy, lamp.data.color = power, linear(color)
    at_target(lamp, target)


def shot(name, label, eye, target, lens, sun, warm, softboxes, *, wide=False, horizontal_fill=.90, ambient=.32):
    sc = bpy.data.scenes.new(name)
    bpy.context.window.scene = sc
    sc['shot'] = name.split(' ',1)[1].lower()
    sc.unit_settings.system, sc.unit_settings.scale_length = 'METRIC', 1/UNITS_PER_METRE
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1600,900,100
    sc.world = bpy.data.worlds.new(name)
    sc.world.use_nodes = True
    sc.world.node_tree.nodes.get('Background').inputs['Color'].default_value = (.48,.48,.48,1)
    sc.world.node_tree.nodes.get('Background').inputs['Strength'].default_value = ambient
    sc.collection.children.link(stage)
    socket = empty('Instrument position',(0,0,0),role='instrument')
    socket.instance_type, socket.instance_collection = 'COLLECTION', instrument
    socket.scale = [METRONOME_HEIGHT_M * UNITS_PER_METRE / 3.94] * 3
    camera_angle(label, eye, target, lens, wide=wide, horizontal_fill=horizontal_fill)
    key = link('Key / '+name,bpy.data.lights.new('Hard key','SUN'))
    key.location = sun
    key.data.energy, key.data.color, key.data.angle = warm[0],linear(warm[1]),radians(4)
    at_target(key,target)
    for i,(at,size,power,color) in enumerate(softboxes):
        softbox('Softbox '+str(i+1), at, size, power, color)
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
    if name in ('clock','vase'):
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
    return obj


# A loose 13 cm driver, face up on its magnet, beside the shared metronome.
driver = empty('Floor speaker', (-.69,-.08,0), role='floorSpeaker')
paper = finish('Pressed graphite paper', '766b60', .60, 0, .06)
frame = finish('Stamped speaker basket', '50585a', .32, .68, .08)
cyl('Ferrite magnet', (0,0,.038), .135, .076, black, .009, parent=driver)
cyl('Magnet back plate', (0,0,.012), .139, .024, frame, .006, parent=driver)
for i in range(6):
    angle = i*pi/3
    rib = cube('Basket spoke', (.152*cos(angle),.152*sin(angle),.11), (.131,.045,.024), frame, .005, driver)
    rib.rotation_euler = (0,-.57,angle)
ring('Stamped mounting flange',(0,0,.159),.209,.26,.021,frame,parent=driver)
for i in range(4):
    angle = (i+.5)*pi/2
    cyl('Recess in mounting flange',(.244*cos(angle),.244*sin(angle),.170),.011,.002,black,.001,parent=driver)
ring('Rubber surround',(0,0,.172),.194,.228,.026,black,parent=driver)
# A formed paper cone with a domed centre. The outer lip stays in its surround.
cone = dish('Paper cone and domed dust cap',
            [(.065,-.073),(.195,-.005),(.197,0),(.158,-.020),(.099,-.059),
             (.074,-.064),(.065,-.043),(.048,-.022),(.026,-.011),(.006,-.009)],
            paper, driver, (0,0,.174))
cone['role'] = 'wooferCone'
cone.shape_key_add(name='Basis')
stroke = cone.shape_key_add(name='Excursion')
for vertex in stroke.data:
    radius = np.hypot(vertex.co.x, vertex.co.y)
    travel = np.clip((.195-radius)/.118, 0, 1)
    vertex.co.z += .14 * travel**2 * (3 - 2*travel)


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


# A right-angle speaker plug seats vertically in a recessed floor jack.
# The cable leaves its boot horizontally and rests on the deck between ends.
jack = empty('Floor speaker socket', (-1.00,.30,0), driver)
cube('Socket gasket', (0,0,.009), (.45,.34,.018), black, .015, jack)
cube('Brushed floor plate', (0,0,.020), (.43,.32,.022), nickel, .014, jack)
for x in [-.172,.172]:
    for y in [-.112,.112]:
        cyl('Countersunk plate screw',(x,y,.032),.017,.003,frame,.001,parent=jack)
        cube('Screw slot',(x,y,.034),(.021,.004,.002),ink,.001,jack)
cyl('Jack insulating collar',(0,0,.035),.061,.008,black,.002,parent=jack)
ring('Jack ferrule',(0,0,.043),.024,.048,.014,brass,parent=jack)
cyl('Seated plug shaft',(0,0,.062),.022,.055,nickel,.002,parent=jack)
cube('Right-angle plug shell',(.019,0,.101),(.12,.075,.075),frame,.023,jack)
rod('Tapered strain relief',(.071,0,.102),(.174,0,.102),.035,.019,black,jack)
for x in [.090,.113,.136]:
    cyl('Boot rib',(x,0,.102),.034-(x-.090)*.18,.008,black,.002,(0,pi/2,0),jack)
cube('Basket terminal block',(-.177,-.104,.094),(.077,.070,.054),black,.008,driver)
rod('Terminal sleeve',(-.188,-.117,.095),(-.226,-.150,.073),.025,.018,brass,driver)
jacket = finish('Warm rubber cable jacket','84523a',.46,0,.13)
tube('Speaker cord',[(-.826,.30,.102),(-.742,.30,.086),(-.65,.28,.038),
     (-.565,.22,.017),(-.534,.064,.017),(-.59,-.128,.017),(-.529,-.266,.017),
     (-.389,-.29,.017),(-.295,-.223,.025),(-.222,-.147,.076)], .015, jacket, driver)
for obj in [driver, *driver.children_recursive]:
    stage.objects.link(obj)
    stage_scene.collection.objects.unlink(obj)


def rug(name, center, size, yaw, corner, pattern, colors):
    width, depth = size
    root = empty(name, (*center,0), role='prop')
    root.rotation_euler.z = radians(yaw)
    # Dye the warp and weft into the same image so the pattern survives GLB export.
    nx, ny = 768, round(768 * depth/width)
    y, x = np.mgrid[:ny,:nx]
    u, v = (x+.5)/nx, (y+.5)/ny
    if pattern == 'arches':
        bands = np.hypot((u-.14)*width, (v-.93)*depth) / .49
        dye = np.array([0,0,1,2,2,1,0,3])[bands.astype(int) % 8]
    elif pattern == 'runner':
        repeat = (u*4.5 + .34*np.abs(v*2-1)) % 1
        dye = np.select([repeat<.15, repeat<.20, repeat<.55, repeat<.62], [1,2,0,3], default=0)
    else:
        check = (np.floor(u*12) + np.floor(v*6)).astype(int) % 2
        dye = np.where(v<.38, np.where(check,0,1), np.where(check,0,2))
    edge = np.minimum(np.minimum(u,1-u)*width,np.minimum(v,1-v)*depth)
    dye = np.where(edge<.062,3,np.where((edge>.13)&(edge<.175),1,dye))
    palette = np.array([[int(c[i:i+2],16)/255 for i in (0,2,4)] for c in colors])
    warp, weft = np.cos(2*pi*x/3.8), np.cos(2*pi*y/4.3)
    fiber = .965 + .025*warp + .028*weft + .025*warp*weft + .018*np.sin(.47*y+.013*x)
    pixels = np.ones((ny,nx,4),dtype=np.float32)
    pixels[:,:,:3] = np.clip(palette[dye]*fiber[:,:,None],0,1)
    image = bpy.data.images.new(name+' / flatweave',width=nx,height=ny)
    image.pixels.foreach_set(pixels.ravel())
    image.pack()
    wool = finish(name+' / wool', colors[0], .95, 0, 0)
    bs = wool.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Specular IOR Level'].default_value = .17
    tex = wool.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image = image
    wool.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])

    # A single closed pile mesh gives the rug an opaque edge above the polished floor.
    outline = rounded_rectangle(width,depth,corner)
    top = .038
    n = len(outline)
    vertices = [(x,y,z) for z in [.001,top] for x,y in outline]
    faces = [tuple(reversed(range(n))),tuple(range(n,2*n))]
    faces.extend((i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n))
    pile = mesh('Flatwoven pile',vertices,faces,wool)
    pile.parent = root
    uv = pile.data.uv_layers.new()
    for loop in pile.data.loops:
        x,y,_ = vertices[loop.vertex_index]
        uv.data[loop.index].uv = (x/width+.5,y/depth+.5)

    threads, faces = [], []
    for sx in [-1,1]:
        for i,y in enumerate(np.arange(-depth/2+corner,depth/2-corner,.060)):
            x = sx*(width/2-.012)
            end = x+sx*(.11+.028*sin(i*1.3))
            k = len(threads)
            threads.extend([(x,y-.016,.020),(end,y-.008,.010),(end,y+.009,.010),(x,y+.016,.020)])
            faces.append((k,k+1,k+2,k+3) if sx==1 else (k+3,k+2,k+1,k))
    fringe = mesh('Knotted fringe',threads,faces,ivory)
    fringe.parent = root
    return top+.001


def breakfast_orrery(table, x, y):
    base = empty('Clockwork orrery',(x,y,surface_height(table,x,y)),role='prop')
    cyl('Stepped enamel plinth',(0,0,.085),.47,.17,teal,.035,parent=base)
    cyl('Brass chapter ring',(0,0,.19),.40,.04,brass,.009,parent=base)
    cyl('Solar spindle',(0,0,.74),.066,1.11,nickel,.01,parent=base)
    gold = finish('Polished solar enamel','ffb13c',.18,.35,.42)
    blue = finish('Ultramarine planet','395aba',.19,.07,.55)
    ellipsoid('Gilded sun',(0,0,1.31),(.29,)*3,gold,base)
    for reach, angle, level, height, radius, mat in [
        (.57,154,.44,.95,.135,porcelain),(.84,-69,.54,.81,.17,red),(1.10,18,.65,1.12,.205,blue)]:
        px,py = reach*cos(radians(angle)),reach*sin(radians(angle))
        cyl('Spindle collar',(0,0,level),.121,.065,brass,.01,parent=base)
        rod('Orbital arm',(0,0,level),(px,py,level),.039,.031,brass,base)
        rod('Planet spindle',(px,py,level),(px,py,height),.031,.031,nickel,base)
        ellipsoid('Enamel planet',(px,py,height),(radius,)*3,mat,base)
        if mat == blue:
            ring('Saturn ring',(px,py,height),.26,.397,.030,brass,(radians(29),radians(13),0),parent=base)
    ring('Ecliptic',(0,0,.76),.975,1.01,.037,brass,(radians(17),0,radians(-24)),parent=base)


def broadcast_image(name, colors):
    w, h = 512, 288
    y, x = np.mgrid[:h, :w]
    u, v = (x + .5) / w, (y + .5) / h
    # Rest frame of the two-color signal animated by the Three.js player.
    edge = .5 + .10*np.sin(2*pi*1.25*u)
    coverage = np.clip((v-edge)*h+.5, 0, 1)[:, :, None]
    image = bpy.data.images.new(name + ' / broadcast', width=w, height=h)
    pixels = np.ones((h, w, 4), dtype=np.float32)
    rgb = (1-coverage)*.16*np.array(linear(colors[0])) + coverage*.85*np.array(linear(colors[1]))
    pixels[:, :, :3] = np.where(rgb < .0031308, rgb*12.92, 1.055*rgb**(1/2.4)-.055)
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
    # Louvres and the four mount sockets catch the grazing light on reverse shots.
    vents, slots = [], []
    for y in [.41,.48,.55]:
        for i in range(29):
            x = (i-14)*.105
            k = len(vents)
            vents.extend([(x-.039,y-.012,-.225),(x-.039,y+.012,-.225),
                          (x+.039,y+.012,-.225),(x+.039,y-.012,-.225)])
            slots.append(tuple(range(k,k+4)))
    vent = mesh('TV / cooling louvres',vents,slots,black)
    vent.parent = tv
    for x in [-.40,.40]:
        for y in [-.55,.25]:
            cyl('TV / mount socket',(x,y,-.225),.046,.008,nickel,.003,parent=tv)
            cyl('TV / threaded insert',(x,y,-.231),.027,.005,ink,.002,parent=tv)
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
shot('01 Parlor', 'Sofa wide', (1.18,-3.95,1.05), (-.32,2.7,1.95), 16.5,
     (-4.7,-6,7.4),(1.55,'ffe0ae'),[((-3,-2,5),(2.6,4.7),145,'ffebcf')], wide=True)
camera_angle('End-table side', (4.92,-1.84,4.62), (-.30,2.45,1.56), 12.2)
camera_angle('Over the sofa arm', (-7.71,5.14,7.50), (1.12,3.02,2.34), 23.15)
prop('sofa', (-1.58,5.25), angle=6)
table = prop('side-table', (3.48,3.85), angle=-14)
side_lamp(3.76,4.02, surface_height(table,3.76,4.02))
prop('clock', (2.97,3.53), bottom=surface_height(table,2.97,3.53), angle=-8)
television((-1.47,5.57,5.30), (-.45,.60,.90), -7, ('2ce1f3','6779ff'), 2300)

# A clockwork orrery stands between the two place settings. The
# inverted third chair forms a counterweight to the floating television.
shot('02 Breakfast', 'High table', (-2.5,-4.10,6.60), (-.12,2.58,2.38), 14.1,
     (4,-3,7.5),(1.65,'ffcb99'),[((-.5,-4,6),(1,3.5),155,'fff6e9')], horizontal_fill=.80)
camera_angle('Below the tabletop', (2.66,-3.83,1.05), (-.31,2.87,1.93), 18.5)
camera_angle('Across the inverted chair', (7.36,6.39,7.22), (-.40,2.71,1.49), 15.55)
table = prop('dining-table', (0,3.45))
prop('dining-chair', (-4.02,2.56), angle=52)
prop('dining-chair', (4.03,2.53), angle=-53)
prop('dining-chair', (2.59,7.90), bottom=3.58, angle=-20, tilt=(162,0))
breakfast_orrery(table, -.10,3.90)
place_setting(table,-1.40,3.43, cup=True)
place_setting(table,1.32,2.98)
television((-3.70,5.97,4.88), (.48,2.00,2.28), 13, ('ff674c','ffb446'), 2100)

# Closed volumes stand on one shelf and lie in an offset stack on the next.
shot('03 Library', 'Reader’s side', (2.0,-4.56,1.92), (-.60,2.17,1.91), 16.1,
     (-4,-2,6.3),(1.55,'c9e5ff'),[((3,-3,5),(2.4,3.8),165,'f5ecce')])
camera_angle('Along the shelves', (-5.78,-.76,3.28), (-.28,2.75,1.65), 14.0)
camera_angle('Over the reading chair', (6.44,5.17,5.67), (-.67,2.22,2.25), 23.35)
case = prop('bookcase', (-5.68,5.66))
pile = rug('Reading rug',(2.80,5.06),(6.25,6.05),0,.42,'arches',('88503f','d4b992','aa8554','584939'))
prop('reading-chair', (2.38,6.25), bottom=pile, angle=-28)
prop('floor-lamp', (4.98,6.66), bottom=pile, angle=-36)
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
shot('04 Listening', 'Above the deck', (-2.7,-4.7,5.00), (.10,2.75,1.63), 23.45,
     (4.7,-.8,5.8),(1.5,'ffba91'),[((3,2,4.7),(3.5,1),190,'f99cb9')])
camera_angle('Platter level', (2.85,-3.62,.94), (.08,3.20,1.68), 21)
camera_angle('Over the left speaker', (-6.30,4.53,7.46), (.12,2.43,1.42), 14.75)
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

mint = finish('Celadon ABS', '78aa95', .22, 0, .48)
orange = finish('Persimmon ABS', 'e46c3e', .23, 0, .45)
plum = finish('Oxblood vinyl', '793644', .34, 0, .25)
steel = finish('Brushed chrome', 'ccd0d2', .22, .85)
linen = finish('Unbleached cotton', 'e6d5bb', .83, 0, 0)


walnut = finish('Walnut lacquer','61362b',.28,0,.30)

shot('05 Exchange', 'Above the steps', (-2.80,-2.40,8.55), (.20,2.40,3.16), 11.05,
     (-3.2,-3,6.6),(1.35,'ffe1c0'),[((1.2,-2,6),(3,3),155,'d5e5ff')], horizontal_fill=.64)
camera_angle('From the stool', (-4.16,-2.62,1.54), (-.36,3.15,2.90), 13.20)
camera_angle('Down the counter', (6.72,-.62,2.76), (.35,3.60,2.82), 14)
rug('Switchboard runner',(-3.78,.55),(5.25,1.85),-8,.12,'runner',('704349','cf7655','d3bf9b','422f3d'))
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
# The tread side opens onto the floor; the top platform meets the front edge at an angle.
ladder = prop('stepladder', (.54,2.79), angle=30)
ladder.parent['frameSubject'] = True
stool = empty('Operator stool',(-4.72,3.28,0),role='prop')
cyl('Weighted foot',(0,0,.07),.68,.14,ink,parent=stool)
cyl('Adjustable post',(0,0,.82),.11,1.50,steel,parent=stool)
ring('Footrest',(0,0,.60),.42,.47,.06,steel,parent=stool)
for k in range(3):
    a = k*2*pi/3
    rod('Footrest spoke',(0,0,.60),(.45*cos(a),.45*sin(a),.60),.029,.029,steel,stool)
ellipsoid('Vinyl seat',(0,0,1.64),(.77,.77,.16),plum,stool,.65)
television((3.88,5.49,2.92),(-1.17,1.83,5.32), -43, ('ef608f','708aff'), 2350)


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


shot('06 Conservatory', 'Through the leaves', (5.15,8.47,8.20), (-.43,2.54,1.46), 15.4,
     (-4.8,-1,6.9),(1.45,'ffe8c5'),[((3.8,1.7,5.7),(1.8,3.1),165,'e7ffd9')])
camera_angle('Beneath the grow light', (-1.50,-4.14,1.12), (-.28,3.01,2.02), 10.7)
camera_angle('Across the pots', (-4.12,-1.10,2.38), (.15,2.09,2.62), 6.85)
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


shot('07 Launderette', 'Floor level', (-5.72,-1.65,.66), (-.12,4.17,1.72), 20,
     (3.6,-4.1,7.6),(1.65,'e7f8ff'),[((-3,-1.5,5),(3.3,1.5),215,'fff1e4')])
camera_angle('Cart side', (3.79,-2.91,4.61), (-.04,2.74,1.66), 12.15)
camera_angle('Above the machines', (3.08,4.82,9.51), (1.97,3.62,.84), 18.8)
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


def pinball_print(name, size, parent, at, rotation, backglass=False):
    width, height = size
    nx = 640
    ny = round(nx*height/width)
    y,x = np.mgrid[:ny,:nx]
    u,v = (x+.5)/nx,(y+.5)/ny
    colors = np.array([linear(c) for c in ('164d56','317b77','fab95f','dc6545','fee0a4','1b3547')])
    paint = np.zeros_like(x)
    if backglass:
        paint.fill(5)
        sweep = v - .17*u
        for low,high,color in [(.16,.21,1),(.22,.25,2),(.26,.36,3),(.37,.39,4)]:
            paint[(sweep>low)&(sweep<high)] = color
        radius = np.hypot((u-.65)*width/height,v-.58)
        paint[radius<.329] = 2
        paint[np.hypot((u-.72)*width/height,v-.633)<.26] = 5
        orbit = np.hypot((u-.63)*1.02,(v-.57+.24*(u-.63))*3.4)
        paint[(orbit>.321)&(orbit<.330)] = 4
    else:
        lane = np.abs(u-.49) - .15*np.sin(pi*(v-.04))
        for low,high,color in [(.133,.145,4),(.151,.185,3),(.189,.203,2)]:
            paint[(lane>low)&(lane<high)] = color
        for cx,cy,r in [(.32,.67,.12),(.60,.69,.12),(.47,.52,.105),(.49,.255,.132)]:
            d = np.hypot(u-cx,(v-cy)*height/width)
            paint[(d<r)&(d>r-.009)] = 4
            paint[d<r-.023] = 1
    for cx,cy,r in [(.11,.67,.036),(.31,.53,.019),(.86,.73,.027),(.20,.85,.022),(.70,.32,.018)]:
        dx,dy = np.abs(u-cx)*width/height,np.abs(v-cy)
        paint[(np.sqrt(dx/r)+np.sqrt(dy/r))<1] = 4
    rgb = colors[paint]
    pixels = np.ones((ny,nx,4),dtype=np.float32)
    pixels[:,:,:3] = np.where(rgb<.0031308,12.92*rgb,1.055*rgb**(1/2.4)-.055)
    image = bpy.data.images.new(name,width=nx,height=ny)
    image.pixels.foreach_set(pixels.ravel())
    image.pack()
    mat = finish(name,'ffffff',.23,0,.47)
    bs = mat.node_tree.nodes.get('Principled BSDF')
    texture = mat.node_tree.nodes.new('ShaderNodeTexImage')
    texture.image = image
    mat.node_tree.links.new(texture.outputs['Color'],bs.inputs['Base Color'])
    if backglass:
        mat.node_tree.links.new(texture.outputs['Color'],bs.inputs['Emission Color'])
        bs.inputs['Emission Strength'].default_value = .40
    face = mesh(name,[(-width/2,-height/2,0),(width/2,-height/2,0),
                      (width/2,height/2,0),(-width/2,height/2,0)],[(0,1,2,3)],mat)
    face.parent, face.location, face.rotation_euler = parent, at, rotation
    uv = face.data.uv_layers.new()
    for loop,coord in zip(face.data.loops,[(0,0),(1,0),(1,1),(0,1)]):
        uv.data[loop.index].uv = coord


def flipper(parent, x, angle):
    # Two different-radius ends give the bat a broad pivot and narrow rubber tip.
    outline = [(offset+radius*cos(a),radius*sin(a)) for offset,radius,start in
               [(0,.12,pi/2),(.54,.065,-pi/2)] for a in np.linspace(start,start+pi,17)]
    n = len(outline)
    vertices = [(px,py,z) for z in [.075,.205] for px,py in outline]
    faces = [tuple(reversed(range(n))),tuple(range(n,2*n))]
    faces.extend((i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n))
    obj = mesh('Ivory flipper',vertices,faces,porcelain,.021)
    obj.parent,obj.location,obj.rotation_euler.z = parent,(x,-1.33,0),radians(angle)
    cyl('Flipper pivot',(x,-1.33,.21),.049,.015,brass,.004,parent=parent)


def pinball_machine(at, yaw):
    cab = empty('Eclipse pinball machine',at,role='prop')
    cab.rotation_euler.z = radians(yaw)
    cab['frameSubject'] = True
    enamel = finish('Midnight turquoise lacquer','256c70',.235,0,.51)
    apricot = finish('Marigold bumper caps','efa833',.21,0,.47)
    for x in [-1,1]:
        for y in [-1,1]:
            foot = (x*1.22,y*1.86)
            cyl('Levelling foot',(*foot,.040),.115,.080,black,.015,parent=cab)
            rod('Splayed steel leg',(*foot,.080),(x*1.055,y*1.66,2.85),.052,.106,steel,cab)
    # The rails, graphics and game hardware all follow the same inclined deck.
    width,length = 2.47,4.44
    slope = .137
    corners = [(-width/2,-length/2),(width/2,-length/2),(width/2,length/2),(-width/2,length/2)]
    vertices = [(x,y,2.44 if not top else 3.71+slope*y) for top in (False,True) for x,y in corners]
    faces = [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    case = mesh('Lacquered wedge cabinet',vertices,faces,enamel,.065)
    case.parent = cab
    for side in [-1,1]:
        # Broad screen-printed chevrons on the cabinet sides read in the reverse view.
        for z,mat in [(2.67,orange),(2.82,apricot)]:
            stripe = mesh('Comet side flash',[(side*(width/2+.003),y,z+dz)
                          for y,dz in [(-2.06,0),(-.42,.25),(.46,.08),(2.01,.57),(2.01,.69),
                                       (.46,.22),(-.42,.41),(-2.06,.038)]],
                          [tuple(range(8)) if side>0 else tuple(reversed(range(8)))],mat)
            stripe.parent = cab
    field = empty('Inclined playfield',(0,0,3.718),cab)
    field.rotation_euler.x = atan2(slope,1)
    pinball_print('Eclipse / playfield',(2.31,4.24),field,(0,0,.003),(0,0,0))
    for side in [-1,1]:
        cube('Polished side rail',(side*1.195,0,.059),(.088,4.43,.137),steel,.028,field)
    cube('Lockdown bar',(0,-2.15,.06),(2.46,.19,.16),steel,.045,field)
    tube('Shooter lane',[(.916,-1.94,.086),(.916,.92,.086),(.87,1.60,.086),
                         (.66,1.88,.086),(.26,1.97,.086)],.033,steel,field)
    for x,y in [(-.42,.83),(.32,.90),(-.07,.22)]:
        cyl('Pop bumper collar',(x,y,.063),.229,.12,porcelain,.023,parent=field)
        cyl('Kick ring',(x,y,.15),.248,.036,steel,.012,parent=field)
        ellipsoid('Mushroom cap',(x,y,.215),(.219,.219,.083),apricot,field,.82)
        cyl('Bumper medallion',(x,y,.294),.076,.011,orange,.003,parent=field)
    for side in [-1,1]:
        posts = [(side*.84,-.41),(side*.84,-1.10),(side*.51,-1.22)]
        for x,y in posts:
            cyl('Slingshot post',(x,y,.08),.052,.16,brass,.012,parent=field)
        tube('Slingshot rubber',[(x,y,.096) for x,y in posts+[posts[0]]],.040,orange,field,sampled=True)
    flipper(field,-.57,-20)
    flipper(field,.57,200)
    ellipsoid('Polished pinball',(.66,-.13,.082),(.082,)*3,steel,field)
    cube('Coin door',(0,-2.235,2.93),(1.06,.057,.64),tv_trim,.066,cab)
    for x in [-.245,.245]:
        cube('Coin return',(x,-2.276,2.99),(.272,.041,.30),steel,.031,cab)
        cube('Coin slot',(x,-2.301,3.055),(.134,.014,.042),ink,.008,cab)
    rod('Shooter rod',(.99,-2.22,3.24),(.99,-2.48,3.24),.046,.046,steel,cab)
    ellipsoid('Plunger knob',(.99,-2.48,3.24),(.112,.110,.112),orange,cab)
    head = empty('Backbox',(0,1.81,4.10),cab)
    cube('Backbox shell',(0,0,1.01),(2.88,.62,2.14),enamel,.093,head)
    cube('Backglass frame',(0,-.321,1.01),(2.70,.052,1.93),steel,.037,head)
    pinball_print('Eclipse / backglass',(2.58,1.83),head,(0,-.350,1.01),(pi/2,0,0),backglass=True)
    # Reel windows sit below the painted sky and are inscribed in the glass.
    cube('Score escutcheon',(0,-.36,.34),(1.53,.035,.306),ink,.035,head)
    for i,digit in enumerate('04720'):
        x = (i-2)*.271
        cube('Score reel window',(x,-.389,.34),(.239,.022,.22),ivory,.013,head)
        data = bpy.data.curves.new('Mechanical numeral','FONT')
        data.body,data.size,data.align_x,data.align_y = digit,.206,'CENTER','CENTER'
        numeral = link('Reel '+digit,data)
        numeral.parent,numeral.location,numeral.rotation_euler.x = head,(x,-.403,.34),pi/2
        data.materials.append(ink)
        bpy.context.view_layer.objects.active = numeral
        bpy.ops.object.select_all(action='DESELECT')
        numeral.select_set(True)
        bpy.ops.object.convert(target='MESH')


arcade = shot('08 Arcade', 'Over the playfield', (-3.95,-.78,8.28), (-.12,3.05,2.45), 12.65,
              (-4,2,5.9),(1.18,'ffbc90'),[((2,-2,4.5),(2,3.5),120,'e4c5e0')], horizontal_fill=.85)
# Existing player integrations address the eighth layout by its original asset ID.
arcade['shot'] = 'daybed'
camera_angle('Arcade wide', (2.20,-5.09,2.39), (.15,3.29,2.62), 18.0, wide=True)
camera_angle('Across the launch lane', (-8.70,3.30,6.18), (-.09,4.49,2.11), 17.0)
pile = rug('Arcade kilim',(.20,4.78),(8.55,4.78),-10,.28,'check',('ae7565','533e4b','d2ad8c','493642'))
pinball_machine((.28,4.86,pile),-62)
table = prop('side-table',(5.84,4.43),angle=-8)
side_lamp(6.18,4.77,surface_height(table,6.18,4.77))
book((5.39,4.04,surface_height(table,5.39,4.04)+.091),(0,0,13),teal)
television((-3.15,7.45,4.58),(1.08,2.50,1.62), 18, ('ffc177','db709b'), 2000)


def rounded_slab(name, z, width, depth, height, corner, mat, parent):
    outline = rounded_rectangle(width, depth, corner)
    n = len(outline)
    verts = [(x,y,z+dz) for dz in (-height/2,height/2) for x,y in outline]
    faces = [tuple(reversed(range(n))), tuple(range(n,2*n))]
    faces.extend((i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n))
    obj = mesh(name, verts, faces, mat, min(.032,height/5))
    obj.parent = parent
    for face in list(obj.data.polygons)[2:]:
        face.use_smooth = True
    return obj


# High-key soda fountain. The cap, edge band and corbel share the same
# capsule outline so the broad window reads as a continuous highlight.
shot('09 Citrus', 'At the fountain', (2.64,-5.14,1.57), (-.28,3.08,2.23), 20,
     (-4.3,-5.2,8.7), (3.50,'fff2d5'), [((-3.5,-1.2,8),(6.2,4.8),680,'fff7eb')], ambient=.54, wide=True)
camera_angle('Over the juicer', (5.66,4.94,6.67), (-1.26,3.64,2.72), 16)
camera_angle('Along the footrail', (-5.43,-1.65,2.12), (-.68,2.66,2.00), 12)
softbox('Clerestory on the sweep', (4.5,.4,7.8), (6.8,4.6), 3250, 'edfffa', (.5,9.3,2.5))
lemon = finish('Lemon custard laminate','f3bb39',.235,0,.52)
sherbet = finish('Tangerine ABS','f16829',.21,0,.54)
cream = finish('Vanilla enamel','ffebc5',.29,0,.36)
counter = empty('Fluted soda fountain',(-.46,5.42,0),role='prop')
counter.rotation_euler.z = radians(-5)
rounded_slab('Inset toe kick',.13,5.66,1.55,.26,.70,steel,counter)
rounded_slab('Lemon cabinet',1.58,6.02,1.82,2.65,.87,lemon,counter)
for i in range(-10,11):
    cube('Fluted enamel',(.193*i,-.907,1.57),(.068,.058,2.28),cream,.028,counter)
rounded_slab('Tangerine edge',2.963,6.28,2.13,.12,1.03,sherbet,counter)
rounded_slab('Countertop',3.135,6.36,2.19,.224,1.055,cream,counter)
tube('Chrome footrail',[(-2.64,-.65,.65),(-2.43,-1.16,.65),(-1.95,-1.29,.65),
                       (1.95,-1.29,.65),(2.43,-1.16,.65),(2.64,-.65,.65)],.067,steel,counter)
for x in [-1.5,1.5]:
    rod('Footrail bracket',(x,-.87,.59),(x,-1.29,.65),.042,.052,steel,counter)

for x,y,seat in [(-2.25,2.68,sherbet),(1.33,2.45,mint)]:
    stool = empty('Tulip counter stool',(x,y,0),role='prop')
    dish('Flared enamel pedestal',[(.63,0),(.69,.055),(.61,.13),(.28,.23),(.15,.40),
                                    (.115,1.64),(.22,1.79),(.48,1.86)],cream,stool)
    ring('Stool foot ring',(0,0,.79),.39,.44,.063,steel,parent=stool)
    for i in range(3):
        a = 2*pi*i/3
        rod('Foot ring spoke',(0,0,.79),(.414*cos(a),.414*sin(a),.79),.021,.021,steel,stool)
    cyl('Seat lip',(0,0,1.90),.70,.095,steel,parent=stool)
    ellipsoid('Vinyl button seat',(0,0,2.064),(.76,.76,.12),seat,stool,.62)

# Working parts of a hand lever citrus press, bolted to one die-cast foot.
press = empty('Lever citrus press',(-1.15,-.09,3.247),parent=counter)
press.rotation_euler.z = radians(-12)
cube('Cast press foot',(0,.04,.072),(.90,1.00,.144),sherbet,.064,press)
rod('Press column',(0,.35,.14),(0,.35,1.47),.095,.076,steel,press)
ring('Basket cradle',(0,-.12,.60),.27,.35,.09,sherbet,parent=press)
rod('Basket bracket',(0,.32,.59),(0,.13,.59),.079,.079,sherbet,press)
dish('Juice strainer',[(.20,.53),(.32,.61),(.41,.77),(.41,.81),(.36,.82),(.18,.68)],steel,press,(0,-.12,0))
ellipsoid('Orange in the strainer',(0,-.12,.79),(.29,.29,.18),sherbet,press)
dish('Press bell',[(.36,1.04),(.36,1.10),(.29,1.23),(.13,1.28)],cream,press,(0,-.12,0))
tube('Cast lever',[(0,-.12,1.25),(0,.14,1.44),(0,.36,1.45),(0,.64,1.72),(0,.83,1.91)],.059,sherbet,press)
rod('Bakelite grip',(0,.69,1.77),(0,.94,2.02),.078,.073,ink,press)
bowl = empty('Footed fruit bowl',(1.26,-.04,3.247),parent=counter)
dish('Sorbet coupe',[(.37,0),(.40,.065),(.16,.13),(.16,.30),(.39,.38),
                      (.63,.52),(.68,.64),(.64,.66),(.50,.47),(.24,.39)],mint,bowl)
for x,y,z in [(-.27,-.10,.61),(.23,-.17,.61),(.01,.28,.62),(-.02,.025,.97)]:
    ellipsoid('Valencia orange',(x,y,z),(.266,.266,.25),sherbet,bowl)
    cyl('Calyx',(x,y,z+.245),.040,.016,teal,.003,parent=bowl)
television((-.34,6.56,5.70),(-1.6,1.65,1.60),-10,('fff2ac','8de7dc'),880)


# Low-key projection booth. The screen is rolled almost upright. A warm
# strip along the mechanism separates the spools from the blue-black wall.
shot('10 Nocturne', 'House lights down', (-1.56,-5.16,1.44), (-.10,3.25,1.74), 17,
     (3.5,5.8,7),(.32,'abc5ff'), [], ambient=.062)
camera_angle('Over the take-up reel', (3.30,7.08,8.72), (.03,2.35,1.72), 16)
camera_angle('Across the aisle', (5.64,-1.54,2.62), (.05,2.58,1.73), 17)
softbox('Amber edge on the projector', (1.70,6.7,5.15), (1.90,.32), 210, 'ffaf75', (.20,4.83,2.7))
softbox('Cool strip on the spools', (-3.7,1.5,3.9), (.60,2.50), 52, 'b1c9ff', (.20,4.83,3.27))
softbox('Light on the escapement', (-.83,-1.85,2.25), (.56,.95), 48, 'ffe5c8', (0,0,.41))
midnight = finish('Midnight blue Bakelite','233344',.28,0,.47)
velvet = finish('Aubergine seat vinyl','603246',.39,0,.20)
reel_metal = finish('Brushed pewter','b2b7be',.305,.68,.15)
trolley = empty('Projector trolley',(.20,4.88,0),role='prop')
trolley.rotation_euler.z = radians(-8)
for x in [-1.31,1.31]:
    for y in [-.64,.64]:
        cyl('Swivel wheel',(x,y,.145),.145,.13,black,.018,(pi/2,0,0),trolley)
        rod('Tubular leg',(x,y,.25),(x,y,2.34),.057,.057,reel_metal,trolley)
cube('Lower trolley shelf',(0,0,.57),(2.83,1.48,.09),midnight,.034,trolley)
cube('Projector table',(0,0,2.36),(3.07,1.65,.16),midnight,.066,trolley)
for z, mat in [(.715,midnight),(.926,plum)]:
    cyl('Film canister',(.28,-.02,z),.64,.20,mat,parent=trolley)
    ring('Rolled can seam',(.28,-.02,z+.063),.621,.652,.041,steel,parent=trolley)
projector = empty('Portable 16 mm projector',(0,0,2.44),parent=trolley)
cube('Projector shoe',(0,0,.094),(1.82,.92,.188),ink,.063,projector)
cube('Motor housing',(0,.02,.60),(1.56,.84,.90),midnight,.132,projector)
for i in range(7):
    cube('Cooling fin',(.13+i*.063,-.405,.62),(.022,.023,.47),reel_metal,.008,projector)
for x,mat in [(-.70,reel_metal),(.79,brass)]:
    rod('Folding spool arm',(.02,.09,.82),(x,.09,1.62),.080,.060,reel_metal,projector)
    cyl('Axle',(x,-.09,1.62),.078,.47,steel,.013,(pi/2,0,0),projector)
    cyl('Film winding',(x,-.11,1.62),.41,.136,ink,.012,(pi/2,0,0),projector)
    for y in [-.205,-.02]:
        ring('Open spool flange',(x,y,1.62),.485,.575,.056,mat,(pi/2,0,0),parent=projector)
        cyl('Spool hub',(x,y,1.62),.105,.065,mat,.012,(pi/2,0,0),projector)
        for k in range(3):
            a = 2*pi*k/3 + (.15 if x<0 else .95)
            rod('Spool spoke',(x+.075*cos(a),y,1.62+.075*sin(a)),
                (x+.522*cos(a+.27),y,1.62+.522*sin(a+.27)),.056,.078,mat,projector)
for x,r,d,mat in [(-.88,.22,.36,midnight),(-1.09,.19,.20,steel),(-1.22,.223,.13,midnight),
                  (-1.294,.17,.026,tv_glass)]:
    cyl('Projection lens',(x,-.10,.73),r,d,mat,.013,(0,pi/2,0),projector)
seat = empty('Single cinema seat',(3.58,3.38,0),role='prop')
seat.rotation_euler.z = radians(-52)
cube('Bolted base',(0,0,.08),(1.25,1.22,.16),midnight,.055,seat)
rod('Seat pedestal',(0,0,.16),(0,.1,1.03),.26,.20,reel_metal,seat)
ellipsoid('Seat pan',(0,-.11,1.18),(.89,.92,.19),velvet,seat,.46)
back = ellipsoid('Padded back',(0,.65,1.97),(.95,.18,1.00),velvet,seat,.46)
back.rotation_euler.x = radians(-10)
for x in [-1.02,1.02]:
    tube('Armrest bow',[(x,.47,1.05),(x,.41,1.59),(x,.24,1.78),(x,-.54,1.78)],.063,reel_metal,seat)
    cube('Polished arm cap',(x,-.14,1.82),(.22,1.08,.13),midnight,.061,seat)
television((-3.58,4.30,3.24),(.65,1.25,1.40),73,('899dff','b983c9'),400)


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
