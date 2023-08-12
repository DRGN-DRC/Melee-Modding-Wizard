#!/usr/bin/python
# This file's encoding: UTF-8, so that non-ASCII characters can be used in strings.
#
#		███╗   ███╗ ███╗   ███╗ ██╗    ██╗			-------                                                   -------
#		████╗ ████║ ████╗ ████║ ██║    ██║		 # -=======---------------------------------------------------=======- #
#		██╔████╔██║ ██╔████╔██║ ██║ █╗ ██║		# ~ ~ Written by DRGN of SmashBoards (Daniel R. Cappel);  May, 2020 ~ ~ #
#		██║╚██╔╝██║ ██║╚██╔╝██║ ██║███╗██║		 #            [ Built with Python v2.7.16 and Tkinter 8.5 ]            #
#		██║ ╚═╝ ██║ ██║ ╚═╝ ██║ ╚███╔███╔╝		  # -======---------------------------------------------------======- #
#		╚═╝     ╚═╝ ╚═╝     ╚═╝  ╚══╝╚══╝ 			 ------                                                   ------
#		  -  - Melee Modding Wizard -  -  

import os
import io
import time
import math
#import enum
import pyglet
import ctypes
import win32api
import Tkinter as Tk

from operator import add, mul
from collections import OrderedDict

from basicFunctions import printStatus

# Disable a few options for increased performance
pyglet.options['debug_gl'] = True
pyglet.options['audio'] = ( 'silent', )
#pyglet.options['shadow_window'] = False
pyglet.options['search_local_libs'] = False

from pyglet import gl
from pyglet.window import key, Projection3D
from pyglet.window import Window as pygletWindow
from pyglet.app.base import EventLoop
from pyglet.graphics import Group, OrderedGroup, TextureGroup
from pyglet.window.event import WindowEventLogger

import globalData

# class WrapMode( enum.IntEnum ):
# 	gl.GL_CLAMP_TO_EDGE = 0
# 	gl.GL_REPEAT = 1
# 	gl.GL_MIRRORED_REPEAT_IBM = 2


# class GXBlendFactor( enum.IntEnum ):
# 	ZERO = gl.GL_ZERO
# 	ONE = gl.GL_ONE
# 	SOURCECOLOR = gl.GL_SRC_COLOR
# 	INVSOURCECOLOR = gl.GL_ONE_MINUS_SRC_COLOR
# 	SOURCEALPHA = gl.GL_SRC_ALPHA
# 	INVSOURCEALPHA = gl.GL_ONE_MINUS_SRC_ALPHA
# 	DESTALPHA = gl.GL_DST_ALPHA
# 	INVDESTALPHA = gl.GL_ONE_MINUS_DST_ALPHA

# 	DESTCOLOR = SOURCECOLOR
# 	INVDESTCOLOR = INVSOURCECOLOR

WrapMode = [
	gl.GL_CLAMP_TO_EDGE, 
	gl.GL_REPEAT, 
	gl.GL_MIRRORED_REPEAT_IBM
]

GXTexFilter = [
	gl.GL_NEAREST,
	gl.GL_LINEAR,
	gl.GL_NEAREST_MIPMAP_NEAREST,
	gl.GL_LINEAR_MIPMAP_NEAREST,
	gl.GL_NEAREST_MIPMAP_LINEAR,
	gl.GL_LINEAR_MIPMAP_LINEAR
]

# GXAlphaOp = [
# 	gl.
# ]
# typedef enum _GXAlphaOp
# {
#     GX_AOP_AND,
#     GX_AOP_OR,
#     GX_AOP_XOR,
#     GX_AOP_XNOR,
#     GX_MAX_ALPHAOP
# } GXAlphaOp;

GXBlendMode = [ # Blending equation set by glBlendEquation
	None, 							# GX_BM_NONE (direct EFB write)
	gl.GL_FUNC_ADD, 				# GX_BM_BLEND
	gl.GL_FUNC_REVERSE_SUBTRACT,	# GX_BM_LOGIC
	gl.GL_FUNC_SUBTRACT,			# GX_BM_SUBTRACT (HW2 only)
	gl.GL_MAX						# GX_MAX_BLENDMODE
]

# GXLogicOp = [ # SDK
# 	gl.GL_CLEAR,
# 	gl.GL_SET,
# 	gl.GL_COPY,
# 	gl.GL_COPY_INVERTED,
# 	gl.GL_NOOP,
# 	gl.GL_INVERT,
# 	gl.GL_AND,
# 	gl.GL_NAND,
# 	gl.GL_OR,
# 	gl.GL_NOR,
# 	gl.GL_XOR,
# 	gl.GL_EQUIV,
# 	gl.GL_AND_REVERSE,
# 	gl.GL_AND_INVERTED,
# 	gl.GL_OR_REVERSE,
# 	gl.GL_OR_INVERTED
# ]

GXLogicOp = [ # HSDRaw
	gl.GL_CLEAR,
	gl.GL_AND,
	gl.GL_AND_REVERSE,
	gl.GL_COPY,
	gl.GL_AND_INVERTED,
	gl.GL_NOOP,
	gl.GL_XOR,
	gl.GL_OR,
	gl.GL_NOR,
	gl.GL_EQUIV,
	gl.GL_INVERT,
	gl.GL_OR_REVERSE,
	gl.GL_COPY_INVERTED,
	gl.GL_OR_INVERTED,
	gl.GL_NAND,
	gl.GL_SET
]

GXCompare = [
	gl.GL_NEVER,
	gl.GL_LESS,
	gl.GL_EQUAL,
	gl.GL_LEQUAL,
	gl.GL_GREATER,
	gl.GL_NOTEQUAL,
	gl.GL_GEQUAL,
	gl.GL_ALWAYS
]

GXBlendFactor = [
	gl.GL_ZERO,
	gl.GL_ONE,
	gl.GL_SRC_COLOR,
	gl.GL_ONE_MINUS_SRC_COLOR,
	gl.GL_SRC_ALPHA,
	gl.GL_ONE_MINUS_SRC_ALPHA,
	gl.GL_DST_ALPHA,
	gl.GL_ONE_MINUS_DST_ALPHA,

	gl.GL_SRC_COLOR, # DESTCOLOR
	gl.GL_ONE_MINUS_SRC_COLOR # Inverse DESTCOLOR
]


