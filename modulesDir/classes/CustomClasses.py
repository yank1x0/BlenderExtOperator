
from tkinter import *
import time
#---------------------------
#CUSTOM CLASSES IMPLEMENTED IN TKINTER

#---------------------------

#button built for continuous action while held down
class ContButton(Button):
	def __init__(self,*args,**kwargs):
		super(ContButton, self).__init__(*args, **kwargs)
		self._STATE=0
		self._timeInterval=1 #default button invoke set to once per program cycle
		self.ticks=1 #program cycles counter
		self.bind("<ButtonPress>", self.on_press)
		self.bind("<ButtonRelease>", self.on_release)

	def setTimeInterval(self,val):
		if isinstance(val,int):
			self._timeInterval=val

	#this should be called by the main tkinter program during cycle
	def tick(self):
		if self.ticks%self._timeInterval==0:
			self.invoke()
			self.ticks=1
		else:
			self.ticks+=1

	def on_press(self, event):
		self._STATE=1

	def on_release(self, event):
		self._STATE=0

# class BackgroundFrame(FrameContainer,):
	# def __init__(self,dir='v',max=1,*args, **kwargs):	
		# super(BackgroundFrame, self).__init__(*args, **kwargs)
	

#class to handle grid frame panels more easily
#usage:
# - the direction and maximum row/col capacity is set when instance initialized
# - when the capcity of row/col is exceeded, the next widgets are displayed on new row/col
# - a separator can add space before the widget coming after it, and skip row/col
# - setting the padding/anchor will affect all widgets coming after the change, until next change
# NOTE: the columns and rows are relative to the content, and all the grid cells are scaled
#		to match the largest content!
class FrameContainer(Frame):
	def __init__(self,dir,max,*args, **kwargs):	
		super(FrameContainer, self).__init__(*args, **kwargs)
		self._dir=dir
		self._max=max
		self._widgets=[]
		self._widgetsCounter=0
		self._separators=[]
		self._anchor=W
		self._anchors=[]
		self._default_h_pad=0
		self._default_v_pad=0
		self._default_v_paddings=[]
		self._default_h_paddings=[]
		self.HIDDEN=0
		self.ACTIVE=1
		self._status=0
		self._perma_widgets=[]

	def getStatus(self):
		return self._status

	#permanent widget - a widget that isn't hidden when others do
	def setPermaWidget(self,ind):
		self._perma_widgets.append(self._widgets[ind])
		return self

	def removePermaWidget(self,ind):
		widget=self._widgets[ind]
		del self._perma_widgets[self._perma_widgets.index(widget)]
		return self

	def addWidget(self,widget,ind=-1):
		if ind==-1:
			self._widgets.append(widget)
			self._widgetsCounter+=1
			self._anchors.append(self._anchor)
			self._default_h_paddings.append(self._default_h_pad)
			self._default_v_paddings.append(self._default_v_pad)
		elif ind>=0:
			self._widgets.insert(ind,widget)
			self._widgetsCounter+=1
			self._anchors.insert(ind,self._anchor)
			self._default_h_paddings.insert(ind,self._default_h_pad)
			self._default_v_paddings.insert(ind,self._default_v_pad)
		else:
			print("negative index")
		return self

	def setAnchor(self,anchor):
		self._anchor=anchor
		return self

	def setDefaultPadding(self,hpad,vpad):
		self._default_h_pad=hpad
		self._default_v_pad=vpad
		return self

		#a separator of whole line/column

	def getWidgets(self):
		return self._widgets

	def removeWidget(self,ind):
		widget=self._widgets[ind]
		if isinstance(widget,FrameContainer):
			widget.hideWidgets()
		widget.grid_remove()
		del self._widgets[ind]
		self._widgetsCounter-=1
		del self._anchors[ind]
		del self._default_h_paddings[ind]
		del self._default_v_paddings[ind]
		return self

	def refresh(self):
		self.hideWidgets()
		self.showWidgets()
		return self

	def setStatus(self,status):
		self._status=status

	def hideWidgets(self):
		for widget in self._widgets:
			if widget in self._perma_widgets:
				continue
			widget.grid_remove()
			if isinstance(widget,FrameContainer):
				widget.hideWidgets()

