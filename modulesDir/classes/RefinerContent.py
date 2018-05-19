import bpy
import bmesh
import numpy as np
import mathutils
import math
import time
from mathutils import Vector, Matrix
from numpy.linalg import svd
from bl_ui.properties_paint_common import UnifiedPaintPanel
from bpy.app.handlers import persistent
from IvoryDigital.classes.Constants import *
from subprocess import call

#==========================================
# METHODS AND GLOBALS USED BY THE REFINER LOGIC

# ===========================================

delta_upper = Vector((0.0,0.0,0.0))	   
delta_lower = Vector((0.0,0.0,0.0))	   
delta_ul = Vector((0.0,0.0,0.0))	
z_axis = Vector((0.0,0.0,1.0))	  
z_axis_neg = Vector((0.0,0.0,1.0)) 

def rot_handler(scene):
	""" listener that checks the three planes and synchronizes delta with the sliders """
	print("Rot Handler RefinerContent")
	if name_plane_group in bpy.data.groups:
		obs = bpy.data.groups[name_plane_group].objects
		for ob in obs:
			if ob.name == 'plane_vertical_UPPER':
				fix = -1.0
			else:
				fix = 1.0
			ob.delta_rotation_euler[0] = scene.delta_rot_x * fix
			ob.delta_location[2] = scene.delta_loc_z * fix		  
						

""" Operator Replacements """
def objectDeselectAll(context):
	for ob in context.scene.objects: ob.select=False

def rotateAxisAngle(axis, angle, ob):
	""" Rotates ob around axis by angle radians using quaternions in world space """
	axis.normalize()
	#qm = mathutils.Quaternion(axis, angle).to_matrix().to_4x4()
	qm = Matrix.Rotation(angle, 4, axis) 
	loc, rot, scale = ob.matrix_world.decompose()
	locMat = Matrix.Translation(loc)
	rotMat = rot.to_matrix().to_4x4()
	scaleMat = Matrix.Scale(scale[0],4,(1,0,0)) * Matrix.Scale(scale[1],4,(0,1,0)) * Matrix.Scale(scale[2],4,(0,0,1))
	ob.matrix_world = locMat * qm * rotMat * scaleMat	 

def objectDuplicate(ob, context, linked = False):
	""" Creates and returns an (optionally linked) duplicate of object ob """
	if linked:
		new_ob = bpy.data.objects.new(ob.name, ob.data) # this will create a linked copy of ob.data
		context.scene.objects.link(new_ob) # adds the object to the active scene
		return new_ob
	else:
		new_ob = bpy.data.objects.new(ob.name, ob.data.copy()) # this will create a regular copy of ob.data
		context.scene.objects.link(new_ob)
		return new_ob

""" Bezier tools from addon and animation nodes """
#cubic bezier value
def cubic(p, t):
	return p[0]*(1.0-t)**3.0 + 3.0*p[1]*t*(1.0-t)**2.0 + 3.0*p[2]*(t**2.0)*(1.0-t) + p[3]*t**3.0

#length of the curve
def arclength(obj):
	length = 0.0

	if obj.type=="CURVE":
		prec = 1000 #precision
		inc = 1/prec #increments

		#subdivide the curve in 1000 lines and sum its magnitudes
		for i in range(0, prec):
			ti = i*inc
			tf = (i+1)*inc
			a = calct(obj, ti)
			b = calct(obj, tf)
			r = (b-a).magnitude
			length+=r

	return length

def arcLengthSegment(left, right):
	""" returns the length of a spline segment defined by left and right """
	length = 0.0

	prec = 1000 #precision
	inc = 1/prec #increments

	#subdivide the curve in 1000 lines and sum its magnitudes
	for i in range(0, prec):
		ti = i*inc
		tf = (i+1)*inc
		a = evaluate(left, right, ti)
		b = evaluate(left, right, tf)
		r = (b-a).magnitude
		length+=r

	return length

#calculates a global parameter t along all control points
#t=0 begining of the curve
#t=1 ending of the curve
def calct(obj, t):

	spl=None
	mw = obj.matrix_world
	if obj.data.splines.active==None:
		if len(obj.data.splines)>0:
			spl=obj.data.splines[0]
	else:
		spl = obj.data.splines.active

	if spl==None:
		return False

	if spl.type=="BEZIER":
		points = spl.bezier_points
		nsegs = len(points)-1

		d = 1.0/nsegs
		seg = int(t/d)
		t1 = t/d - int(t/d)

		if t==1:
			seg-=1
			t1 = 1.0

		p = getbezpoints(spl,mw, seg)

		coord = cubic(p, t1)

		return coord
	
#gets a bezier segment's control points on global coordinates
def getbezpoints(spl, mt, seg=0):
	points = spl.bezier_points
	p0 = mt * points[seg].co
	p1 = mt * points[seg].handle_right
	p2 = mt * points[seg+1].handle_left
	p3 = mt * points[seg+1].co
	return p0, p1, p2, p3

#<from AN>
def getCoeffs(left, right):
	""" returns the interpolation coefficients between two bezier points """
	coeffs = [left.co,
			left.co * (-3.0) + left.handle_right * (+3.0),
			left.co * (+3.0) + left.handle_right * (-6.0) + right.handle_left * (+3.0),
			left.co * (-1.0) + left.handle_right * (+3.0) + right.handle_left * (-3.0) + right.co]
	return coeffs

def getCoeffsAlt(left, right, hl, hr):
	""" returns the interpolation coefficients between two bezier points """
	coeffs = [left.co,
			left.co * (-3.0) + hr * (+3.0),
			left.co * (+3.0) + hr * (-6.0) + hl * (+3.0),
			left.co * (-1.0) + hr * (+3.0) + hl * (-3.0) + right.co]
	return coeffs
			
def evaluate(left, right, parameter):
	""" returns the coordinates in local space between bezier points left and right at position "parameter" """ 
	c = getCoeffs(left, right)
	return c[0] + parameter * (c[1] + parameter * (c[2] + parameter * c[3]))

def evaluateAlt(left, right, hl, hr, parameter):
	""" returns the coordinates in local space between bezier points left and right at position "parameter" """ 
	c = getCoeffsAlt(left, right, hl, hr)
	return c[0] + parameter * (c[1] + parameter * (c[2] + parameter * c[3]))

def evaluateTangent(left, right, parameter):
	""" returns the tangent in local space between bezier points left and right at position "parameter" """
	c = getCoeffs(left, right)
	return c[1] + parameter * (c[2] * 2 + parameter * c[3] * 3)

def evaluateTangentAlt(left, right, hl, hr, parameter):
	""" returns the tangent in local space between bezier points left and right at position "parameter" """
	c = getCoeffsAlt(left, right, hl, hr)
	return c[1] + parameter * (c[2] * 2 + parameter * c[3] * 3)
#</from AN>
						
