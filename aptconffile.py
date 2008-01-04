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
import debinstall2.shelltools as sht

def writeconf(dest, group, perms):
    """write a configuration file for use by apt-ftparchive"""
    fdesc = open(dest, "w")
    fdesc.write(APTDEFAULT_APTCONF)
    fdesc.close()
    sht.set_permissions(dest, -1, group, perms)

APTDEFAULT_APTCONF = '''\
// This config is for use with the pool-structure for the packages, thus we
// don't use a Tree Section in here

// The debian archive should be in the current working dir
Dir {
	ArchiveDir ".";
	CacheDir ".";
};

Default {
	Packages::Compress ". gzip bzip2";
	Sources::Compress ". gzip bzip2";
	Contents::Compress ". gzip bzip2";
};

// Includes the main section. You can structure the directory tree under
// ./pool/main any way you like, apt-ftparchive will take any deb (and
// source package) it can find. This creates a Packages a Sources and a
// Contents file for these in the main section of the sid release
BinDirectory "pool/main" {
	Packages "dists/sid/main/binary-i386/Packages";
	Sources "dists/sid/main/source/Sources";
	Contents "dists/sid/Contents-i386";
}

// This is the same for the contrib section
BinDirectory "pool/contrib" {
	Packages "dists/sid/contrib/binary-i386/Packages";
	Sources "dists/sid/contrib/source/Sources";
	Contents "dists/sid/Contents-i386";
}

// This is the same for the non-free section
BinDirectory "pool/non-free" {
	Packages "dists/sid/non-free/binary-i386/Packages";
	Sources "dists/sid/non-free/source/Sources";
	Contents "dists/sid/Contents-i386";
};

// By default all Packages should have the extension ".deb"
Default {
	Packages {
		Extensions ".deb";
	};
};


'''

