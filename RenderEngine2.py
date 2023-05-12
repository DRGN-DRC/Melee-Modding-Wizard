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

import ttk
import time
import pyglet
import win32api
import Tkinter as Tk

from pyglet import gl
from pyglet.window import key, Projection3D
from pyglet.app.base import EventLoop
from pyglet.window.event import WindowEventLogger
from pyglet.window import Window as pygletWindow

import globalData


class RenderEngine( Tk.Frame ):

	""" This module creates a pyglet rendering environment (a window), and embeds
		it into a Tkinter frame for incorporation into the larger GUI. """
	
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
		config = screen.get_matching_configs( gl.Config(double_buffer=True, depth_size=8, alpha_size=8) )[0]
		self.window = pygletWindow( display=display, config=config, width=self.width, height=self.height, resizable=resizable, visible=False )
		#self.window.projection = Projection3D(  ) #todo
		self.window.on_draw = self.on_draw
		# openGlVersion = self.window.context._info.get_version().split()[0]
		# print( 'Rendering with OpenGL version {}'.format(openGlVersion) )

		# Set the pyglet parent window to be the tkinter canvas
		GWLP_HWNDPARENT = -8
		pyglet_handle = self.window.canvas.hwnd
		win32api.SetWindowLong( pyglet_handle, GWLP_HWNDPARENT, self.canvas.winfo_id() )
		
		# Set up the OpenGL context
		gl.glEnable( gl.GL_DEPTH_TEST ) # Do depth comparisons and update the depth buffer
		gl.glDepthFunc( gl.GL_LEQUAL )
		gl.glEnable( gl.GL_ALPHA_TEST )
		gl.glEnable( gl.GL_BLEND )
		#gl.glBlendFunc( gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA )
		gl.glEnable( gl.GL_LINE_SMOOTH ) # Anti-aliasing
		gl.glEnable( gl.GL_POLYGON_SMOOTH )
		gl.glEnable( gl.GL_MULTISAMPLE )
		try:
			gl.glEnable( gl.GL_MULTISAMPLE_ARB )
		except pyglet.gl.GLException:
			print( "Warning: Anti-aliasing is not supported on this computer." )

		self.vertices = []
		self.edges = []
		self.triangles = []
		self.quads = []

		self.resetView()

		# self.vertices = pyglet.graphics.vertex_list( 8,
		# 	('v3f', [-0.5,-0.5,-0.5, 0.5,-0.5,-0.5, 0.5,0.5,-0.5, -0.5,0.5,-0.5, -0.5,-0.5,0.5, 0.5,-0.5,0.5, 0.5,0.5,0.5, -0.5,0.5,0.5]),
		# 	('c3B', [255,0,0, 255,255,0, 0,255,0, 0,0,255, 255,0,255, 255,255,255, 0,255,255, 128,128,128])
		# )

		# quad_vertices = ('v2f', [100, 100, 200, 100, 200, 200, 100, 200])
		# line_vertices = ('v2f', [50, 50, 200, 200])
		# triangle_vertices = ('v2f', [300, 100, 350, 200, 250, 200])

		# self.quad_batch = pyglet.graphics.vertex_list(4, quad_vertices)
		# self.line_batch = pyglet.graphics.vertex_list(2, line_vertices)
		# self.triangle_batch = pyglet.graphics.vertex_list(3, triangle_vertices)

		#self.pack_propagate( False )

		# Set up event handling for controls
		#self.window._enable_event_queue = True
		self.window.on_mouse_drag = self.on_mouse_drag
		#self.window.on_key_press = self.on_key_press
		#self.window.on_mouse_scroll = self.on_mouse_scroll 	# doesn't work!?
		self.window.on_mouse_scroll = self.zoom
		self.master.bind( "<MouseWheel>", self.zoom )
		self.master.bind( '<KeyPress>', self.on_key_press )
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

	def resetView( self ):
		
		self.maxZoom = 200

		self.scale = 1.0
		self.rotation_X = 0
		self.rotation_Y = 0

		self.translation_X = 0.0
		self.translation_Y = 0.0
		self.translation_Z = 0.0

	def resizeViewport( self, event ):

		""" Updates the tkinter canvas and pyglet rendering canvas 
			when the Tkinter frame is resized. """
		
		self.width = event.width
		self.height = event.height

		self.canvas['width'] = self.width
		self.canvas['height'] = self.height

		# Update the pyglet rendering canvas
		gl.glViewport( 0, 0, self.width, self.height )
		self.window._update_view_location( self.width, self.height )

	def addVertex( self, vertices, color=(128, 128, 128, 255), tags=(), hidden=False ):

		if len( vertices ) != 3:
			print( 'Incorrect number of coordinates given to create a vertex: ' + str(vertices) )
			return None

		vertex = Vertex( vertices, color, tags, hidden )
		self.vertices.append( vertex )

		return vertex

	def addEdge( self, vertices, color=None, colors=(), tags=(), hidden=False ):

		""" Translates given points into a series of edges (lines) to be batch-rendered. 
			The given vertices should contain 6 values (2 sets of x/y/z coords). """

		if len( vertices ) != 6:
			print( 'Incorrect number of coordinates given to create an edge: ' + str(vertices) )
			return None

		edge = Edge( vertices, color, colors, tags, hidden )
		self.edges.append( edge )

		return edge

	# def addEdges( self, edgePoints, color=None, colors=(), tags=(), hidden=False ):

	# 	""" Translates given points into a series of data points (edges) to be batch-rendered. 
	# 		The edgePoints arg should be a list of tuples, where each tuple contains 6 values 
	# 		(2 sets of x/y/z coords). """

	# 	for vertices in edgePoints:
	# 		if len( vertices ) != 6:
	# 			print( 'Incorrect number of points given to create an edge: ' + str(vertices) )
	# 			continue
	# 		edge = Edge( vertices, color, colors, tags, hidden )
	# 		self.edges.append( edge )

	def addQuad( self, vertices, color=None, colors=(), tags=(), hidden=False ):

		if len( vertices ) != 12:
			print( 'Incorrect number of points given to create a quad: ' + str(vertices) )
			return None

		quad = Quad( vertices, color, colors, tags, hidden )
		self.quads.append( quad )

		return quad
	
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
			else:
				unknownObjects.append( prim )

		if unknownObjects:
			print( 'Unable to add unknown, non-primitive objects!:'.format(unknownObjects) )

	def renderJoint( self, joint ):

		""" Recursively scans the given joint and all child/next joints for 
			Display Objects and Polygon Objects. Breaks down Polygon Objects 
			into primitives and renders them to the display. """

		# Check for a polygon object to render
		dobj = joint.DObj
		if dobj:
			pobj = dobj.PObj
			if pobj:
				primitives = pobj.decodeGeometry()
				self.addPrimitives( primitives )

		# Check for a child joint to render
		childJoint = joint.initChild( 'JointObjDesc', 2 )
		if childJoint:
			self.renderJoint( childJoint )

		# Check for a 'next' joint to render
		nextJoint = joint.initChild( 'JointObjDesc', 3 )
		if nextJoint:
			self.renderJoint( nextJoint )

	def zoom( self, event ):
		#print( 'zoom' )
		if event.delta > 0: # zoom in
			self.scale *= 1.09
		elif event.delta < 0: # zoom out
			self.scale /= 1.09

	# def on_mouse_scroll( self, *args ):

	# 	print('zoom2' )
	# 	print(args)

	def on_key_press( self, *args ):

		#print( 'pressed ' + str(symbol) )
		if not args:
			return
		symbol, modifiers = args

		if symbol == key.R:
			print( 'resetting' )
			self.resetView()
		elif symbol == key.LEFT:
			print('The left arrow key was pressed.')
		elif symbol == key.ENTER:
			print('The enter key was pressed.')

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
			self.rotation_X += dx
			self.rotation_Y -= dy
		elif buttons == 4: # Right-click button held
			self.translation_X += dx / 5.0
			self.translation_Y += dy / 5.0
		# else: Multiple buttons held; do nothing and 
		# wait 'til the user gets their act together. :P

	def on_draw( self ):
		# Clear the screen
		gl.glClearColor( *self.bgColor )
		gl.glClear( gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT )
		gl.glLineWidth( 3 ) # Set edge widths to 3 pixels
		
		# Set the projection matrix to a perspective projection and apply translation (camera pan)
		gl.glMatrixMode( gl.GL_PROJECTION )
		gl.glLoadIdentity()
		gl.gluPerspective( 60, float(self.width) / self.height, 0.1, 1000 )
		gl.glTranslatef( self.translation_X, self.translation_Y, -self.maxZoom )

		# Set up the modelview matrix and apply transformations
		gl.glMatrixMode( gl.GL_MODELVIEW )
		gl.glLoadIdentity()
		gl.glRotatef( self.rotation_X, 0, 1, 0 )
		gl.glRotatef( self.rotation_Y, 1, 0, 0 )
		gl.glScalef( self.scale, self.scale, self.scale )
		
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

	def getObjects( self, primitive=None ):

		# Confine the search to improve performance
		if primitive == 'vertex':
			objects = self.vertices
		elif primitive == 'edge':
			objects = self.edges
		elif primitive == 'triangle':
			objects = self.triangles
		elif primitive == 'quad':
			objects = self.quads
		else:
			if primitive:
				print( 'Warning; unrecognized primitive: ' + str(primitive) )
			objects = self.vertices + self.edges + self.triangles + self.quads

		return objects

	def showPart( self, tag, visible, primitive=None ):

		for obj in self.getObjects( primitive ):
			if tag in obj.tags:
				obj.hidden = not visible

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

		else:
			if primitive:
				print( 'Warning; unrecognized primitive: ' + str(primitive) )

			self.vertices = []
			self.edges = []
			self.triangles = []
			self.quads = []

			for obj in self.getObjects( primitive ):
				if tag not in obj.tags:
					if isinstance( obj, Vertex ):
						self.vertices.append( obj )
					elif isinstance( obj, Edge ):
						self.edges.append( obj )
					elif isinstance( obj, Triangle ):
						self.triangles.append( obj )
					elif isinstance( obj, Quad ):
						self.quads.append( obj )

	def stop( self ):

		""" Before exiting, we need to let the event loop end peacefully, 
			so it doesn't try to update anything that doesn't exist and crash. """

		# Allow the next iteration of the loop to continue, 
		# but modify it to call this method again once it's done.
		# el = pyglet.app.event_loop
		# if el.is_running and el.step != self.stop:
		# 	el.is_running = False
		# 	el.has_exit = True
		# 	el.step = self.stop
		# 	return

		# self.window.close()
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


