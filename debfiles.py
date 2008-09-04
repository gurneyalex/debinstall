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

"""helper classes to manipulate debian packages"""
import os.path as osp

from debian_bundle import deb822

from debinstall.signature import check_sig
from debinstall.checkers import ALL_CHECKERS

class Changes:
    def __init__(self, filename):
        self.filename = filename
        self.changes = deb822.Changes(open(filename))
        self.dirname = osp.dirname(filename)

    def get_dsc(self):
        """return the full path to the dsc file in the changes file
        or None if there is no source included in the upload"""
        for info in self.changes['Files']:
            if info['name'].endswith('.dsc'):
                return osp.join(self.dirname, info['name'])
        return None

    def get_all_files(self):
        all_files = [self.filename]
        for info in self.changes['Files']:
            all_files.append(osp.join(self.dirname, info['name']))
        return all_files

    def check_sig(self, out_wrong=None):
        """check the gpg signature of the changes file and the dsc file
        (if it exists)

        return: True if all checked sigs are correct, False otherwise.
        out_wrong can be a list, in which case the full paths to the
        wrong signatures files are appended.
        """
        status = True
        if out_wrong is None:
            out_wrong = []
        if not check_sig(self.filename):
            status = False
            out_wrong.append(self.filename)
        dsc = self.get_dsc()
        if dsc is not None and not check_sig(dsc):
            status = False
            out_wrong.append(dsc)
        return status

    def run_checkers(self, checkers, out_wrong=None):
        status = True
        if out_wrong is None:
            out_wrong = []
        for checker in ALL_CHECKERS:
            if checker.command not in checkers:
                continue
            success, _, stderr = checker.run(self.filename)
            if not success:
                out_wrong += stderr
            status = status and success
        return status
