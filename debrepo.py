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
"""wrapper functions to run the apt-ftparchive command"""

import os
import os.path as osp
import subprocess
import logging
from glob import glob

from logilab.common.clcommands import CommandError

logger = logging.getLogger('ldi.apt-ftparchive')


def generate_aptconf(repodir, origin='Logilab'):
    """write a configuration file for use by apt-ftparchive"""
    path = osp.join(repodir, 'apt.conf')
    stream = open(path, "w")
    stream.write(APTDEFAULT_APTCONF % {'origin': origin,
                                       'repodir': repodir})
    for distrib in glob(osp.join(repodir, 'dists', '*')):
        if osp.isdir(distrib) and not osp.islink(distrib):
            distrib = osp.basename(distrib)
            stream.write(BINDIRECTORY_APTCONF % {'distribution': distrib})
    stream.close()
    return path

APTDEFAULT_APTCONF = '''// Generated file, do not modify !!

APT {
  FTPArchive {
    Release {
        Origin "%(origin)s";
        Label  "%(origin)s debian packages repository";
        Description "created by the ldi utility";
    };
  };
};

Default {
        Packages::Compress ". gzip bzip2";
        Sources::Compress ". gzip bzip2";
        Contents::Compress ". gzip bzip2";
        FileMode 0664;
};

Dir {
        ArchiveDir "%(repodir)s/dists";
};
'''

BINDIRECTORY_APTCONF = '''\

BinDirectory "%(distribution)s" {
    Packages "%(distribution)s/Packages";
    Sources "%(distribution)s/Sources";
    Contents "%(distribution)s/Contents"
};
'''


def clean(debian_dir):
    for mask in ['Packages*', 'Source*', 'Content*', 'Release*']:
        for path in glob(osp.join(debian_dir, mask)):
            logger.debug("remove '%s'" % path)
            os.remove(path)


def generate(debian_dir, aptconf):
    command = ['apt-ftparchive', '-q=2', 'generate', aptconf]
    logger.debug('running command: %s' % ' '.join(command))
    pipe = subprocess.Popen(command)
    status = pipe.wait()
    if status != 0:
        raise CommandError('apt-ftparchive exited with error status %d' % status)
    logger.debug('new index files: %s' % debian_dir)


def release(debian_dir, aptconf):
    distrib = osp.basename(debian_dir)
    release_file = osp.join(debian_dir, 'Release')
    command = ['apt-ftparchive', '-c', aptconf, 'release', debian_dir,
               '-o', 'APT::FTPArchive::Release::Codename=%s' % distrib]
    logger.debug('running command: %s' % ' '.join(command))
    pipe = subprocess.Popen(command, stdout=subprocess.PIPE)
    stdout, stderr = pipe.communicate()
    release = open(release_file, 'w')
    release.write(stdout)
    release.close()
    if pipe.returncode != 0:
        raise CommandError('apt-ftparchive exited with error status %d'
                           % pipe.returncode)
    logger.debug('new Release file: %s' % (osp.join(debian_dir, release_file)))


def sign(debian_dir, key_id):
    releasepath = osp.join(debian_dir, 'Release')
    signed_releasepath = releasepath + '.gpg'
    command = ['gpg', '-b', '-a', '--yes', '--default-key', key_id, '-o', signed_releasepath, releasepath]
    logger.debug('running command: %s' % ' '.join(command))
    pipe = subprocess.Popen(command)
    pipe.communicate()
    status = pipe.wait()
    if status != 0:
        raise CommandError('gpg exited with status %d' % status)