class Primitive:

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
		except Exception as err:
			print( 'Invalid color(s) given to create a primitive; {}'.format(err) )
			colors = defaultColor * pointCount

		return colors


class Vertex:
	def __init__( self, coords, color=(0, 0, 0, 255), tags=(), hidden=False, size=2 ):
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
		self.u = 0
		self.v = 0

		self.color = color
		self.tags = tags
		self.hidden = hidden
		self.size = size
	
	def render( self, batch ):
		if not self.hidden:
			gl.glPointSize( self.size )
			batch.add( 1, gl.GL_POINTS, None, ('v3f', (self.x, self.y, self.z)), ('c4B', self.color) )


class Edge( Primitive ):

	def __init__( self, vertices, color=None, colors=(), tags=(), hidden=False ):
		self.vertices = ( 'v3f', vertices )
		self.vertexColors = ( 'c4B', self.interpretColors( 2, color, colors ) )
		self.tags = tags
		self.hidden = hidden
	
	def render( self, batch ):
		if not self.hidden:
			batch.add( 2, gl.GL_LINES, None, self.vertices, self.vertexColors )


class Triangle( Primitive ):

	def __init__( self, vertices, color=None, colors=(), tags=(), hidden=False ):
		self.vertices = ( 'v3f', vertices )
		self.vertexColors = ( 'c4B', self.interpretColors( 3, color, colors ) )
		self.tags = tags
		self.hidden = hidden
	
	def render( self, batch ):
		if not self.hidden:
			batch.add( 3, gl.GL_TRIANGLES, None, self.vertices, self.vertexColors )


class Quad( Primitive ):

	def __init__( self, vertices, color=None, colors=(), tags=(), hidden=False ):
		self.vertices = ( 'v3f', vertices )
		self.vertexColors = ( 'c4B', self.interpretColors( 4, color, colors ) )
		self.tags = tags
		self.hidden = hidden
	
	def render( self, batch ):
		if not self.hidden:
			batch.add( 4, gl.GL_QUADS, None, self.vertices, self.vertexColors )