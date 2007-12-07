"""The ldi command provides access to various subcommands to
manipulate debian packages and repositories"""
import sys
import os
import os.path as osp

from logilab.common import optparser

from debinstall2.debfiles import Changes
from debinstall2.command import LdiCommand, CommandError
from debinstall2 import shelltools as sht
from debinstall2.signature import check_sig

def run(args=None):
    if args is None:
        args = sys.argv[1:]
    usage = """usage: ldi <command> <options> [arguments]"""
    parser = optparser.OptionParser(usage=usage)
    for cmd in (Create, Upload, Publish, Archive):
        instance = cmd()
        instance.register(parser)
    run, options, args = parser.parse_command(args)
    run(options, args, parser)


class Create(LdiCommand):
    """create a new repository"""
    name = "create"
    arguments = "repository_name"
    opt_specs = [
        ('-a', '--apt-config',
         {'dest': "aptconffile",
          'help': 'apt-ftparchive configuration file for the new repository'}
         ),
        ('-s', '--source-repo',
         {'action':'append',
          'default': [],
          'dest': 'source_repositories',
          'help': "the original repository from which a sub-repository "
                  "should be created"}
         ),
        ('-p', '--package',
         {'action':'append',
          'default': [],
          'dest': 'packages',
          'help': "a package to extract from a repository into a "
                  "sub-repository"}
         ),
        ] 


    def pre_checks(self, option_parser):
        LdiCommand.pre_checks(self, option_parser)
        self.repo_name = self.args[0]
        directories = [self.get_config_value(confkey)
                       for confkey in ('destination', 'configurations')]
        sht.ensure_directories(directories)
        sht.ensure_permissions(directories, self.group, 0775, 0664)
                
    def post_checks(self):
        directories = [self.get_config_value(confkey)
                       for confkey in ('destination', 'configurations')]
        sht.ensure_permissions(directories, self.group, 0775, 0664)
    
    def process(self):
        dest_base_dir = self.get_config_value("destination")
        conf_base_dir = self.get_config_value('configurations')
        repo_name = self.args[0]
        dest_dir = osp.join(dest_base_dir, repo_name)
        aptconf = osp.join(conf_base_dir, '%s-apt.conf' % repo_name)
        ldiconf = osp.join(conf_base_dir, '%s-ldi.conf' % repo_name)
        if osp.isdir(dest_dir) or osp.isfile(aptconf) or osp.isfile(ldiconf):
            raise CommandError('A repository with that name already exists.')

        if self.options.source_repositories:
            if not self.options.packages:
                message = 'No packages to extract from the source repositories'
                raise CommandError(message)
        if self.options.packages:
            if not self.options.source_repositories:
                message = 'No source repositories for package extraction'
                raise CommandError(message)
        

        sht.mkdir(dest_dir, self.group, 0775)
        sht.mkdir(osp.join(dest_dir, 'debian'), self.group, 0775)
        sht.mkdir(osp.join(dest_dir, 'incoming'), self.group, 0775)
        if self.options.aptconffile is not None:
            sht.copy(self.options.aptconffile, aptconf)
        else:
            import aptconffile
            aptconffile.writeconf(aptconf, self.group, 0664)
        import ldiconffile
        ldiconffile.writeconf(ldiconf, self.group, 0664,
                              self.options.source_repositories,
                              self.options.packages)

class Upload(LdiCommand):
    """upload a new package to the incoming queue of a repository"""
    name = "upload"
    min_args = 2
    max_args = sys.maxint
    arguments = "repository package.changes [...]"


    def _get_all_package_files(self, changes_files):
        file_list = []
        for filename in changes_files:
            changes = Changes(filename)
            file_list += changes.get_all_files()
        return file_list



    def _check_signatures(self, changes_files):
        """return True if the changes files and appropriate dsc files
        are correctly signed.
        
        raise CommandError otherwise.
        """
        failed = []
        for filename in changes_files:
            changes = Changes(filename)
            changes.check_sig(failed)
        if failed:
            raise CommandError('The following files are not signed:\n' + \
                               '\n'.join(failed))
        return True
    
    def process(self):
        repository = self.args[0]
        changes_files = self.args[1:]
        self._check_signatures(changes_files)
        all_files = self._get_all_package_files(changes_files)
        destdir = osp.join(self.get_config_value('destination'),
                           repository,
                           'incoming')
        for filename in all_files:
            sht.copy(filename, destdir, self.group, 0775)
        
        
class Publish(LdiCommand):
    """process the incoming queue of a repository"""
    name = "publish"
    min_args = 0
    max_args = sys.maxint
    argument = "[source_package...]"
    def pre_checks(self, option_parser):
        pass
    
    def post_checks(self):
        pass
    
    def process(self):
        raise NotImplementedError("This command is not yet available")
    
class Archive(LdiCommand):
    """cleanup a repository by moving old unused packages to an
    archive directory"""
    name = "archive"

    def pre_checks(self, option_parser):
        pass

    def post_checks(self):
        pass

    def process(self):
        raise NotImplementedError("This command is not yet available")
    

class Destroy(LdiCommand):
    """completely remove a repository, its packages and the
    configuration files"""
    name = 'destroy'

    def process(self):
        raise NotImplementedError("This command is not yet available")