def manualParentCopy(obSrc, obDest, parentSrc, parentDest):
	""" Places obDest relative to parentDest like obSrc is placed to parentSrc.
		Works like child-parent-relationships but as a one-time function that does not break existing child-parent-relationships. """
	
	destMw = parentDest.matrix_world
	srcMw = parentSrc.matrix_world
	srcMwInv = srcMw.inverted(Matrix.Identity(4))
	
	obSrcMw = obSrc.matrix_world
	tempMatrix = srcMwInv * obSrcMw
	
	transformResult = destMw * tempMatrix
	try:
		obDest.matrix_world = transformResult
	except:
		print("obDest Nonetype?")
		
def composeMatrix(location, rotation, scale):
	# Scale
	scaleMatrix = Matrix.Identity(3)
	scaleMatrix[0][0] = scale[0]
	scaleMatrix[1][1] = scale[1]
	scaleMatrix[2][2] = scale[2]

	# Rotation
	matrix = (rotation.to_matrix() * scaleMatrix).to_4x4()

	# Translation
	matrix[0][3] = location[0]
	matrix[1][3] = location[1]
	matrix[2][3] = location[2]
	
	return matrix						 


def parentClear(ob, type):
	""" Clears the parent of an object. Optionally keeps the transform. Can be expanded with further options. """
	if type == 'CLEAR_KEEP_TRANSFORM':
		mw = ob.matrix_world.copy()
		ob.parent = None
		ob.matrix_world = mw
	else:
		ob.parent = None


def locationFromRaycast(ob, point, direction):
	""" Returns location in world space of the intersection with object of a ray cast from point in direction """
	ob_mw = ob.matrix_world
	ob_mwi = ob_mw.inverted()
	point_rel = ob_mwi * point
	hit, loc, norm, face = ob.ray_cast(point_rel, direction)
	if loc == Vector((0.0, 0.0, 0.0)):
		direction = direction * (-1) # the plane can move in both directions
		hit, loc, norm, face = ob.ray_cast(point_rel, direction)
	loc_world = ob_mw * loc
	return loc_world
						
def set_parent_trans(ob1, ob2):
	""" Create a child parent hierarchy similar to the operator """
	ob1.parent = ob2
	ob1.matrix_parent_inverse = ob2.matrix_world.inverted()
	return True

def channels_from_color(color, num):
	""" Provide inverted color channel definitions since in Blender vertex colors are white by default """
	if color=='RED' and num == 0:
		return 1
	if color=='RED' and num == 1:
		return 2
	if color=='GREEN' and num == 0:
		return 0
	if color=='GREEN' and num == 1:
		return 2
	if color=='BLUE' and num == 0:
		return 0
	if color=='BLUE' and num == 1:
		return 1

def plane_from_normal(ctr, normal):
	""" Creates a plane rotated into the direction of the normal """
	normal_vector = Vector(normal)
	quat = normal_vector.to_track_quat('Z', 'Y') # for normal to rotation only quaternion is available. Z is direction, Y is up
	quat_obj = mathutils.Quaternion(quat)
	eul = quat_obj.to_euler()
	bpy.ops.mesh.primitive_plane_add(location=ctr, rotation=eul[0:3])
	plane = bpy.context.object
	return plane

def plane_fit(points):
	""" Returns center of point cloud and normal vector of a plane fit """
	points = np.reshape(points, (np.shape(points)[0], -1)) # get list into format suitable for numpy
	p3 = points.T
	points = p3
	ctr = points.mean(axis=1)
	x = points - ctr[:,np.newaxis]
	M = np.dot(x, x.T)
	return ctr, svd(M)[0][:,-1]

def fuzzyColor(colFuz, col, delta):
	return abs(colFuz[0] - col[0]) <= delta and abs(colFuz[1] - col[1]) <= delta and abs(colFuz[2] - col[2]) <= delta

def get_colored_verts(ob, color, delta):
	""" Returns the vertices of the chosen color in a list (list includes duplicates) """
	mesh = ob.data
	verts_col_layer = mesh.vertex_colors["Col"]    
	
	tk = list()
	for j,poly in enumerate(mesh.polygons):
		for idx in poly.loop_indices:
			if fuzzyColor(verts_col_layer.data[idx].color, color, delta):
				loop = mesh.loops[idx]
				v = loop.vertex_index
				tk.append(mesh.vertices[v].co)
				poly.select = True # for testing purposes only, will be used in another function
	return tk    

	
def mean_verts(verts):
	""" returns the mean Z-location of a list of vertices """
	tmp = [v[2] for v in verts]
	mean = np.mean(tmp)
	return mean

def create_plane_head(verts, name, head):
	bpy.ops.object.select_all(action='DESELECT')
	fit = plane_fit(verts)
	plane = plane_from_normal(fit[0], fit[1])
	plane.name = name
	prm = plane.matrix_world
	hm = head.matrix_world
	plane.matrix_world = hm * prm
	bpy.ops.object.select_all(action='DESELECT')
	return plane

def create_linked_duplicates(ob, group_name_linked, context):
	""" create a linked duplicate of the objects in the group ob is in """
	bpy.ops.object.select_all(action='DESELECT')
	ob.select = True
	for obj in ob.users_group[0].objects:
		bpy.ops.object.select_all(action='DESELECT')
		obj.select = True
		bpy.ops.object.duplicate(linked=True)
		obj.select = False
		bpy.ops.object.group_link(group=group_name_linked)
		name = context.active_object.name[:-4] + '_linked'
		
def get_distance(vec1, vec2):
	""" returns the distance between two vectors """
	return math.sqrt((vec2[0] - vec1[0])**2 + (vec2[1] - vec1[1])**2 + (vec2[2] - vec1[2])**2)

def getLocalAxis(ob, axis):
	""" returns the local axis of an object in world space as Vector """
	matrix = ob.matrix_world
	if axis == "Z" or axis == "z":
		return Vector((matrix[0][2], matrix[1][2], matrix[2][2]))
	elif axis == "Y" or axis == "y":
		return Vector((matrix[0][1], matrix[1][1], matrix[2][1]))
	elif axis == "X" or axis == "x":
		return Vector((matrix[0][0], matrix[1][0], matrix[2][0]))
	else:
		return Vector((0.0, 0.0, 0.0))	
	
def bool_away(context, ob, locob, dist):
	""" removes geometry by creating a cube and applying a boolean modifier """
	bpy.ops.object.select_all(action='DESELECT')
	bpy.ops.mesh.primitive_cube_add(radius=dist+0.1, location=locob.matrix_world.translation)
	cube = context.object
	mod = ob.modifiers.new('Boolean',type='BOOLEAN')
	mod.object = cube
	mod.operation = 'DIFFERENCE'
	bpy.context.scene.objects.active = ob
	bpy.ops.object.modifier_apply(apply_as='DATA', modifier=mod.name)
	bpy.context.scene.objects.unlink(cube)	  

