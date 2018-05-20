import bpy
from subprocess import call
from IvoryDigital.classes.Constants import *
from IvoryDigital.classes.GeneralMethods import GeneralMethods
import os.path
import time
import mathutils
import bmesh
import math
from tkinter import Button
import addon_utils

#===================================
#GENERIC METHODS FOR CONTROLLING ALL THE RELEVANT SCENE ASPECTS
#
#==================================

class SceneController:

	def __init__(self,WIN_TITLE):
		self.WIN_TITLE=WIN_TITLE
		#self.WIN_TITLE_EDITED=WIN_TITLE_EDITED
		self.WIN_TITLE_EDITED=WIN_TITLE
		self.scene=bpy.context.scene
		self._surfaceElevation=0
		self.newContext = bpy.context.copy()
		self._camPosition=CAM_TOP_VIEW
		self.MAX=1
		self.MIN=2
		self.selectionMode=DEFAULT

	def initializeSceneRefiner(self):
		self.setCameraPosition('FRONT')
		#addon_utils.enable("Animation Nodes")
		bpy.ops.wm.addon_enable(module="animation_nodes")
		call([FULL_SCREEN,self.WIN_TITLE])

	def printSelectionObjStatus(self):
		for obj in bpy.context.scene.objects:
			print(obj.name+" selected: "+str(obj.select))
		print("active obj: "+str(bpy.context.scene.objects.active.name))

	def printObjectsAndMeshes(self,msg):
		print(msg)
		print("objects:")
		for object in bpy.data.objects:
			print(object.name)
		print("meshes:")
		for mesh in bpy.data.meshes:
			print(mesh.name)

	def initializeSceneModeller(self):

		#set top-down view
		#--------------------
		self.setCameraPosition('TOP')
		call([FULL_SCREEN,self.WIN_TITLE])
		#--------------------

	def fullScreenToggle(self):
		call([FULL_SCREEN,self.WIN_TITLE])

	def setCameraPosition(self,cameraPosition):
		self.resetContext()
		self._camPosition=cameraPosition
		bpy.ops.view3d.viewnumpad(self.newContext, 'EXEC_DEFAULT', type=cameraPosition)

	def circleSelect(self):
		call([CIRCLE_SELECT,self.WIN_TITLE])
		self.selectionMode=CIRCLE

	def fillHole(self):
		if not self.selectionMode==DEFAULT:
			self.cancelCircleSelect()
		call([FILL_HOLE,self.WIN_TITLE])

	def borderSelect(self):
		self.cancelCircleSelect()
		call([BORDER_SELECT,self.WIN_TITLE])
		self.selectionMode=BORDER

	def cancelCircleSelect(self):
		call([ESC,self.WIN_TITLE])
		self.selectionMode=DEFAULT

	def quitSelect(self):
		call([QUIT_SELECT,self.WIN_TITLE])
		self.selectionMode=DEFAULT

	def setZoom(self,zoomValue):
		self.resetContext()
		bpy.ops.view3d.zoom(self.newContext,delta=zoomValue)

	def resetContext(self):
		self.newContext = bpy.context.copy()
				#prepare contex
		for area in bpy.context.screen.areas:
			if area.type == "VIEW_3D":
				break

		for region in area.regions:
			if region.type == "WINDOW":
				break

		space = area.spaces[0]

		self.newContext['area'] = area
		self.newContext['region'] = region
		self.newContext['space_data'] = space

	def saveBlendAs(self):
		print("saveas")
		bpy.ops.wm.save_as_mainfile(filepath=INSTALL_DIR+"\\res\\test.blend")

	def setViewportShading(self,shadingStyle):
		for area in bpy.context.screen.areas: # iterate through areas in current screen
			if area.type == 'VIEW_3D':
				for space in area.spaces: # iterate through spaces in current VIEW_3D area
					if space.type == 'VIEW_3D': # check if space is a 3D view
						space.viewport_shade = shadingStyle# set the viewport shading to rendered

	def save(self):
		print("save")
		call([SAVE,self.WIN_TITLE])

	def getProportionalEditingStatus(self):
		return bpy.data.scenes["Scene"].tool_settings.proportional_edit

	def getProportionalEditingFalloffStyle(self):
		return bpy.data.scenes["Scene"].tool_settings.proportional_edit_falloff

	def enableProportionalEditing(self,falloffStyle):
		bpy.data.scenes["Scene"].tool_settings.proportional_edit='ENABLED'
		bpy.data.scenes["Scene"].tool_settings.proportional_edit_falloff=falloffStyle

	def disableProportionalEditing(self):
		bpy.data.scenes["Scene"].tool_settings.proportional_edit='DISABLED'

	#change the elevation for all selected surfaces regardless of object
	def changeSurfaceElevation(self,axis,newElevation,proportionalEditing,falloffStyle):
		valueVect=(0, 0, newElevation) #default
		if axis==X_AXIS:
			valueVect=(newElevation, 0, 0)
		elif axis==Y_AXIS:
			valueVect=(0, newElevation, 0)
		elif axis==Z_AXIS:
			valueVect=(0, 0, newElevation)
		if proportionalEditing=='ENABLED':
			bpy.ops.transform.translate(value=valueVect,proportional=proportionalEditing,proportional_edit_falloff=falloffStyle)
		else:
			bpy.ops.transform.translate(value=valueVect)
			

	def changeSurfaceElevationFreeVector(self,objectName,extent,vector,proportionalEditing,falloffStyle):
		object = bpy.data.objects[objectName]
		mesh = object.data	
		bm = bmesh.from_edit_mesh(mesh)
		movedVertIndexes=[]

		for face in bm.faces:
			if not face.select:
				continue
			if vector==None:
				stressDirec=face.normal
			else:
				stressDirec=self.localToGlobalCoords(vector)
			for vert in face.verts:
				if GeneralMethods.isPresentInList(vert.index,movedVertIndexes):
					continue
				vert.co=(vert.co[0]+stressDirec[0]*extent,vert.co[1]+stressDirec[1]*extent,vert.co[2]+stressDirec[2]*extent)
				movedVertIndexes+=[vert.index]
		bmesh.update_edit_mesh(object.data)


	def moveObject(self,objName,axis,extent):
		object=bpy.data.objects[objName]
		if axis==X_AXIS:
			vec = mathutils.Vector((1.0*extent, 0.0, 0.0))
		elif axis==Y_AXIS:
			vec = mathutils.Vector((0.0, 1.0*extent, 0.0))
		elif axis==Z_AXIS:
			vec = mathutils.Vector((0.0, 0.0, 1.0*extent))

		object.location = object.location + vec

	# def changeSurfaceElevationFreeVector(self,objectName,facesIndexList,extent,vector):
		# object = bpy.data.objects[objectName]
		# mesh = object.data	
		# bm = bmesh.from_edit_mesh(mesh)
		# facesList=bm.faces
		# for ind in facesIndexList:
			# face=facesList[ind]
			# face.select=True
			# for vert in face.verts:
				# vert.co=(vert.co[0]+vector[0]*extent,vert.co[1]+vector[1]*extent,vert.co[2]+vector[2]*extent)
		# bmesh.update_edit_mesh(object.data)
		#print("init: "+str(vector)+" "+str(valueVect))

	# def changeSurfaceFromListElevation(self,objectName,facesList,axis,newElevation,proportionalEditing,falloffStyle):
		# valueVect=(0, 0, newElevation) #default
		# object = bpy.data.objects[objectName]
		# mesh = object.data	
		# bm = bmesh.from_edit_mesh(mesh)

		# if axis==X_AXIS:
			# valueVect=(newElevation, 0, 0)
		# elif axis==Y_AXIS:
			# valueVect=(0, newElevation, 0)
		# elif axis==Z_AXIS:
			# valueVect=(0, 0, newElevation)
		# elif axis==NORMAL:

			# for face in bm.faces:
				# if not face.select:
					# continue
				# bpy.ops.transform.translate(value=valueVect,proportional=proportionalEditing,proportional_edit_falloff=falloffStyle)
			
		# bpy.ops.transform.translate(value=valueVect,proportional=proportionalEditing,proportional_edit_falloff=falloffStyle)


	def changeSelectedFacesColor(self,objectName,color):
		self.setObjectMode(objectName,'VERTEX_PAINT',False)
		bpy.data.meshes[GEL_MESH].use_paint_mask=True
		bpy.data.brushes["Draw"].color=color
		bpy.ops.paint.vertex_color_set()
		self.setObjectMode(objectName,'EDIT',False)

	def cameraFreeMove(self,axis,extent):
		for area in bpy.context.screen.areas:
			if area.type == "VIEW_3D":
				break
		space=area.spaces[0]
		rv3d=space.region_3d
		if axis==X_AXIS:
			rv3d.view_location.x += extent
		elif axis==Y_AXIS:
			rv3d.view_location.y += extent
		elif axis==Z_AXIS:
			rv3d.view_location.z += extent

	def teethMove(self,axis,extent):
		teeth = bpy.data.objects[TEETH_OBJ]
		if axis==X_AXIS:
			#vec = mathutils.Vector((extent, 0.0, 0.0))
			teeth.location.x+=extent
		elif axis==Y_AXIS:
			#vec = mathutils.Vector((0.0, extent, 0.0))
			teeth.location.y+=extent
		elif axis==Z_AXIS:
			#vec = mathutils.Vector((0.0, 0.0, extent))
			teeth.location.z+=extent
		#inv = teeth.matrix_world.copy()
		#inv.invert()
		# vec aligned to local axis
		# vec_rot = vec * inv
		# teeth.location+=vec_rot

	def selectAllToggle(self):
		bpy.ops.mesh.select_all(action='TOGGLE')
	
	def getSelectedFacesIndexesList(self,objectName):
		object = bpy.data.objects[objectName]
		mesh = object.data	
		result=[]
		bm = bmesh.from_edit_mesh(mesh)
		facesList=bm.faces
		for i in range(0,len(facesList)):
			bm.faces.ensure_lookup_table()
			if facesList[i].select:
				result = result+[i]
		return result


	def deleteFacesFromMesh(self,objName,deleteSelected):
		# Get the active mesh
		object = bpy.data.objects[objName]
		mesh = object.data

		# Get a BMesh representation
		bm = bmesh.from_edit_mesh(mesh)
		if deleteSelected:
			facesToDelete = [f for f in bm.faces if f.select] 
		else:
			facesToDelete = [f for f in bm.faces if not f.select] 

		bmesh.ops.delete(bm, geom=facesToDelete, context=5)

		# Show the updates in the viewport
		# and recalculate n-gon tessellation.
		bmesh.update_edit_mesh(mesh, True)

	def deleteObject(self,objname):
		bpy.ops.object.select_all(action='DESELECT')
		bpy.data.objects[objname].select = True
		bpy.ops.object.delete()

	def getAdjuscentFacesIndexes(self,faceInd,objectName):
		result=[]
		object = bpy.data.objects[objectName]
		mesh = object.data
		bm = bmesh.from_edit_mesh(mesh)
		relevantFace=bm.faces[faceInd]
		for edge in relevantFace.edges:
			linkedFaces = edge.link_faces
			for linkedFace in linkedFaces:
				result+=[linkedFace.index]
		return result
		
	def selectAdjuscentFaces(self,objectName,keepOrigFaceSelected):
		object = bpy.data.objects[objectName]
		mesh = object.data
		
		bm = bmesh.from_edit_mesh(mesh)
		selectedFaces=[f for f in bm.faces if f.select]

		for face in selectedFaces:
			for edge in face.edges:
				linkedFaces = edge.link_faces
				for linkedFace in linkedFaces:
					linkedFace.select = True
		if not keepOrigFaceSelected:
			face.select=False
		bmesh.update_edit_mesh(mesh, True)		


	#get the faces from the selection with a coordinate that falls whithin range
	def getSelectedFacesByCoordCondition(self,objName,axis,min,max):
		faces=self.getObjectFacesList(objName)
		result=[]
		for i in range(0,len(faces)):
			face=faces[i]
			if not face.select:
				continue
			centerCoord=self.localToGlobalCoords(face.calc_center_median())[axis]
			if centerCoord<min or centerCoord>max:
				continue
			result+=[i]

		return result

	#find min/max faces coords on a certain axis
	def findExtremumFacesCoords(self,objName,axis,type):
		#bpy.context.scene.objects.active = bpy.data.objects[objName]
		faces=self.getObjectFacesList(objName)
		if type==self.MIN:
			result=math.inf
		else:
			result=-1*math.inf
		for i in range(0,len(faces)):
			face=faces[i]
			centerCoord=(bpy.data.objects[objName].matrix_world*face.calc_center_median())[axis]
			if (type==self.MAX and centerCoord>result) or (type==self.MIN and centerCoord<result):
				result=centerCoord
		return result

	def findBothExtremumFacesCoords(self,objName,axis):
		faces=self.getObjectFacesList(objName)
		result=[0,0]
		for i in range(0,len(faces)):
			face=faces[i]
			centerCoord=self.localToGlobalCoords(face.calc_center_median())[axis]
			if centerCoord>result[1]:
				result[1]=centerCoord
			if centerCoord<result[0]:
				result[0]=centerCoord
		return result

	def localToGlobalCoords(self,vector):
		return bpy.context.active_object.matrix_world*vector
		
	#get perimeter edges indexes 
	def getPerimeterEdgesIndexes(self,objName):
		object = bpy.data.objects[objName]
		mesh = object.data
		counter=0
		bm = bmesh.from_edit_mesh(mesh)
		selectedFaces=[f for f in bm.faces if f.select]
		result=[]

		for face in selectedFaces:
			for edgeInd in range(0,len(face.edges)):
				linkedFaces = face.edges[edgeInd].link_faces
				if len(linkedFaces)==1:
					result+=[edgeInd]
		return result

	def selectAdjuscentFacesNum(self,objectName,numOfFaces):
		object = bpy.data.objects[objectName]
		mesh = object.data
		counter=0
		
		bm = bmesh.from_edit_mesh(mesh)
		selectedFaces=[f for f in bm.faces if f.select]

		for face in selectedFaces:
			for edge in face.edges:
				linkedFaces = edge.link_faces
				for linkedFace in linkedFaces:
					if not counter<numOfFaces:
						bmesh.update_edit_mesh(mesh, True)
						return
					counter+=1
					linkedFace.select = True

		bmesh.update_edit_mesh(mesh, True)

	def subdivideFaces(self,objectName,divisionLevel):
		object = bpy.data.objects[objectName]
		object.modifiers.new("subd", type='SUBSURF')
		object.modifiers['subd'].levels = divisionLevel

	def selectFacesFromIndexList(self,objectName,facesIndexList):
		object = bpy.data.objects[objectName]
		if not object.mode=='EDIT':
			self.setObjectMode(objectName,'EDIT',False)
		mesh = object.data
		bm = bmesh.from_edit_mesh(mesh)
		bm.faces.ensure_lookup_table()
		for ind in facesIndexList:
			if not ind>len(bm.faces):
				bm.faces[ind].select=True

	def getFaceCoords(self,objectName,faceIndex):
		object = bpy.data.objects[objectName]
		init_mode='EDIT'
		if not object.mode=='EDIT':
			init_mode='OBJECT'
			self.setObjectMode(objectName,'EDIT',False)
		mesh = object.data
		bm = bmesh.from_edit_mesh(mesh)
		bm.faces.ensure_lookup_table()
		face=bm.faces[faceIndex]
		result=object.matrix_world*face.calc_center_median()
		self.setObjectMode(objectName,init_mode,False)
		return result

	def deSelectFacesFromIndexList(self,objectName,facesIndexList):
		object = bpy.data.objects[objectName]
		if not object.mode=='EDIT':
			self.selectObjectToggle(objectName)
			self.setObjectMode(objectName,'EDIT',False)
		mesh = object.data
		bm = bmesh.from_edit_mesh(mesh)
		bm.faces.ensure_lookup_table()
		for ind in facesIndexList:
			if not ind>len(bm.faces):
				bm.faces[ind].select=False

	def selectFaceByIndex(self,objName,faceInd):
		object = bpy.data.objects[objName]
		mesh = object.data	
		bm = bmesh.from_edit_mesh(mesh)
		bm.faces.ensure_lookup_table()
		bm.faces[faceInd].select=True

	def objSetVisibility(self,objName,hide):
		object=bpy.data.objects[objName]
		initMode=1

		if object.mode=='EDIT':
			initMode=2
			self.setObjectMode(objName,'OBJECT',False)

		object.hide_render=hide
		object.hide=hide

		if initMode==2:
			self.setObjectMode(objName,'EDIT',False)

	def importObject(self,objFilepath):
		''' Imports non-Blender file formats. Supported: OBJ, FBX, PLY '''
		fileExt = objFilepath.rsplit('.', 1)[1].lower() #safer, allows for fileNames with dots in between. Lowercase for easier comparison
		if fileExt == 'obj':
			bpy.ops.import_scene.obj(filepath=objFilepath)
		elif fileExt == 'fbx':
			bpy.ops.import_scene.fbx(filepath=objFilepath)
		elif fileExt == 'ply':
			bpy.ops.import_mesh.ply(filepath=objFilepath)
		importedName=bpy.context.selected_objects[0].name
		obj=bpy.data.objects[importedName]

		#fix for sharp edges cyan marking
		bpy.context.scene.objects.active=obj
		obj.select=True
		self.setObjectMode(obj.name,'EDIT',False)
		bpy.context.tool_settings.mesh_select_mode = (False, True, False)
		bpy.ops.mesh.mark_sharp(clear=True)
		bpy.context.tool_settings.mesh_select_mode = (True, False, False)
		self.setObjectMode(obj.name,'OBJECT',False)
		return importedName

	def importObjectsGroupFromBlend(self,sourceFile,groupName):
		with bpy.data.libraries.load(sourceFile) as (df, dt):
			dt.groups=[groupName]
		print("loaded group "+groupName+". objects list:")
		groups = bpy.data.groups
		# alias existing group, or generate new group and alias that
		group = groups.get(groupName, groups.new(groupName))
		for obj in dt.groups[0].objects:
			print(obj.name)
			bpy.context.scene.objects.link(obj)
			if obj.name not in group.objects:
				group.objects.link(obj)


	def importAllObjectsFromBlend(self,sourceFile):
		with bpy.data.libraries.load(sourceFile) as (df, dt):
			for groupName in df.groups:
				print("attempting to import group "+groupName)
				self.importObjectsGroupFromBlend(sourceFile,groupName)
		
	def selectObjectToggle(self,objName):
		scene = bpy.context.scene
		object = scene.objects[objName]
		if object.select:
			object.select = False
		else:
			object.select = True	
			scene.objects.active = object

	def selectObject(self,objName):
		scene = bpy.context.scene
		bpy.ops.object.select_all(action='DESELECT')
		bpy.data.objects[objName].select = True
		scene.objects.active = bpy.data.objects[objName]

	def getObjectFullName(self,str,ind=0):
		scene = bpy.context.scene
		bpy.ops.object.select_all(action='DESELECT')
		candidates=[ob for ob in bpy.data.objects if str in ob.name]
		if len(candidates)==0:
			return
		return candidates[ind].name

	def setOccludeSelection(self,status):
		for scr in bpy.data.screens:
			for area in scr.areas:
				for space in area.spaces:
					if space.type == 'VIEW_3D':
						space.use_occlude_geometry = status

	def setClipping(self,value,startOrEnd):
		for window in bpy.context.window_manager.windows:
				for area in window.screen.areas: 
					if area.type == 'VIEW_3D':
						break
				if startOrEnd=='start':
					area.spaces.active.clip_start = value
				elif startOrEnd=='end':
					area.spaces.active.clip_end = value
				else:
					print("wrong startOrEnd in SceneController.setClipping")
				return

	def setObjectMode(self,objName,setMode,selectAllToggle):
		bpy.ops.object.mode_set(mode=setMode, toggle=False)
		if setMode=='EDIT':
			bpy.ops.mesh.select_mode(type="FACE")
		if selectAllToggle:
			bpy.ops.mesh.select_all(action='TOGGLE')

	def getSelectedFacesCoordsList(self,objName,axis):
		result=[]
		obj = bpy.data.objects[objName]
		initMode=1

		# if obj.mode=='EDIT':
			# initMode=2
			# self.setObjectMode(objName,'OBJECT',False)

		allFaces=self.getObjectFacesList(objName)
		selectedFaces=[f for f in allFaces if f.select]
		for i in range(0,len(selectedFaces)):
			face=selectedFaces[i]
			loc_obj = face.calc_center_median()
			loc_world = obj.matrix_world * loc_obj			
			if axis==VECTOR:
				result+=[loc_world]
			else:
				result+=[loc_world[axis]]

		# if initMode==2:
			# self.setObjectMode(objName,'EDIT',False)

		return result

	def getFacesCoordsList(self,objName,axis):
		result=[]
		obj = bpy.data.objects[objName]
		allFaces=self.getObjectFacesList(objName)
		selectedFaces=[f for f in allFaces]
		for i in range(0,len(selectedFaces)):
			face=selectedFaces[i]
			loc_obj = face.calc_center_median()
			loc_world = obj.matrix_world * loc_obj			
			if axis==VECTOR:
				result+=[loc_world]
			else:
				result+=[loc_world[axis]]
		return result

	#find max/min coord face on a certain axis
	def getExremumFace(self,objName,axis,extremum):
		faces=self.getObjectFacesList(objName)
		initFace=faces[0]
		initExtCoord=self.localToGlobalCoords(initFace.calc_center_median())[axis]
		extrCoord=initExtCoord
		edgeFaceIndex=0
		for i in range(0,len(faces)):
			face=faces[i]
			coord=self.localToGlobalCoords(face.calc_center_median())[axis]
			if extremum==MAX:
				if coord>extrCoord:
					extrCoord=coord
					edgeFaceIndex=i
			elif extremum==MIN:
				if coord<extrCoord:
					extrCoord=coord
					edgeFaceIndex=i
		return edgeFaceIndex
		
	def getVerticesVectorsList(self,objName,selectType):
		result=[]
		initMode=1
		obj = bpy.data.objects[objName]

		if obj.mode=='EDIT':
			initMode=2
			self.setObjectMode(objName,'OBJECT',False)

		allVertices=obj.data.vertices
		if GeneralMethods.compareStrings(selectType,'ALL'):
			selectedVertices=allVertices
		elif GeneralMethods.compareStrings(selectType,'SELECTED'):
			selectedVertices=[v for v in allVertices if v.select]
		elif GeneralMethods.compareStrings(selectType,'NON-SELECTED'):
			selectedVertices=[v for v in allVertices if not v.select]	

		for i in range(0,len(selectedVertices)):
			vertex=selectedVertices[i]
			loc_obj = vertex.co
			loc_world = obj.matrix_world * loc_obj
			result+=[loc_world]

		if initMode==2:
			self.setObjectMode(objName,'EDIT',False)

		return result

	def getVerticesIndexList(self,objName,selectType):
		result=[]
		initMode=1
		obj = bpy.data.objects[objName]

		if obj.mode=='EDIT':
			initMode=2
			self.setObjectMode(objName,'OBJECT',False)

		allVertices=obj.data.vertices

		for i in range(0,len(allVertices)):
			vertex=allVertices[i]
			if GeneralMethods.compareStrings(selectType,'ALL'):
				result+=[vertex]
			elif GeneralMethods.compareStrings(selectType,'SELECTED'):
				if vertex.select:
					result+=[vertex]
			elif GeneralMethods.compareStrings(selectType,'NON-SELECTED'):
				if not vertex.select:
					result+=[vertex]

		if initMode==2:
			self.setObjectMode(objName,'EDIT',False)

		return result

	def convertObjToMesh(self,obj):
		scene=bpy.context.scene
		if obj:
			origName=obj.name
			mesh = obj.to_mesh(scene, False, 'PREVIEW')
			# add an object
			o = bpy.data.objects.new("RefObj", mesh)
			scene.objects.link(o)
			o.matrix_world = obj.matrix_world
			# not keep original
			bpy.data.objects[origName].select=True
			bpy.ops.object.delete()
			o.name=origName
			return mesh

	def joinObjects(self,objNames):
		for name in objNames:
			obj=bpy.data.objects[name]
			obj.select=True
			if obj.mode=='EDIT':
				initMode=2
				self.setObjectMode(objName,'OBJECT',False)
		bpy.ops.object.join()

	def getSelectedFacesList(self,objectName):
		object = bpy.data.objects[objectName]
		mesh = object.data
		bm = bmesh.from_edit_mesh(mesh)
		selectedFaces=[f for f in bm.faces if f.select]
		bmesh.update_edit_mesh(object.data)
		return selectedFaces

	#returns faces indexes in a plato style : the base is excluded.
	#baseSize - indicates the "boldness" of the base
	def hillStyleSelection(self,objectName,baseSize):
		tempSelectedFaces=self.getSelectedFacesIndexesList(objectName)
		borderFacesIndexes=self.getPerimeterSelectedFacesIndexes(objectName)
		object = bpy.data.objects[objectName]
		mesh = object.data
		bm = bmesh.from_edit_mesh(mesh)
		allFaces=bm.faces

		#deselect all that isn't in border indexes list
		for selIndex in tempSelectedFaces:
			face=allFaces[selIndex]
			if not GeneralMethods.isPresentInList(selIndex,borderFacesIndexes):
				face.select=False

		#select adjuscent faces to the border multiple times
		for i in range(0,baseSize):
			self.selectAdjuscentFaces(objectName,True)
			
		#get their indexes by looping through all faces and saving the select=True ones
		facesIndexesToExclude=self.getSelectedFacesIndexesList(objectName)

		#reset selection
		self.selectAllToggle()

		#exclude the base indexes from the hill elevation surface
		hillSurfaceIndexes=GeneralMethods.excludeValuesFromList(facesIndexesToExclude,tempSelectedFaces)

		#reselect hill surface
		#self.selectFacesFromIndexList(GEL_MODEL,hillSurfaceIndexes)

		return hillSurfaceIndexes

	def getObjectFacesList(self,objectName):
		object = bpy.data.objects[objectName]
		initMode=1
		if object.mode=='OBJECT':
			initMode=2
			self.setObjectMode(objectName,'EDIT',False)
		mesh = object.data
		counter=0
		bm = bmesh.from_edit_mesh(mesh)
		bm.faces.ensure_lookup_table()
		if initMode==2:
			self.setObjectMode(objectName,'OBJECT',False)
		return bm.faces

	def selectAllObjects(self):
		objectsList=bpy.data.objects
		for object in objectsList:
			if object.mode=='EDIT':
				self.setObjectMode(object.name,'OBJECT',False)
			if not object.select:
				object.select=True

	def joinSelectedObjects(self):
		bpy.ops.object.join()
	
	def exportSelectedObject(self,objFilePath):
		bpy.ops.export_scene.obj(filepath=objFilePath,use_selection=True)

	def getMedianCoordsOnPlane(self,facesCoordsList,plane):
		axis1Coords=[]
		axis2Coords=[]
		facesCoordsListOnPlane=[]

		for faceCoords in facesCoordsList:
			axis1Coords+=[faceCoords[plane[0]]]
			axis2Coords+=[faceCoords[plane[1]]]

		avCoordAxis1=(GeneralMethods.getMaxVal(axis1Coords)+GeneralMethods.getMinVal(axis1Coords))/2
		avCoordAxis2=(GeneralMethods.getMaxVal(axis2Coords)+GeneralMethods.getMinVal(axis2Coords))/2
		median=[avCoordAxis1,avCoordAxis2]
		return median
		

			


		


