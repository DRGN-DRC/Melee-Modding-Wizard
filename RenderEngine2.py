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
from pyglet.window import key
from pyglet.app.base import EventLoop
from pyglet.window.event import WindowEventLogger
from pyglet.window import Window as pygletWindow

import globalData


class RenderEngine( Tk.Frame ):

	""" This module creates a pyglet rendering environment (a window), and embeds
		it into a Tkinter frame for incorporation into the larger GUI. """
	
	def __init__( self, parent, dimensions=(640, 480), resizable=False, *args, **kwargs ):

		Tk.Frame.__init__( self, parent, background='black' )

		self.width = dimensions[0]
		self.height = dimensions[1]

		# Create a Tkinter canvas to hold the Pyglet window's canvas
		self.canvas = Tk.Canvas( self, width=self.width, height=self.height )
		self.canvas.pack()

		# Create an invisible Pyglet window (cannot create a canvas without a window)
		display = pyglet.canvas.get_display()
		screen = display.get_default_screen()
		config = screen.get_matching_configs( gl.Config(double_buffer=True, depth_size=8, alpha_size=8) )[0]
		self.window = pygletWindow( display=display, config=config, width=self.width, height=self.height, resizable=resizable, visible=False )
		self.window.on_draw = self.on_draw
		# openGlVersion = self.window.context._info.get_version().split()[0]
		# print( 'Rendering with OpenGL version {}'.format(openGlVersion) )

		# Set the pyglet parent window to be the tkinter canvas
		GWLP_HWNDPARENT = -8
		pyglet_handle = self.window.canvas.hwnd
		win32api.SetWindowLong( pyglet_handle, GWLP_HWNDPARENT, self.canvas.winfo_id() )
		
		# Set up the OpenGL context
		#gl.glClearColor( 0, 0, 0, 1 )
		# gl.glEnable( gl.GL_DEPTH_TEST ) # Do depth comparisons and update the depth buffer
		# gl.glEnable( gl.GL_LINE_SMOOTH ) # Anti-aliasing
		# gl.glEnable( gl.GL_BLEND )
		# gl.glLineWidth( 3 ) # Set edge width to 3 pixels
		# gl.glEnable( gl.GL_ALPHA_TEST )
		# gl.glDepthFunc( gl.GL_LEQUAL )
		# gl.glMatrixMode( gl.GL_PROJECTION )
		# gl.glLoadIdentity()
		# gl.gluPerspective( 60, float(self.width) / float(self.height), 0.1, 100.0 )
		#gl.glMatrixMode( gl.GL_MODELVIEW )
		#gl.glTranslatef( 0, 0, -5 )

		# self.vertices = ( 'v3f', [] )
		# self.vertexColors = ( 'c3B', [] )
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

		if resizable:
			self.bind( "<Configure>", self.resizeViewport )

		# Set up event handling for controls
		self.window.on_mouse_drag = self.on_mouse_drag
		self.master.bind( '<KeyPress>', self.on_key_press )
		self.master.bind( "<MouseWheel>", self.zoom )
		# self.master.bind( "<Motion>", self.rotate ) # Mouse motion with Left-Click held down
		# self.master.bind( "<B3-Motion>", self.pan ) # Mouse motion with Right-Click held down

		# Start the event loop
		pyglet.app.event_loop = CustomEventLoop( globalData.gui.root )
		pyglet.app.event_loop.run()

		# Move focus to the parent window (will initially be the pyglet window by default)
		self.master.after( 1, lambda: self.master.focus_force() )

	def addEdge( self, vertices, color=None, colors=(), tags=(), hidden=False ):

		""" Translates given points into a series of data points (edges) to be batch-rendered. 
			The edgePoints arg should be a list of tuples, where each tuple contains 6 values 
			(2 sets of x/y/z coords). """

		if len( vertices ) != 6:
			print( 'Incorrect number of points given to create an edge: ' + str(vertices) )
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

	def resetView( self ):
		
		self.maxZoom = 200

		self.scale = 1.0
		self.rotation_X = 0
		self.rotation_Y = 0

		self.translation_X = 0.0
		self.translation_Y = 0.0
		self.translation_Z = 0.0

	def zoom( self, event ):

		scroll_y = event.delta / 30

		if scroll_y > 0: # zoom in
			self.scale *= 1.09
		elif scroll_y < 0: # zoom out
			self.scale /= 1.09

	def on_key_press( self, symbol ):

		print(symbol)

		if symbol == key.R:
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
		gl.glClearColor( 0, 0, 0, 1 )
		gl.glClear( gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT )

		gl.glEnable( gl.GL_DEPTH_TEST ) # Do depth comparisons and update the depth buffer
		gl.glDepthFunc( gl.GL_LEQUAL )
		gl.glEnable( gl.GL_ALPHA_TEST )
		gl.glEnable( gl.GL_BLEND )
		gl.glBlendFunc( gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA )
		gl.glHint(gl.GL_MULTISAMPLE_FILTER_HINT_NV, gl.GL_NICEST)
		gl.glEnable( gl.GL_LINE_SMOOTH ) # Anti-aliasing
		gl.glEnable( gl.GL_MULTISAMPLE )
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

	def showPart( self, tag, visible, primitive=None ):

		if primitive == 'edge':
			objects = self.edges
		elif primitive == 'triangle':
			objects = self.triangles
		elif primitive == 'quad':
			objects = self.quads
		else:
			if primitive:
				print( 'Warning; unrecognized primitive: ' + str(primitive) )
			objects = self.edges + self.triangles + self.quads

		for obj in objects:
			if tag in obj.tags:
				obj.hidden = not visible

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

	def stop( self ):

		""" Before exiting, we need to let the event loop end peacefully, 
			so it doesn't try to update anything that doesn't exist and crash. """

		# Allow the next iteration of the loop to continue, 
		# but modify it to call this method again once it's done.
		el = pyglet.app.event_loop
		if el.is_running and el.step != el.stop:
			el.is_running = False
			el.has_exit = True
			el.step = self.stop
			return

		self.window.close()


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

		for window in pyglet.app.windows:
			# Set context/render focus to this window
			window.switch_to()

			# Queue handling mouse input and drawing (updating) the canvas
			#window.dispatch_events()
			window.dispatch_event('on_mouse_drag')
			window.dispatch_event('on_draw')
			
			# Swap the display buffers to show the rendered image
			window.flip()

		# Re-queue for the next frame
		self.root.after( 17, self.step )

	def stop( self ):

		""" The typical end to the pyglet 'run' method. """

		self.is_running = False
		self.has_exit = True

		# self.dispatch_event('on_exit')
		# platform_event_loop = pyglet.app.platform_event_loop
		# platform_event_loop.stop()


