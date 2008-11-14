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

"""wrapper functions to run the apt-ftparchive commande"""

import os
import os.path as osp
from glob import glob
import subprocess
import logging

from debinstall.command import CommandError
from debinstall.logging_handlers import CONSOLE


logger = logging.getLogger('debinstall.apt-ftparchive')
logger.setLevel(logging.DEBUG)
logger.addHandler(CONSOLE)

def clean(debian_dir):
    candidates = ['Packages*', 'Source*', 'Content*', 'Release*']
    for candidate in candidates:
        for path in glob(osp.join(debian_dir, candidate)):
            os.remove(path)

def generate(debian_dir, aptconf, group):
    command = ['apt-ftparchive', 'generate', aptconf]
    logger.info('running %s$ %s', os.getcwd(), ' '.join(command))
    pipe = subprocess.Popen(command)
    status = pipe.wait()
    if status != 0:
        raise CommandError('apt-ftparchive exited with error status %d'%status)

def release(debian_dir, aptconf, group, distrib):
    release = open(osp.join(debian_dir, 'Release'), 'w')
    command = ['apt-ftparchive', '-c', aptconf, 'release', debian_dir, '-o',
               'APT::FTPArchive::Release::Suite=%s' % distrib]
    logger.info('running %s$ %s', os.getcwd(), ' '.join(command))
    pipe = subprocess.Popen(command,
                            stdout=release)
    status = pipe.wait()
    if status != 0:
        raise CommandError('apt-ftparchive exited with error status %d' % status)

def sign(debian_dir, key_id, group):
    releasepath = osp.join(debian_dir, 'Release')
    signed_releasepath = releasepath + '.gpg'
    command = ['gpg', '-b', '-a', '--yes', '--default-key', key_id, '-o', signed_releasepath, releasepath]
    logger.info('running %s$ %s', os.getcwd(), ' '.join(command))
    pipe = subprocess.Popen(command)
    pipe.communicate()
    status = pipe.wait()
    if status != 0:
        raise CommandError('gpg exited with status %d' % status)
