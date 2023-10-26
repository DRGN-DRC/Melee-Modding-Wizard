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

""" If the following is True, several debug features will be enabled.
	Rendering calls to OpenGL functions will be checked afterwards for
	errors using 'glGetError'. This will severely impact performance,
	but provide useful exceptions in case of those points of failure. """
DEBUGMODE = False

# Disable a few options for increased performance
pyglet.options['debug_gl'] = DEBUGMODE
pyglet.options['audio'] = ( 'silent', )
#pyglet.options['shadow_window'] = False
pyglet.options['search_local_libs'] = False

from pyglet import gl
from pyglet.window import key, Projection3D
from pyglet.window import Window as pygletWindow
from pyglet.app.base import EventLoop
from pyglet.graphics import Group, OrderedGroup, TextureGroup
#from pyglet.window.event import WindowEventLogger

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

GXAnisotropy = [
	1.0,
	2.0,
	4.0,
	4.0 # Checked and updated upon initialization
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


# def normalizeRadians( angle_radians ):

# 	""" Takes an angle in radians and ensures it stays within one full revolution 
# 		(0 to 2π radians or 0 to 360 degrees) while preserving its direction. """

# 	# Ensure angle_radians is within the range [0, 2π)
# 	normalized_angle = angle_radians % (2 * math.pi)

# 	# Ensure the result is non-negative
# 	if normalized_angle < 0:
# 		normalized_angle += 2 * math.pi

# 	return normalized_angle


class RenderEngine( Tk.Frame ):

	""" This module creates a pyglet rendering environment (a window), and embeds
		it into a Tkinter frame for incorporation into the larger GUI. This also 
		uses a custom render loop, allowing draw updates to be delegated by the 
		main program's event loop instead of pyglet's normal application event loop. """

	maxAnisotropy = None

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
		self.camera = Camera( self )
		self.aspectRatio = self.width / float( self.height )
		self.window.projection = Projection3D( self.camera.fov, self.camera.zNear, self.camera.zFar ) # todo: need custom class to replace glFrustum & friends; http://www.manpagez.com/man/3/glFrustum/
		self.window.on_draw = self.on_draw
		self.bind( '<Expose>', self.refresh )
		if DEBUGMODE:
			openGlVersion = self.window.context._info.get_version().split()[0]
			print( 'Rendering with OpenGL version {}'.format(openGlVersion) )

		# Set the pyglet parent window to be the tkinter canvas
		GWLP_HWNDPARENT = -8
		pyglet_handle = self.window.canvas.hwnd
		win32api.SetWindowLong( pyglet_handle, GWLP_HWNDPARENT, self.canvas.winfo_id() )

		# Ensure this window is targeted for operations that should affect it
		self.window.switch_to()

		self.fragmentShader = self.compileShader( gl.GL_FRAGMENT_SHADER, 'fragment' )
		
		# Set up a default render mode in the shader to allow for basic primitives
		if self.fragmentShader:
			self.setShaderInt( 'enableTextures', False )
			self.setShaderInt( 'useVertexColors', True )
			self.setShaderInt( 'alphaOp', -1 )

		# Set up the OpenGL context
		gl.glClearColor( *self.bgColor )
		gl.glClearDepth( 1.0 ) # Depth buffer setup

		gl.glEnable( gl.GL_TEXTURE_2D )
		gl.glTexParameterf( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_BASE_LEVEL, 0 )
		gl.glTexParameterf( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAX_LEVEL, 11 ) # Support for texture dimensions up to 1024

		# Check maximum anisotropy level
		if not self.maxAnisotropy:
			maxAnisotropy = gl.GLfloat( 0.0 ) # Variable to store the result
			gl.glGetFloatv( gl.glext_arb.GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT, ctypes.byref(maxAnisotropy) )
			self.maxAnisotropy = maxAnisotropy.value
			GXAnisotropy[3] = self.maxAnisotropy

		gl.glEnable( gl.GL_BLEND )
		gl.glEnable( gl.GL_ALPHA_TEST )
		gl.glEnable( gl.GL_DEPTH_TEST ) # Do depth comparisons
		#gl.glEnable( gl.GL_COLOR_LOGIC_OP )
		gl.glDepthMask( True )

		gl.glBlendFunc( gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA )
		gl.glAlphaFunc( gl.GL_GREATER, 0 )
		gl.glDepthFunc( gl.GL_LEQUAL ) # The type of depth testing to do

		# gl.glEnable( gl.GL_LIGHTING )
		# halfHeight = math.tan( self.camera.fov / 2 ) * self.camera.zNear
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

		# Set up event handling for controls
		#self.window._enable_event_queue = True
		#self.window.on_key_press = self.on_key_press
		self.window.on_mouse_drag = self.camera.on_mouse_drag
		self.window.on_mouse_scroll = self.camera.on_mouse_scroll
		self.window.on_mouse_release = self.camera.on_mouse_release
		self.master.bind( "<MouseWheel>", self.camera.on_mouse_scroll )
		#self.master.bind( '<KeyPress>', self.on_key_press2 )
		#self.master.bind( "<1>", self.window.activate() ) # Move focus to the parent when clicked on

		if resizable:
			self.tic = time.time()
			self.bind( "<Configure>", self.resizeViewport )

		# Start the render event loop using Tkinter's main event loop
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
		self.batches = []
		self.textureCache = {}

		# Add a marker to show the origin point
		if DEBUGMODE:
			self.addEdge( [-2,0,0, 2,0,0], (255, 0, 0, 255), tags=('originMarker',), thickness=3 )
			self.addEdge( [0,-2,0, 0,2,0], (0, 255, 0, 255), tags=('originMarker',), thickness=3 )
			self.addEdge( [0,0,-2, 0,0,2], (0, 0, 255, 255), tags=('originMarker',), thickness=3 )

		self.window.updateRequired = True

	def resetView( self ):
		self.camera.reset()
		self.window.updateRequired = True

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
			#self.camera.defineFrustum()

		self.window.updateRequired = True

	def refresh( self, event=None ):

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
			print( 'Unable to add unknown, non-primitive objects!: {}'.format(unknownObjects) )

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
		# xCoordAbs = -abs( xyzCoords[0] ) * 1.4
		# if xCoordAbs < self.camera.rotationPoint[2] and xCoordAbs > -self.camera.zFar:
		# 	if xCoordAbs < -800:
		# 		self.camera.rotationPoint = ( self.camera.rotationPoint[0], self.camera.rotationPoint[1], -800 )
		# 	else:
		# 		self.camera.rotationPoint = ( self.camera.rotationPoint[0], self.camera.rotationPoint[1], xCoordAbs )

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

		# Modify appearance of hidden joints
		jointClass = globalData.fileStructureClasses['JointObjDesc']
		parentJObj = parentDobj.getParent( jointClass )
		if parentJObj.flags & 1<<4: # Checking the HIDDEN flag
			alphaAdjustment = .25
		else:
			alphaAdjustment = 1.0

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
			for dobjOffset in dobjOffsets:
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
					materialGroup = TexturedMaterial( self, textures )
				else:
					materialGroup = Material( self, mobj )
					#print( 'No textures for {}'.format(dobj.name) )
				materialGroup.transparency *= alphaAdjustment

				# Update the render group's renderState from the DObj (if the DObj has the property)
				materialGroup.renderState = getattr( dobj, 'renderState', 'normal' )

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
			# parentJointOffset = next(iter( parents ))
			# parentJoint = parentJoint.dat.initSpecificStruct( jointClass, parentJointOffset )
			parentJoint = parentJoint.getParent( jointClass )
		
		# Apply the accumulated transforms
		for primitive in primitives:
			primitive.rotate( *rotation )
			primitive.scale( *scale )
			primitive.translate( *translation )

	def separateBatches( self ):

		""" Sorts vertex lists (primitives) into separate rendering batches, 
			so that partially transparent model parts will be rendered last. """

		opaqueParts = []
		transparentParts = []

		for primitive in self.vertexLists:
			if primitive.renderGroup.transparency < 1.0:
				transparentParts.append( primitive )
			else:
				opaqueParts.append( primitive )

		self.batches = [ opaqueParts, transparentParts ]

		self.window.updateRequired = True

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
				imageDataOffset, width, height, imageType, _, _, maxLOD = imgHeader.getValues()

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
	
	def reloadTexture( self, offset ):

		""" Deletes cached pyglet textures and converts a new instance from the texture 
			object. Useful in cases where the original texture is updated or replaced. """

		# Delete any stored converted instance of the texture
		# if offset in self.textureCache:
		# 	del self.textureCache[offset]

		reconversionComplete = False

		# Seek out and update texture groups currently using the texture
		for primitive in self.vertexLists:
			renderGroup = primitive.renderGroup

			if isinstance( renderGroup, TexturedMaterial ):
				# Get the texture object currently used by the render group
				textureObj = renderGroup.textures[renderGroup.index]

				if textureObj.offset == offset or offset in renderGroup.mipmaps:
					if not reconversionComplete:
						# Convert the texture anew (replacing old texture cache(s))
						renderGroup.texture = renderGroup._convertTexObject( textureObj )
						reconversionComplete = True

					else: # Just need to update the currently selected texture
						renderGroup.texture = renderGroup.getPygletTexture( textureObj )

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
			printStatus( 'Unable to initialize {} shader. Switching to fixed-function pipeline'.format(filename), warning=True )
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

	def setShaderMatrix( self, variableName, matrix ):
		location = gl.glGetUniformLocation( self.fragmentShader, variableName )
		gl.glext_arb.glUniformMatrix4fv( location, 1, False, (gl.GLfloat * 16)(*matrix) )

	def on_draw( self ):

		""" Places the camera and renders all primitives to the display. """

		try:
			# Clear the screen
			gl.glClear( gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT )

			#halfHeight = math.tan( self.camera.fov / 2 ) * self.zNear
			# lightPosition = ( 100, 100, 200, 1.0 )
			# gl.glLightfv( gl.GL_LIGHT0, gl.GL_POSITION, (gl.GLfloat * 4)(*lightPosition) )
			#gl.glLightfv( gl.GL_LIGHT0, gl.GL_POSITION, (gl.GLfloat * 4)(self.camera.rotationPoint[0], self.camera.rotationPoint[1], self.camera.rotationPoint[2], 1.0) )

			# Set the projection matrix to a perspective projection
			gl.glMatrixMode( gl.GL_PROJECTION )
			gl.glLoadIdentity()
			gl.gluPerspective( self.camera.fov, self.aspectRatio, self.camera.zNear, self.camera.zFar )

			# Set the camera position, facing direction, and orientation
			gl.gluLookAt( self.camera.position.x, self.camera.position.y, self.camera.position.z, 
				self.camera.rotationPoint[0], self.camera.rotationPoint[1], self.camera.rotationPoint[2], 
				self.camera.upVector.x, self.camera.upVector.y, self.camera.upVector.z )

			# vm = self.camera.buildMatrix()
			# print(vm)
			# view_matrix_array = (ctypes.c_float * len(vm))(*vm)
			# # gl.glMultMatrixf(sum(self.camera.buildMatrix(), []))  # Flatten the matrix and apply
			# gl.glMultMatrixf( view_matrix_array )

			# Render a batch for each set of objects that have been added
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
			if len( self.batches ) > 1:
				for vertexLists in self.batches:
					batch = pyglet.graphics.Batch()
					for prim in vertexLists:
						prim.render( batch )
					batch.draw()
			elif self.vertexLists:
				batch = pyglet.graphics.Batch()
				for prim in self.vertexLists:
					prim.render( batch )
				batch.draw()

			# Check for any general errors
			if DEBUGMODE:
				# The option "pyglet.options['debug_gl']" must be True for the following to work
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

			# Re-separate batches
			self.separateBatches()

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

			# Re-separate batches
			self.separateBatches()

		self.window.updateRequired = True

	def stop( self ):

		""" Setting this flag on the render window allows the event loop end peacefully, 
			so it doesn't try to update anything that doesn't exist and crash. """

		self.window.has_exit = True


class Camera( object ):

	def __init__( self, renderEngine ):
		self.engine = renderEngine

		# These should be updated for context of different scene/model sizes
		self.fov = 45
		self.zNear = 5
		self.zFar = 3500
		self.stepSize = 0.1
		self._focalDistance = 10
		self.defaultToAltZoom = False

		# self.matrix = [
		# 	1.0, 0.0, 0.0, -self.position.x,
		# 	0.0, 1.0, 0.0, -self.position.y,
		# 	0.0, 0.0, 1.0, -self.position.z,
		# 	0.0, 0.0, 0.0, 1.0
		# ]

		self.reset()

	@property
	def focalDistance( self ):
		return self._focalDistance

	@focalDistance.setter
	def focalDistance( self, value ):
		self._focalDistance = value
		self.stepSize = value * 0.01

	# def buildMatrix( self ):
	# 	#u = Vector()
	# 	#def create_view_matrix(camera_position, look_at_point, up_vector):

	# 	forward = Vector( *self.direction.subtract( self.position ) )
	# 	forward.normalize()

	# 	#right = normalize_vector(cross_product(up_vector, forward))
	# 	#right = self.upVector.crossProduct( forward )
	# 	# right = cross_product( self.upVector, forward )
	# 	# new_up = cross_product(forward, right)
	# 	right = self.upVector.crossProduct( forward )
	# 	new_up = forward.crossProduct( right )

	# 	view_matrix = [
	# 		right.x, new_up.y, -forward.x, 0,
	# 		right.y, new_up.y, -forward.y, 0,
	# 		right.z, new_up.z, -forward.z, 0,
	# 		-self.position.x, -self.position.y, -self.position.z, 1
	# 	]

	# 	return view_matrix

	def reset( self ):

		""" Resets camera position, orientation (facing direction), and rotation-focus point. """

		self.rotationX = 90 # Rotation angle around the X-axis, in degrees
		self.rotationY = 90 # Rotation angle around the Y-axis, in degrees
		
		self.position = Vector()
		self.rotationPoint = ( 0.0, 0.0, 0.0 )

		self.rightVector = Vector( x=1.0 )
		self.upVector = Vector( y=1.0 )
		self.forwardVector = Vector( z=1.0 )

	def defineFrustum( self ):

		""" Defines the viewable area of the render environment, which is composed 
			of 6 sides and shaped like the cross-section of a pyramid. The result 
			of this function is a tuple of the planes (sides) enclosing this area. """

		# Create vectors for the plane corners (points on the near plane, and vectors to the far plane)
		fovRads = math.radians( self.fov )
		halfHeight = math.tan( fovRads / 2 ) * self.zNear
		halfWidth = halfHeight * self.engine.aspectRatio

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

	def setRotationPoint( self, tags=None, primitive=None, skipRotationReset=False ):

		""" Resets the camera and centers it on the object(s) with the given tag. 
			This is done by setting a new rotation point and camera coordinates.
			The tags and primitive arguments may be used to filter among targets. """

		# if not skipRotationReset:
		# 	self.engine.resetView()

		self.reset()

		xCoords = []; yCoords = []; zCoords = []

		# Check if tags is an iterable or a single item, and make it a set
		if tags:
			if hasattr( tags, '__iter__' ):
				tags = set( tags )
			else:
				# Is not an iterable; make it into one
				tags = set( [tags] )

		# Find all of the x/y/z coordinates of the target object(s)
		for obj in self.engine.getObjects( primitive ):
			if not tags or tags & set( obj.tags ):
				if obj.__class__ == Vertex:
					xCoords.append( obj.x )
					yCoords.append( obj.y )
					zCoords.append( obj.z )
				else:
					objCoordsX = []; objCoordsY = []; objCoordsZ = []

					# Iterate over the vertices by individual coordinates
					coordsIter = iter( obj.vertices[1] )
					coordsList = [ coordsIter ] * 3
					for x, y, z in zip( *coordsList ):
						objCoordsX.append( x )
						objCoordsY.append( y )
						objCoordsZ.append( z )

					minX = min( objCoordsX )
					minY = min( objCoordsY )
					minZ = min( objCoordsZ )
					maxX = max( objCoordsX )
					maxY = max( objCoordsY )
					maxZ = max( objCoordsZ )

					# Ignore very large structures (like skyboxes)
					if maxX - minX > 500 or maxY - minY > 500 or maxZ - minZ > 500:
						continue

					xCoords.extend( objCoordsX )
					yCoords.extend( objCoordsY )
					zCoords.extend( objCoordsZ )

		# Set defaults and exit if no coordinates could be collected
		if not xCoords:
			return

		# Calculate the centerpoint of all of the scanned objects
		maxX = max( xCoords )
		maxY = max( yCoords )
		maxZ = max( zCoords )
		minX = min( xCoords )
		minY = min( yCoords )
		minZ = min( zCoords )
		x = ( maxX + minX ) / 2.0
		y = ( maxY + minY ) / 2.0
		z = ( maxZ + minZ ) / 2.0

		# Determine depth (zoom level); try to get the entire model part/group in the frame
		width = maxX - minX
		height = maxY - minY
		depth = maxZ - minZ
		if width > ( height * self.engine.aspectRatio ):
			# Use x-axis to determine zoom level
			zOffset = width * 1.4
		else:
			# Use y-axis to determine zoom level (and also zoom out a little further)
			zOffset = height * self.engine.aspectRatio * 1.4

		# Ensure the camera doesn't clip into the object and we're not too far away
		if ( zOffset - self.zNear * 1.5 ) < ( depth / 2 ):
			zOffset = ( depth / 2 * 1.4 ) + self.zNear
		if zOffset > 800:
			zOffset = 800

		# Set the new rotation point and focal distance
		self.rotationPoint = ( x, y, z )
		self.focalDistance = zOffset

		# Set the camera position
		self.position.x = x
		self.position.y = y
		self.position.z = z + zOffset

	def updatePosition( self ):

		""" Updates the position of the camera, based on the centerpoint for 
			rotation, distance from that point, and current rotation values. 
			This translates sphere coordinates into world space coordinates. """

		radsX = math.radians( self.rotationX ) # Latitude
		radsY = math.radians( self.rotationY ) # Longitude
		self.position.x = self.rotationPoint[0] + self._focalDistance * math.sin( radsX ) * math.cos( radsY )
		self.position.y = self.rotationPoint[1] + self._focalDistance * math.cos( radsX )
		self.position.z = self.rotationPoint[2] + self._focalDistance * math.sin( radsX ) * math.sin( radsY )

	def updateOrientation( self, invert=False ):
		
		""" Updates the vectors tracking forward/right/up orientations. 
			Should be called any time either rotation value is changed. """

		# Create a vector between the camera position and target object
		self.forwardVector = Vector( self.position.x - self.rotationPoint[0], 
									 self.position.y - self.rotationPoint[1], 
									 self.position.z - self.rotationPoint[2] )
		self.forwardVector.normalize()

		# Calculate the right vector (perpendicular to the plane formed by forward and strait up)
		self.rightVector = Vector( y=1.0 ).crossProduct( self.forwardVector )
		self.rightVector.normalize()
		if invert:
			self.rightVector.x *= -1.0

		# Calculate the up vector (perpendicular to the plane of forward and right)
		self.upVector = self.forwardVector.crossProduct( self.rightVector )
		self.upVector.normalize()
		if invert:
			self.upVector.y *= -1.0

	def on_mouse_scroll( self, event ):

		""" Zoom in or out by moving the camera and rotation point forward or back, relative to
			the camera's facing direction. If right-click is held, then only the focal distance 
			will be updated, which will move the camera closer/further from the rotation point. 
			If self.defaultToAltZoom = True, methods for right-click behavior will be reversed. """

		rightClickHeld = event.state & 1024
		shiftHeld = event.state & 1

		if self.defaultToAltZoom:
			# Invert the determination to change which method is used
			rightClickHeld = not rightClickHeld

		# Update focal distance (distance from the camera to the rotation point)
		if rightClickHeld:
			# Zoom in/out by adjusting focal point only
			if event.delta > 0:
				# Zoom in
				if shiftHeld:
					self.focalDistance *= .88
				else:
					self.focalDistance *= .94
				if self._focalDistance < 2:
					self.focalDistance = 2
			elif event.delta < 0:
				# Zoom out
				if shiftHeld:
					self.focalDistance *= 1.12
				else:
					self.focalDistance *= 1.06

			# Update position with the new focal distance (sphere radius)
			self.updatePosition()
		else:
			# Right-click is not held. Move both the camera and rotation point forward/back in space
			speedMultiplier = ( shiftHeld * 2 ) + 1 # Results in 1 or 2
			if event.delta > 0:
				# Zoom in
				movementAmount = self.stepSize * -3.5 * speedMultiplier
			elif event.delta < 0:
				# Zoom out
				movementAmount = self.stepSize * 3.5 * speedMultiplier

			# Calculate translation to move the camera in line with its forward direction
			translateX = self.forwardVector.x * movementAmount
			translateY = self.forwardVector.y * movementAmount
			translateZ = self.forwardVector.z * movementAmount

			# Update the camera position
			self.position.x += translateX
			self.position.y += translateY
			self.position.z += translateZ

			# Update the rotation point coordinates (moving it with camera position)
			newX = self.rotationPoint[0] + translateX
			newY = self.rotationPoint[1] + translateY
			newZ = self.rotationPoint[2] + translateZ
			self.rotationPoint = ( newX, newY, newZ )

		self.engine.window.updateRequired = True

	def on_mouse_drag( self, *args ):

		""" Handles mouse input for rotation and panning of the scene. 
			buttons = Bitwise combination of the mouse buttons currently pressed. 
			modifiers = Bitwise combination of any keyboard modifiers currently active. """

		# Grab the event arguments (excluding x and y coords)
		if not args:
			return
		dx, dy, buttons, modifiers = args[2:]

		if buttons == 1: # Left-click button held; rotate the model
			self.rotationX += dy
			self.rotationY += dx
			# https://en.wikipedia.org/wiki/Transformation_matrix#Examples_in_3D_computer_graphics 		#todo
			# http://n64devkit.square7.ch/tutorial/graphics/6/6_4.htm

			# Constrain input
			self.rotationX = self.rotationX % 360
			self.rotationY = self.rotationY % 360
			if self.rotationX == 0: # Model will disappear at this angle
				self.rotationX = 0.1

			# Allow the camera to flip upside down to follow the model rotation
			if self.rotationX > 180:
				invert = True
			else:
				invert = False

			self.updatePosition()
			self.updateOrientation( invert )

			# Allow the camera to flip upside down to follow the model rotation
			if self.rotationX > 180:
				if self.upVector.y > 0:
					self.upVector.y = -1.0 * self.upVector.y
			elif self.upVector.y < 0:
				# Less than 180 degrees and camera is upside down. Make the y value positive again
				self.upVector.y = -1.0 * self.upVector.y

		elif buttons == 4: # Right-click button held; translate the camera
			# Determine how far to move per step
			shiftHeld = modifiers & 1
			speedMultiplier = ( shiftHeld * 2 ) + 1 # Results in 1 or 2
			stepSize = ( self.stepSize / 3.0 ) * speedMultiplier
			amountRight = -dx * stepSize
			amountUp = -dy * stepSize

			# Calculate translation to move the camera perpendicular to its forward direction
			translateX = self.rightVector.x * amountRight + self.upVector.x * amountUp
			translateY = self.rightVector.y * amountRight + self.upVector.y * amountUp
			translateZ = self.rightVector.z * amountRight + self.upVector.z * amountUp

			# Update the camera position
			self.position.x += translateX
			self.position.y += translateY
			self.position.z += translateZ

			# Update the rotation point coordinates (moving it parallel to camera position)
			newX = self.rotationPoint[0] + translateX
			newY = self.rotationPoint[1] + translateY
			newZ = self.rotationPoint[2] + translateZ
			self.rotationPoint = ( newX, newY, newZ )

		self.engine.window.updateRequired = True

	def on_mouse_release( self, x, y, button, modifiers ):

		# Only operate on right-click release
		if button != 4:
			return
		elif not DEBUGMODE:
			return

		# Show the new position of the rotation point
		self.engine.addEdge( [self.rotationPoint[0]-2,self.rotationPoint[1],self.rotationPoint[2], self.rotationPoint[0]+2,self.rotationPoint[1],self.rotationPoint[2]], (255, 0, 0, 255), tags=('originMarker',), thickness=2 )
		self.engine.addEdge( [self.rotationPoint[0],self.rotationPoint[1]-2,self.rotationPoint[2], self.rotationPoint[0],self.rotationPoint[1]+2,self.rotationPoint[2]], (0, 255, 0, 255), tags=('originMarker',), thickness=2 )
		self.engine.addEdge( [self.rotationPoint[0],self.rotationPoint[1],self.rotationPoint[2]-2, self.rotationPoint[0],self.rotationPoint[1],self.rotationPoint[2]+2], (0, 0, 255, 255), tags=('originMarker',), thickness=2 )

	# def toWorldSpace( self, x, y, z ):

	# 	theta_x = math.radians( self.engine.rotation_X )  # Angle for rotation around the x-axis (45 degrees)
	# 	theta_y = math.radians( self.engine.rotation_Y )

	# 	# Rotation around the x-axis
	# 	new_x = x
	# 	new_y = y * math.cos(theta_x) - z * math.sin(theta_x)
	# 	new_z = y * math.sin(theta_x) + z * math.cos(theta_x)

	# 	# Rotation around the y-axis
	# 	final_x = new_x * math.cos(theta_y) + new_z * math.sin(theta_y)
	# 	final_y = new_y
	# 	final_z = -new_x * math.sin(theta_y) + new_z * math.cos(theta_y)

	# 	return final_x, final_y, final_z


class Vector( object ):

	def __init__( self, x=0, y=0, z=0 ):
		self.x = x
		self.y = y
		self.z = z

	def __iter__( self ):

		""" Allows this object's properties to be expanded using the * operator. """

		return iter( (self.x, self.y, self.z) )

	def normalize( self ):

		""" Normalize into a unit vector. """

		magnitude = math.sqrt( self.x**2 + self.y**2 + self.z**2 )

		self.x = self.x / magnitude
		self.y = self.y / magnitude
		self.z = self.z / magnitude

	def subtract( self, vectorB ):
		return [ self.x - vectorB.x, self.y - vectorB.y, self.z - vectorB.z ]

	def crossProduct( self, vectorB ):
		
		""" Calculates a vector product between this vector and another given vector,
			and returns a new vector perpendicular to these. """

		Ax, Ay, Az = self.x, self.y, self.z
		Bx, By, Bz = vectorB.x, vectorB.y, vectorB.z

		Cx = (Ay * Bz) - (Az * By)
		Cy = (Az * Bx) - (Ax * Bz)
		Cz = (Ax * By) - (Ay * Bx)
		# Cx = (Az * By) - (Ay * Bz)
		# Cy = (Ax * Bz) - (Az * Bx)
		# Cz = (Ay * Bx) - (Ax * By)

		return Vector( Cx, Cy, Cz )
	
	def rotate( self, x=0, y=0, z=0 ):

		""" The x, y, and z arguments define which axis to rotate around, 
			and by how many degrees. """
		
		if z: # Yaw
			theta_z = math.radians( z )

			self.x = self.x * math.cos(theta_z) - self.y * math.sin(theta_z)
			self.y = self.x * math.sin(theta_z) + self.y * math.cos(theta_z)

		if x: # Pitch
			theta_x = math.radians( x )
			
			self.y = self.y * math.cos(theta_x) - self.z * math.sin(theta_x)
			self.z = self.y * math.sin(theta_x) + self.z * math.cos(theta_x)

		if y: # Roll
			theta_y = math.radians( y )

			self.x = self.x * math.cos(theta_y) + self.z * math.sin(theta_y)
			self.z = -self.x * math.sin(theta_y) + self.z * math.cos(theta_y)

	def getAngle( self, vectorB ):

		""" Calculates and returns the angle (in degrees) between this 
			vector and another given vector. """

		dot_product = sum( a * b for a, b in zip(self, vectorB) )
		magnitude1 = math.sqrt( sum(a**2 for a in self) )
		magnitude2 = math.sqrt( sum(b**2 for b in vectorB) )
		
		cos_theta = dot_product / ( magnitude1 * magnitude2 )
		
		# Ensure cos_theta is within the valid range [-1, 1]
		cos_theta = max( min(cos_theta, 1.0), -1.0 )
		
		# Calculate the angle in radians and convert to degrees
		angle_radians = math.acos( cos_theta )
		angle_degrees = math.degrees( angle_radians )

		return angle_degrees


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
	
	def contains( self, point ):

		""" Returns True if the given point is on this plane. """

		return self.equation( point ) == 0


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

		if primType == 0xB8: primitiveType = gl.GL_POINTS				# 0
		elif primType == 0xA8: primitiveType = gl.GL_LINES				# 1
		elif primType == 0xB0: primitiveType = gl.GL_LINE_STRIP			# 3
		elif primType == 0x90: primitiveType = gl.GL_TRIANGLES			# 4
		elif primType == 0x98: primitiveType = gl.GL_TRIANGLE_STRIP		# 5
		elif primType == 0xA0: primitiveType = gl.GL_TRIANGLE_FAN		# 6
		elif primType == 0x80: primitiveType = gl.GL_QUADS				# 7
		#elif primType == 0x88: primitiveType = gl.GL_QUADS				# 7
		else: # Failsafe
			print( 'Warning! Invalid primitive type detected: 0x{:X}'.format(primType) )
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
			self.texCoords = renderGroup.updateTexCoords( self.texCoords )

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
		self.renderState = 'normal'

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

		""" Sets rendering context (OpenGL state) for primitives using this group,
			and sets values in the shader if it is being used. """

		# Set values in the shader if it's in use
		if self.renderEngine.fragmentShader:
			self.renderEngine.setShaderInt( 'useVertexColors', self.useVertexColors )
			if self.renderState == 'normal':
				self.renderEngine.setShaderInt( 'renderState', 0 )
			else: # dim
				self.renderEngine.setShaderInt( 'renderState', 1 )

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
			self.renderEngine.setShaderInt( 'renderState', 0 )

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
		self.mipmaps = []
		self.texture = self.getPygletTexture( initialTexture )

		# Perform material initialization and set material properties
		super( TexturedMaterial, self ).__init__( renderEngine, initialTexture.mobj )

		self._setTexProperties()

	def _setTexProperties( self ):

		""" Checks a few properties from the texture's TObj struct, 
			and prepares wrap modes and repeat properties for render. """

		tobj = self.textures[self.index].tobj
		tobjValues = tobj.getValues()
		self.texFlags = tobj.flags

		self.texGenSrc = tobjValues[3]
		self.matrix = tobj.buildLocalInverseMatrix()
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
			self.lodBias = lodValues[1] # Should be between -4.0 to 3.99 (validate?)
			#self.lodBias, self.biasClamp, self.edgeLodEnable = lodValues[1:4] # LOD Bias should be between -4.0 to 3.99 (validate?) #todo
			self.anisotrophy = GXAnisotropy[lodValues[5]]

			# Check the image data header to get Min/Max LOD
			imgHeaderClass = globalData.fileStructureClasses['ImageObjDesc']
			imgHeader = tobj.dat.initSpecificStruct( imgHeaderClass, tobjValues[21], tobj.offset )
			isMipmap, self.minLOD, self.maxLOD = imgHeader.getValues()[-3:]
			if not isMipmap:
				print( 'WAT' )
				print( "{} references a LOD struct, but the image description claims it's not a mipmap texture!".format(tobj.name) )
		else:
			self.minFilter = gl.GL_LINEAR
			self.lodBias = 0.0
			self.anisotrophy = 0.0
			self.minLOD, self.maxLOD = 0.0, 0.0
		
		# Check for a TEV struct
		#tevObjClass = globalData.fileStructureClasses['TevObjDesc']
		#tevStruct = self.dat.initSpecificStruct( tevObjClass, tobjValues[24], tobj.offset, printWarnings=False )

	def getPygletTexture( self, textureObj ):

		""" Checks for a texture that has already been converted to a Pyglet image 
			in the render engine's cache and returns it if found. If not available, 
			the texture is converted and saved into the cache. """

		# Check if this one is available in the cache
		texture = self.renderEngine.textureCache.get( textureObj.offset )

		# Convert the texture and save it in the cache if not already available
		if not texture:
			texture = self._convertTexObject( textureObj )

		return texture

	def _convertTexObject( self, textureObj ):

		""" Gets the given texture (struct) object from the game's 
			native texture format and converts it to a pyglet image. """

		# Decode the texture
		width, height = textureObj.width, textureObj.height
		imageDataOffset = textureObj.offset
		imageDataLength = textureObj.imageDataLength
		imageDataClass = globalData.fileStructureClasses['ImageDataBlock']
		pilImage = textureObj.dat.getTexture( imageDataOffset, width, height, textureObj.imageType, imageDataLength, getAsPilImage=True )

		lodLevel = 0
		self.mipmaps = []
		level0Image = None

		while pilImage:
			# Convert it for use with pyglet
			pygletImage = pyglet.image.ImageData( width, height, 'RGBA', pilImage.tobytes() )
			texture = pygletImage.get_texture()
			texture.data = pygletImage.get_data()
			texture.level = lodLevel

			# Save in the cache for future lookup
			self.renderEngine.textureCache[imageDataOffset] = texture
			if not level0Image:
				assert lodLevel == 0, 'Unable to convert the root texture for {}!'.format( textureObj.name )
				level0Image = texture

			# Check for mipmap textures to convert
			if lodLevel >= textureObj.maxLOD:
				break
			else:
				# Calculate new info for the next image
				imageDataOffset += imageDataLength # This is of the last image, not the current imageDataLength below
				width = int( math.ceil(width / 2.0) )
				height = int( math.ceil(height / 2.0) )
				imageDataLength = imageDataClass.getDataLength( width, height, textureObj.imageType )

				# Process the new image
				pilImage = textureObj.dat.getTexture( imageDataOffset, width, height, textureObj.imageType, imageDataLength, getAsPilImage=True )
				self.mipmaps.append( imageDataOffset )
				lodLevel += 1

		return level0Image
	
	def changeTextureIndex( self, index ):

		""" Switches the current texture to a different one 
			in this group, converting it if needed. """

		assert index >= 0 and index < len( self.textures ), 'Texture group index out of range! {}'.format( index )

		# Get the current texture object in use by this group
		self.index = index
		textureObj = self.textures[index]

		# Set the image (convert to pyglet texture if needed) and update texture properties
		self.texture = self.getPygletTexture( textureObj )
		self._setTexProperties()

	def updateTexCoords( self, texCoords ):

		""" Updates/fixes texture coordinates for particular cases. Specifically:
		
				- Textures with dimensions that are not a power of 2 will have padding 
				  (blank texture space) added by OpenGL when loaded, which requires ST 
				  texture coordinates to compensate for the new texture dimensions. 
				- Textures which repeat will need to have their coordinates expanded out
				  of the usual -1.0 to 1.0 coordinate range.
		"""

		textureObj = self.textures[self.index]
		width, height = textureObj.width, textureObj.height

		# Check texture width/height for non-power of 2 dimensions
		if width & ( width - 1 ) != 0:
			# Not a power of 2; coordinates need adjusting
			nextPow2 = 1 << ( width - 1 ).bit_length()
			xAdjustment = float( width ) / nextPow2 * self.repeatS
		else:
			# Width is a power of 2
			xAdjustment = self.repeatS
		if height & ( height - 1 ) != 0:
			# Not a power of 2; coordinates need adjusting
			nextPow2 = 1 << ( height - 1 ).bit_length()
			yAdjustment = float( height ) / nextPow2 * self.repeatT
		else:
			# Height is a power of 2
			yAdjustment = self.repeatT

		# Adjust x/y texture coordinates, if needed
		if xAdjustment != 1:
			newCoords = [ coord * xAdjustment if i % 2 == 0 else coord for i, coord in enumerate(texCoords[1]) ]
			texCoords = ( texCoords[0], newCoords )
		if yAdjustment != 1:
			newCoords = [ coord * yAdjustment if i % 2 == 1 else coord for i, coord in enumerate(texCoords[1]) ]
			texCoords = ( texCoords[0], newCoords )

		return texCoords

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
		gl.glBindTexture( self.texture.target, self.texture.id )
		if self.mipmaps:
			# Add the base (level 0) texture (updates the currently bound texture)
			gl.glTexImage2D( gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, self.texture.width, self.texture.height, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, self.texture.data )

			# Add subsequent mipmap levels (updates the currently bound texture)
			for offset in self.mipmaps:
				texture = self.renderEngine.textureCache.get( offset )
				gl.glTexImage2D( gl.GL_TEXTURE_2D, texture.level, gl.GL_RGBA, texture.width, texture.height, 0, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, texture.data )

			# Set mipmap (LOD) parameters
			gl.glTexParameterf( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_LOD, self.minLOD )
			gl.glTexParameterf( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAX_LOD, self.maxLOD )
			gl.glTexParameterf( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_LOD_BIAS, self.lodBias )
			gl.glTexParameterf( gl.GL_TEXTURE_2D, gl.glext_arb.GL_TEXTURE_MAX_ANISOTROPY_EXT, self.anisotrophy )

		# Update the fragment shader
		if self.renderEngine.fragmentShader:
			self.renderEngine.setShaderInt( 'texGenSource', self.texGenSrc )
			self.renderEngine.setShaderInt( 'enableTextures', True )
			self.renderEngine.setShaderInt( 'textureFlags', self.texFlags )
			self.renderEngine.setShaderFloat( 'textureBlending', self.blending )
			self.renderEngine.setShaderMatrix( 'textureMatrix', self.matrix )

		# Texture filtering
		gl.glTexParameteri( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, self.minFilter )
		gl.glTexParameteri( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, self.magFilter )

		# Wrap mode
		gl.glTexParameteri( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, self.wrapModeS )
		gl.glTexParameteri( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, self.wrapModeT )

	def unset_state( self ):

		""" Clears/resets rendering context (OpenGL state) for primitives 
			using this group and its parent material group. """

		# Unet states for the material
		super( TexturedMaterial, self ).unset_state()
		
		# Unset states for this texture
		if self.enableTextures:
			#gl.glDisable( self.texture.target )

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