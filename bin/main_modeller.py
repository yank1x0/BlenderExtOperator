#!/usr/bin/env python3
'''========================
author: rami yankelov

***
summary:
-----------
this is an example of blender operator that is coupled with blender instance but has independent GUI (Tkinter-based in this example),
unlike the usual blender operator extensions that are meant to be accessed from blender GUI itself.
in its basis, the idea is to separate the blender thread cycle and 
note this is just sample of a single projoect component, not the full project. multiple pre-requisites and configurations are required for the full project.
the purpose is demonstration only.

in addition, few function examples are added, to demonstrate how to control and design the independet gui of the operator.
more general-purpose blender functions can be found in classes.SceneController.

blender version 2.78
python 3.6
***

#========================='''

import bpy
from classes.SceneController import SceneController
from classes.CustomClasses import ContButton
from classes.CustomClasses import FrameContainer
from classes.CustomClasses import StickyButton
from classes.Constants import *
from classes.GeneralMethods import GeneralMethods
from multiprocessing import Process, Queue
import time
from subprocess import call
from tkinter import *
import sys
import bmesh
import math
from os import listdir
import mathutils
from os import path

WIN_TITLE="Blender"
PROJ_PATH=sys.argv[1]
sceneController=SceneController(WIN_TITLE)

AUX_WINDOW_STATE=INACTIVE
EXECUTE_PENDING=False
PENDING_FUNCTION=None
PENDING_FUNCTION_ARGS=None

TICKS=0

#operator to handle the external gui window
class ProgramCycle(bpy.types.Operator):
	bl_idname = 'wm.ivorydigital_gui'
	bl_label = 'Start IvoryDigital gui'
	bl_options = {'REGISTER'}
	global sceneController

	def on_closing(self):
		global WIN_TITLE
		self._auxWindow.destroy()
		call([CLOSE_APP,WIN_TITLE])
		self._mainWindow.destroy()

	def __init__(self):
		self._timer = None
		self._counter=0
		self._mainWindow = Tk()
		self._mainWindow.bind("<Button-1>",lambda x: self.hideButtonLabel())
		self._mainWindow.protocol("WM_DELETE_WINDOW", self.on_closing)
		self._mainWindow.configure(background='white')

		self._mainWindow.wm_title("IvoryDigital")

		#auxillary window - when additional gui presentation is needed outside the main Tk window, in blender env. for example-present some animation while hovering
		self._auxWindow=Toplevel()
		self._auxWindow.overrideredirect(1)
		self._auxWindow.withdraw()
		self.auxCanvas=Canvas(self._auxWindow)
		self.auxLabel=Label(self._auxWindow)
		self.auxCanvas.pack()
		self.auxLabel.pack()

		self._camPosition=StringVar()
		self._camPosition.set("TOP")

		self.scrWidth = self._mainWindow.winfo_screenwidth()
		self.scrHeight = self._mainWindow.winfo_screenheight()

	def __del__(self):
		print("End")

'''
this is the actual operator loop. by setting the float PROGRAM_CYCLE to a certain value, we 
dictate that the custom modal content is ecxecuted every PROGRAM_CYCLE seconds.
now, in that time space, we can execute our actions for the custom GUI and anything else
with the blender context. 
'''
	def modal(self, context, event):
		global AUX_WINDOW_STATE, PENDING_FUNCTION, EXECUTE_PENDING,PENDING_FUNCTION_ARGS,TICKS
		if event.type == 'TIMER':

			#if we want to divide the custom execution time space between several external gui components,
			#each getting different amount of time:
			TICKS+=PROGRAM_CYCLE
			execute_aux_tasks=( int(TICKS*100)%int(100*AUX_CYCLE)==0 )
			execute_gui_tasks=( int(TICKS*100)%int(100*GUI_CYCLE)==0 )
			if ( int(TICKS*100)%int(100*RESET_TICKS)==0 ):
				TICKS=0
			#if we only want to control 1 external window in blender context, above is not needed.

			try:
				if AUX_WINDOW_STATE==ACTIVE:
					#update aux window if it is time
					if execute_aux_tasks:
						self._auxWindow.update_idletasks()
						self._auxWindow.update()
						self._auxWindow.lift()

					#if there is an ongoing function waiting for execution, execute it,
					if execute_gui_tasks:
						if EXECUTE_PENDING and PENDING_FUNCTION is not None:
							PENDING_FUNCTION(*PENDING_FUNCTION_ARGS)
							EXECUTE_PENDING=False
							PENDING_FUNCTION_ARGS=None

				#execute main window
				if execute_gui_tasks:
					self._mainWindow.update_idletasks()
					self._mainWindow.update()
					if AUX_WINDOW_STATE==INACTIVE:
						self._mainWindow.lift()

			except TclError: #app window closed
				sys.exit()
		return {'PASS_THROUGH'}

	'''
	this is the method used to set a custom function to be executed in the next opportunity
	when the timer reaches PROGRAM_CYCLE seconds.
	any function can be delegated this way, and then be executed with access to blender context.

	for example, in our custom gui window we could have a button to set the camera position in the blender context.
	the the button would need the following binding:
	ButtonObj.bind("<Button-1>",lambda x: self.executeAction(sceneController.setCameraPosition('TOP')))
	'''
	def executeAction(self, function,*args):
			global PENDING_FUNCTION,EXECUTE_PENDING,PENDING_FUNCTION_ARGS
			PENDING_FUNCTION=function
			PENDING_FUNCTION_ARGS=args
			EXECUTE_PENDING=True

	def invoke(self, context, event):
		wm = context.window_manager
		self._timer = wm.event_timer_add(PROGRAM_CYCLE, context.window)
		wm.modal_handler_add(self)
		self.executeAction(self.begin)
		return {'RUNNING_MODAL'}

	def begin(self):
		self.objectsPlacement()
		self.initComponents()
		bpy.data.materials[0].diffuse_color=(0.099, 0.075, 0.068)
		sceneController.setClipping(2000.0,'end')

	#example of how to display a secondary hovering ui window.
	def displayButtonLabel(self,event,txt):
		try:
			baseWidth=math.ceil(0.0155*(self.scrWidth/3.5))
			totWidth=baseWidth*len(txt)
			#config the auxillary window for the purpose and size
			self.configAuxWindow(auxText=txt,scr_x=event.x_root,scr_y=event.y_root,
				aux_width=totWidth , aux_height=math.floor((1/32)*(self.scrHeight/1.1)), bgcolor="yellow", auxfont=("Helvetica 8"),
				auxTextColor='black')

			self.setAuxWindowStatus(ACTIVE)
		except Exception:
			print("exception in auxWindow")

	def registerContButton(self,contButton):
		self._contButtons.append(contButton)

	def unregisterContButton(self,contButton):
		del self._contButtons[contButton]


	def initComponents(self):
		pass
		#initialization of all the GUI components using bpy context


	def setAuxWindowStatus(self,status,hide_main_panel=False):
		global AUX_WINDOW_STATE
		if status==ACTIVE:
			if self._auxWindow is None:
				return
			AUX_WINDOW_STATE=ACTIVE
			self._auxWindow.deiconify()
			if hide_main_panel:
				self._mainWindow.withdraw()
			self._auxWindow.update_idletasks()
			self._auxWindow.update()
			self._auxWindow.lift()
		else:
			self._mainWindow.deiconify()
			self.auxCanvas.delete("all")
			self._auxWindow.withdraw()
			AUX_WINDOW_STATE=INACTIVE

def register():
	bpy.utils.register_module(__name__)

register()

bpy.ops.wm.ivorydigital_gui('INVOKE_DEFAULT')
	