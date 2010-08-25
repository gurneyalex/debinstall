# Copyright (c) 2007-2010 LOGILAB S.A. (Paris, FRANCE).
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
"""helper classes to manipulate debian packages"""

import os.path as osp
import sys
from subprocess import Popen, PIPE

from debian import deb822

from logilab.common.decorators import cached

class BadSignature(Exception): pass

class CheckerError(Exception): pass


def check_sig(filename):
    """return True if the file is correctly signed"""
    pipe = Popen(["gpg", "--verify",  filename], stderr=PIPE)
    pipe.stderr.read()
    status = pipe.wait()
    if status != 0:
        raise BadSignature('%s is not properly signed' % filename)


class Changes(object):
    def __init__(self, path):
        self.path = path
        self.filename = osp.basename(path)
        self.changes = deb822.Changes(open(path))
        self.dirname = osp.dirname(path)

    def __getitem__(self, key):
        return self.changes[key]

    def get_dsc(self):
        """return the full path to the dsc file in the changes file
        or None if there is no source included in the upload"""
        for path in self.get_all_files():
            if path.endswith('.dsc'):
                return path
        return None

    def get_pristine(self):
        """return the full path to the pristine tarball in the changes file
        or None if there is no one is included in the upload"""
        for path in self.get_all_files():
            if path.endswith('.orig.tar.gz'):
                return path
        return None

    @cached
    def get_all_files(self, check_if_exists=True):
        all_files = set((self.path,))
        for info in self.changes['Files']:
            path = osp.join(self.dirname, info['name'])
            # TODO Need unit tests
            if check_if_exists:
                try:
                    fdesc = open(path)
                    fdesc.close()
                except IOError, exc:
                    raise Exception("Cannot read '%s' from %s"
                                    % (info['name'], self.path))
            all_files.add(path)
        return all_files

    def check_sig(self):
        """check the gpg signature of the changes file and the dsc file (if it
        exists). Raise an exception if that's not the case.
        """
        check_sig(self.path)
        dsc = self.get_dsc()
        if dsc is not None:
            check_sig(dsc)

    def run_checkers(self, checkers):
        from debinstall.checkers import ALL_CHECKERS
        errors = []
        for check in checkers:
            try:
                checker = ALL_CHECKERS[check]
            except KeyError:
                raise Exception('no such checker %s' % check)
            success, stdout, stderr = checker.run(self.path)
            if not success:
                errors.append('checker %s is in error on %s: \n%s\n%s'
                              % (check, self.path, stdout, stderr))
        if errors:
            raise CheckerError('\n'.join(errors))
