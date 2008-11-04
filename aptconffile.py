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

def writeconf(dest, group, perms, distribution, origin):
    """write a configuration file for use by apt-ftparchive"""
    fdesc = open(dest, "w")
    fdesc.write(APTDEFAULT_APTCONF % {'distribution': distribution,
                                      'origin': origin})
    fdesc.close()

APTDEFAULT_APTCONF = '''\
APT {
  FTPArchive {
    Release {
        Origin "%(origin)s";
        Label  "Debian packages Repository";
        Suite  "%(distribution)s";
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

TreeDefault {
    Directory "%(distribution)s/";
    SrcDirectory "%(distribution)s/";

};

BinDirectory "%(distribution)s" {
    Packages "%(distribution)s/Packages";
    Sources "%(distribution)s/Sources";
    Contents "%(distribution)s/Contents"
};
'''

