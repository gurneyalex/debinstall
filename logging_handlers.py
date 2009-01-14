# Copyright (c) 2007-2008 LOGILAB S.A. (Paris, FRANCE).
# http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

import sys
import os.path as osp
import logging
from logilab.common.logging_ext import ColorFormatter


isatty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

CONSOLE = logging.StreamHandler()
LOG_FORMAT = '[%(levelname)-8s] %(name)-10s: %(message)s'

if not isatty or '--no-color' in sys.argv:
    formatter = logging.Formatter(LOG_FORMAT)
else:
    formatter = ColorFormatter(LOG_FORMAT)
CONSOLE.setFormatter(formatter)

if osp.isdir(osp.join(osp.dirname(__file__), '.hg')):
    CONSOLE.setLevel(logging.DEBUG)
    logger = logging.getLogger('root')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(CONSOLE)
    logger.debug('Using development version')
else:
    CONSOLE.setLevel(logging.INFO)