def align_mold(context, ul):
	""" Aligns the selected mold, creates a duplicate and a synced plane """
	
	global delta_upper
	global delta_lower
	global delta_ul
	
	print("aligning mold")
	
	scn = context.scene
	rot_fix = 1
	red = [1.0, 0.0, 0.0]
	green = [0.0, 1.0, 0.0]
	
	group_name = "group_" + ul
	group_name_linked = group_name + '_linked'
	bpy.ops.group.create(name=group_name)
	bpy.ops.group.create(name=group_name_linked)
	
	ob = bpy.context.active_object # TODO: get by object name, more robust
	bpy.ops.object.group_link(group=group_name)
	
	#bpy.ops.object.select_all(action='DESELECT')
	print("Getting red vertices")
	start = time.time()
	verts_red = get_colored_verts(ob, red, 0.05)
	print("Time: " + str(time.time() - start))
	print("Doing plane fit for red vertices")
	start = time.time()
	fit = plane_fit(verts_red)
	print("Time: " + str(time.time() - start))
	plane_red = plane_from_normal(fit[0], fit[1])
	plane_red.name = 'plane_red_' + ul
	plane_red.select = True
	bpy.ops.object.group_link(group=group_name)
	
	print("Getting green vertices")
	start = time.time()
	verts_green = get_colored_verts(ob, green, 0.05)
	print("Time: " + str(time.time() - start))
	print("Doing plane fit for green vertices")
	start = time.time()
	fit = plane_fit(verts_green)
	print("Time: " + str(time.time() - start))
	plane_green = plane_from_normal(fit[0], fit[1])
	plane_green.name = 'plane_green_' + ul
	plane_green.select = True
	bpy.ops.object.group_link(group=group_name)
	
	dist = get_distance(plane_red.location, plane_green.location)*1.5 # for later use
	
	set_parent_trans(ob, plane_red)
	set_parent_trans(plane_green, ob)
	#set_parent_trans(plane_blue, ob)
	plane_red.location = (0.0, 0.0, 0.0)
	plane_red.rotation_euler = (deg_90, 0.0, 0.0) # rotated 90° along X-axis
	bpy.ops.object.select_all(action='DESELECT')
	plane_green.select = True
	if plane_green.matrix_world.translation[1] > 0.0:
		plane_red.rotation_euler[2] = deg_90*2
		rot_fix = -1
	bpy.ops.object.select_all(action='DESELECT')
	plane_green.select = True
	bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
	#bpy.ops.object.transform_apply( rotation = True )
	#normal_green = plane_green.data.polygons[0].normal
	pgmw = plane_green.matrix_world.copy()
	normal_green = Vector((pgmw[0][2], pgmw[1][2], pgmw[2][2])) # get the local Z-axis
	upvec = Vector((0.0,0.0,1.0)) # Vector pointing straight upwards
	ang = upvec.angle(normal_green)*(rot_fix)
	set_parent_trans(plane_green, ob)
	plane_red.rotation_euler[1] = ang
	
	head = context.scene.objects[name_head]
	verts_red_head = get_colored_verts(head, red, 0.1)
	verts_green_head = get_colored_verts(head, green, 0.1)
	mean_vert_red_head = mean_verts(verts_red_head)
	mean_vert_green_head = mean_verts(verts_green_head)
	
	""" Create planes on fiducials of the head for both upper and lower.
		This has to be done before any of the two fiducials is booled away. """
	bpy.ops.object.select_all(action='DESELECT')
	if bpy.data.objects.get("plane_head_upper_red") is None:
		""" in case on fiducial device has already been booled away, dont remove the lower half """
		if bpy.data.objects.get("plane_red_LOWER.001x") is not None: #hack
			print("plane_red_LOWER.001 not found")
			verts_red_head_upper = [v for v in verts_red_head if v[2] < mean_vert_red_head]
			verts_green_head_upper = [v for v in verts_green_head if v[2] < mean_vert_green_head]
		else:
			verts_red_head_upper = verts_red_head
			verts_green_head_upper = verts_green_head
		plane_head_upper_red = create_plane_head(verts_red_head_upper, 'plane_head_upper_red', head)
		plane_head_upper_green = create_plane_head(verts_green_head_upper, 'plane_head_upper_green', head)
	else:
		plane_head_upper_red = bpy.data.objects.get("plane_head_upper_red")
		plane_head_upper_green = bpy.data.objects.get("plane_head_upper_green")
	if bpy.data.objects.get("plane_head_lower_red") is None:
		""" in case on fiducial device has already been booled away, dont remove the upper half """
		if bpy.data.objects.get("plane_red_UPPER.001x") is not None: #hack
			print("plane_red_UPPER.001 not found")
			verts_red_head_lower = [v for v in verts_red_head if v[2] > mean_vert_red_head]
			verts_green_head_lower = [v for v in verts_green_head if v[2] > mean_vert_green_head]
		else:
			verts_red_head_lower = verts_red_head
			verts_green_head_lower = verts_green_head
		plane_head_lower_red = create_plane_head(verts_red_head_lower, 'plane_head_lower_red', head)
		plane_head_lower_green = create_plane_head(verts_green_head_lower, 'plane_head_lower_green', head)
	else:
		plane_head_lower_red = bpy.data.objects.get("plane_head_lower_red")
		plane_head_lower_green = bpy.data.objects.get("plane_head_lower_green")

	""" Bool fiducial device away before linked duplicate is created """
	bool_away(context, ob, plane_green, dist)	 
	
	print("Creating Linked Duplicates")
	create_linked_duplicates(ob, group_name_linked, context)
		
	obname = ob.name
	ob_linked = scn.objects[obname + '.001']
	plane_red_linked = scn.objects['plane_red_' + ul + '.001']
	plane_green_linked = scn.objects['plane_green_' + ul + '.001']
	bpy.ops.object.select_all(action='DESELECT')
	ob_linked.select = True
	bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
	set_parent_trans(ob_linked, plane_red_linked)
	bpy.ops.object.select_all(action='DESELECT')
	plane_green_linked.select = True
	bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
	set_parent_trans(plane_green_linked, ob_linked)
	
	if ul == 'UPPER':
		plane_red_linked.location = plane_head_upper_red.location
		plane_red_linked.rotation_euler = plane_head_upper_red.rotation_euler
	if ul == 'LOWER':
		plane_red_linked.location = plane_head_lower_red.location
		plane_red_linked.rotation_euler = plane_head_lower_red.rotation_euler
	
	bpy.ops.object.select_all(action='DESELECT')
	plane_red.select = True
	
	if plane_red_linked.matrix_world.translation[1] < plane_green_linked.matrix_world.translation[1]:
		bpy.ops.object.select_all(action='DESELECT')
		plane_red_linked.select = True
		bpy.ops.transform.resize(value=(1,1,-1), constraint_axis=(False, False, True), constraint_orientation='LOCAL')
			
	bpy.ops.object.select_all(action='DESELECT')
	plane_green_linked.select = True
	bpy.ops.object.make_single_user(type='SELECTED_OBJECTS', object=True, obdata=True)
	bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
	bpy.ops.object.transform_apply( rotation = True )
	normal_green_linked = plane_green_linked.data.polygons[0].normal
	set_parent_trans(plane_green_linked, ob_linked)
	bpy.ops.object.select_all(action='DESELECT')
	
	if ul == 'UPPER':
		plane_head_upper_green.select = True
		#bpy.ops.object.transform_apply( rotation = True )
		#normal_green_head_upper = plane_head_upper_green.data.polygons[0].normal
		pgmwu = plane_head_upper_green.matrix_world.copy()
		normal_green_head_upper = Vector((pgmwu[0][2], pgmwu[1][2], pgmwu[2][2])) # get the local Z-axis
		ang_upper = normal_green_head_upper.angle(normal_green_linked)*(-1)
	if ul == 'LOWER':
		plane_head_lower_green.select = True
		#bpy.ops.object.transform_apply( rotation = True )
		#normal_green_head_lower = plane_head_lower_green.data.polygons[0].normal
		pgmwl = plane_head_lower_green.matrix_world.copy()
		normal_green_head_lower = Vector((pgmwl[0][2], pgmwl[1][2], pgmwl[2][2])) # get the local Z-axis
		if plane_green_linked.matrix_world.translation[0] < (plane_head_lower_green.matrix_world.translation[0] + 0.01):
			rotfix = 1
		else:
			rotfix = -1
		ang_lower = normal_green_head_lower.angle(normal_green_linked)*rotfix
			
	bpy.ops.object.select_all(action='DESELECT')
	plane_red_linked.select = True
	matrix = plane_red_linked.matrix_world
	z_axis = (matrix[0][2], matrix[1][2], matrix[2][2]) # get the local Z-axis
	if ul == 'UPPER':
		bpy.ops.transform.rotate(value=ang_upper, axis=z_axis)
		if plane_green_linked.matrix_world.translation[2] > (plane_head_upper_green.matrix_world.translation[2] - 2.0):
			bpy.ops.transform.rotate(value=deg_180, axis=z_axis)
	if ul == 'LOWER':
		bpy.ops.transform.rotate(value=ang_lower, axis=z_axis)
		if plane_green_linked.matrix_world.translation[2] < (plane_head_lower_green.matrix_world.translation[2] + 2.0):
			bpy.ops.transform.rotate(value=deg_180, axis=z_axis)
	#plane_red_linked.rotation_euler[1] = ang_upper
	
	""" the lower mold needs some further operations """
	if ul == 'LOWER':
		bpy.ops.object.select_all(action='DESELECT')
		plane_red.select = True
		#plane_red.rotation_euler[1] += deg_90*2
		plane_red.location[0] += 150
		
	if ul == 'UPPER':
		bpy.ops.object.select_all(action='DESELECT')
		plane_red.select = True
		matrix = plane_red.matrix_world.copy()
		z_axis = (matrix[0][2], matrix[1][2], matrix[2][2]) # get the local Z-axis
		if plane_green.matrix_world.translation[2] < plane_red.matrix_world.translation[2]:
			bpy.ops.transform.rotate(value=deg_180, axis=z_axis)
		#plane_red.rotation_euler[1] += deg_90*2
		plane_red.location[0] += 250
		
	""" finally align both the molds inverted and invert the normals as well """
	bpy.ops.object.select_all(action='DESELECT')
	plane_red.select = True
	matrix = plane_red.matrix_world
	z_axis = (matrix[0][2], matrix[1][2], matrix[2][2]) # get the local Z-axis
	#bpy.ops.transform.rotate(value=deg_180, axis=z_axis)
	scn.objects.active = ob
	bpy.ops.object.mode_set(mode = 'EDIT')
	bpy.ops.mesh.select_all(action='SELECT')
	bpy.ops.mesh.flip_normals() # just flip normals
	bpy.ops.object.mode_set(mode = 'OBJECT')
	
	""" Bool fiducial device at the head away """
	if ul == 'LOWER':
		bool_away(context, head, plane_head_lower_green, dist)
	if ul == 'UPPER':
		bool_away(context, head, plane_head_upper_green, dist)
		
	""" If both models are aligned, create planes """
	if bpy.data.objects.get(name_plane_vertical) is not None:
		plane_orig = bpy.data.objects.get(name_plane_vertical)
		loc = plane_red.matrix_world.translation
		if ul == 'LOWER':
			delta = plane_orig.matrix_world.translation - plane_head_lower_red.matrix_world.translation
		if ul == 'UPPER':
			delta = plane_orig.matrix_world.translation - plane_head_upper_red.matrix_world.translation
		mat = plane_orig.matrix_world
		bpy.ops.object.select_all(action='DESELECT')
		if ul == 'LOWER':
			#bpy.ops.mesh.primitive_plane_add(location=loc + delta, rotation=(mat.to_euler()[0], mat.to_euler()[1], mat.to_euler()[2]))
			bpy.ops.mesh.primitive_plane_add(location=loc, rotation=(mat.to_euler()[0], mat.to_euler()[1], mat.to_euler()[2]))
		if ul == 'UPPER':
			bpy.ops.mesh.primitive_plane_add(location=loc, rotation=(mat.to_euler()[0], mat.to_euler()[1], mat.to_euler()[2]))
			#bpy.ops.mesh.primitive_plane_add(location=(0.0,0.0,0.0))
		
		plane = bpy.context.object	  
		set_parent_trans(plane_orig, plane_red_linked)
		ml = plane_orig.matrix_local.copy()
		set_parent_trans(plane, plane_red)
		#plane.parent = plane_red
		plane.matrix_local = ml	   
		plane.scale = plane_orig.scale/2
		plane.name = name_plane_vertical + '_' + ul
		plane.select = True
		if not name_plane_group in bpy.data.groups:
			bpy.ops.group.create(name=name_plane_group)
		bpy.ops.object.group_link(group=name_plane_group)
		