class RenderEngine( Tk.Frame ):

	""" This module creates a pyglet rendering environment (a window), and embeds
		it into a Tkinter frame for incorporation into the larger GUI. This also 
		uses a custom render loop, allowing draw updates to be delegated by the 
		main program's event loop instead of pyglet's normal application event loop. """

	def __init__( self, parent, dimensions=(640, 480), resizable=False, **kwargs ):

		self.width = dimensions[0]
		self.height = dimensions[1]

		Tk.Frame.__init__( self, parent, **kwargs )

		# Create a Tkinter canvas to hold the Pyglet window's canvas
		self.canvas = Tk.Canvas( self, width=self.width, height=self.height, borderwidth=0, highlightthickness=0 )
		self.canvas.pack()

		# Interpret a background color for the Pyglet canvas; check for a given background color, or default to black
		backgroundColor = kwargs.get( 'background', 'black' )
		self.bgColor = list( globalData.gui.root.winfo_rgb(backgroundColor) ) # Returns (r, g, b) with 16 bit color depth
		self.bgColor = tuple( [v/65536.0 for v in self.bgColor] + [1] ) # Convert to 0-1 range and add an alpha channel

		# Create an invisible Pyglet window (cannot create a Pyglet canvas without a window)
		display = pyglet.canvas.get_display()
		screen = display.get_default_screen()
		config = screen.get_matching_configs( gl.Config(double_buffer=True, depth_size=8, alpha_size=8, samples=4) )[0]
		self.window = pygletWindow( display=display, config=config, width=self.width, height=self.height, resizable=resizable, visible=False )
		self.fov = 60; self.zNear = 5; self.zFar = 3500
		self.aspectRatio = self.width / float( self.height )
		self.window.projection = Projection3D( self.fov, self.zNear, self.zFar ) # todo: need custom class to replace glFrustum & friends; http://www.manpagez.com/man/3/glFrustum/
		self.window.on_draw = self.on_draw
		self.bind( '<Expose>', self.refresh )
		openGlVersion = self.window.context._info.get_version().split()[0]
		print( 'Rendering with OpenGL version {}'.format(openGlVersion) )

		# Set the pyglet parent window to be the tkinter canvas
		GWLP_HWNDPARENT = -8
		pyglet_handle = self.window.canvas.hwnd
		win32api.SetWindowLong( pyglet_handle, GWLP_HWNDPARENT, self.canvas.winfo_id() )

		# Ensure this window is targeted for operations that should affect it
		self.window.switch_to()

		self.fragmentShader = self.compileShader( gl.GL_FRAGMENT_SHADER, 'fragment' )
		
		# Set up a default render mode in the shader for basic primitives
		if self.fragmentShader:
			self.setShaderInt( 'enableTextures', False )
			self.setShaderInt( 'useVertexColors', True )
			self.setShaderInt( 'alphaOp', -1 )

		# Set up the OpenGL context
		gl.glClearColor( *self.bgColor )
		gl.glClearDepth( 1.0 ) # Depth buffer setup

		gl.glEnable( gl.GL_BLEND )
		gl.glEnable( gl.GL_ALPHA_TEST )
		gl.glEnable( gl.GL_DEPTH_TEST ) # Do depth comparisons
		#gl.glEnable( gl.GL_COLOR_LOGIC_OP )
		gl.glDepthMask( True )

		gl.glBlendFunc( gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA )
		gl.glAlphaFunc( gl.GL_GREATER, 0 )
		gl.glDepthFunc( gl.GL_LEQUAL ) # The type of depth testing to do

		# gl.glEnable( gl.GL_LIGHTING )
		# halfHeight = math.tan( self.fov / 2 ) * self.zNear
		# lightPosition = ( -halfHeight, -halfHeight, -4000, 1.0 )
		# gl.glLightfv( gl.GL_LIGHT0, gl.GL_POSITION, (gl.GLfloat * 4)(*lightPosition) )
		# gl.glLightfv( gl.GL_LIGHT0, gl.GL_DIFFUSE, (gl.GLfloat * 4)(1.0, 1.0, 1.0, 1.0) )
		# gl.glLightfv( gl.GL_LIGHT0, gl.GL_AMBIENT, (gl.GLfloat * 4)(1.0, 1.0, 1.0, 1.0) )
		# gl.glLightfv( gl.GL_LIGHT0, gl.GL_SPECULAR, (gl.GLfloat * 4)(1.0, 1.0, 1.0, 1.0) )
		# gl.glEnable( gl.GL_LIGHT0 )
		
		#gl.glCullFace( gl.GL_BACK )
		gl.glDisable( gl.GL_CULL_FACE ) # Enabled by default
		#gl.glPolygonMode( gl.GL_FRONT_AND_BACK, gl.GL_LINE ) # Enable for wireframe mode (need to reset line widths)

		#gl.glEnable( gl.GL_TEXTURE_2D )
		# gl.glTexParameteri( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR )
		# gl.glTexParameteri( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR )

		try: # Anti-aliasing
			gl.glEnable( gl.GL_LINE_SMOOTH )
			gl.glEnable( gl.GL_POLYGON_SMOOTH )
			gl.glEnable( gl.GL_MULTISAMPLE )
			gl.glEnable( gl.GL_MULTISAMPLE_ARB )
		except pyglet.gl.GLException:
			print( 'Warning: Anti-aliasing is not supported on this computer.' )
			print( 'Rendering with OpenGL version {}'.format(openGlVersion) )

		self.edges = []
		self.clearRenderings()
		self.resetView()
		#self.defineFrustum()

		# Set up event handling for controls
		#self.window._enable_event_queue = True
		self.window.on_mouse_drag = self.on_mouse_drag
		#self.window.on_key_press = self.on_key_press
		#self.window.on_mouse_scroll = self.on_mouse_scroll2 	# doesn't work!?
		self.window.on_mouse_scroll = self.on_mouse_scroll
		self.master.bind( "<MouseWheel>", self.on_mouse_scroll )
		self.master.bind( '<KeyPress>', self.on_key_press2 )
		#self.master.bind( "<1>", self.window.activate() ) # Move focus to the parent when clicked on

		if resizable:
			self.tic = time.time()
			self.bind( "<Configure>", self.resizeViewport )

		# Start the render event loop using Tkinter's main event loop
		#self.window.updateRequired = True
		if not pyglet.app.event_loop.is_running:
			pyglet.app.event_loop = CustomEventLoop( self.winfo_toplevel() )
			pyglet.app.event_loop.run()

		# Move focus to the parent window (will be the pyglet window by default)
		self.master.after( 1, lambda: self.master.focus_force() )

	def clearRenderings( self, preserveBones=True ):

		if preserveBones:
			bones = []
			for edge in self.edges:
				if 'bones' in edge.tags:
					bones.append( edge )
			self.edges = bones
		else:
			self.edges = []

		self.vertices = []
		self.triangles = []
		self.quads = []
		self.vertexLists = []
		self.textures = {}

		# Add a marker to show the origin point
		# self.addEdge( [-2,0,0, 2,0,0], (255, 0, 0, 255), tags=('originMarker',), thickness=3 )
		# self.addEdge( [0,-2,0, 0,2,0], (0, 255, 0, 255), tags=('originMarker',), thickness=3 )
		# self.addEdge( [0,0,-2, 0,0,2], (0, 0, 255, 255), tags=('originMarker',), thickness=3 )

		self.window.updateRequired = True

	def resetView( self ):
		self.rotation_X = 0
		self.rotation_Y = 0

		self.translation_X = 0.0
		self.translation_Y = 0.0
		self.translation_Z = 0.0

		self.window.updateRequired = True

	def defineFrustum( self ):

		""" Defines the viewable area of the render environment, which is 
			composed of 6 sides and shaped like the cross-section of a pyramid. 
			The result of this function is a list of the planes (sides) enclosing this area. """

		# Create vectors for the plane corners (points on the near plane, and vectors to the far plane)
		halfHeight = math.tan( self.fov / 2 ) * self.zNear
		halfWidth = halfHeight * self.aspectRatio
		topLeft = ( -halfWidth, halfHeight, -self.zNear )
		topRight = ( halfWidth, halfHeight, -self.zNear )
		bottomLeft = ( -halfWidth, -halfHeight, -self.zNear )
		bottomRight = ( halfWidth, -halfHeight, -self.zNear )

		self.frustum = (
			Plane( (0,0,0)+bottomLeft+topLeft ), 		# Left
			Plane( (0,0,0)+topLeft+topRight ), 			# Top
			Plane( (0,0,0)+topRight+bottomRight ), 		# Right
			Plane( (0,0,0)+bottomRight+bottomLeft ), 	# Bottom
			Plane( bottomLeft+topLeft+topRight ),		# Near
			Plane()	# Far
		)

	def focusCamera( self, tags=None, primitive=None, skipRotationReset=False ):

		""" Resets the camera and centers it on the object with the given tag. 
			The tag and primitive arguments may be given to filter to targets. """

		if not skipRotationReset:
			self.resetView()

		xCoords = []
		yCoords = []
		zCoords = []

		# Check if tags is an iterable or a single item
		if tags:
			if hasattr( tags, '__iter__' ):
				tags = set( tags )
			else: # Is not an iterable
				tags = set( [tags] )

		# Find all of the x/y/z coordinates of the target object(s)
		for obj in self.getObjects( primitive ):
			if not tags or tags & set( obj.tags ):
				if obj.__class__ == Vertex:
					xCoords.append( obj.x )
					yCoords.append( obj.y )
					zCoords.append( obj.z )
				else:
					# Iterate over the vertices by individual coordinates
					coordsIter = iter( obj.vertices[1] )
					coordsList = [ coordsIter ] * 3
					for x, y, z in zip( *coordsList ):
						xCoords.append( x )
						yCoords.append( y )
						zCoords.append( z )

		# Set defaults and exit if no coordinates could be collected
		if not xCoords:
			self.translation_X = 0
			self.translation_Y = 0
			self.translation_Z = -10
			return

		# Calculate new camera X/Y coords
		maxX = max( xCoords )
		maxY = max( yCoords )
		maxZ = max( zCoords )
		x = ( maxX + min(xCoords) ) / 2.0
		y = ( maxY + min(yCoords) ) / 2.0
		z = ( maxZ + min(zCoords) ) / 2.0

		# Determine depth (zoom level); try to get the entire model part/group in the frame
		xSpan = maxX - x
		ySpan = maxY - y
		zSpan = maxZ - z
		if xSpan > ySpan:
			# Use x-axis to determine zoom level
			if zSpan > xSpan:
				zOffset = zSpan * 1.6
			else:
				zOffset = xSpan * 1.5
		else:
			# Use y-axis to determine zoom level
			if zSpan > ySpan:
				zOffset = zSpan * 1.6
			else:
				zOffset = ySpan * 1.7

		# Set the new camera position
		self.translation_X = -x
		self.translation_Y = -y
		self.translation_Z = -z - abs( zOffset )

	def resizeViewport( self, event ):

		""" Updates the tkinter canvas and pyglet rendering canvas 
			when the Tkinter frame is resized. """
		
		self.width = event.width
		self.height = event.height

		self.canvas['width'] = self.width
		self.canvas['height'] = self.height

		# Update the GL rendering viewport and pyglet window/canvas
		self.window.switch_to()
		gl.glViewport( 0, 0, self.width, self.height )
		self.window._update_view_location( self.width, self.height )

		# Update the frustum if the aspect ratio changes
		newAspectRatio = float(self.width) / self.height
		if self.aspectRatio != newAspectRatio:
			self.aspectRatio = newAspectRatio
			#self.defineFrustum()

		self.window.updateRequired = True

	def refresh( self, event ):

		""" Tells the render engine to update/redraw the display canvas at its next opportunity. 
			This is bound to the <Expose> Tkinter event, which will occur whenever at least 
			some part of the program or widget becomes visible after having been covered up 
			by another window or widget. """

		self.window.updateRequired = True

	def addVertex( self, vertices, color=(128, 128, 128, 255), tags=(), show=True, size=4 ):

		if len( vertices ) != 3:
			print( 'Incorrect number of coordinates given to create a vertex: ' + str(vertices) )
			return None

		vertex = Vertex( vertices, color, tags, show, size )
		self.vertices.append( vertex )

		self.window.updateRequired = True

		return vertex

	def addEdge( self, vertices, color=None, colors=(), tags=(), show=True, thickness=2 ):

		""" Translates given points into a series of edges (lines) to be batch-rendered. 
			The given vertices should contain 6 values (2 sets of x/y/z coords). """

		if len( vertices ) != 6:
			print( 'Incorrect number of coordinates given to create an edge: ' + str(vertices) )
			return None

		edge = Edge( vertices, color, colors, tags, show, thickness )
		self.edges.append( edge )

		self.window.updateRequired = True

		return edge

	def addEdges( self, edgePoints, color=None, colors=(), tags=(), show=True, thickness=2 ):

		""" Translates given points into a series of data points (edges) to be batch-rendered. 
			The edgePoints arg should be a list of tuples, where each tuple contains 6 values 
			(2 sets of x/y/z coords). """

		for vertices in edgePoints:
			if len( vertices ) != 6:
				print( 'Incorrect number of points given to create an edge: ' + str(vertices) )
				continue

			edge = Edge( vertices, color, colors, tags, show, thickness )
			self.edges.append( edge )

		self.window.updateRequired = True

	def addQuad( self, vertices, color=None, colors=(), tags=(), show=True ):

		if len( vertices ) != 12:
			print( 'Incorrect number of points given to create a quad: ' + str(vertices) )
			return None

		quad = Quad( vertices, color, colors, tags, show )
		self.quads.append( quad )

		self.window.updateRequired = True

		return quad
	
	def addVertexLists( self, vertexLists, renderGroup=None, dobj='', pobj='' ):

		""" Adds one or more entries of a display list. Each display list entry contains 
			one or more primitives of the same type (e.g. edge/triangle-strip/etc)."""

		for vertexList in vertexLists:
			if dobj and pobj:
				vertexList.tags = ( dobj, pobj )
			if renderGroup:
				vertexList.addRenderGroup( renderGroup )
			self.vertexLists.append( vertexList )

			# self.window.updateRequired = True
			# self.canvas.update()

		self.window.updateRequired = True
	
	def addPrimitives( self, primitives ):

		""" Add one or more pre-initialized primitives without coords validation. """

		if not primitives:
			return

		unknownObjects = []

		for prim in primitives:
			if isinstance( prim, Vertex ):
				self.vertices.append( prim )
			elif isinstance( prim, Edge ):
				self.edges.append( prim )
			elif isinstance( prim, Triangle ):
				self.triangles.append( prim )
			elif isinstance( prim, Quad ):
				self.quads.append( prim )
			elif isinstance( prim, VertexList ):
				self.vertexLists.append( prim )
			else:
				unknownObjects.append( prim )

		if unknownObjects:
			print( 'Unable to add unknown, non-primitive objects!:'.format(unknownObjects) )

		self.window.updateRequired = True

	def loadSkeleton( self, rootJoint, showBones=True ):

		""" Initialize joints used for bones in the model, create bone objects for them, 
			and calculate model tranformations for all bone vertices, which will be used for their meshes. """
		
		# Skip if this skeleton has already been loaded
		if rootJoint.offset in rootJoint.dat.skeletons:
			return

		# Create a new skeleton to add to the dat file
		rootJoint.dat.skeletons[rootJoint.offset] = {}
		skeleton = rootJoint.dat.skeletons[rootJoint.offset]
		Bone.count = 0

		dobjClass = globalData.fileStructureClasses.get( 'DisplayObjDesc' )
		dobjClass.count = 0

		child = rootJoint.initChild( 'JointObjDesc', 2 )

		# Give IDs to the primary Display Objects (useful for determining high/low-model parts)
		self._enumerateDObjs( rootJoint, skeleton )

		modelMatrix = rootJoint.buildLocalMatrix()
		
		# Recursively add bones for this joint's child and the child's siblings
		for siblingOffset in child.getSiblings():
			if siblingOffset in skeleton:
				continue

			sibling = rootJoint.dat.getStruct( siblingOffset )

			# if not sibling.isBone:
			# 	print( 'Non-bone added to skeleton: ' + hex(0x20+sibling.offset) )

			self._addBone( rootJoint, sibling, modelMatrix, showBones, skeleton )

		#print( 'Added these bones: ' + str([hex(o+0x20) for o in self.skeleton]) + ' to skeleton dict ' + str(rootJoint.offset) )

		self.window.updateRequired = True

		return skeleton

	def _addBone( self, parentJoint, thisJoint, modelMatrix, showBones, skeleton ):

		""" Recursive helper function to loadSkeleton(); creates a bone for the given joints, 
			adds it to the model skeleton dictionary, and repeats for this bone's children. """

		# Add this bone to the renderer and skeleton dictionary
		bone = Bone( parentJoint, thisJoint, modelMatrix, showBones )
		self.edges.append( bone )
		skeleton[thisJoint.offset] = bone

		# Give IDs to the Display Objects (useful for determining high/low-model parts)
		self._enumerateDObjs( thisJoint, skeleton )

		# Check for children to add
		childJoint = thisJoint.initChild( 'JointObjDesc', 2 )
		if childJoint:
			for siblingOffset in childJoint.getSiblings():
				if siblingOffset in skeleton:
					continue

				sibling = childJoint.dat.getStruct( siblingOffset )

				# if not sibling.isBone:
				# 	print( 'Non-bone added to skeleton: ' + hex(0x20+sibling.offset) )

				self._addBone( thisJoint, sibling, bone.modelMatrix, showBones, skeleton )
				bone.children.append( sibling.offset )

	def _enumerateDObjs( self, joint, skeleton ):

		""" Enumerates Display Objects (model parts) as they're encountered across the skeleton. 
			These enumerations are useful for determining high/low-model parts within the model. """

		# Check for a display object on this joint
		dobj = joint.initChild( 'DisplayObjDesc', 4 )
		if not dobj:
			return

		dobjClass = globalData.fileStructureClasses.get( 'DisplayObjDesc' )

		# Get all sibling objects (including this one) in this set and assign them IDs
		for offset in dobj.getSiblings():
			sibling = joint.dat.getStruct( offset )
			if sibling:
				sibling.id = dobjClass.count
				dobjClass.count += 1
				sibling.skeleton = skeleton

	def loadStageSkeletons( self, stageFile, showBones=True ):

		""" Goes through the Game Objects Array of a stage file 
			and loads each root skeleton among the root joints. """

		gobjsArray = stageFile.getGObjs()
	
		for _, entryValues in gobjsArray.iterateEntries():
			joint = stageFile.getStruct( entryValues[0] )
			if not joint:
				continue

			# Check if this is a skeleton root joint
			if joint.flags & 2:
				#print( '{} is skeleton root'.format(joint.name) )
				self.loadSkeleton( joint, showBones )

	def renderJoint( self, joint, parent=None, showBones=False, skeleton=None ):

		""" Recursively scans the given joint and all child/next joints for 
			Display Objects and Polygon Objects. Breaks down Polygon Objects 
			into primitives and renders them to the display. This method is 
			used for model parts with static rigging (no animations) as it only 
			applys translations from parent joints (ignoring rotation/scale) 
			and does not use a skeleton. """

		# https://www.flipcode.com/documents/matrfaq.html#Q1 #todo

		primitives = []

		# Check for a child joint to render
		childJoint = joint.initChild( 'JointObjDesc', 2 )
		if childJoint:
			# Render child joints and collect their primitives in order to apply transformations
			primitives.extend( self.renderJoint(childJoint, joint, showBones) )

		# Check for a 'next' (sibling) joint to render
		nextJoint = joint.initChild( 'JointObjDesc', 3 )
		if nextJoint:
			if not parent:
				parent = joint
			self.renderJoint( nextJoint, parent, showBones )

		# Check for a display object and polygon object(s) to render
		dobj = joint.DObj
		if dobj:
			primitives.extend( self.renderDisplayObj(dobj) )

		# Apply joint transformations for this joint's meshes as well as its children
		transformationValues = joint.getValues()[5:14] # 9 values; 3 for each of rotation/scale/translation
		for primitive in primitives:
			primitive.rotate( *transformationValues[:3] )
			primitive.scale( *transformationValues[3:6] )
			primitive.translate( *transformationValues[6:] )

		# Add a vertex to represent this joint
		xyzCoords = transformationValues[6:]
		if not skeleton:
			primitives.append( self.addVertex( xyzCoords, (255, 0, 0, 255), ('bones',), showBones ) )

		# Track the largest +/- x values to adjust the camera zoom
		xCoordAbs = -abs( xyzCoords[0] ) * 1.4
		if xCoordAbs < self.translation_Z and xCoordAbs > -self.zFar:
			self.translation_Z = xCoordAbs

			if self.translation_Z < -800:
				self.translation_Z = -800

		# Connect a line between the current joint and its parent joint
		if parent and not skeleton:
			# Parent vertices will be added by the calling method's transformation step(s)
			edge = self.addEdge( (0,0,0) + xyzCoords, colors=((0,255,0,255), (0,0,255,255)), tags=('bones',), show=showBones )
			primitives.append( edge )

		# Update the display to show current render progress
		self.canvas.update()

		return primitives
	
	def renderDisplayObj( self, parentDobj, includeSiblings=True ):

		""" Parses and renders the given Display Object (DObj) and 
			all of its siblings. """

		primitives = []

		if includeSiblings:
			dobjOffsets = parentDobj.getSiblings()
		else:
			dobjOffsets = [ parentDobj.offset ]

		# Check current vertexList tags to prevent creating duplicate DObjs
		vertexListTags = set()
		for vertList in self.getObjects( 'vertexList' ):
			vertexListTags.update( vertList.tags )

		try:
			# Iterate over this DObj (and its siblings, if enabled)
			for dobjOffset in reversed( dobjOffsets ):
				dobj = parentDobj.dat.getStruct( dobjOffset )

				# Prevent creating duplicate DObjs
				if dobjOffset in vertexListTags:
					continue

				# Check for a polygon object to render
				pobj = dobj.PObj
				if not pobj:
					continue

				# Check for a material
				mobj = dobj.MObj
				if not mobj:
					print( 'No material object found for ' + dobj.name )
					continue

				# Check for textures (usually just one, but there can be more)
				textures = self.collectTextures( dobj )
				if textures:
					materialGroup = self._addTextureGroup( textures )
				else:
					materialGroup = Material( self, mobj )
					#print( 'No textures for {}'.format(dobj.name) )

				# Iterate over this PObj and its siblings
				for pobjOffset in pobj.getSiblings():
					pobj = dobj.dat.getStruct( pobjOffset )

					# Create some additional rendering context for these polygons
					#pGroup = PolygonGroup( self, materialGroup, pobj )

					# Parse out primitives for this mesh
					pobjPrimitives = pobj.decodeGeometry()

					# If this is something attached to a skeleton, update part coordinates to model space
					if dobj.skeleton:
						pobj.moveToModelSpace( pobjPrimitives, dobj.skeleton )

					self.addVertexLists( pobjPrimitives, materialGroup, dobjOffset, pobjOffset )
					primitives.extend( pobjPrimitives )

		# except AttributeError:
		# 	pass # This is fine; likely a DObj that doesn't have a PObj
		except Exception as err:
			if dobj and pobj:
				print( 'Unable to render {}; {}'.format(pobj.name, err) )
			elif dobj:
				print( 'Unable to render {}; {}'.format(dobj.name, err) )
			else:
				print( 'Unable to render {}; {}'.format(parentDobj.name, err) )

		return primitives
	
	def applyJointTransformations( self, primitives, parentJoint ):

		""" Recursively moves through all Joint struct parents until no more 
			are found, and applies all of their transformation values to the 
			given primitives. """

		rotation = [ 0, 0, 0 ]
		scale = [ 1.0, 1.0, 1.0 ]
		translation = [ 0, 0, 0 ]

		jointClass = globalData.fileStructureClasses['JointObjDesc']

		# Ascend the Joint structures tree while accumulating transformation values
		while parentJoint:
			# Gather the current transform values
			transformationValues = parentJoint.getValues()[5:14] # 9 values; 3 for each of rotation/scale/translation
			rotation = list( map(add, rotation, transformationValues[:3]) )
			scale = list( map(mul, scale, transformationValues[3:6]) )
			translation = list( map(add, translation, transformationValues[6:]) )
			
			# Check for another parent joint
			parents = parentJoint.getParents()
			if not parents:
				break

			# Attempt to initialize the parent object
			parentJointOffset = next(iter( parents ))
			parentJoint = parentJoint.dat.initSpecificStruct( jointClass, parentJointOffset )
		
		# Apply the accumulated transforms
		for primitive in primitives:
			primitive.rotate( *rotation )
			primitive.scale( *scale )
			primitive.translate( *translation )
	
	def collectTextures( self, dobj ):

		""" Collects all textures attached to the given Display Object (DObj), 
			following all '_Next' pointers in the Texture Object(s). 
			Returns a list of texture objects (file structs), to be decoded later. """

		tobj = None
		textures = []

		try:
			# Check for a texture object (TObj)
			mobj = dobj.MObj
			if not mobj:
				raise Exception( 'no attached material object' )
			
			tobj = mobj.initChild( 'TextureObjDesc', 2 )

			while tobj:
				# Get basic info on the texture
				imgHeader = tobj.initChild( 'ImageObjDesc', 21 )
				imageDataOffset, width, height, imageType, mipmapFlag, minLOD, maxLOD = imgHeader.getValues()

				# Check for palette info
				paletteHeader = tobj.initChild( 'PaletteObjDesc', 22 )
				if paletteHeader:
					paletteDataOffset = paletteHeader.getValues()[0]
					paletteHeaderOffset = paletteHeader.offset
				else:
					paletteDataOffset = -1
					paletteHeaderOffset = -1

				# Initialize a structure for the image data
				texture = dobj.dat.initTexture( imageDataOffset, imgHeader.offset, paletteDataOffset, paletteHeaderOffset, width, height, imageType, maxLOD, 0 )
				texture.tobj = tobj
				texture.mobj = mobj
				textures.append( texture )

				# Check for siblings
				tobj = tobj.initChild( 'TextureObjDesc', 1 )
		
		except AttributeError:
			pass # This is fine; likely a DObj that doesn't have a MObj/TObj

		except Exception as err:
			if mobj and tobj:
				print( 'Unable to get a texture from {}; {}'.format(tobj.name, err) )
			elif mobj:
				print( 'Unable to get a texture from {}; {}'.format(mobj.name, err) )
			else:
				print( 'Unable to get a texture from {}; {}'.format(dobj.name, err) )

		return textures

	def _addTextureGroup( self, textures ):

		""" Converts the given texture objects (file structures) to 
			textures for pyglet and stores them into texture groups. """

		# Use the first texture data offset as an ID
		firstTextureOffset = textures[0].offset
		
		textureGroup = self.textures.get( firstTextureOffset )

		if not textureGroup:
			# Create a pyglet TextureGroup object and store it
			textureGroup = TexturedMaterial( self, textures )
			self.textures[firstTextureOffset] = textureGroup
		
		return textureGroup
	
	def reloadTexture( self, offset ):

		""" Forces the texture to be be reinitialized and re-decoded from 
			data in the dat file. Typically in cases it has been replaced. """

		# Seek out and update the respective texture group
		for group in self.textures.values():
			if offset in [ texture.offset for texture in group.textures ]:
				group.reloadTexture( offset )
				break

		self.window.updateRequired = True

	# def on_key_press( self, *args ):

	# 	#print( 'pressed ' + str(symbol) )
	# 	if not args:
	# 		return
	# 	symbol, modifiers = args

	# 	if symbol == key.R:
	# 		print( 'resetting' )
	# 		self.resetView()
	# 	elif symbol == key.LEFT:
	# 		print('The left arrow key was pressed.')
	# 	elif symbol == key.ENTER:
	# 		print('The enter key was pressed.')

	# 	self.window.updateRequired = True

	def on_key_press2( self, event ):

		print( 'pressed ' + event.keysym )
		symbol = event.keysym.lower()

		if symbol == 'r':
			print( 'resetting' )
			self.resetView()
		elif symbol == key.LEFT:
			print('The left arrow key was pressed.')
		elif symbol == key.ENTER:
			print('The enter key was pressed.')

		self.window.updateRequired = True

	def on_mouse_scroll( self, event ):

		""" Move the camera in and out (toward/away) from the rendered model. """

		if event.delta > 0: # zoom in
			self.translation_Z *= .95
		elif event.delta < 0: # zoom out
			self.translation_Z *= 1.05

		self.window.updateRequired = True

	# def on_mouse_scroll2( self, *args ):

	# 	print('zoom2' )
	# 	print(args)

	def on_mouse_drag( self, *args ):

		""" Handles mouse input for rotation and panning of the scene. 
			buttons = Bitwise combination of the mouse buttons currently pressed. 
			modifiers = Bitwise combination of any keyboard modifiers currently active. """

		# Grab the event arguments (excluding x and y coords)
		#print('dragged')
		if not args:
			return
		dx, dy, buttons, modifiers = args[2:]

		if buttons == 1: # Left-click button held
			self.rotation_X += dx / 2.0
			self.rotation_Y -= dy / 2.0
			# https://en.wikipedia.org/wiki/Transformation_matrix#Examples_in_3D_computer_graphics 		#todo
			# http://n64devkit.square7.ch/tutorial/graphics/6/6_4.htm
		elif buttons == 4: # Right-click button held
			# Translate as a function of zoom level
			# self.translation_X += dx / 2.0
			# self.translation_Y += dy / 2.0
			self.translation_X += self.translation_Z * 0.004 * -dx
			self.translation_Y += self.translation_Z * 0.004 * -dy
		# else: Multiple buttons held; do nothing and 
		# wait 'til the user gets their act together. :P

		self.window.updateRequired = True

	def compileShader( self, shaderType, filename ):

		""" Compiles the fragment shader and links it to the rendering program. """

		try:
			# Load the shader file
			filePath = os.path.join( globalData.scriptHomeFolder, 'bin', filename + '.shader' )
			shaderFile = io.open( filePath, mode="r", encoding="utf-8" )
			shaderSource = shaderFile.read()
			shaderFile.close()

			# Encode the shader source code to bytes and load it into a buffer
			#shaderSource = fragmentShader.encode( 'utf-8' )
			sourceBuffer = ctypes.create_string_buffer( shaderSource )

			# Create a pointer to the shader source buffer
			cTypesPointer = ctypes.POINTER( ctypes.c_char )
			sourcePointer = ctypes.cast( sourceBuffer, cTypesPointer )

			# Compile the shader
			shader = gl.glCreateShader( shaderType )
			gl.glShaderSource( shader, 1, ctypes.byref(sourcePointer), None )
			gl.glCompileShader( shader )

			# Check if the shader compilation was successful
			status = ctypes.c_int()
			gl.glGetShaderiv( shader, gl.GL_COMPILE_STATUS, ctypes.byref(status) )
			if status.value == 0:
				info_log = ctypes.create_string_buffer(4096)
				length = ctypes.c_int()
				gl.glGetShaderInfoLog( shader, 4096, ctypes.byref(length), info_log )
				raise Exception( info_log.value.decode('utf-8') )

			# Link the shader to a program object and activate it for rendering
			shaderProgram = gl.glCreateProgram()
			gl.glAttachShader( shaderProgram, shader )
			gl.glLinkProgram( shaderProgram )

			# Check for any general errors
			error_code = gl.glGetError()
			if error_code != gl.GL_NO_ERROR:
				raise Exception( "Error found after linking {} shader: {}".format(filename, gl.gluErrorString(error_code)) )
			
			# Check for any linking errors
			link_status = gl.GLint()
			gl.glGetProgramiv( shaderProgram, gl.GL_LINK_STATUS, link_status )
			if link_status.value == gl.GL_FALSE:
				raise Exception( "Error linking {} shader: {}".format(filename, gl.gluErrorString(error_code)) )

			# Activate the program object
			gl.glUseProgram( shaderProgram )
			print( '{} shader compiled and linked successfully.'.format(filename) )

			# Free memory
			gl.glDeleteShader( shader )

		except Exception as err:
			printStatus( 'There was an error during shader initialization', warning=True )
			print( err )
			return None
		
		return shaderProgram

	def setShaderInt( self, variableName, value ):
		""" May also be used to set boolean uniforms. """
		location = gl.glGetUniformLocation( self.fragmentShader, variableName )
		gl.glUniform1i( location, value )

	def setShaderFloat( self, variableName, value ):
		location = gl.glGetUniformLocation( self.fragmentShader, variableName )
		gl.glUniform1f( location, value )

	def setShaderVec4( self, variableName, values ):
		location = gl.glGetUniformLocation( self.fragmentShader, variableName )
		gl.glUniform4f( location, *values )

	def on_draw( self ):

		""" Renders all primitives to the display. """

		try:
			# Clear the screen
			gl.glClear( gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT )
				
			#halfHeight = math.tan( self.fov / 2 ) * self.zNear
			# lightPosition = ( 100, 100, 200, 1.0 )
			# gl.glLightfv( gl.GL_LIGHT0, gl.GL_POSITION, (gl.GLfloat * 4)(*lightPosition) )
			#gl.glLightfv( gl.GL_LIGHT0, gl.GL_POSITION, (gl.GLfloat * 4)(self.translation_X, self.translation_Y, -self.translation_Z, 1.0) )

			# Set the projection matrix to a perspective projection and apply translation (camera pan)
			gl.glMatrixMode( gl.GL_PROJECTION )
			gl.glLoadIdentity()
			gl.gluPerspective( self.fov, self.aspectRatio, self.zNear, self.zFar )
			gl.glTranslatef( self.translation_X, self.translation_Y, self.translation_Z )

			# Set up the modelview matrix and apply mouse rotation input transformations
			gl.glMatrixMode( gl.GL_MODELVIEW )
			gl.glLoadIdentity()
			gl.glRotatef( self.rotation_Y, 1, 0, 0 )
			gl.glRotatef( self.rotation_X, 0, 1, 0 )

			# Render a batch for each set of objects that have been added
			# if self.fragmentShader:
			# 	self.setShaderInt( 'enableTextures', False )
			# 	self.setShaderInt( 'useVertexColors', True )
			# 	self.setShaderInt( 'alphaOp', -1 )
			if self.vertices:
				batch = pyglet.graphics.Batch()
				for vertex in self.vertices:
					vertex.render( batch )
				batch.draw()
			if self.edges:
				batch = pyglet.graphics.Batch()
				for edge in self.edges:
					edge.render( batch )
				batch.draw()
			if self.triangles:
				batch = pyglet.graphics.Batch()
				for triangle in self.triangles:
					triangle.render( batch )
				batch.draw()
			if self.quads:
				batch = pyglet.graphics.Batch()
				for quad in self.quads:
					quad.render( batch )
				batch.draw()

			if self.vertexLists:
				# if self.fragmentShader:
				# 	self.setShaderInt( 'enableTextures', True )
				# 	self.setShaderInt( 'useVertexColors', False )
				# 	self.setShaderInt( 'alphaOp', -1 )

				#for vList in self.vertexLists:
				batch = pyglet.graphics.Batch()
				for prim in self.vertexLists:
					prim.render( batch )
				batch.draw()
			
			# Check for any general errors
			error_code = gl.glGetError()
			if error_code != gl.GL_NO_ERROR:
				raise Exception( 'Found an error during rendering: {}'.format(gl.gluErrorString(error_code)) )

		except Exception as err:
			# Do not raise an exception here, or the render loop will end.
			print( 'An error occurred during rendering: {}'.format(err) )

	def getObjects( self, primitive=None ):

		""" Fetches all primitives of the given type (vertex/edge/triangle/quad). """

		# Confine the search to improve performance
		if primitive == 'vertex':
			objects = self.vertices
		elif primitive == 'edge':
			objects = self.edges
		elif primitive == 'triangle':
			objects = self.triangles
		elif primitive == 'quad':
			objects = self.quads
		elif primitive == 'vertexList':
			objects = self.vertexLists
			# objects = []
			# for vList in self.vertexLists:
			# 	objects.extend( vList )
		else:
			if primitive:
				print( 'Warning; unrecognized primitive: ' + str(primitive) )
			objects = self.vertices + self.edges + self.triangles + self.quads + self.vertexLists
			# objects = self.vertices + self.edges + self.triangles + self.quads
			# for vList in self.vertexLists:
			# 	objects.extend( vList )

		return objects
	
	def getPrimitiveTotals( self ):
		
		""" Collects totals for the number of each type of vertexList 
			and primitive among vertexLists being rendered. 
			Returns a dict of key=primType, value=[groupCount, primCount] """
		
		totals = OrderedDict( [ 
			('Vertices', [0, 0]), ('Lines', [0, 0]), ('Line Strips', [0, 0]), 
			('Triangles', [0, 0]), ('Triangle Strips', [0, 0]), ('Triangle Fans', [0, 0]), 
			('Quads', [0, 0])
		] )
		
		for primitive in self.vertexLists:
			if primitive.type == gl.GL_POINTS:
				totals['Vertices'][0] += 1
				totals['Vertices'][1] += len( primitive.vertices[1] )
			elif primitive.type == gl.GL_LINES:
				totals['Lines'][0] += 1
				lineCount = len( primitive.vertices[1] ) / 2
				totals['Lines'][1] += lineCount
				totals['Vertices'][1] += lineCount * 2
			elif primitive.type == gl.GL_LINE_STRIP:
				totals['Line Strips'][0] += 1
				lineCount = ( len(primitive.vertices[1]) - 2 ) / 2 # -2 for degenerate vertices
				totals['Line Strips'][1] += lineCount
				totals['Vertices'][1] += lineCount - 1 # +1 vertex, but -2 for degenerate vertices
			elif primitive.type == gl.GL_TRIANGLES:
				totals['Triangles'][0] += 1
				triangleCount = len( primitive.vertices[1] ) / 3
				totals['Triangles'][1] += triangleCount
				totals['Vertices'][1] += len( primitive.vertices[1] )
				totals['Lines'][1] += len( primitive.vertices[1] )
			elif primitive.type == gl.GL_TRIANGLE_STRIP:
				totals['Triangle Strips'][0] += 1
				triangleCount = len( primitive.vertices[1] ) - 4 # Subtract initial 2 point and 2 degenerate vertices
				totals['Triangle Strips'][1] += triangleCount
				totals['Vertices'][1] += triangleCount + 2
				totals['Lines'][1] += ( triangleCount * 2 ) + 1
			elif primitive.type == gl.GL_TRIANGLE_FAN:
				totals['Triangle Fans'][0] += 1
				triangleCount = len( primitive.vertices[1] ) - 4 # Subtract initial 2 point and 2 degenerate vertices
				totals['Triangle Fans'][1] += triangleCount
				totals['Vertices'][1] += triangleCount + 2
				totals['Lines'][1] += ( triangleCount * 2 ) + 1
			elif primitive.type == gl.GL_QUADS:
				totals['Quads'][0] += 1
				quadCount = len( primitive.vertices[1] ) / 4
				totals['Quads'][1] += quadCount
				totals['Vertices'][1] += len( primitive.vertices[1] )
				totals['Lines'][1] += len( primitive.vertices[1] )

		return totals

	def showPart( self, tag, visible, primitive=None ):

		""" Toggles the visibility for all primitives with a specified tag. 
			A primitive type may be given to improve performance. """

		for obj in self.getObjects( primitive ):
			if tag in obj.tags:
				obj.show = visible

		self.window.updateRequired = True

	def showAll( self, visible=True, primitive=None ):

		""" Toggles the visibility for all primitives with a specified tag. 
			A primitive type may be given to improve performance. """

		for obj in self.getObjects( primitive ):
			obj.show = visible

		self.window.updateRequired = True

	def removePart( self, tag, primitive=None ):

		""" Removes objects with the given tag from this render instance. 
			A primitive type may be given to improve performance. """

		if primitive == 'vertex':
			newObjList = []
			for obj in self.vertices:
				if tag not in obj.tags:
					newObjList.append( obj )
			self.vertices = newObjList

		elif primitive == 'edge':
			newObjList = []
			for obj in self.edges:
				if tag not in obj.tags:
					newObjList.append( obj )
			self.edges = newObjList

		elif primitive == 'triangle':
			newObjList = []
			for obj in self.triangles:
				if tag not in obj.tags:
					newObjList.append( obj )
			self.triangles = newObjList

		elif primitive == 'quad':
			newObjList = []
			for obj in self.quads:
				if tag not in obj.tags:
					newObjList.append( obj )
			self.quads = newObjList

		elif primitive == 'vertexList':
			newObjList = []
			for obj in self.vertexLists:
				if tag not in obj.tags:
					newObjList.append( obj )
			self.vertexLists = newObjList

		else:
			if primitive:
				print( 'Warning; unrecognized primitive: ' + str(primitive) )

			self.vertices = []
			self.edges = []
			self.triangles = []
			self.quads = []
			self.vertexLists = []

			for obj in self.getObjects( primitive ):
				# Keep parts that don't have the given tag
				if tag not in obj.tags:
					if isinstance( obj, Vertex ):
						self.vertices.append( obj )
					elif isinstance( obj, Edge ):
						self.edges.append( obj )
					elif isinstance( obj, Triangle ):
						self.triangles.append( obj )
					elif isinstance( obj, Quad ):
						self.quads.append( obj )
					elif isinstance( obj, VertexList ):
						self.vertexLists.append( obj )

		self.window.updateRequired = True

	def stop( self ):

		""" Setting this flag on the render window allows the event loop end peacefully, 
			so it doesn't try to update anything that doesn't exist and crash. """

		self.window.has_exit = True


