from tkinter import *
import numpy
from math import *
import ctypes
import os
import PIL
from PIL import Image
import io
from shutil import copyfile
from shutil import rmtree
from tkinter import filedialog

class GeneralMethods:
	#all arrays are unsorted

	ABOVE=1
	BELOW=2
	ABOVE_OR_EQUAL=3
	BELOW_OR_EQUAL=4

	def popUpInfoMessage(text):
		ctypes.windll.user32.MessageBoxW(0, text, "info", 0)

	def getMedian(list):
		list2=sorted(list)
		return list2[len(list2)//2]


	def abs(val):
		if val<0.0:
			return -1*val
		return val

	def getMaxVal(values):
		maxVal=values[0]
		for val in values:
			if val>maxVal:
				maxVal=val
		return maxVal

	def getMaxInd(values):
		maxVal=values[0]
		result=0
		for ind in range(0,len(values)):
			val=values[ind]
			if val>maxVal:
				maxVal=val
				result=ind
		return result

	def strRepresentsInt(s):
		try: 
			int(s)
			return True
		except ValueError:
			return False

	def getMinInd(values):
		minVal=values[0]
		for ind in range(0,len(values)):
			val=values[ind]
			if val<minVal:
				maxVal=val
				result=ind
		return result

	def getMinVal(values):
		minVal=values[0]
		for val in values:
			if val<minVal:
				minVal=val
		return minVal

	def removeDoublesInList(list):
		result=[]
		hash={}
		for ind in range(0,len(list)):
			if not list[ind] in hash:
				result+=[list[ind]]
		return result

	def isPresentInList(value,list):
		if len(list)==0:
			return False
		for listVal in list:
			if listVal==value:
				return True
		return False


	def distBetween2Points(point1,point2):
		sum=pow(point2[0]-point1[0],2)+pow(point2[1]-point1[1],2)
		return sqrt(sum)

	#returns the nearest 2 xy points indexes from 2 given arrays 
	def getNearestPoints(coordsList1,coordsList2,exceptionIndices):
		minDist=GeneralMethods.distBetween2Points(coordsList1[0],coordsList2[0])
		nearestMembers=[0,0]
		for i in range(0,len(coordsList1)):
			for j in range(0,len(coordsList2)):
				if (not (exceptionIndices is None)) and GeneralMethods.isPresentInList(j,exceptionIndices):
					continue
				coords1=coordsList1[i]
				coords2=coordsList2[j]
				dist=GeneralMethods.distBetween2Points(coords1,coords2)
				if dist<minDist:
					minDist=dist
					nearestMembers=[i,j]
		return nearestMembers

	def getMathcingIndices(value,list,condition):
		result=[]
		for i in range(0,len(list)):
			if condition==GeneralMethods.ABOVE_OR_EQUAL:
				if list[i]>=value:
					result+=[i]
		return result
			

	def excludeValuesFromList(valuesToExclude,origList):
		return [x for x in origList if not (x in valuesToExclude)]
		
	def printList(list):
		listStr=""
		for i in range(0,len(list)):
			listStr+=str(" "+str(list[i])+" ")
		print(listStr)

	#OLD-QUICK LOW QUALITY IMAGE RESIZE 
	# def createScaledPhotoImage(gifPath,finalW,finalH):
		# img=PhotoImage(file=gifPath)
		# origH=img.height()
		# origW=img.width()
		# heightFactor=float("%.1f" % (finalH/origH))
		# widthFactor=float("%.1f" % (finalW/origW))
		# intWidthFactor=int(widthFactor*10)
		# intHeightFactor=int(heightFactor*10)
		# img=img.zoom(intWidthFactor,intHeightFactor)
		# img=img.subsample(10,10)
		# return img

	#high-res image resize when PIL module ImageTk isn't working in blender :(
	def createScaledPhotoImage(gifPath,widthFactor,heightFactor,temp_dir,master_canvas=None):
		if widthFactor==1 and heightFactor==1:
			return PhotoImage(file=gifPath)
		try:
			img=Image.open(gifPath)
		except IOError:
			print("in createScaledPhotoImage: "+gifPath+" not found")
			return None
		origW,origH=img.size
		finalW=floor(origW*widthFactor)
		finalH=floor(origH*heightFactor)
		img=img.resize((finalW,finalH),Image.ANTIALIAS)
		buffer = io.BytesIO()
		img.save(buffer, format = "gif")
		filename=gifPath.split('\\')[len(gifPath.split('\\'))-1]
		temp_path=temp_dir+"\\"+filename.split('.')[0]+".gif"
		open(temp_path, "wb").write(buffer.getvalue())
		if master_canvas is None:
			return PhotoImage(file=temp_path)
		else:
			return PhotoImage(master=master_canvas,file=temp_path)

	def browseFile(description,filetype,initDir=os.getcwd()):
		print("initdir="+initDir)
		return filedialog.askopenfilename(filetypes = ((description, "*."+filetype),),initialdir=initDir)

	#center a tkinter window on the screen
	def center(toplevel,toplevel_w,toplevel_h):
		toplevel.update_idletasks()
		w = toplevel.winfo_screenwidth()
		h = toplevel.winfo_screenheight()
		#size = tuple(int(_) for _ in toplevel.geometry().split('+')[0].split('x'))
		size=(toplevel_w,toplevel_h)
		print(str(size[0])+"x"+str(size[1]))
		x = w/2 - size[0]/2
		y = h/2 - size[1]/2
		toplevel.geometry("%dx%d+%d+%d" % (size + (x, y)))

	def getFilename(path,delim):
		return path.split(delim)[len(path.split(delim))-1] if path is not None else None

	def deleteFilesExtension(dir,ext,exclude=[]):
		for file in os.listdir(dir):
			if (file.split('.')[1]==ext) and (not file in exclude):
				os.remove("\\".join([dir,file]))

	def clearFolderContents(folder):
		for the_file in os.listdir(folder):
			file_path = os.path.join(folder, the_file)
			try:
				if os.path.isfile(file_path):
					os.remove(file_path)
				elif os.path.isdir(file_path):
					clearFolderContents(file_path)
			except Exception as e:
				print(e)
		
		