#		 """ modify global delta for handler """
#		 if ul == 'LOWER':
#			 delta_lower = plane_orig.matrix_world.translation - (loc + delta)
#			 if bpy.data.objects.get('plane_vertical_UPPER') is not None:
#				 pu = bpy.data.objects.get('plane_vertical_UPPER')
#				 delta_ul = plane.matrix_world.translation - pu.matrix_world.translation
#		 if ul == 'UPPER':
#			 delta_upper = plane_orig.matrix_world.translation - (loc - delta)
#			 if bpy.data.objects.get('plane_vertical_LOWER') is not None:
#				 pl = bpy.data.objects.get('plane_vertical_UPPER')
#				 delta_ul = plane.matrix_world.translation - pl.matrix_world.translation
				
		bpy.ops.object.select_all(action='DESELECT')		
		#vec1 = plane_green.matrix_world.translation - plane_red.matrix_world.translation
		#vec2 = plane_green_linked.matrix_world.translation - plane_red_linked.matrix_world.translation		   
		#ang = vec1.angle(vec2) 
		#rotaxis = vec1.cross(vec2)
		#rotaxis.normalize
		plane.select = True
		plane.show_wire = True
		plane.draw_type = 'WIRE'
		#bpy.ops.transform.rotate(value = ang * (-1), axis=rotaxis)
		
		set_parent_trans(plane_orig, plane_red_linked)
		#ml = plane_orig.matrix_local.copy()
		
		""" make the head semi-transparent """
		if len(head.material_slots) == 0:
			mat = bpy.data.materials.get("HeadMat")
			if mat is None:
				mat = bpy.data.materials.new(name="HeadMat")
				head.data.materials.append(mat)
				hm = head.data.materials[0]
				hm.use_transparency = True
				hm.alpha = 0.3
				hm.specular_alpha = 0.0
				head.show_transparent = True
						
		
