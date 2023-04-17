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
import pyglet
import win32api
import Tkinter as Tk

from pyglet.gl import *
from pyglet.window import key
from pyglet.app.base import EventLoop
from pyglet.window.event import WindowEventLogger
from pyglet.window import Window as pygletWindow

import globalData


class RenderEngine( ttk.Frame ):

	""" This module creates a pyglet rendering environment (a window), and embeds
		it into a Tkinter frame for incorporation into the larger GUI. """
	
	def __init__( self, parent, dimensions=(640, 480), resizable=False, *args, **kwargs ):

		ttk.Frame.__init__( self, parent )

		self.width = dimensions[0]
		self.height = dimensions[1]

		# Create a Tkinter canvas to hold the Pyglet window's canvas
		self.canvas = Tk.Canvas( self, width=self.width, height=self.height )
		self.canvas.pack()

		# Create an invisible Pyglet window (cannot create a canvas without a window)
		display = pyglet.canvas.get_display()
		self.window = pygletWindow( display=display, width=self.width, height=self.height, resizable=resizable, visible=False )
		#self.window.push_handlers( WindowEventLogger() )
		#self.window.remove
		#self.window.on_key_press = self.on_key_press

		# self.window.switch_to()
		# self.window.activate()

		# Set the pyglet parent window to be the tkinter canvas
		GWLP_HWNDPARENT = -8
		pyglet_handle = self.window.canvas.hwnd
		win32api.SetWindowLong( pyglet_handle, GWLP_HWNDPARENT, self.canvas.winfo_id() )
		
		# Set up the OpenGL context
		glClearColor(0, 0, 0, 1)
		glEnable(GL_DEPTH_TEST)
		glDepthFunc(GL_LEQUAL)
		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		gluPerspective(60, float(self.width) / float(self.height), 0.1, 100.0)
		glMatrixMode(GL_MODELVIEW)
		glTranslatef(0, 0, -3)

		# Schedule the update function to be called every 1/60 seconds
		#pyglet.clock.schedule_interval(self.update, 1.0/60.0)

		self.vertices = pyglet.graphics.vertex_list( 8,
			('v3f', [-1,-1,-1, 1,-1,-1, 1,1,-1, -1,1,-1, -1,-1,1, 1,-1,1, 1,1,1, -1,1,1]),
			('c3B', [255,0,0, 255,255,0, 0,255,0, 0,0,255, 255,0,255, 255,255,255, 0,255,255, 128,128,128])
		)

		self.scale = 1.0
		self.rotation = 0

		quad_vertices = ('v2f', (100, 100, 200, 100, 200, 200, 100, 200))
		line_vertices = ('v2f', (50, 50, 200, 200))
		triangle_vertices = ('v2f', (300, 100, 350, 200, 250, 200))

		self.quad_batch = pyglet.graphics.vertex_list(4, quad_vertices)
		self.line_batch = pyglet.graphics.vertex_list(2, line_vertices)
		self.triangle_batch = pyglet.graphics.vertex_list(3, triangle_vertices)

		if resizable:
			self.bind( "<Configure>", self.resize )

		# schedule a function to be called periodically
		#self.window.dispatch_events()
		# eventLoopStep = pyglet.app.event_loop.step
		# globalData.gui.root.after( 0, eventLoopStep )
		self.window.on_draw = self.on_draw
		parent.bind( '<KeyPress>', self.on_key_press )
		parent.bind( "<MouseWheel>", self.zoom )

		# self.bind( '<FocusIn>', self.on_focus )

		pyglet.app.event_loop = CustomEventLoop()
		pyglet.app.event_loop.run()

		parent.after( 1, lambda: parent.focus_force() )

	# def on_focus( self, event=None ):
	# 	print('refocusing')
	# 	self.window.switch_to()
	# 	self.window.activate()

	def zoom( self, event ):

		scroll_y = event.delta / 30

		if scroll_y > 0: # zoom in
			self.scale *= 1.05
		elif scroll_y < 0: # zoom out
			self.scale /= 1.05

		#print( 'new scale: ' + str(self.scale) )

	def on_draw(self):
		self.window.clear()
		
		# Render 3D scene here
		#glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
		#glLoadIdentity()
		#glTranslatef(0, 0, -5)
		#glRotatef(self.rotation, 1, 1, 1)

		#self.vertices.draw(GL_QUADS)
		


		# Swap the display buffers to show the rendered image
		#self.window.flip()
		 # set the projection matrix to a perspective projection

		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		gluPerspective(45, float(self.width) / self.height, 0.1, 1000)

		# set the modelview matrix to a scaled view
		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()
		glTranslatef(0, 0, -5)
		glRotatef(self.rotation, 1, 1, 1)
		glScalef(self.scale, self.scale, self.scale)

		self.vertices.draw(GL_QUADS)

		# self.quad_batch.draw(GL_QUADS)
		# self.line_batch.draw(GL_LINES)
		# self.triangle_batch.draw(GL_TRIANGLES)
		
		# draw some stuff
		#glColor3f(1, 0, 0)
		# glBegin(GL_TRIANGLES)
		# glVertex3f(-100, -100, 0)
		# glVertex3f(0, 100, 0)
		# glVertex3f(100, -100, 0)
		# glEnd()

		self.rotation += 1
		#globalData.gui.root.after(17, self.update)
		
		#globalData.gui.root.after( 17, pyglet.app.platform_event_loop.step )

	#@pygletWindow.event
	def on_key_press( self, symbol, modifiers):
		if symbol == key.A:
			print('The "A" key was pressed.')
		elif symbol == key.LEFT:
			print('The left arrow key was pressed.')
		elif symbol == key.ENTER:
			print('The enter key was pressed.')

	def resize(self, event):
		print('resizeing')
		# resize the Pyglet window when the Tkinter frame is resized
		self.width = event.width
		self.height = event.height

		#self.window.set_size(self.width, self.height)
		self.canvas['width'] = self.width
		self.canvas['height'] = self.height

		self.window.on_resize( self.width, self.height )

	def stop( self ):

		# if self.update != self.stop:
		# 	self.update = self.stop
		# 	return

		ev = pyglet.app.event_loop
		if ev.step != ev.stop:
			ev.step = ev.stop
			return

		#pyglet.app.event_loop.stop()
		
		# self.is_running = False
		# self.has_exit = True
		# self.dispatch_event('on_exit')
		# platform_event_loop = pyglet.app.platform_event_loop
		# platform_event_loop.stop()

		self.window.close()


