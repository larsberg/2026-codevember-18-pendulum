"""Build the editable set. Run with Blender 5.3 in background/factory-startup mode."""
from pathlib import Path
from math import atan2, cos, pi, radians, sin
import bpy
from mathutils import Vector

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


def text_on_scale(value, x, y, parent, mat):
    data = bpy.data.curves.new('Tempo engraving', 'FONT')
    data.body, data.size, data.align_x, data.align_y = value, .083, 'CENTER', 'CENTER'
    data.resolution_u = 4
    o = link('Tempo ' + value, data)
    o.parent, o.location = parent, (x, y, .015)
    data.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target='MESH')


orange = finish('Vermilion lacquer / ABS', 'd94622', .215, 0, .65)
ivory = finish('Ivory enamel', 'f4e3ba', .29)
ink = finish('Carbon moulding', '192522', .27, 0, .35)
nickel = finish('Brushed nickel', 'c6c5b8', .21, .89, .1)
brass = finish('Warm brass', 'cf9a50', .23, .75)
black = finish('Recess / charcoal', '111714', .54)
teal = finish('Petrol blue', '21616a', .3)
pale = finish('Celadon', '8bb1a6', .28)
iris = finish('Ultramarine', '303d9a', .24)
chalk = finish('Warm porcelain', 'e8d4ae', .3)
red = finish('Oxblood', '7c282a', .26)
peach = finish('Apricot', 'e29370', .3)
mustard = finish('Saffron', 'c5963f', .27)

# A freestanding wind-up instrument. The dial plane is parallel to the sloping shell.
master = bpy.context.scene
master.name = 'Instrument'
shell('Elastomer foot', [(.0,.99,.72,0),(.13,1.01,.73,0)], ink, .045)
shell('Lower case', [(.11,1.01,.74,0),(.24,1.035,.765,0),(.65,.981,.719,.012)], orange, .082)
shell('Case parting line', [(.62,.974,.717,.013),(.665,.976,.717,.014)], black, .012)
shell('Tapered case', [(.655,.981,.717,.014),(3.85,.341,.281,.115),(3.94,.313,.25,.115)], orange, .115)
shell('Crown', [(3.925,.317,.255,.115),(3.967,.306,.243,.116)], ink, .024)

face_origin = (0,-.730,.67)
face = empty('Dial tooling plane', face_origin)
face.rotation_euler.x = atan2(3.18, .54)
# Dial plate tapers to follow the moulded housing.
def faceplate(name, lo, hi, y0, y1, height, mat):
    verts = [(x*w,y,z) for z in [0,height] for y,w in [(y0,lo),(y1,hi)] for x in [-1,1]]
    faces = [(0,2,3,1),(4,5,7,6),(0,1,5,4),(1,3,7,5),(3,2,6,7),(2,0,4,6)]
    o = mesh(name,verts,faces,mat,.024)
    o.parent = face
    return o