def rotate_by_vecs(vec1, vec2, ob):
	""" rotate object by angle between to vectors, deprecated due to use of operator """
	ang = vec1.angle(vec2)
	rotaxis = vec1.cross(vec2)
	rotaxis.normalize
	ob.select = True
	bpy.ops.transform.rotate(value = ang, axis=rotaxis)
	
def rotateByVecs(vec1, vec2, ob):
	""" rotate object by angle between to vectors """
	ang = vec1.angle(vec2)
	rotaxis = vec1.cross(vec2)
	#ob.select = True
	rotateAxisAngle(rotaxis, ang, ob)		   
	
def crown_eye_create_empty_middle(scn, e1, name_other):
	""" creates the emties for the head alignment and the corresponding planes """
	if name_other == 'eye_first' or name_other == 'eye_second':
		name_middle = "eye_middle"
	elif name_other == 'lip_left' or name_other == 'lip_right':
		name_middle = "lips_middle"
	else:
		name_middle = "nose_middle"
	print("Name other: " + name_other)
	print("Name e1: " + e1.name)
	e2 = bpy.data.objects.get(name_other)
	mp = midpoint(e1.matrix_world.translation, e2.matrix_world.translation)
	if bpy.data.objects.get(name_middle) is None:
		e = bpy.data.objects.new(name_middle, None )
		bpy.context.scene.objects.link(e)
	else:
		e = bpy.data.objects.get(name_middle)
		for ob in e.children:
			""" Clear parent inverse for all children """
			mw = ob.matrix_world.copy()
			ob.parent = None
			ob.matrix_world = mw
	e.empty_draw_size = 20
	e.empty_draw_type = 'PLAIN_AXES'
	e.matrix_world.translation = mp
	plane = plane_from_normal(mp, e1.matrix_world.translation - e2.matrix_world.translation)
	plane.show_wire = True
	if name_other == 'eye_first' or name_other == 'eye_second':
		name_plane = name_plane_horizontal
	else:
		name_plane = name_plane_vertical
	if bpy.data.objects.get(name_plane) is not None:
		to_delete = bpy.data.objects.get(name_plane)
		to_delete.name = "deleted"
		scn.objects.unlink(to_delete)
	
	plane.name = name_plane
	if plane.name == name_plane_vertical:
		bpy.ops.object.select_all(action='DESELECT')
		plane.select = True
		if not name_plane_group in bpy.data.groups:
			bpy.ops.group.create(name=name_plane_group)
		bpy.ops.object.group_link(group=name_plane_group)
		""" make vertical plane axis-aligned """
		#plane.rotation[2] = deg_90			
	return e
				
def crown_eye_create_empty(name, part):
	print("Creating Empty")
	scn = bpy.context.scene
	name_empty = part + "_" + name
	name_other = part + "_" + theother(name)
	if bpy.data.objects.get(name_empty) is not None:
		if bpy.data.objects.get(name_other) is not None:
			e1 = bpy.data.objects.get(name_empty)
			e1.matrix_world.translation = scn.cursor_location
			e = crown_eye_create_empty_middle(scn, e1, name_other)
		else:
			e = bpy.data.objects.get(name_empty)
			e.matrix_world.translation = scn.cursor_location
	elif bpy.data.objects.get(name_other) is not None:
		e1 = bpy.data.objects.new(name_empty, None )
		bpy.context.scene.objects.link(e1)
		e1.empty_draw_size = 5
		e1.empty_draw_type = 'SPHERE'
		e1.matrix_world.translation = scn.cursor_location
		e = crown_eye_create_empty_middle(scn, e1, name_other)
	else:
		e = bpy.data.objects.new(name_empty, None )
		bpy.context.scene.objects.link(e)
		e.empty_draw_size = 5
		e.empty_draw_type = 'SPHERE'
		e.matrix_world.translation = scn.cursor_location

	return e

def theother(name):
	if name == 'first':
		return 'second'
	if name == 'second':
		return 'first'
	if name == 'upper':
		return 'lower'
	if name == 'lower':
		return 'upper'
	if name == 'left':
		return 'right'
	if name == 'right':
		return 'left'
	else:
		return 'unknown'

def midpoint(vec1, vec2):
	vec3 = (vec1 + vec2) / 2
	return vec3

def markTrash(context):
	#bpy.data.screens["Default"]
	bpy.types.SpaceView3D.use_occlude_geometry = False
	bpy.ops.object.mode_set(mode = 'EDIT')
	bpy.ops.mesh.select_all(action='DESELECT')

def markHoles(context):
	bpy.ops.object.mode_set(mode = 'EDIT')
	bpy.ops.mesh.select_all(action='DESELECT')
	bpy.types.SpaceView3D.use_occlude_geometry = True

def enterSculptMode():
	bpy.ops.object.mode_set(mode = 'SCULPT')
	

def cp_for_align(name_parent, list_children):
	if bpy.data.objects.get(name_parent) is not None:
		em = bpy.data.objects.get(name_parent)
		for name_child in list_children:
			if bpy.data.objects.get(name_child) is not None:
				child = bpy.data.objects.get(name_child)
			else:
				print("Name child:  " + name_child)
				return False
			if child not in em.children:
				set_parent_trans(child, em)
	else:
		print("Name parent: " + name_parent)
		return False
	return True
	
