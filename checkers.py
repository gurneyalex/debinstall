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

"""common interface to linda and lintian"""

from subprocess import Popen, PIPE

class Checker:
    command = "command"
    options = []
    ok_status = (0, )
    def run(self, changesfile):
        argv = [self.command] + self.options + [changesfile]
        pipe = Popen(argv, stdout=PIPE, stderr=PIPE)
        stdout = pipe.stdout.readlines()
        stderr = pipe.stderr.readlines()
        return pipe.wait in self.ok_status, stdout, stderr

class LintianChecker(Checker):
    command = "lintian"

class LindaChecker(Checker):
    command = "linda"
    error_status = (0, 1,)


ALL_CHECKERS = [LintianChecker(),
                LindaChecker(),
                ]
