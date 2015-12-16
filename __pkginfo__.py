# pylint: disable=W0622
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
"""Copyright (c) 2000-2011 LOGILAB S.A. (Paris, FRANCE).
http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

modname = distname = 'debinstall'
numversion = (2, 8, 0)
version = '.'.join([str(num) for num in numversion])


license = 'GPL'
description = "tool for managing debian repositories at Logilab"
author = "Logilab S.A."
author_email = "contact@logilab.fr"
web = "http://www.logilab.org/project/%s" % modname

long_desc = """
 debinstall provides the ldi command for managing debian repositories at
 Logilab. We hope that it will, one day, be usefull to others.
 .
 It provides functionnality for :
  * checking validaty of incoming directory
  * cleaning up of repositories
  * more to come.
"""

scripts = ['bin/ldi']

from os.path import join, isdir
include_dirs = [join('tests', 'data'), join('tests', 'packages')]