def add_curve_point(context, model_type, num):
	""" names for both curve data and curve object """
	print("adding curve point "+str(num))
	curve_name = 'curve_' + model_type
	curve_name_ob = curve_name + '_ob'
	curve_name_empty_left = 'curve_empty_' + model_type + '_left'
	curve_name_empty_right = 'curve_empty_' + model_type + '_right'
	
	loc = context.scene.cursor_location
	
	""" check for curve data or create when necessary """
	if bpy.data.curves.get(curve_name) is None:
		curvedata = bpy.data.curves.new(name=curve_name,type='CURVE')
	else:
		curvedata = bpy.data.curves.get(curve_name)
	curvedata.dimensions = '3D'
	curvedata.fill_mode = 'FULL'
	
	""" check for curve object or create when necessary. link it into scene """
	if bpy.data.objects.get(curve_name_ob) is None:
		ob = bpy.data.objects.new(curve_name_ob, curvedata)
		bpy.context.scene.objects.link(ob)
		ob.show_x_ray = True
	else:
		ob = bpy.data.objects.get(curve_name_ob)
		ob.show_x_ray = True
		
	""" the actual points and lines have to be set as splines """
	try:
		polyline = curvedata.splines[0]
	except:
		polyline = curvedata.splines.new('BEZIER')
		polyline.bezier_points.add(3) # to get four points, add 3 because one is there already
	
	points = polyline.bezier_points
	num_pt = num-1
	points[num_pt].co = loc	   
	for i, pt in enumerate(points):
		if i == len(points)-1:
			hr = (points[i].co+points[0].co) / 2
		else:
			hr = (points[i].co+points[i+1].co) / 2
		if i == 0:
			hl = (points[i].co+points[len(points)-1].co) / 2
		else:
			hl = (points[i].co+points[i-1].co) / 2
		
		points[i].handle_left = hl
		points[i].handle_right = hr
		
	if num == 3:
		if bpy.data.objects.get(curve_name_empty_left) is None:
			e = bpy.data.objects.new(curve_name_empty_left, None)
			bpy.context.scene.objects.link(e)
		else:
			e = bpy.data.objects.get(curve_name_empty_left)
		e.location = points[num_pt-1].handle_right
		e.show_x_ray = True
		createHook(ob, e, num_pt-1, context)
	if num == 4:
		if bpy.data.objects.get(curve_name_empty_right) is None:
			e = bpy.data.objects.new(curve_name_empty_right, None)
			bpy.context.scene.objects.link(e)
		else:
			e = bpy.data.objects.get(curve_name_empty_right)
		e.location = points[num_pt-1].handle_left
		e.show_x_ray = True
		createHook(ob, e, num_pt-1, context)

def createHook(obj, e, i, context):
	# select and make curve object active (for later edit mode)
	obj.select = True
	context.scene.objects.active = obj
	
	b_points = obj.data.splines[0].bezier_points
	
	m0 = obj.modifiers.new(str(i), 'HOOK')
	m0.object = e
	
	# make sure no control points are selected
	for p in b_points:
		p.select_control_point = False
		p.select_right_handle = False
		p.select_left_handle = False
		
	bpy.ops.object.mode_set(mode="EDIT")
	# the mode_set() invalidated the pointers, so get fresh ones
	p0 = obj.data.splines[0].bezier_points[i]
	if i == 2:
		p0.select_left_handle=True
		bpy.ops.object.hook_assign(modifier=str(i))
		bpy.ops.object.hook_reset(modifier=str(i))
		p0.select_left_handle = False
	elif i == 1:
		p0.select_right_handle=True
		bpy.ops.object.hook_assign(modifier=str(i))
		bpy.ops.object.hook_reset(modifier=str(i))
		p0.select_right_handle = False
	
	bpy.ops.object.mode_set(mode="OBJECT")

def duplicate_teeth(tooth_obj, src, dest, context):
	tooth_dest = tooth_obj.copy()
	tooth_dest.data = tooth_obj.data.copy()
	context.scene.objects.link(tooth_dest)
	parentClear(tooth_dest, 'CLEAR_KEEP_TRANSFORM')
	
	manualParentCopy(tooth_obj, tooth_dest, src, dest)

def seperateTeethFromParents(groupName):
	""" Splits the tooth objects and their bounding box parents into two separate lists of objects and sorts them by name """
	if groupName in bpy.data.groups:
		teeth = list()
		teethParents = list()
		group = bpy.data.groups.get(groupName)
		obs = group.objects
		for ob in obs:
			if len(ob.name.split('.')) > 1:
				teethParents.append(ob)
			else:
				if len(ob.name.split('.')) == 1:
					teeth.append(ob)
				else:
					return None
		if groupName in ['t_UPPER_left', 't_UPPER_right', 't_LOWER_left', 't_LOWER_right']: # todo: find a better system for dynamic names
			teeth.sort(key=lambda x: x.name, reverse=False)
			teethParents.sort(key=lambda x: x.name, reverse=False)
		else:
			teeth.sort(key=lambda x: x.name, reverse=True)
			teethParents.sort(key=lambda x: x.name, reverse=True)		 
		return teeth, teethParents
		
	else:
		return None
	