class CustomEventLoop( EventLoop ):

	""" We can't use pyglet's native event loop without interfering with Tkinter's. 
		So we'll create a modified one that will be goverened by Tkinter. """

	def __init__( self, root ):
		super( CustomEventLoop, self ).__init__()
		self.root = root
	
	def run( self ):

		""" Begin processing events, scheduled functions and window updates.
			Performs the usual pyglet startup. However, while this method would 
			normally block as the pyglet event loop runs, we will instead queue 
			updates (pyglet event loop steps) and then return. """

		self.has_exit = False
		self._legacy_setup()

		# platform_event_loop = pyglet.app.platform_event_loop
		# platform_event_loop.start()
		# self.dispatch_event('on_enter')

		self.is_running = True

		# Schedule pyglet updates in Tkinter's event loop
		self.root.after( 0, self.step )

	def step( self ):

		# Track whether there are any windows left to update
		queueNextStep = False

		for window in pyglet.app.windows:
			# Shut down any windows wanting to exit
			if window.has_exit:
				window.close()
				continue
			
			queueNextStep = True

			# Skip redraws if there haven't been any changes
			if not window.updateRequired:
				continue

			# Skip this window if the user isn't interacting with it
			# if not window._mouse_in_window:
			# 	continue

			# Set keyboard focus to this window if the mouse is over it
			# if window._mouse_in_window:
			# 	window.activate()

			# Set context/render focus to this window
			window.switch_to()

			# Queue handling mouse input and drawing (updating) the canvas
			# window.dispatch_event( 'on_mouse_drag' )	# still fires dragged without this
			#window.dispatch_event( 'on_key_press' )
			window.dispatch_event( 'on_draw' )
			#window.dispatch_pending_events()	# still fires dragged without this
			#window.dispatch_events()	# still fires dragged without this
			
			# Swap the display buffers to show the rendered image
			window.flip()

			# Set the flag indicating redraws are no longer required
			window.updateRequired = False

		# Re-queue for the next frame
		if queueNextStep:
			self.root.after( 17, self.step )
		else:
			self.stop()

	def stop( self ):

		""" The typical end to the pyglet 'run' method. """

		self.is_running = False
		self.has_exit = True

		# self.dispatch_event('on_exit')
		# platform_event_loop = pyglet.app.platform_event_loop
		# platform_event_loop.stop()


