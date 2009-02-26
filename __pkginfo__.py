# pylint: disable-msg=W0622
# coding: iso-8859-1
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
"""Copyright (c) 2000-2008 LOGILAB S.A. (Paris, FRANCE).
http://www.logilab.fr/ -- mailto:contact@logilab.fr  
"""

import glob
modname = 'debinstall'
numversion = (2, 2, 1)
version = '.'.join([str(num) for num in numversion])


license = 'GPL'
copyright = '''Copyright © 2007-2009 LOGILAB S.A. (Paris, FRANCE).
http://www.logilab.fr/ -- mailto:contact@logilab.fr'''

short_desc = "tool for managing debian repositories at Logilab"

long_desc = """
 debinstall provides a tool for managing debian repositories at
 Logilab. We hope that it will, one day, be usefull to others.
 .
 It provides functionnality for : 
  * checking validaty of incoming directory
  * cleaning up of repositories
  * more to come.
"""

author = "Logilab"
author_email = "devel@logilab.fr"

# TODO - publish
web = "http://www.logilab.org/project/%s" % modname
ftp = "ftp://ftp.logilab.org/pub/%s" % modname


scripts = ['bin/debinstall']
debian_name = 'debinstall'
debian_maintainer = 'Alexandre Fayolle' 
debian_maintainer_email = 'alexandre.fayolle@logilab.fr'
pyversions = ["2.4"]

debian_handler = 'python-dep-standalone'
 
from os.path import join
include_dirs = [join('tests', 'data'), join('tests', 'packages')]