def toothPlacer(parent_ob, parent_ob_location, plane_name, vec, ul, context):
	print("Placing tooth. Direction Vector: " + str(vec))
	
	parent_ob.location = parent_ob_location
		
	plane = bpy.data.objects.get(plane_name)
	mw = plane.matrix_world
	mwi = mw.inverted()
	
	
	# src and dst in local space of plane
	#origin0 = mwi * spline_points[0].co
	#origin1 = mwi * spline_points[1].co
	direction = Vector((0.0,0.0,1.0))
	
	#hit, loc, norm, face = plane.ray_cast(origin0, direction)			  
	#loc_plane_0 = mw * loc
	
	#hit, loc, norm, face = plane.ray_cast(origin1, direction)
	#loc_plane_1 = mw * loc
	
	#print(loc_plane_0, loc_plane_1)
	
	vec1 = Vector((1.0,0.0,0.0)) # x-axis as vector for teeth emtpy
	#vec_bez = origin0 - origin1
	#vec_bez = spline_points[0].co - spline_points[1].co
	vec_bez = vec
	#vec2 = loc_plane_0 - loc_plane_1
	#vec2_tmp = vec2.copy()
	#vec2[2] = 0.0
	#bpy.ops.object.select_all(action='DESELECT')
	objectDeselectAll(context)
	#rotate_by_vecs(vec1, vec2, parent_ob)
	
	parent_face = parent_ob.data.polygons
	parent_face = parent_face[parent_face.active]
	parent_normal = parent_face.normal
	
	plane = bpy.data.objects.get(plane_name)			
	plane_face = plane.data.polygons[0]
	plane.rotation_mode = 'QUATERNION'
	plane_normal = plane.rotation_quaternion * plane_face.normal
	print(plane_normal)
	plane.rotation_mode = 'XYZ'
	
	#print(parent_ob.matrix_world)
	#bpy.ops.object.select_all(action='DESELECT')
	#rotate_by_vecs(parent_normal, plane_normal, parent_ob)
	#print(parent_ob.matrix_world)
	
	# TODO: make local x-axis align with line
	#bpy.ops.object.select_all(action='DESELECT')
	objectDeselectAll(context)
	parent_ob.select = True
	print("Vec_bez: " + str(vec_bez))
	vec_bez_flat = vec_bez.copy()
	vec_bez_flat[2] = 0
	parent_ob_mw = parent_ob.matrix_world.copy()
	print(parent_ob_mw)
	parent_ob_x_axis = Vector((parent_ob_mw[0][0], parent_ob_mw[1][0], parent_ob_mw[2][0]))
	parent_ob_x_axis[2] = 0
	print("parent object vectors")
	print(vec_bez_flat)
	print(parent_ob_x_axis)
	rot_angle_z = vec_bez_flat.angle(parent_ob_x_axis)
	print("Rot angle Z: " + str(rot_angle_z))
	z_axis = Vector((0.0,0.0,1.0))
	parent_ob.select = True
	print(parent_ob.rotation_euler)
	rot_temp = parent_ob.rotation_euler[2]
	#bpy.ops.transform.rotate(value = rot_angle_z, axis=z_axis)
	parent_ob.rotation_euler[2] = rot_angle_z + rot_temp
	print(parent_ob.rotation_euler)
	#rotate_by_vecs(vec_bez_flat, parent_ob_x_axis, parent_ob)
	
	""" rotate the parent ob to match rotation of plane """
	if ul == 'UPPER':
		clz = getLocalAxis(parent_ob, "Z")
	elif ul == 'LOWER':
		clz = getLocalAxis(parent_ob, "Z") * (-1)
	clp = getLocalAxis(plane, "Z")
	bpy.context.scene.update()
	rotateByVecs(clz, clp, parent_ob)
	
	""" rotate parent ob around local Z-axis to make local X-axis point in direction of vec """
	plNorm = vec.cross(z_axis)
	A = getLocalAxis(parent_ob, "X")
	B = plNorm	  
	
	tmp = A.dot(B)/(B.length*B.length)
	pt = A - tmp*B
	
	if ul == 'UPPER':
		clz = getLocalAxis(parent_ob, "Z")
	elif ul == 'LOWER':
		clz = getLocalAxis(parent_ob, "Z") * (-1)
		
	ang = A.angle(pt)
	#bpy.ops.object.select_all(action='DESELECT')
	objectDeselectAll(context)
	parent_ob.select = True
	#bpy.ops.transform.rotate(value = ang, axis=clz)	
	
def align_teeth(ul, context):
	""" Align the teeth along the curve including correct rotation """
	group_name_left = 't_' + ul + '_left'
	group_name_right = 't_' + ul + '_right'
	group_name_right_curve = 't_' + ul + '_right_curve'
	group_name_left_curve = 't_' + ul + '_left_curve'
	group_names = [group_name_left, group_name_right, group_name_right_curve, group_name_left_curve]
	group_names_curve = [group_name_right_curve, group_name_left_curve]
	curve_name = 'curve_' + ul + '_ob'
	
	print("Aligning Teeth")
	
	empty_name_left = 'curve_empty_' + ul + '_left'
	empty_name_right = 'curve_empty_' + ul + '_right'
	
	plane_name = name_plane_vertical + '_' + ul
	
	if bpy.data.objects.get(curve_name) is not None:
		curve_ob = bpy.data.objects.get(curve_name)
		sp = curve_ob.data.splines[0]
	else:
		print("Could not find tooth placement curve " + curve_name)
		return {'FINISHED'}
	
	left = sp.bezier_points[1]
	right = sp.bezier_points[2]
	arcLength = arcLengthSegment(left, right)
	arcLengthTeeth = 0.0
	
	""" compute the length of all front teeth in a train to later compare it with the length of the curve """
	for group_name in group_names_curve:
		if group_name in bpy.data.groups:
			teethCurve, teethParentsCurve = seperateTeethFromParents(group_name)
			for parent_ob in teethParentsCurve:
				arcLengthTeeth += parent_ob.dimensions[0]
	arcLengthDiff = arcLength - arcLengthTeeth
				
	print("Arc Length Teeth: " + str(arcLengthTeeth))
	print("Arc Length Curve: " + str(arcLength))
	print("Arc Length Difference: " + str(arcLengthDiff))
	
	
	for group_name in group_names:
		if group_name in bpy.data.groups:
			
			teeth, teethParents = seperateTeethFromParents(group_name)
			
			if teethParents is not None:
				print("Found teeth group and placer objects")
			else:
				print("Could not find master empty for teeth group " + group_name)
				return {'FINISHED'}
			
			if len(sp.bezier_points) > 3:
				""" move all objects in group to layer 1 before translation """
				obs = bpy.data.groups[group_name].objects
				for ob in obs:
					ob.layers[0] = True
			
			if group_name == group_name_left:
				dist = get_distance(sp.bezier_points[0].co, sp.bezier_points[1].co)
				vec = sp.bezier_points[1].co - sp.bezier_points[0].co
			elif group_name == group_name_right:
				dist = get_distance(sp.bezier_points[3].co, sp.bezier_points[2].co)
				vec = sp.bezier_points[2].co - sp.bezier_points[3].co
			elif group_name == group_name_right_curve or group_name == group_name_left_curve:
				dist = arcLength
				
			print("Vector: " + str(vec))
			
			delta=arcLengthDiff/dist/2 #for moving the teeth if arc is too short
			e = 0.0
			oldwidth = 0.0
			
			hl = bpy.data.objects.get(empty_name_right).location
			hr = bpy.data.objects.get(empty_name_left).location
			
			for parent_ob in teethParents:
				
				width = parent_ob.dimensions[0]/2
				e += (width+oldwidth)/dist # the teeth have different widths
				oldwidth = width
				
				print("width: " + str(width))
				print("e: " + str(e))
				print("e * vec: " + str(e * vec))
				
				spline_points = list()
				
				direction = Vector((0.0,0.0,0.0)) # initialization
				
				if group_name == group_name_left:
					point = sp.bezier_points[1].co - (e-delta) * vec
					direction = sp.bezier_points[0].co - sp.bezier_points[1].co
				elif group_name == group_name_right:
					point = sp.bezier_points[2].co - (e-delta) * vec
					direction = sp.bezier_points[3].co - sp.bezier_points[2].co
				elif group_name == group_name_right_curve:
					point = evaluateAlt(left, right, hl, hr, 1-e-delta)
					direction = evaluateTangentAlt(left, right, hl, hr, 1-e-delta)
				elif group_name == group_name_left_curve:
					point = evaluateAlt(left, right, hl, hr, e+delta)
					direction = evaluateTangentAlt(left, right, hl, hr, e+delta)
					
