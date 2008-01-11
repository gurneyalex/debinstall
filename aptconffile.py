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
import debinstall.shelltools as sht

def writeconf(dest, group, perms):
    """write a configuration file for use by apt-ftparchive"""
    fdesc = open(dest, "w")
    fdesc.write(APTDEFAULT_APTCONF)
    fdesc.close()
    sht.set_permissions(dest, -1, group, perms)
    

APTDEFAULT_APTCONF = '''\
APT {
  FTPArchive {
    Release {
        Origin "WRITEME";
        Label  "WRITEME";
        Suite  "sid";
        Description "WRITEME";
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
        ArchiveDir ".";
};

TreeDefault {
    Directory "debian/";
    SrcDirectory "debian/";

};

BinDirectory "debian" {
    Packages "debian/Packages";
    Sources "debian/Sources";
    Contents "debian/Contents"
};
'''