class Vertex:
	def __init__( self, coords, color=(128, 128, 128), tags=(), hidden=False ):
		#store x, y, z coordinates
		self.x = coords[0]
		self.y = coords[1]
		self.z = coords[2]
		self.color = color
		self.tags = tags
		self.hidden = hidden


class ShapeBase:

	@staticmethod
	def interpretColors( pointCount, color, colors ):

		if color:
			# A single color was given
			colors = color[:3] * pointCount
		elif not colors:
			# No colors given; default to gray
			colors = ( 128, 128, 128 ) * pointCount
		elif len( colors ) == 1:
			# A single color given; copy it for all points
			colors = ( colors[0][:3] ) * pointCount
		elif pointCount != len( colors ):
			# Ehh?
			print( 'Warning! Unexpected number of colors given to add edges: ' + str(colors) )
			colors = ( colors[0][:3] ) * pointCount

		return colors


class Edge( ShapeBase ):

	def __init__( self, vertices, color=None, colors=(), tags=(), hidden=False ):
		self.vertices = ( 'v3f', vertices )
		self.vertexColors = ( 'c3B', self.interpretColors( 2, color, colors ) )
		self.tags = tags
		self.hidden = hidden
	
	def render( self, batch ):
		if not self.hidden:
			batch.add( 2, gl.GL_LINES, None, self.vertices, self.vertexColors )


# class Triangle( ShapeBase ):

# 	def __init__( self ):
# 		self.vertices = pyglet.graphics.vertex_list( 3, ('v3f', [-0.5,-0.5,0.0, 0.5,-0.5,0.0, 0.0,0.5,0.0]),
# 														('c3B', [100,200,250, 200,110,110, 100,250,100]) )


class Quad( ShapeBase ):

	def __init__( self, vertices, color=None, colors=(), tags=(), hidden=False ):
		self.vertices = ( 'v3f', vertices )
		self.vertexColors = ( 'c3B', self.interpretColors( 4, color, colors ) )
		self.tags = tags
		self.hidden = hidden
	
	def render( self, batch ):
		if not self.hidden:
			batch.add( 4, gl.GL_QUADS, None, self.vertices, self.vertexColors )