#				 if group_name == group_name_left:
#					 point = sp.bezier_points[1].co - e * vec
#					 direction = sp.bezier_points[0].co - sp.bezier_points[1].co
#				 elif group_name == group_name_right:
#					 point = sp.bezier_points[2].co - e * vec
#					 direction = sp.bezier_points[3].co - sp.bezier_points[2].co
#				 elif group_name == group_name_right_curve:
#					 point = evaluateAlt(left, right, hl, hr, 1-e)
#					 direction = evaluateTangentAlt(left, right, hl, hr, 1-e)
#				 elif group_name == group_name_left_curve:
#					 point = evaluateAlt(left, right, hl, hr, e)
#					 direction = evaluateTangentAlt(left, right, hl, hr, e)
				
				print("point: " + str(point))
				print("direction: " + str(direction))
				
				#direction = Vector((0.0,0.0,1.0))
				plane = bpy.data.objects.get(plane_name)
				loc_plane = locationFromRaycast(plane, point, z_axis)
				point[2] = loc_plane[2]
					
				#mp = midpoint(sp.bezier_points[0].co, sp.bezier_points[1].co)
				
				toothPlacer(parent_ob, point, plane_name, direction, ul, context)
				
				tooth_obj = parent_ob.children[0] # each tooth has it's own parent
				
				""" TODO: Molds need unique names """
				if ul == 'UPPER':
					src = context.scene.objects[NAME_JAW_UPPER]
					dest = context.scene.objects[NAME_JAW_UPPER + '.001']
				if ul == 'LOWER':
					src = context.scene.objects[NAME_JAW_LOWER]
					dest = context.scene.objects[NAME_JAW_LOWER + '.001'] 
				
				duplicate_teeth(tooth_obj, src, dest, context)
				# #set planes semi transparent
				headObj=bpy.data.objects.get(name_head)
				pv = bpy.data.objects.get(name_plane_vertical)
				ph = bpy.data.objects.get(name_plane_horizontal)
				if pv is not None:
					pv.data.materials.append(headObj.data.materials[0])
					pv.show_transparent = True
				else:
					print("Plane Vertical not Found")
				if ph is not None:
					ph.data.materials.append(headObj.data.materials[0])
					ph.show_transparent = True
				else:
					print("Plane Horizontal not Found")
	
def deleteSelectedFaces(context):
	mesh_data = bpy.context.edit_object.data #get the active mesh's data
	bm = bmesh.from_edit_mesh(mesh_data)
	selected_vertices = [v for v in bm.verts if v.select]
	bmesh.ops.delete(bm, geom=selected_vertices, context=1)
	bmesh.update_edit_mesh(mesh_data, True)
	bpy.ops.mesh.select_all(action='DESELECT')
	#call([ESC,"Blender"])

def deleteUnSelectedFaces(context):
	mesh_data = bpy.context.edit_object.data #get the active mesh's data
	bm = bmesh.from_edit_mesh(mesh_data)
	selected_vertices = [v for v in bm.verts if not v.select]
	bmesh.ops.delete(bm, geom=selected_vertices, context=1)
	bmesh.update_edit_mesh(mesh_data, True)
	bpy.ops.mesh.select_all(action='DESELECT')
	#call([ESC,"Blender"])
	

def alignUpper(context):
	bpy.ops.object.select_all(action='DESELECT')
	bpy.data.objects[NAME_JAW_UPPER].select = True
	bpy.context.scene.objects.active = bpy.data.objects[NAME_JAW_UPPER]
	align_mold(context, 'UPPER')

def alignLower(context):
	bpy.ops.object.select_all(action='DESELECT')
	bpy.data.objects[NAME_JAW_LOWER].select = True
	align_mold(context, 'LOWER')



def deselectAll(context):
	bpy.ops.mesh.select_all(action='DESELECT')

def alignHead(context):
	scn = bpy.context.scene
	e1 = scn.objects.get(name_nose_upper)
	crown_eye_create_empty_middle(scn, e1, name_nose_lower)
	
	list_children = [name_head, name_eye_first, name_eye_second, name_plane_horizontal, name_plane_vertical, name_nose_upper, name_nose_middle, name_nose_lower, name_lip_left, name_lip_right]
	
	try_cp = cp_for_align(name_eye_middle, list_children)
	if try_cp == False:
		print("Setup of child-parent hierarchy for alignment failed, objects not found.")
		return {'FINISHED'}
	
	ef = bpy.data.objects.get(name_eye_first)
	em = bpy.data.objects.get(name_eye_middle)
	es = bpy.data.objects.get(name_eye_second)
	nu = bpy.data.objects.get(name_nose_upper)
	nm = bpy.data.objects.get(name_nose_middle)
	ph = bpy.data.objects.get(name_plane_horizontal)
	pv = bpy.data.objects.get(name_plane_vertical)
	head = bpy.data.objects.get(name_head)
	
	em.location = (0.0,0.0,0.0)
	bpy.ops.object.select_all(action='DESELECT') # force redraw
	xvec = Vector((1.0,0.0,0.0)) # Vector pointing along x-axis
	zvec = Vector((0.0,0.0,1.0)) # Vector pointing along z-axis
	svec = es.matrix_world.translation.copy()		 
	ang = svec.angle(xvec)
	rotaxis = svec.cross(xvec)
	rotaxis.normalize
	em.select = True
	bpy.ops.transform.rotate(value = ang, axis=rotaxis)
	bpy.ops.object.select_all(action='DESELECT')
	nuvec = nu.matrix_world.translation.copy()
	nmvec = nm.matrix_world.translation.copy()
	uvec = nuvec - nmvec
	ang2 = uvec.angle(zvec)
	rotaxis2 = uvec.cross(zvec)
	rotaxis2.normalize
	em.select = True
	bpy.ops.transform.rotate(value = ang2, axis=rotaxis2)
	
	dim = head.dimensions[1]/2
	ph.scale=Vector((dim, dim, dim))
	pv.scale=Vector((dim, dim, dim))
	
	""" check and correct the direction of the face """
	if ef.matrix_world.translation[0] < es.matrix_world.translation[0]:
		bpy.ops.transform.rotate(value = deg_180, axis=zvec)
	
	""" apply transformation from parent to plane_vertical and re-parent """
	bpy.ops.object.select_all(action='DESELECT')
	pv.select = True	
	bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
	set_parent_trans(pv, em)
	
	""" center view on head in front ortho mode """
	print("Going into front ortho")
	bpy.ops.object.select_all(action='DESELECT')
	head.select = True
	""" to call an operator from outside, we need to communicate it the right area and region via override """
	for area in bpy.context.screen.areas:
		print(area.type)
		if area.type == 'VIEW_3D':
			for region in area.regions:
				if region.type == 'WINDOW':
					override = bpy.context.copy() # we need a copy of the context where we override area and region
					override['area'] = area
					override['region'] = region
	bpy.ops.view3d.view_selected(override)
	bpy.ops.view3d.viewnumpad(override, type='FRONT')
	for area in bpy.context.screen.areas:
		if area.type == 'VIEW_3D':
			if area.spaces.active.region_3d.view_perspective == 'PERSP':
				area.spaces.active.region_3d.view_perspective = 'ORTHO'


