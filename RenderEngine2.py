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
		self.window = pyglet.window.Window( display=display, width=self.width, height=self.height, resizable=resizable, visible=False )
		
		#self.window.switch_to()

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
		self.rotation = 0

		if resizable:
			self.bind( "<Configure>", self.resize )

		# schedule a function to be called periodically
		self.window.dispatch_events()
		globalData.gui.root.after( 0, self.update )

	# def startEventLoop( self ):
	# 	""" The event loop thread function. Do not override or call
	# 		directly (it is called by __init__). """
		
	# 	# gl_lock = Lock()
	# 	# gl_lock.acquire()
	# 	try:
	# 		display = pyglet.canvas.get_display()
	# 		self.window = pyglet.window.Window( display=display, width=self.width, height=self.height, resizable=False, visible=True )
	# 		self.window.switch_to()
	# 		self.window.setup()
	# 		pyglet.app.run()
	# 	except Exception as e:
	# 		print( "Window initialization failed: %s" % (str(e)) )
	# 	# gl_lock.release()

	def update(self):
		self.window.clear()
		# Render 3D scene here

		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
		glLoadIdentity()
		glTranslatef(0, 0, -5)
		glRotatef(self.rotation, 1, 1, 1)

		self.vertices.draw(GL_QUADS)

		# Swap the display buffers to show the rendered image
		self.window.flip()

		self.rotation += 1
		globalData.gui.root.after(17, self.update)

	# #@self.event
	# def on_key_press(self, symbol, modifiers):
	# 	if symbol == key.A:
	# 		print('The "A" key was pressed.')
	# 	elif symbol == key.LEFT:
	# 		print('The left arrow key was pressed.')
	# 	elif symbol == key.ENTER:
	# 		print('The enter key was pressed.')

	def resize(self, event):
		# resize the Pyglet window when the Tkinter frame is resized
		self.width = event.width
		self.height = event.height

		#self.window.set_size(self.width, self.height)
		self.canvas['width'] = self.width
		self.canvas['height'] = self.height

	def stop( self ):

		if self.update != self.stop:
			self.update = self.stop
			return

		self.window.close()