class Plane:

	""" Defined in point-normal form. """

	def __init__( self, points ):

		""" Should be initialized with a flattened list of coordinates 
			for 3 or more points (x, y, z coords for each; i.e. >= 9 values). """

		# Both are tuples of (z, y, z)
		self.point = points[:3] # Any point on the plane
		self.normal = self._getNormal( points )

	def _getNormal( self, points ):

		""" Returns a vector that is perpendicular to the region of the given 3 points. """

		# Create two vectors among the points (originating from same point)
		p1x,p1y,p1z, p2x,p2y,p2z, p3x,p3y,p3z = points[:9]
		ux, uy, uz = ( p2x-p1x, p2y-p1y, p2z-p1z ) # Vector from P1 to P2
		vx, vy, vz = ( p3x-p1x, p3y-p1y, p3z-p1z ) # Vector from P1 to P3

		# Calculate the cross product of the two vectors
		return ( uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx )
	
	def equation( self, point ):

		""" Equation of a plane, with normal vector (a, b, c). """

		x, y, z = point
		x0, y0, z0 = self.point
		a, b, c = self.normal

		return a * ( x - x0 ) + b * ( y - y0 ) + c ( z - z0 )

	def pointOnPlane( self, point ):

		""" Returns True if the given point is on this plane. """

		return self.equation( point ) == 0
	
	def contains( self, point ):
		x, y, z = point
		return 