# !NOTE: the columns and rows are relative to the CONTENT, and all the grid cells are SCALED
#		to match the LARGEST content!
	def addSeparator(self,dir,size,lines_to_skip=0):
		sepOrder=self._widgetsCounter-1
		if (len(self._separators)>0 and self._separators[len(self._separators)-1]._order==sepOrder):
			print("sep merged")
			self._separators[len(self._separators)-1]._size+=size
			self._separators[len(self._separators)-1]._lines_to_skip+=lines_to_skip
		else:
			self._separators.append(self.FrameContainerSeparator(dir,size,sepOrder,self._widgetsCounter-1,lines_to_skip))
		return self

	def addWidgets(self,widgets):
		for widget in widgets:
			self.addWidget(widget)
		return self

	def clearWidgets(self):
		self._status=self.HIDDEN
		for widget in self._widgets:
			widget.destroy()
		self._widgets=[]
		self._widgetsCounter=0
		self._separators=[]
		self._anchors=[]
		self._default_h_paddings=[]
		self._default_v_paddings=[]
		return self
		

	def showWidgets(self):
		r=0
		c=0
		separatorIndex=0
		h_pad=0
		v_pad=0
		widgetUIInd=1
		separator=None

		for i in range(0,self._widgetsCounter):
			widget=self._widgets[i]
			#determine horizontal/vertical padding
			if len(self._separators)>separatorIndex and self._separators[separatorIndex]._order==i-1:
				separator=self._separators[separatorIndex]
				if separator._dir=='h':
					h_pad=separator._size
				else:
					v_pad=separator._size

				separatorIndex+=1
			else:
				separator=None

			#if before that comes a separator that skips lines
			if separator is not None and separator._lines_to_skip>0:
				for l in range(0,separator._lines_to_skip):
					if self._dir=='h':
						c=0
						r+=1
					elif self._dir=='v':
						c+=1
						r=0
				widgetUIInd=1

			if isinstance(widget,FrameContainer):
				widget.showWidgets()

			if i>0:
				widget.grid(row=r, column=c, columnspan=1, rowspan=1,padx=(self._default_h_paddings[i]+h_pad,0),pady=(self._default_v_paddings[i]+v_pad,0),sticky=self._anchors[i])
			else:
				widget.grid(row=r, column=c, columnspan=1, rowspan=1,padx=(h_pad,0),pady=(v_pad,0),sticky=self._anchors[i])


			if (separator is not None):
				h_pad=0
				v_pad=0

				
			#if a line/column is complete
			if widgetUIInd%self._max==0:
				if self._dir=='h':
					c=0
					r+=1
				elif self._dir=='v':
					c+=1
					r=0
				#nullify the padding after a line/column is complete
				h_pad=0
				v_pad=0
				widgetUIInd=1
			else:
				if self._dir=='h':
					c+=1
				elif self._dir=='v':
					r+=1
				widgetUIInd+=1

	class FrameContainerSeparator:
		#empty space widget to sparate groups of widgets vertically
		#or horizontally
		def __init__(self,dir,size,order,last_cell_ind,lines_to_skip):
			self._dir=dir
			self._size=size
			self._order=order
			self._last_cell_ind=last_cell_ind
			self._lines_to_skip=lines_to_skip

# class ExtButton(Button):
	# def __init__(self,*args, **kwargs):
		# super(StickyButton, self).__init__(*args, **kwargs)
		# self._hoverText=None
		# self.hoverLabel = None

	# def enableHover(self,container):
		# self.hoverLabel=Label(container, text="")
		# self.hoverLabel.pack()

	# def setHoverMessage(self,msg):
		# self._hoverText=msg

	

class StickyButton(Button):
	def __init__(self,*args, **kwargs):
		super(StickyButton, self).__init__(*args, **kwargs)
		self._img=None
		self._pressedImg=None
		self._clicked=0
		self.bind('<Button-1>',lambda _: self.onclick())
		self._clickCommand=None
		self._unClickCommand=None
		self._id=0
		self._descript=None

	def getImage(self):
		return self._img

	def getDescript(self):
		return self._descript

	def setId(self,id):
		self._id=id
		return self

	def getId(self):
		return self._id

	def setDescript(self,descript):
		self._descript=descript
		return self

	def setClickCommand(self,cmd):
		self._clickCommand=cmd
		return self

	def setUnClickCommand(self,cmd):
		self._unClickCommand=cmd
		return self

	def onclick(self):
		if self._clicked==1:
			if not self._img==None:
				self.config(image=self._img,relief=GROOVE)
			if not self._unClickCommand==None:
				self._unClickCommand()
			self._clicked=0
		else:
			if not self._pressedImg==None:
				self.config(image=self._pressedImg,relief=SUNKEN)
			if not self._clickCommand==None:
				self._clickCommand()
			self._clicked=1

	def setStatus(self,status):
		if status=='clicked':
			if not self._pressedImg==None:
				self.config(image=self._pressedImg,relief=SUNKEN)
			self._clicked=1
		elif status=='released':
			if not self._img==None:
				self.config(image=self._img,relief=GROOVE)
			self._clicked=0
		return self

	def getStatus(self):
		if self._clicked==1:
			return 'clicked'
		else:
			return 'released'
		
	def setImage(self,img):
		self._img=img
		self.config(image=img)
		return self

	def setPressedImage(self,img):
		self._pressedImg=img
		return self

	


