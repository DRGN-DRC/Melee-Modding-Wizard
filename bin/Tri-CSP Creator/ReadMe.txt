

Official thread:

	https://smashboards.com/threads/tri-csp-creator.448104/


This program can be used with the GUI, or by command line. When used via command line, it can be used in two different ways; either with a config file, or without. When running without providing a config file, size and position arguments for each image will need to be provided. In other words, the program has these three run modes:

    gui                 Run this program using a GUI, which can accept
                        optional arguments for image filepaths to pre-populate
                        those inputs. (default, if run without arguments)

    cmd                 Run this program via command line only, in which case
                        image paths and most other arguments are required. Run
                        "Tri-CSP-Creator.py cmd -h" to see a list of all
                        arguments.

    cmd-config          Run this program via command line only, using image
                        filepaths and one configuration filepath as arguments.


You can run '"Tri-CSP Creator.exe" cmd -h' to see all of the arguments required.




	Masks:

Whether using the GUI or command line, the purpose of masks is to block out extra content that may appear in some screenshots. For example, if you look at the costume screenshots for Falco or Sheik (for left/right alts, aka side poses), you'll notice other character costumes in some of them. (In these cases, this is because they were collected in bulk.) Such extra characters or items in the screenshot will appear in the finished CSP. For these, if you set one of the screenshots that DOES NOT have extra characters in it as the "mask", then that image will be the one used to determine outline selection, and will be used to cut-out the selections on the other side poses.



	Tips / Troubleshooting:

Make sure your in-game screenshots come out to be 1920x1080! If they are not these dimensions, TCC will not place the characters from them in the correct locations. You'll need to go back to the set-up guides in the thread to double-check your preparation. Likely, you don't have Dolphin set to fullscreen mode, or your screen resolution is not set to 1920x1080.

If you're running into other problems, try checking what problems and solutions other users had within the thread linked to at the top of this document.



	Other scripts:

The "python-fu-remove-background.py" script is not needed for the TCC; it is just included with this download for convenience, in case there is other manual editing in GIMP that you may want to do. You can install it just like the others, by placing it in the GIMP plug-ins folder. It will select and remove a pure color background behind a character, stage, or other asset that you've taken a screenshot of (assuming you did it using debug mode, where the background is not rendered), leaving a nice feathered edge. (By "pure color", I mean a single, solid color filling the entire background to be removed; usually black or magenta. Though any single, solid color will work, depending on what colors are in your target.) When using contiguous mode, the background color to remove is expected to be magenta.