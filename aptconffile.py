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

