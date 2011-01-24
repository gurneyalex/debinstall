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
"""common interface to lintian"""

import os
from subprocess import Popen, PIPE


class Checker(object):
    command = None
    options = []
    ok_status = (0, )
    def run(self, changesfile):
        # we need to run this with normal privileges, otherwise the
        # perl behind lintian complains loudly
        euid = os.geteuid()
        egid = os.getegid()
        os.seteuid(os.getuid())
        os.setegid(os.getgid())
        status, stdout, stderr = self.do_run(changesfile)
        os.seteuid(euid)
        os.setegid(egid)
        return status in self.ok_status, stdout, stderr

    def do_run(self, changesfile):
        argv = [self.command] + self.options + [changesfile]
        try:
            pipe = Popen(argv, stdout=PIPE, stderr=PIPE)
        except OSError:
            raise Exception('%s is not installed' % self.command)
        stdout = pipe.stdout.read()
        stderr = pipe.stderr.read()
        status = pipe.wait()
        return status, stdout, stderr

class LintianChecker(Checker):
    command = "lintian"
    # XXX make options configurable
    options = ['-vi', '--suppress-tags', 'bad-distribution-in-changes-file']
    ok_status = (0, 2)


ALL_CHECKERS = {'lintian': LintianChecker()}
