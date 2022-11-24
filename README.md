# Melee Modding Wizard (MMW)
<p align="center">
<img align="right" width="128" height="128" src="https://raw.githubusercontent.com/DRGN-DRC/Melee-Modding-Wizard/main/imgs/logo.png">
</p>

This program provides a large variety of features and tools for modding Super Smash Bros. Melee and the 20XX Hack Pack. This incorporates major functions of DTW, such as game disc and extracted disc root/folder operations, as well as a suite of code development and installation tools from MCM.

Check out the thread here for a broader feature overview: [Melee Modding Wizard on SmashBoards.com](https://smashboards.com/threads/melee-modding-wizard-beta-v0-9-3.517823/)

## Installation & Setup

This is built in Python 2 (with plans to transition to Python 3), and I don't have a compiled build just yet. So for now, you'll need to install Python in order to run this. I've included the dependencies and wrote a simple installer for them, found in the "Dependencies" folder. The batch script will install Python v2.7.18 (unless Python is already installed to C:\Python27 on your system), and then install the remaining python modules needed to that same instance. It's not set up to install into your PATH variable, so if you already have another version of Python on your system, it should be fine. After running that, you should just be able to open the program by running "- - MMW_Debug.bat" in the root folder. Although to use playback/import of music in the Audio Manager tab, you'll also need to install .Net Framework v4.6.1, which you can find [here](https://www.microsoft.com/en-us/download/details.aspx?id=49981).

## Credits, Copyright, and Licenses
* **MeleeMedia**   ( [Website](https://smashboards.com/threads/meleemedia-mth-thp-and-hps-conversion.505591/) | [GitHub](https://github.com/Ploaj/MeleeMedia) )    `- Converts audio and video formats`
    - Created by Ploaj (2020)
* **png.py**       ( [Website](https://pypng.readthedocs.io/en/latest/) | [GitHub](https://github.com/drj11/pypng/) )    `- PNG codec used within the TPL codec`
    - Copyright (c) 2015 Pavel Zlatovratskii <scondo@mail.ru>
    - Copyright (c) 2006 Johann C. Rocholl <johann@browsershots.org>
    - Portions Copyright (C) 2009 David Jones <drj@pobox.com>
    - And probably portions Copyright (C) 2006 Nicko van Someren <nicko@nicko.org>
    - Original concept by Johann C. Rocholl.
    - MIT License
* **pngquant**      ( [Website](https://pngquant.org/) | [GitHub](https://github.com/kornelski/pngquant) )    `- Used in palette and CSP trim color generation`
    - Copyright (c) by Kornel Lesiński (2009-2018), Greg Roelofs (1997-2002), and Jef Poskanzer (1989, 1991)
    - Licensed under GPL v3 or later
* **wimgt**        ( [Website](https://szs.wiimm.de/wimgt/) | [GitHub](https://github.com/Wiimm/wiimms-szs-tools) )    `- Used for CMPR (type _14) texture encoding`
    - Copyright (c) by Wiimm (2011)
    - GNU GPL v2 or later
* **xxHash**    ( [PyPI](https://pypi.org/project/xxhash/) | [GitHub](https://github.com/ifduyue/python-xxhash) )      `- Used for Dolphin hash generation`
    - Copyright (c) by Yue Du (2014-2020)
    - Licensed under [BSD 2-Clause License](http://opensource.org/licenses/BSD-2-Clause)