class Primitive( object ):

	@staticmethod
	def interpretColors( pointCount, color, colors ):

		""" Checks a primitive's color and colors arguments. A single given color 
			takes priority and will be used for all vertices if provided. If no color 
			and no colors are given, vertex colors will default to gray. """

		defaultColor = ( 128, 128, 128, 255 )

		try:
			if color:
				# A single color was given
				assert len( color ) == 4, 'the given color should be an RGBA tuple.'
				colors = color * pointCount
			elif not colors:
				# No color(s) given; default to gray
				colors = defaultColor * pointCount
			elif len( colors ) == 1:
				# A single color given; copy it for all points
				assert len( colors[0] ) == 4, 'the given color should be an RGBA tuple.'
				colors = ( colors[0], ) * pointCount
			elif pointCount != len( colors ):
				# Ehh?
				print( 'Warning! Unexpected number of colors given to primitive: ' + str(colors) )
				assert len( colors[0] ) == 4, 'the given color should be an RGBA tuple.'
				colors = ( colors[0], ) * pointCount
			else:
				# Number of colors matches number of points
				flattenedList = []
				for color in colors:
					assert len( color ) == 4, 'the given colors should all be RGBA tuples.'
					flattenedList.extend( color )
				colors = flattenedList
		except Exception as err:
			print( 'Invalid color(s) given to create a primitive; {}'.format(err) )
			colors = defaultColor * pointCount

		return colors
	
	def scale( self, scaleX, scaleY, scaleZ ):

		""" Modifies the size (scaling) of the primitive's coordinates by the given amounts. """

		if self.__class__ == Vertex:
			self.x *= scaleX
			self.y *= scaleY
			self.z *= scaleZ
		else:
			newCoords = []
			coordsIter = iter( self.vertices[1] )
			coordsList = [ coordsIter ] * 3
			
			for x, y, z in zip( *coordsList ):
				newCoords.extend( (x*scaleX, y*scaleY, z*scaleZ) )

			self.vertices = ( self.vertices[0], newCoords )

	def translate( self, translateX, translateY, translateZ ):

		""" Modifies an array of point coordinates by their respective 
			translation amount (linear movement, parallel to one axis). """

		if self.__class__ == Vertex:
			if translateX:
				self.x += translateX
			if translateY:
				self.y += translateY
			if translateZ:
				self.z += translateZ
		else:
			coords = self.vertices[1]
			newCoords = []

			# Iterate over the coords in sets of z/y/z coordinates
			coordsIter = iter( coords )
			coordsList = [ coordsIter ] * 3
			for x, y, z in zip( *coordsList ):
				newCoords.append( x + translateX )
				newCoords.append( y + translateY )
				newCoords.append( z + translateZ )

			# Assign the new coordinates to the primitive
			self.vertices = ( self.vertices[0], newCoords )

	def rotate( self, rotationX, rotationY, rotationZ ):

		""" Rotates the primitive's vertex coordinates around each axis by the given angle amounts (in radians). 
			Rotates in XYZ order. """

		# Do nothing if all rotation amounts are zero
		if not rotationX and not rotationY and not rotationZ:
			return

		# Compute sin and cos values to make a rotation matrix
		cos_x, sin_x = math.cos( rotationX ), math.sin( rotationX )
		cos_y, sin_y = math.cos( rotationY ), math.sin( rotationY )
		cos_z, sin_z = math.cos( rotationZ ), math.sin( rotationZ )

		# Generate a 3D rotation matrix from angles around the X, Y, and Z axes
		rotationMatrix = [
			[cos_y * cos_z, -cos_x * sin_z + sin_x * sin_y * cos_z, sin_x * sin_z + cos_x * sin_y * cos_z], # X-axis rotation
			[cos_y * sin_z, cos_x * cos_z + sin_x * sin_y * sin_z, -sin_x * cos_z + cos_x * sin_y * sin_z], # Y-axis rotation
			[-sin_y, sin_x * cos_y, cos_x * cos_y] # Z-axis rotation
		]

		# Multiply the rotation matrix with each vertices' coordinates
		if self.__class__ == Vertex:
			originalCoords = ( self.x, self.y, self.z )
			rotatedCoords = self.matrixMultiply_3x3( rotationMatrix, originalCoords )
			self.x, self.y, self.z = rotatedCoords
		else:
			newCoords = []
			coordsIter = iter( self.vertices[1] )
			coordsList = [ coordsIter ] * 3

			for point in zip( *coordsList ):
				rotatedCoords = self.matrixMultiply_3x3( rotationMatrix, point )
				newCoords.extend( rotatedCoords )

			self.vertices = ( self.vertices[0], newCoords )

	def transform( self, m ):

		""" Applies rotaion, scale, and translation transformations to this 
			primitive's vertices using the given transformation matrix. 
			The given matrix should be a flattened 4x4, in column-major order. """

		# Apply the transformations to each vertices' coordinates
		if self.__class__ == Vertex:
			x, y, z = ( self.x, self.y, self.z )
			
			self.x = m[0]*x + m[4]*y + m[8]*z + m[12]
			self.y = m[1]*x + m[5]*y + m[9]*z + m[13]
			self.z = m[2]*x + m[6]*y + m[10]*z + m[14]
		else:
			newCoords = []
			coordsIter = iter( self.vertices[1] )
			coordsList = [ coordsIter ] * 3

			for x, y, z in zip( *coordsList ):
				newCoords.append( m[0]*x + m[4]*y + m[8]*z + m[12] )
				newCoords.append( m[1]*x + m[5]*y + m[9]*z + m[13] )
				newCoords.append( m[2]*x + m[6]*y + m[10]*z + m[14] )

			self.vertices = ( self.vertices[0], newCoords )

	def matrixMultiply_3x3( self, matrix, vertex ):

		""" Multipies a 3x3 matrix with a vertex to rotate it. """

		result = [ 0.0, 0.0, 0.0 ]

		for i in range( 3 ):
			for j in range( 3 ):
				result[i] += matrix[i][j] * vertex[j]

		return result

	def matrixMultiply_4x4( self, matrix1, matrix2 ):

		""" Performs matrix multiplication on two flattened 4x4 
			arrays representing matrices in column-major format. 
			Creates a new matrix and does not modify the originals."""

		# Check if the matrices are compatible for multiplication
		assert len( matrix1 ) == len( matrix2 ), "Incompatible matrix dimensions for multiplication"

		result = [ 0.0 ] * 16

		# Calculate the dot product for each element in the result
		for i in range( 4 ):
			for j in range( 4 ):
				for k in range( 4 ):
					#result[i * 4 + j] += matrix1[i * 4 + k] * matrix2[k * 4 + j] # row-major
					result[i + j * 4] += matrix1[i + k * 4] * matrix2[k + j * 4]

		return result


