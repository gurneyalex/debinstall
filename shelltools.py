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

"""various shell functions to help working with files and permissions"""
# XXX integrate in logilab.common ?
import os
import os.path as osp
import grp
import shutil

def set_permissions(path, uid, gid, mod):
    """set owner and permissions on path

    uid and gid and numeric user and group ids (gid can also be a group name)
    mod is the permission as an integer"""
    gid = getgid(gid)
    try:
        os.chown(path, uid, gid)
    except OSError, exc:
        raise RuntimeError('Failed to set ownership %s,%s on %s: %s' % (uid, gid, path, exc))
    try:
        os.chmod(path, mod)
    except OSError, exc:
        raise RuntimeError('Failed to set permissions %s on %s: %s' % (mod, path, exc))

def getgid(group):
    """return the group id for group.

    group can be a group name or or a goup id (in which case it is
    returned unchanged)
    """
    if type(group) is str:
        gid = grp.getgrnam(group).gr_gid
    else:
        gid = group
    return gid

def copy(source, dest, group, perms):
    """copy source to dest using shutil.copy and set the permissions"""
    if osp.isdir(dest):
        dest = osp.join(dest, osp.basename(source))
    shutil.copy(source, dest)
    set_permissions(dest, -1, group, perms)

def move(source, dest, group, perms):
    """move source to dest using shutil.move and set the permissions"""
    if osp.isdir(dest):
        dest = osp.join(dest, osp.basename(source))
    shutil.move(source, dest)
    set_permissions(dest, -1, group, perms)

def mkdir(path, group, perms):
    """create a directory with the specified permissions"""
    gid = getgid(group)
    os.makedirs(path)
    set_permissions(path, -1, gid, perms)

def rm(path):
    """recursively delete a directory tree or file"""
    if osp.isfile(path):
        os.remove(path)
    elif osp.isdir(path):
        shutil.rmtree(path)
