import debinstall2.shelltools as sht

def writeconf(dest, group, perms, sources, packages):
    f = open(dest, "w")
    f.write(DEFAULT_LDICONF % {'sources': ', '.join(sources),
                               'packages': ', '.join(packages)})
    f.close()
    sht.set_permissions(dest, -1, group, perms)

DEFAULT_LDICONF = '''\
[subrepository]
sources=%(sources)s
packages=%(packages)s
'''
