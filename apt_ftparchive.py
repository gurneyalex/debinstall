import os.path as osp
from glob import glob
import subprocess

from debinstall2.shelltools import set_permissions


def clean(debian_dir):
    candidates= ['Packages*', 'Source*', 'Content*', 'Release*']
    for candidate in candidates:
        for path in glob(osp.join(debian_dir, candidate)):
            osp.remove(path)

def generate(debian_dir, aptconf, group):
    pipe = subprocess.Popen(['apt-ftparchive', 'generate', aptconf])
    status = pipe.wait()
    candidates= ['Packages*', 'Source*', 'Content*', 'Release*']
    for candidate in candidates:
        for path in glob(osp.join(debian_dir, candidate)):
            set_permissions(path, -1, group, 0664)
    if status != 0:
        raise CommandError('apt-ftparchive exited with error status %d'%status)

def release(debian_dir, aptconf, group):    
    release = open(osp.join(debian_dir, 'Release'), 'w')
    pipe = subprocess.Popen(['apt-ftparchive', '-c', aptconf, 'release', debian_dir],
                            stdout=release)
    status = pipe.wait()
    if status != 0:
        raise CommandError('apt-ftparchive exited with error status %d' % status)
    

def sign(debian_dir, key_id, group):
    releasepath = osp.join(debian_dir, 'Release')
    signed_releasepath = releasepath + '.gpg'
    command = ['gpg', '-b', '-a', '--yes', '--default-key', key_id, '-o', signed_releasepath]
    pipe = subprocess.Popen(command)
    status = pipe.wait()
    set_permissions(signed_releasepath, -1, group, 0664)
    if status != 0:
        raise CommandError('gpg exited with status %d' % status)
