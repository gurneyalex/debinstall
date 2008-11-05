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

"""apt.conf file manipulation"""

import os
import re

def writeconf(dest, group, perms, distributions, origin):
    """write a configuration file for use by apt-ftparchive"""
    fdesc = open(dest, "a")
    if fdesc.tell() == 0:
        fdesc.write(APTDEFAULT_APTCONF % {'distributions': ','.join(distributions),
                                          'origin': origin})
    else:
        fdesc.close()
        oldconf = open(dest).read()
        old_dists = re.search(r'Suite\s+"(.*?)";', oldconf).group(1).split(',')
        distributions = list(set(distributions) | set(old_dists))
        os.unlink(dest)
        return writeconf(dest, group, perms, distributions, origin)

    for distribution in distributions:
        fdesc.write(BINDIRECTORY_APTCONF % {'distribution': distribution})
    fdesc.close()

APTDEFAULT_APTCONF = '''\
APT {
  FTPArchive {
    Release {
        Origin "%(origin)s";
        Label  "%(origin)s debian packages repository";
        Suite  "%(distributions)s";
        Description "created by ldi utility";
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
        ArchiveDir "dists";
};

/////////////////////////////////////////////////////
// These sections added for new distribution creation
'''

BINDIRECTORY_APTCONF = '''\

BinDirectory "%(distribution)s" {
    Packages "%(distribution)s/Packages";
    Sources "%(distribution)s/Sources";
    Contents "%(distribution)s/Contents"
};
'''