class Vertex( Primitive ):

	def __init__( self, coords, color=(0, 0, 0, 255), tags=(), show=True, size=4 ):
		# Position
		if coords:
			self.x = coords[0]
			self.y = coords[1]
			self.z = coords[2]
		else:
			self.x = 0
			self.y = 0
			self.z = 0

		# Texture coordinates
		self.s = 0
		self.t = 0

		self.color = color
		self.tags = tags
		self.show = show
		self.size = size		# For rendering appearance size
	
	def render( self, batch ):
		if self.show:
			gl.glPointSize( self.size )
			batch.add( 1, gl.GL_POINTS, None, ('v3f/static', (self.x, self.y, self.z)), ('c4B/static', self.color) )


class Edge( Primitive ):

	def __init__( self, vertices, color=None, colors=(), tags=(), show=True, thickness=2 ):
		self.vertices = ( 'v3f/static', vertices )
		self.vertexColors = ( 'c4B/static', self.interpretColors( 2, color, colors ) )
		self.tags = tags
		self.show = show
		self.thickness = thickness
	
	def render( self, batch ):
		if self.show or 'originMarker' in self.tags:
			gl.glLineWidth( self.thickness )
			batch.add( 2, gl.GL_LINES, None, self.vertices, self.vertexColors )


class Triangle( Primitive ):

	def __init__( self, vertices, color=None, colors=(), tags=(), show=True ):
		self.vertices = ( 'v3f/static', vertices )
		self.vertexColors = ( 'c4B/static', self.interpretColors( 3, color, colors ) )
		self.normals = ( 'n3f/static', [] )
		self.tags = tags
		self.show = show
	
	def render( self, batch ):
		if self.show:
			batch.add( 3, gl.GL_TRIANGLES, None, self.vertices, self.vertexColors )


class Quad( Primitive ):

	def __init__( self, vertices, color=None, colors=(), tags=(), show=True ):
		self.vertices = ( 'v3f/static', vertices )
		self.vertexColors = ( 'c4B/static', self.interpretColors( 4, color, colors ) )
		self.normals = ( 'n3f/static', [] )
		self.tags = tags
		self.show = show
	
	def render( self, batch ):
		if self.show:
			batch.add( 4, gl.GL_QUADS, None, self.vertices, self.vertexColors )


class Bone( Edge ):

	count = 0

	def __init__( self, parent, joint, modelMatrix, show=True, thickness=2 ):

		# Initialize coordinates for two vertices (initially relative to the origin to make rotation simple)
		tx, ty, tz = joint.getValues()[11:14]
		vertices = ( 0, 0, 0, tx, ty, tz )

		# Initialize as a custom edge primitive
		colors = ( (0,255,0,255), (0,0,255,255) ) # Green to Blue fade
		tags=( 'bones', )
		super( Bone, self ).__init__( vertices, None, colors, tags, show, thickness )

		self.name = 'Joint_' + str( Bone.count )
		self.joint = joint
		Bone.count += 1
		self.parent = parent.offset
		self.children = []

		# Build a local matrix for this joint, and use it to update the current model matrix
		localMatrix = joint.buildLocalMatrix()
		self.modelMatrix = self.matrixMultiply_4x4( modelMatrix, localMatrix )

		#epsilon = sys.float_info.epsilon # e.g. 2.22044604925e-16

		# Apply transformations from the parent(s) to this bone to get its vertices into model space
		self.transform( modelMatrix )