faceplate('Dial gasket', .672,.21,.37,3.07,.035,ink)
plate = faceplate('Scale / ivory',.615,.17,.43,3.015,.013,ivory)
plate.location.z = .036
dial = empty('Graduations', (0,0,.054), face)
ticks = []
marks = ['208','184','160','144','126','112','100','88','76','66','56','48','40']
for i in range(49):
    y = .77 + i*.0435
    long = i % 4 == 0
    x = .223 - i*.00248
    for side in [-1,1]:
        ticks.append((side*x, y, .133 if long else .065, .014 if long else .008, 0))
    if long:
        text_on_scale(marks[i//4], (-1 if i%8 == 0 else 1)*(x+.116), y, dial, ink)
ink_mesh('Silkscreen / subdivisions', ticks, ink, dial)
cube('Escapement slot',(0,1.63,.056),(.047,2.51,.014),black,.009,face)
# A circular pin and a visible washer ground the swinging assembly.
cyl('Escapement bearing',(0,.36,.08),.24,.1,ink,parent=face)
cyl('Bearing bezel',(0,.36,.142),.189,.07,brass,parent=face)
arm = empty('Escapement pivot',(0,.36,.204),face,'pendulum')
cube('Polished reed',(0,1.55,.008),(.077,3.27,.050),nickel,.022,arm)
cube('Reed centre groove',(0,1.55,.036),(.015,3.1,.004),black,.002,arm)
cube('Adjustable rider',(0,1.73,.061),(.38,.32,.184),ink,.047,arm)
for dy in [-.095,-.045,.005,.055,.105]:
    cube('Slider knurl',(0,1.73+dy,.155),(.297,.015,.008),nickel,.004,arm)
cube('Beat index',(0,1.72,.165),(.35,.031,.012),orange,.005,arm)
cyl('Pivot cap',(0,0,.08),.128,.08,nickel,parent=arm)
cube('Screw slot',(0,0,.122),(.115,.02,.006),black,.004,arm)
# Winding key on the right cheek, with an open bow.
cyl('Key socket',(.94,.08,.51),.19,.16,ink,rot=(0,pi/2,0))
cyl('Winding arbor',(1.09,.08,.51),.067,.32,brass,rot=(0,pi/2,0))
key = ring('Winding bow',(1.34,.08,.51),.125,.195,.079,brass,(pi/2,0,0))
key.scale = (1.32,1,1)
for i in range(8):
    cube('Sound grille',((i-3.5)*.114,-.754,.393),(.056,.026,.18),black,.022)
for x in [-.77,.77]:
    cyl('Front escutcheon',(x,-.747,.388),.037,.025,brass,rot=(pi/2,0,0))

# Collection instances in the four Blender scenes refer back to this editable instrument.
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


def shot(name, ground, pos, turn, eye, target, lens, sun, warm, softboxes):
    sc = bpy.data.scenes.new(name)
    bpy.context.window.scene = sc
    sc['shot'] = name.split(' ',1)[1].lower()
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1600,900,100
    sc.world = bpy.data.worlds.new(name)
    sc.world.color = (.16,.16,.16)
    sc.world.use_nodes = True
    sc.world.node_tree.nodes.get('Background').inputs['Color'].default_value = (.48,.48,.48,1)
    sc.world.node_tree.nodes.get('Background').inputs['Strength'].default_value = .32
    ground_mat = finish(name+' sweep',ground,.48,0,.035)
    ground_mat['stageFloor'] = True
    # Seamless cove from a flat shooting deck through a quarter-round into the back wall.
    path = [(-120,0),(4.8,0)] + [(4.8+3*sin(i*pi/64),3-3*cos(i*pi/64)) for i in range(1,33)] + [(7.8,45)]
    verts = [(x,y,z) for y,z in path for x in [-110,110]]
    cyc = mesh('Cyclorama',verts,[(2*i,2*i+1,2*i+3,2*i+2) for i in range(len(path)-1)],ground_mat)
    for f in cyc.data.polygons: f.use_smooth = True
    socket = empty('Instrument position',pos,role='instrument')
    socket.instance_type, socket.instance_collection = 'COLLECTION', instrument
    socket.rotation_euler.z = radians(turn)
    focus = empty('Camera focus',target,role='focus')
    cam = link('Camera / '+name,bpy.data.cameras.new(name))
    cam.location, cam.data.lens = eye,lens
    cam.data.sensor_fit = 'HORIZONTAL'
    at_target(cam,target)
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
        at_target(a,pos[:2]+(pos[2]+1.65,))
    return sc


def prop(name, xy, bottom, height, angle):
    bpy.ops.import_scene.gltf(filepath=str(HERE/'sources'/f'{name}.glb'))
    meshes = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    obj, = meshes
    bpy.context.view_layer.update()
    corners = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
    low = Vector([min(c[k] for c in corners) for k in range(3)])
    high = Vector([max(c[k] for c in corners) for k in range(3)])
    pivot = empty(name+' / placement',xy+(bottom,))
    obj.parent = pivot
    obj.location -= Vector(((high.x+low.x)/2,(high.y+low.y)/2,low.z))
    pivot.scale = [height/(high.z-low.z)]*3
    pivot.rotation_euler.z = radians(angle)
    obj.name = name.capitalize()
    bs = obj.data.materials[0].node_tree.nodes.get('Principled BSDF').inputs
    bs['Roughness'].default_value = .3
    bs['Coat Weight'].default_value = .32


def grooves(at,r,depth,count,material,axis='z'):
    for i in range(count):
        t = (i/(count-1)-.5)*depth
        if axis=='z':
            cyl('Turned lip',(at[0],at[1],at[2]+t),r,.043,material,.012)
        else:
            cyl('Turned lip',(at[0]+t,at[1],at[2]),r,.043,material,.012,(0,pi/2,0))


def index_arc(x,y,bottom,r0,r1,mat):
    ring('Sweep gauge',(x,y,bottom),r0,r1,.012,mat,arc=pi)
    rects = []
    for i in range(37):
        a = i*pi/36
        r = r1+.09
        rects.append((x+r*cos(a),y+r*sin(a),.18 if i%6==0 else .08,.014,a))
    ink_mesh('Angular divisions',rects,mat,z=bottom+.008)


shot('01 Escapement','17494d',(-.68,-.25,.66),-8,(5.2,-13.8,5.8),(0,0,2.04),46,
     (-5,-7,10),(2.6,'ffe0ae'),[((-3,-3,7),(3.4,5),540,'ffeed7'),((4,1,5),(1.1,6),690,'b7f4ff')])
cyl('Index table',(-.68,-.25,.32),1.92,.64,pale,.08)
cyl('Table chamfer',(-.68,-.25,.605),1.86,.11,ivory,.039)
index_arc(-.68,-.25,.666,1.59,1.604,ink)
# A broad interrupted sweep creates an aperture behind the dial.
ring('Celadon arch',(-3.14,2.5,.04),1.97,2.8,.82,pale,(pi/2,0,radians(-8)),pi)
cube('Clock block',(2.40,.72,.42),(2.23,1.95,.84),teal,.075)
prop('clock',(2.43,.63),.843,2.42,-12)
for i in range(14):
    cube('Fluted return',(4.39+i*.175,3.9,1.87),(.123,.64,3.74),teal,.052)

shot('02 Counterweight','be725a',(.69,.1,.31),14,(-6.45,-9.0,10.3),(0,.02,1.65),47,
     (5,-2,8),(2.45,'ffebbe'),[((-.5,-4,7),(1,5),630,'fff6e9'),((-4,3,3.8),(3,4),470,'ffc6a3')])
p = cube('Red sample tile',(.68,.15,.15),(3.35,3.13,.30),red,.09)
p.rotation_euler.z = radians(14)
cyl('Tower socket',(-2.36,.8,.32),1.05,.64,mustard,.064)
prop('cups',(-2.36,.8),.641,3.95,25)
for i in range(4):
    cube('Test steps',(2.78,2.65+i*.46,.17*(i+1)),(3.1,.49,.34*(i+1)),peach,.045)
ring('Gauge offcut',(-1.75,-1.92,.12),.59,.87,.24,ivory)
ring('Gauge offcut small',(-2.78,-1.63,.085),.24,.40,.17,red)
ink_mesh('Registration squares',[(x*.33-3.8,y*.33-1.0,.33,.33,0) for x in range(18) for y in range(2) if (x+y)%2==0],red,z=.009)

shot('03 Fluting','ddceb0',(.92,-.32,.77),-22,(6.6,-9.0,3.55),(0,.0,2.15),43,
     (-7,-4,8),(2.7,'ecf4ff'),[((3,-4,6),(3.4,4.8),540,'fff5db'),((-4,2,5),(1.3,5),620,'b9d3ff')])
cube('Blue lacquer plinth',(.98,-.16,.386),(3.63,2.87,.772),iris,.12)
cyl('Porcelain pedestal',(-2.09,.55,.56),1.12,1.12,chalk,.055)
grooves((-2.09,.55,.54),1.15,.82,9,chalk)
prop('vase',(-2.09,.55),1.12,2.54,24)
ring('Ultramarine disc',(-3.1,3.7,1.27),1.13,2.49,.48,iris,(pi/2,0,radians(15)))
index_arc(1,-.3,.013,3.08,3.095,iris)

shot('04 Escarpment','563541',(-.65,.10,1.10),-4,(-4.4,-7.9,4.53),(-.28,.05,2.52),43,
     (5,1,7),(2.65,'ffb79b'),[((-3,-4,5),(1.7,5.8),670,'ffded5'),((2,2,6),(3.5,1),810,'f9adc4')])
cyl('Bakelite pedestal',(-.65,.10,.55),1.52,1.1,red,.085)
grooves((-.65,.1,.50),1.53,.65,6,red)
cyl('Setting sun',(2.30,3.48,2.15),2.28,.44,mustard,.065,(pi/2,0,0))
cube('Gauge support',(1.70,-.30,.14),(1.22,1.10,.28),red,.047)
cyl('Calibration drum',(1.72,-.30,.81),.61,1.33,peach,.07,(0,pi/2,0))
grooves((1.72,-.30,.81),.65,1.06,11,peach,'x')
cyl('Drum hub',(1.035,-.30,.81),.20,.079,ink,.02,(0,pi/2,0))
for i in range(4):
    cube('Raking fin',(-3.75+i*.29,3.63,2.55),(.115,1.25,5.1),red,.035)

bpy.context.window.scene = bpy.data.scenes['01 Escapement']
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.region_3d.view_perspective = 'CAMERA'
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'18-pendulum.blend'),compress=True)
exec(compile((HERE/'export.py').read_text(),str(HERE/'export.py'),'exec'))
