"""various shell functions to help working with files and permissions"""
# XXX integrate in logilab.common ?
import os
import grp
import shutil

def set_permissions(path, uid, gid, mod):
    """set owner and permissions on path
    uid and gid and numeric user and group ids (gid can also be a group name)
    mod is the permission as an integer"""
    gid = getgid(gid)
    try:
        os.chown(path, uid, gid)
        os.chmod(path, mod)
    except OSError, exc:
        raise RuntimeError('Failed to set permissions on %s: %s' % (path, exc))

def ensure_permissions(directories, group, dirperm, fileperm):
    """recursively set the group and permissions to all files and directories in the directories list
    group is a group name or a group id
    dirperm is the permissions to use for directories
    fileperm is the permissions to use for files"""
    if type(directories) is str:
        directories = [directories]
    gid = getgid(group)
    for dirname in directories:
        set_permissions(dirname, -1, gid, dirperm)
        for dirpath, dirnames, filenames in os.walk(dirname):
            for subdir in dirnames:
                subdir = os.path.join(dirpath, subdir)
                set_permissions(subdir, -1, gid, dirperm)
            for filename in filenames:
                filename = os.path.join(dirpath, filename)
                set_permissions(filename, -1, gid, fileperm)


def ensure_directories(directories):
    """create each directory in the directories (a string or a list of
    strings), with the missing directories in between"""
    if type(directories) is str:
        directories = [directories]
    for dirname in directories:
        if not os.path.isdir(dirname):
            os.makedirs(dirname)

def getgid(group):
    if type(group) is str:
        gid = grp.getgrnam(group).gr_gid
    else:
        gid = group
    return gid

def copy(source, dest, group, perms):
    gid = getgid(group)
    shutil.copy(source, dest)
    set_permissions(dest, -1, group, perms)
        


def mkdir(path, group, perms):
    gid = getgid(group)
    os.mkdir(path)
    set_permissions(path, -1, gid, perms)
    