class VertexList( Primitive ):

	def __init__( self, primitiveType, tags=(), show=True ):
		self.type = self.interpretPrimType( primitiveType )
		self.vertices = ( 'v3f/static', [] )
		self.vertexColors = ( 'c4B/static', [] )
		self.texCoords = ( 't2f/static', [] )
		self.normals = ( 'n3f/static', [] )
		self.weights = [] # Envelope index

		self.renderGroup = None
		self.vertexCount = 0
		self.tags = tags
		self.show = show

	def interpretPrimType( self, primType ):

		""" Translates a primitive type/enumeration value into an OpenGL primitive type. """

		if primType == 0xB8: primitiveType = gl.GL_POINTS
		elif primType == 0xA8: primitiveType = gl.GL_LINES
		elif primType == 0xB0: primitiveType = gl.GL_LINE_STRIP
		elif primType == 0x90: primitiveType = gl.GL_TRIANGLES
		elif primType == 0x98: primitiveType = gl.GL_TRIANGLE_STRIP
		elif primType == 0xA0: primitiveType = gl.GL_TRIANGLE_FAN
		elif primType == 0x80: primitiveType = gl.GL_QUADS
		else: # Failsafe
			print( 'Warning! Invalid primitive type: 0x{:X}'.format(primType) )
			primitiveType = gl.GL_POINTS

		return primitiveType

	def finalize( self ):

		""" Validates vertex colors and texture coordinates if they're present, 
			or adds them if they're not. And adds degenerate vertices if needed. """

		self.vertexCount = len( self.vertices[1] ) / 3

		# Validate vertex colors or add them if not present
		if len( self.vertexColors[1] ) / 4 != self.vertexCount:
			self.vertexColors = ( self.vertexColors[0], [255, 255, 255, 255] * self.vertexCount )

		# Validate vertex texture coordinates or add them if not present
		if len( self.texCoords[1] ) / 2 != self.vertexCount:
			self.texCoords = ( self.texCoords[0], [0.0, 0.0] * self.vertexCount )

		if self.type == gl.GL_LINE_STRIP or self.type == gl.GL_TRIANGLE_STRIP:
			self.addDegenerates()
	
	def addDegenerates( self ):

		""" The purpose of degenerate vertices in a strip is to act as separators between segments. 
			By repeating the first and last vertices of a segment, a degenerate triangle (or line) 
			with zero area (or length) is created, which effectively skips over the degenerate 
			vertex and disconnects subsequent segments. """

		# Repeat the first three coordinates at the start
		self.vertices[1].insert( 0, self.vertices[1][2] )
		self.vertices[1].insert( 0, self.vertices[1][2] )
		self.vertices[1].insert( 0, self.vertices[1][2] )
		
		# Repeat the last three coordinates at the end
		self.vertices[1].extend( self.vertices[1][-3:] )

		self.vertexCount += 2
		
		# Repeat the first color at the start
		self.vertexColors[1].insert( 0, self.vertexColors[1][3] )
		self.vertexColors[1].insert( 0, self.vertexColors[1][3] )
		self.vertexColors[1].insert( 0, self.vertexColors[1][3] )
		self.vertexColors[1].insert( 0, self.vertexColors[1][3] )
		
		# Repeat the last color at the end
		self.vertexColors[1].extend( self.vertexColors[1][-4:] )

		# Repeat the first texture coords at the start
		self.texCoords[1].insert( 0, self.texCoords[1][1] )
		self.texCoords[1].insert( 0, self.texCoords[1][1] )
		
		# Repeat the last texture coords at the end
		self.texCoords[1].extend( self.texCoords[1][-2:] )

		# Repeat first/last weights
		if self.weights:
			self.weights.insert( 0, self.weights[0] )
			self.weights.append( self.weights[-1] )

	def addRenderGroup( self, renderGroup ):

		""" Links a render group to this primitive and adjusts texture coordinates 
			for textures that should be repeated or mirrored across a surface. """
		
		self.renderGroup = renderGroup
		
		if isinstance( renderGroup, TexturedMaterial ):
			# Extend discrete space texture coordinates (0-1 range) beyond the 1.0 range for repeating textures
			if renderGroup.repeatS != 1:
				newCoords = [ coord * renderGroup.repeatS if i % 2 == 0 else coord for i, coord in enumerate(self.texCoords[1]) ]
				self.texCoords = ( self.texCoords[0], newCoords )
			if renderGroup.repeatT != 1:
				newCoords = [ coord * renderGroup.repeatT if i % 2 == 1 else coord for i, coord in enumerate(self.texCoords[1]) ]
				self.texCoords = ( self.texCoords[0], newCoords )

	def render( self, batch ):
		if self.show:
			batch.add( self.vertexCount, self.type, self.renderGroup, self.vertices, self.vertexColors, self.texCoords )


# class PrimGroup( Group ):

# 	""" A rendering group for basic primitives; allows for a 
# 		separate rendering context (OpenGL state) just for them. """

# 	def set_state( self ):
		
# 		# gl.glBlendFunc( gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA )
# 		# gl.glBlendEquation( gl.GL_FUNC_ADD )
# 		#gl.glDepthMask( True )
# 		gl.glDisable( gl.GL_BLEND )

# 		# gl.glEnable( gl.GL_DEPTH_TEST )
# 		# #gl.glAlphaFunc( gl.GL_GREATER, 0 )
# 		# gl.glDepthFunc( gl.GL_LEQUAL )
# 		# gl.glColorMask( True, True, True, True )
# 		# gl.glBlendColor( 1.0, 1.0, 1.0, 1.0 )

# 	def unset_state( self ):
# 		gl.glEnable( gl.GL_BLEND )


class Material( Group ):

	""" Represents a render group for model materials. """

	def __init__( self, renderEngine, materialObject ):
		self.renderEngine = renderEngine
		self.materialObj = materialObject
		self.parent = None # Required for recursive Group set_state/unset_state calls
		self.enableTextures = True
		self.useVertexColors = True

		self._setMatProperties()

	def _setMatProperties( self ):

		""" Parses the material for this surface for colors and blending methods,
			and translates some enumerations to avoid per-render-call operations. """

		# Get the material and fetch child structs
		self.matFlags = self.materialObj.flags
		matColorStruct = self.materialObj.initChild( 'MaterialColorObjDesc', 3 )
		pixelProcObj = self.materialObj.initChild( 'PixelProcObjDesc', 5 )

		# Set material colors and other aspects
		if matColorStruct:
			self.diffusion = matColorStruct.diffusion
			self.ambience = matColorStruct.ambience
			self.specular = matColorStruct.specular
			self.transparency = matColorStruct.transparency
			self.shininess = matColorStruct.shininess
		else:
			self.diffusion = [ 1.0, 1.0, 1.0, 1.0 ]
			self.ambience = [ 1.0, 1.0, 1.0, 1.0 ]
			self.specular = [ 1.0, 1.0, 1.0, 1.0 ]
			self.transparency = 1.0
			self.shininess = 100.0

		if not self.renderEngine.fragmentShader:
			# Convert to LP_c_float instances, which glMaterialfv expects
			self.diffusion = (gl.GLfloat * 4)(*self.diffusion)
			self.ambience = (gl.GLfloat * 4)(*self.ambience)
			self.specular = (gl.GLfloat * 4)(*self.specular)
			#self.emission = (gl.GLfloat * 4)(*emission)

		# Enable or disable influence of vertex colors
		if self.matFlags & 2:
			self.useVertexColors = True
		else:
			# Material colors will be used instead
			self.useVertexColors = False

		# Configure per-pixel processing
		if pixelProcObj:
			self.pixelProcEnabled = True
			self.peFlags = pixelProcObj.flags

			# Translate source and destination blending methods
			peValues = pixelProcObj.getValues()
			self.destAlpha = peValues[3] / 255.0
			self.blendMode = GXBlendMode[peValues[4]]
			self.sFactor = GXBlendFactor[peValues[5]]
			self.dFactor = GXBlendFactor[peValues[6]]

			self.logicOp = GXLogicOp[peValues[7]]
			self.depthFunction = GXCompare[peValues[8]]
			#self.alphaFunction = self.depthFunction

			# Translate equations to use for RGB and alpha blending
			self.alphaRef0 = peValues[1] / 255.0
			self.alphaRef1 = peValues[2] / 255.0
			self.alphaOp = peValues[10]
			self.alphaComp0 = peValues[9]
			self.alphaComp1 = peValues[11]
		else:
			self.pixelProcEnabled = False
			self.peFlags = 0x77 # All enabled except Z-Buff Before Texturing (1110111)

			# Set source and destination blending methods
			self.destAlpha = 1.0
			self.blendMode = gl.GL_FUNC_ADD
			self.sFactor = gl.GL_SRC_ALPHA
			self.dFactor = gl.GL_ONE_MINUS_SRC_ALPHA

			self.logicOp = gl.GL_SET
			self.depthFunction = gl.GL_LEQUAL # or GL_LEQUAL?
			#self.alphaFunction = gl.GL_GREATER

			# Set defaults to use for RGB and alpha blending
			self.alphaRef0 = 0
			self.alphaRef1 = 0
			self.alphaOp = -1
			self.alphaComp0 = 7 # gl.GL_ALWAYS (do not consider refs)
			self.alphaComp1 = 7 # gl.GL_ALWAYS

	def set_state( self ):

		""" Sets rendering context (OpenGL state) for primitives using this group. """

		# Set material lighting properties
		if self.renderEngine.fragmentShader:
			self.renderEngine.setShaderInt( 'useVertexColors', self.useVertexColors )

			#if not self.useVertexColors:
			# Use material colors instead
			self.renderEngine.setShaderVec4( 'diffuseColor', self.diffusion )
			self.renderEngine.setShaderVec4( 'ambientColor', self.ambience )
			self.renderEngine.setShaderVec4( 'specularColor', self.specular )
			self.renderEngine.setShaderFloat( 'shininess', self.shininess )
			self.renderEngine.setShaderFloat( 'materialAlpha', self.transparency )
		# else:
			# face = gl.GL_FRONT_AND_BACK
			# gl.glMaterialfv( face, gl.GL_DIFFUSE, self.diffusion )
			# gl.glMaterialfv( face, gl.GL_AMBIENT, self.ambience )
			# gl.glMaterialfv( face, gl.GL_SPECULAR, self.specular )
			# gl.glMaterialfv( face, gl.GL_EMISSION, (gl.GLfloat * 4)(0, 0, 0, 1.0) )
			# gl.glMaterialf( face, gl.GL_SHININESS, self.shininess )

		# Set blending mode between source and destination for both RGB and Alpha
		if self.blendMode:
			gl.glBlendFunc( self.sFactor, self.dFactor )
			gl.glBlendEquation( self.blendMode )
		else:
			# Writing directly to EFB; no need for special blending
			gl.glBlendFunc( gl.GL_ONE, gl.GL_ZERO )
			gl.glBlendEquation( gl.GL_FUNC_ADD )

		# Enable or disable writing into the depth buffer
		if self.matFlags & 1<<29: # RENDER_NO_ZUPDATE
			# Send object to the back (no Z order calculation)
			gl.glDepthMask( gl.GL_FALSE )
		else:
			# Enable writing to depth buffer
			gl.glDepthMask( gl.GL_TRUE )

		# gl.glEnable( gl.GL_COLOR_LOGIC_OP )
		#gl.glLogicOp( self.logicOp )

		if self.pixelProcEnabled:
			# Set variables in the fragment shader for alpha testing
			if self.renderEngine.fragmentShader:
				self.renderEngine.setShaderInt( 'alphaOp', self.alphaOp )
				self.renderEngine.setShaderInt( 'alphaComp0', self.alphaComp0 )
				self.renderEngine.setShaderInt( 'alphaComp1', self.alphaComp1 )
				self.renderEngine.setShaderFloat( 'alphaRef0', self.alphaRef0 )
				self.renderEngine.setShaderFloat( 'alphaRef1', self.alphaRef1 )

			# Control updates to the depth buffer
			if self.peFlags & 1<<4:
				# Enable Z Comparisons
				gl.glEnable( gl.GL_DEPTH_TEST )
				gl.glDepthFunc( self.depthFunction )
				#gl.glAlphaFunc( self.alphaFunction, 0 )
			else:
				gl.glDisable( gl.GL_DEPTH_TEST )
				#gl.glAlphaFunc( gl.GL_GREATER, 0 )

			# Control updates to the frame buffer for colors and the alpha channel
			if self.peFlags & 1:
				# Enable Color updates
				if self.peFlags & 2:
					# Enable Color and Alpha updates
					gl.glColorMask( True, True, True, True )
				else:
					gl.glColorMask( True, True, True, False )
			elif self.peFlags & 2:
				# Enable Alpha updates
				gl.glColorMask( False, False, False, True )
			else: # Allow no updates
				gl.glColorMask( False, False, False, False )

			# Set custom alpha for color blending (Destination Alpha)
			if self.peFlags & 1<<2: # The 'Enable Destination Alpha' flag
				gl.glBlendColor( 1.0, 1.0, 1.0, self.destAlpha )
			else:
				gl.glBlendColor( 1.0, 1.0, 1.0, 1.0 )

			# 1<<3 'Z-Buff Before Texturing'

		# No pixel-processing
		else:
			# Disable pixel-processing alpha test
			if self.renderEngine.fragmentShader:
				self.renderEngine.setShaderInt( 'alphaOp', -1 )

			# Set default operations
			gl.glEnable( gl.GL_DEPTH_TEST )
			gl.glDepthFunc( self.depthFunction )
			#gl.glAlphaFunc( gl.GL_GREATER, 0 )
			gl.glColorMask( True, True, True, True )
			gl.glBlendColor( 1.0, 1.0, 1.0, 1.0 )

	def unset_state( self ):

		""" Clears/resets rendering context (OpenGL state) for primitives using this group. """

		if self.renderEngine.fragmentShader:
			self.renderEngine.setShaderInt( 'alphaOp', -1 )
			self.renderEngine.setShaderInt( 'useVertexColors', True )

		#gl.glDisable( gl.GL_COLOR_MATERIAL )

		#gl.glEnable( gl.GL_BLEND )
		# gl.glDisable( gl.GL_COLOR_LOGIC_OP )

		gl.glBlendFunc( gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA )
		gl.glBlendEquation( gl.GL_FUNC_ADD )
		gl.glDepthMask( True )

		gl.glEnable( gl.GL_DEPTH_TEST )
		#gl.glAlphaFunc( gl.GL_GREATER, 0 )
		gl.glDepthFunc( gl.GL_LEQUAL )
		gl.glColorMask( True, True, True, True )
		gl.glBlendColor( 1.0, 1.0, 1.0, 1.0 )
		#gl.glLogicOp( gl.GL_COPY )


