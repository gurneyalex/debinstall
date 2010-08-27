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
from logilab.common.shellutils import ASK

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
        ArchiveDir "%(archivedir)s";
};
'''

BINDIRECTORY_APTCONF = '''\

BinDirectory "%(distribution)s" {
    Packages "%(distribution)s/Packages";
    Sources "%(distribution)s/Sources";
    Contents "%(distribution)s/Contents"
};
'''

class DebianRepository(object):
    def __init__(self, logger, directory):
        self.logger = logger
        self.directory = directory

    @property
    def incoming_directory(self):
        return osp.join(self.directory, 'incoming')
    @property
    def dists_directory(self):
        return osp.join(self.directory, 'dists')
    @property
    def aptconf_file(self):
        return osp.join(self.directory, 'apt.conf')

    def check_distrib(self, section, distrib):
        distribdir = osp.join(self.directory, section, distrib)
        if not osp.isdir(distribdir):
            raise CommandError(
                "Distribution %s not found in %s" % (distrib, section))
        # Print a warning in case of using symbolic distribution names
        distribdir = osp.realpath(distribdir)
        dereferenced = osp.basename(distribdir)
        if dereferenced != distrib:
            self.logger.warn("deferences symlinked distribution '%s' to '%s'",
                             distrib, dereferenced)
        return distribdir

    def generate_aptconf(self, origin='Logilab'):
        """write a configuration file for use by apt-ftparchive"""
        stream = open(self.aptconf_file, "w")
        stream.write(APTDEFAULT_APTCONF % {
            'origin': origin, 'archivedir': self.dists_directory})
        for distrib in glob(osp.join(self.dists_directory, '*')):
            if osp.isdir(distrib) and not osp.islink(distrib):
                distrib = osp.basename(distrib)
                stream.write(BINDIRECTORY_APTCONF % {'distribution': distrib})
        stream.close()

    def dist_publish(self, dist, gpgkeyid=None):
        self.dist_clean(dist)
        self.ftparchive_generate(dist)
        self.ftparchive_release(dist)
        if gpgkeyid:
            self.sign(dist, gpgkeyid)

    def dist_clean(self, dist):
        for mask in ['Packages*', 'Source*', 'Content*', 'Release*']:
            for path in glob(osp.join(self.dists_directory, dist, mask)):
                self.logger.debug("remove '%s'", path)
                os.remove(path)

    def ftparchive_generate(self, dist):
        command = ['apt-ftparchive', '-q=2',
                   'generate', self.aptconf_file, dist]
        self.logger.debug('running command: %s', ' '.join(command))
        pipe = subprocess.Popen(command)
        status = pipe.wait()
        if status != 0:
            raise CommandError('apt-ftparchive exited with error status %d' % status)

    def ftparchive_release(self, dist):
        distdir = osp.join(self.dists_directory, dist)
        command = ['apt-ftparchive', '-c', self.aptconf_file,
                   'release', distdir,
                   '-o', 'APT::FTPArchive::Release::Codename=%s' % dist]
        self.logger.debug('running command: %s', ' '.join(command))
        release_file = osp.join(distdir, 'Release')
        release = open(release_file, 'w')
        pipe = subprocess.Popen(command, stdout=release)
        pipe.communicate()
        release.close()
        if pipe.returncode != 0:
            raise CommandError('apt-ftparchive exited with error status %d'
                               % pipe.returncode)


    def sign(self, dist, gpgkeyid):
        releasepath = osp.join(self.dists_directory, dist, 'Release')
        signed_releasepath = releasepath + '.gpg'
        command = ['gpg', '-b', '-a', '--yes', '--default-key', gpgkeyid,
                   '-o', signed_releasepath, releasepath]
        self.logger.debug('running command: %s' % ' '.join(command))
        pipe = subprocess.Popen(command)
        pipe.communicate()
        status = pipe.wait()
        if status != 0:
            raise CommandError('gpg exited with status %d' % status)