class CustomEventLoop( EventLoop ):
	
	def run( self ):
		"""Begin processing events, scheduled functions and window updates.

		This method returns when :py:attr:`has_exit` is set to True.

		Developers are discouraged from overriding this method, as the
		implementation is platform-specific.
		"""
		self.has_exit = False
		self._legacy_setup()

		platform_event_loop = pyglet.app.platform_event_loop
		platform_event_loop.start()
		self.dispatch_event('on_enter')

		self.is_running = True
		#print('starting render loop')
		# legacy_platforms = ('XP', '2000', '2003Server', 'post2003')
		# if compat_platform == 'win32' and platform.win32_ver()[0] in legacy_platforms:
		# 	self._run_estimated()
		# else:
		# 	self._run()

		# self.is_running = False
		# self.dispatch_event('on_exit')
		# platform_event_loop.stop()

		pyglet.clock.tick()

		globalData.gui.root.after( 0, self.step )

	def step( self ):
		#print('stepping')
		#pyglet.app.platform_event_loop.step( 1000 )
		
		for window in pyglet.app.windows:
			window.switch_to()
			window.dispatch_events()
			window.dispatch_event('on_draw')
			window.flip()

		#if self.is_running and not self.has_exit:
		globalData.gui.root.after( 17, self.step )

	def stop( self ):

		# if self.step != self.stop:
		# 	self.step = self.stop
		# 	return

		self.is_running = False
		self.has_exit = True
		self.dispatch_event('on_exit')
		platform_event_loop = pyglet.app.platform_event_loop
		platform_event_loop.stop()

		#pyglet.app.exit()