class TexturedMaterial( Material ):

	def __init__( self, renderEngine, textures, index=0 ):
		self.renderEngine = renderEngine
		initialTexture = textures[index]
		
		self.index = index
		self.textures = textures # A list of texture file structure objects
		self.texture = self._convertTexObject( initialTexture ) # Creates a pyglet texture object
		self.pygletConversions = { initialTexture.offset: self.texture }

		# Perform material initialization and set material properties
		super( TexturedMaterial, self ).__init__( renderEngine, initialTexture.mobj )

		self._setTexProperties()

	def _setTexProperties( self ):

		""" Checks a few properties from the texture's TObj struct, 
			and prepares wrap modes and repeat properties for render. """

		tobj = self.textures[self.index].tobj
		tobjValues = tobj.getValues()
		self.texFlags = tobj.flags

		#self.texGenSrc = 
		self.wrapModeS = WrapMode[tobjValues[13]]
		self.wrapModeT = WrapMode[tobjValues[14]]
		self.repeatS = tobjValues[15]
		self.repeatT = tobjValues[16]
		self.blending = tobjValues[19]
		self.magFilter = GXTexFilter[tobjValues[20]]

		# Check for the LoD (Level of Detail) struct
		lodObjClass = globalData.fileStructureClasses['LodObjDes']
		lodStruct = tobj.dat.initSpecificStruct( lodObjClass, tobjValues[23], tobj.offset, printWarnings=False )
		if lodStruct:
			lodValues = lodStruct.getValues()
			self.minFilter = GXTexFilter[lodValues[0]]
		else:
			self.minFilter = gl.GL_LINEAR_MIPMAP_LINEAR
		
		# Check for a TEV struct
		#tevObjClass = globalData.fileStructureClasses['TevObjDesc']
		#tevStruct = self.dat.initSpecificStruct( tevObjClass, tobjValues[24], tobj.offset, printWarnings=False )
		
	def _convertTexObject( self, textureObj ):

		""" Decodes the given texture (struct) object from the game's 
			native texture format and converts it to a pyglet image. """

		# Decode the texture
		width, height = textureObj.width, textureObj.height
		pilImage = textureObj.dat.getTexture( textureObj.offset, width, height, textureObj.imageType, textureObj.imageDataLength, getAsPilImage=True )
		
		# Convert it for use with pyglet
		pygletImage = pyglet.image.ImageData( width, height, 'RGBA', pilImage.tobytes() )
		texture = pygletImage.get_texture()

		return texture
	
	def changeTextureIndex( self, index ):

		""" Switches the current texture to a different one 
			in this group, converting it if needed. """

		assert index >= 0 and index < len( self.textures ), 'Texture group index out of range! {}'.format( index )

		self.index = index
		textureObj = self.textures[index]
		pygletTexture = self.pygletConversions.get( textureObj.offset )

		# Check if this one has already been decoded/converted
		if not pygletTexture:
			pygletTexture = self._convertTexObject( textureObj )
			self.pygletConversions[textureObj.offset] = pygletTexture

		self.texture = pygletTexture
		self._setTexProperties()

	def reloadTexture( self, imageDataOffset ):

		""" Deletes textures converted for use as pyglet textures, and 
			converts a new instance from the texture object. Useful in 
			case the original texture is updated or replaced. """

		# Delete any stored converted instance of the texture
		if imageDataOffset in self.pygletConversions:
			del self.pygletConversions[imageDataOffset]

		# Check if this is the 'current' texture, and re-convert it now if it is
		for i, textureObj in enumerate( self.textures ):
			if i == self.index and textureObj.offset == imageDataOffset:
				# Re-convert a new texture object
				pygletTexture = self._convertTexObject( textureObj )
				self.pygletConversions[imageDataOffset] = pygletTexture
				self.texture = pygletTexture
				break

	def set_state( self ):

		""" Sets rendering context (OpenGL state) for primitives using 
			this group and its parent material group. """

		# Set states for the material
		super( TexturedMaterial, self ).set_state()

		if not self.enableTextures:
			if self.renderEngine.fragmentShader:
				self.renderEngine.setShaderInt( 'enableTextures', False )
			return

		# Enable and bind operations for this texture
		gl.glEnable( self.texture.target ) # i.e. GL_TEXTURE_2D
		gl.glBindTexture( self.texture.target, self.texture.id )
		if self.renderEngine.fragmentShader:
			self.renderEngine.setShaderInt( 'enableTextures', True )
			self.renderEngine.setShaderInt( 'textureFlags', self.texFlags )
			self.renderEngine.setShaderFloat( 'textureBlending', self.blending )

		# Texture Filtering
		gl.glTexParameteri( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, self.magFilter )
		#gl.glTexParameteri( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, self.minFilter )
		gl.glTexParameteri( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR ) # todo; black textures without this specific filter?

		# Wrap Mode
		gl.glTexParameteri( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, self.wrapModeS )
		gl.glTexParameteri( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, self.wrapModeT )

	def unset_state( self ):

		""" Clears/resets rendering context (OpenGL state) for primitives 
			using this group and its parent material group. """

		# Unet states for the material
		super( TexturedMaterial, self ).unset_state()
		
		# Unset states for this texture
		if self.enableTextures:
			gl.glDisable( self.texture.target )

			# Disable texturing for other non-textured surfaces or primitives that might follow this
			if self.renderEngine.fragmentShader:
				self.renderEngine.setShaderInt( 'enableTextures', False )


class PolygonGroup( OrderedGroup ):

	def __init__( self, renderEngine, pobj, parent=None ):
		self.renderEngine = renderEngine
		self.parent = parent

		# Parse the flags to configure polygon properties
		flags = pobj.getValues( 'Polygon_Flags' )
		if flags & 1<<14 and flags & 1<<15:
			self.cullMode = gl.GL_FRONT_AND_BACK
		elif flags & 1<<14:
			self.cullMode = gl.GL_FRONT
		elif flags & 1<<15:
			self.cullMode = gl.GL_BACK
		else:
			self.cullMode = -1

		# if flags & 1:
		# 	self.windingOrder = gl.GL_CCW # Counter-clockwise
		# else:
		# 	self.windingOrder = gl.GL_CW # Clockwise
	
	def set_state( self ):
		# if self.cullMode == -1:
		# 	gl.glDisable( gl.GL_CULL_FACE )
		# else:
		# 	gl.glEnable( gl.GL_CULL_FACE )
		# 	gl.glCullFace( self.cullMode )

		# gl.glFrontFace( self.windingOrder )
		pass

	def unset_state( self ):
		pass