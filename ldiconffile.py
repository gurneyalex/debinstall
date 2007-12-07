"""ldi.conf manipilation utilities"""

import debinstall2.shelltools as sht

def writeconf(dest, group, perms, sources, packages):
    """generate a ldi.conf file with the appropriate values"""
    fdesc = open(dest, "w")
    fdesc.write(DEFAULT_LDICONF % {'sources': ', '.join(sources),
                               'packages': ', '.join(packages)})
    fdesc.close()
    sht.set_permissions(dest, -1, group, perms)

DEFAULT_LDICONF = '''\
[subrepository]
sources=%(sources)s
packages=%(packages)s
'''
