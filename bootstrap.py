#!/usr/bin/env python
"""
Packages = {
    'core': {
        'elgg': { 
         'name':'elgg', 'repo_type':'git', 'repo_url':'git@github.con:lorea/Elgg.git' },
        },
    'tools': {},
    'plugins': {}
}
"""

import json, os, shlex, subprocess

#Packages = { 'core':{}, 'plugins':{}, 'tools':{} }

class PackagesJSON(object):

    def __init__(self, config_json):
        self._config_path = config_json
        try:
            f = open(self._config_path, 'r')
            c = json.load(f)
            f.close()
            self._packages = c
            print "== Loaded %s packages from %s" % (self.count(), self._config_path)
        except:
            self._packages = { 'core':{}, 'tools':{}, 'plugins':{} }

    def save(self):
        try:
            f = open(self._config_path,'w+')
            f.write(json.dumps(self._packages, sort_keys=True, indent=2))
            f.close()
            return True
        except:
            return False

    def core(self):
        return self._packages['core']

    def tools(self):
        return self._packages['tools']

    def plugins(self):
        return self._packages['plugins']

    def _cmd(self, command):
        args = shlex.split(str(command))
        ret  = subprocess.Popen(args, stdout=subprocess.PIPE).communicate()[0]
        return ret

    def count(self, what = 'all'):
        if what in ('core', 'plugins', 'tools'): return len(self.what())
        else: return len(self.core()) + len(self.tools()) + len(self.plugins())

    def register(self, pkey, name, repo_type, repo_url, state = None):
        if not self._packages.has_key(pkey): return False
        if not self._packages[pkey].has_key(name) or state != None:
            self._packages[pkey][name] = dict(name=name, repo_type=repo_type, repo_url=repo_url, state=state)
            return True
        return False

    def install_package(self, pkey, name):
        if not self._packages[pkey].has_key(name): return False
        package = self._packages[pkey][name]
        try:
            installer = "_install_from_%s" % package['repo_type']
            getattr(self, installer).__call__(pkey, package)
            package['state'] = 'installed'
            self._packages[pkey][name] = package
            return True
        except:
            print " !  Error installing " + name
            return False

    def _install_from_git(self, pkey, package):
        self._cmd("git clone %s %s/%s" % (package['repo_url'], pkey, package['name']))

    def _install_from_hg(self, pkey, package):
        self._cmd("hg clone %s %s/%s" % (package['repo_url'], pkey, package['name']))

    def _install_from_zip(self, pkey, package):
        self._cmd("wget -q -O tmp/%s_%s.zip '%s'" % (pkey, package['name'], package['repo_url']))
        self._cmd("unzip -d %s tmp/%s_%s.zip -x __MACOSX\*" % (pkey, pkey, package['name']))

    def update_package(self, pkey, name):
        if not self._packages[pkey].has_key(name): return False
        package = self._packages[pkey][name]
        try:
            updater = "_update_from_%s" % package['repo_type']
            getattr(self, updater).__call__(pkey, package)
            package['state'] = 'installed'
            self._packages[pkey][name] = package
            return True
        except:
            print " !  Error updating " + name
            raise
            return False

    def _update_from_git(self, pkey, package):
        pdir    = pkey + '/' + package['name']
        os.chdir(pdir)
        self._cmd("git pull --update")
        os.chdir('../..')

    def _update_from_hg(self, pkey, package):
        pdir    = pkey + '/' + package['name']
        os.chdir(pdir)
        self._cmd("hg pull")
        os.chdir('../..')

    def _update_from_zip(self, pkey, package):
        self.uninstall_package(pkey, package['name']) 
        self.install_package(pkey, package['name'])

    def uninstall_package(self, pkey, name):
        if not self._packages[pkey].has_key(name): return False
        package = self._packages[pkey][name]
        if package['state'] == None: return False
        pdir = pkey + '/' + name
        if os.path.exists(pdir): self._cmd("rm -rf %s" % pdir)
        if package['repo_type'] == 'zip': self._cmd("rm -f tmp/%s_%s.zip" % (pkey, name))
        if pkey == 'plugins': self._cmd("unlink core/elgg/mod/%s" % name)
        package['state'] = None
        self._packages[pkey][name] = package

    def update_all(self):
        for d in self._packages.keys():
            print "== Updating %s/" % d
            for n in self._packages[d]:
                p = self._packages[d][n]
                print " + %s/%-22s %03s %-55s %s" % (d, n, p['repo_type'], p['repo_url'], p['state'])
                if p['state'] == None and not os.path.isdir("%s/%s" % (d,n)):
                    self.install_package(d, n)
                elif p['state'] == 'installed' or p['state'] == None:
                    self.update_package(d, n)
                elif p['state'] == 'skip':
                    pass
                elif p['state'] == 'remove':
                    self.uninstall_package(d, n)
                else:
                    print " !  Unknwon package state %s" % p['state']
        self.link_plugins()

    def link_plugins(self):
        os.chdir('core/elgg/mod')
        for plugin in os.listdir('../../../plugins/'):
            if os.path.isdir('../../../plugins/' + plugin):
                self._cmd("ln -sf ../../../plugins/%s ." % plugin)
        os.chdir('../../..')


class Helper:
    @classmethod
    def bitbucket(self, user, package):
        return "https://bitbucket.org/%s/%s" % (user, package)

    @classmethod
    def github(self, user, package):
        return "https://github.com/%s/%s.git" % (user, package)

    @classmethod
    def github_dev(self, package):
        return "git@github.com:lorea/%s.git" % package

    @classmethod
    def rhizomatik(self, package):
        return self.bitbucket('rhizomatik', package)

################################################################################
## Register Packages
################################################################################

H        = Helper
Packages = PackagesJSON('bootstrap.json')

def package(pkey, name, repo_type, repo_url, state = None):
    """Register package name to Packages[pkey][name]"""
    if Packages.register(pkey, name, repo_type, repo_url, state):
        print " + registered package %s/%s" % (pkey, name)

## Core 
package('core', 'elgg',     'git', H.github_dev('Elgg'))
package('core', 'elgg',     'git', H.github_dev('Elgg')) # no dups :)
package('core', 'elgg-1.8', 'git', H.github('Elgg','Elgg'))

## Tools
package('tools', 'cryptobot', 'hg', H.bitbucket('caedes','cryptobot'))

for p in ('lorea_gtk', 'python-lorea', 'python-elggconnect'):
    package('tools', p, 'hg', H.rhizomatik(p))

package('tools', 'lorea-node', 'git', H.github_dev('lorea-node'))

## Plugins

# Those are named elgg_<package> on bitbucket
rhizomatik_elgg_plugins = ( 
    'activitystreams', 'admins', 'anonymous_topbar',
    'autosubscribegroup', 'avatar_wall', 'barter', 'calendar',
    'dmmdb', 'dokuwiki', 'editablecomments', 'foafssl',
    'foreign_objects', 'giss', 'graphstats', 'group_operators',
    'lockdown', 'microthemes', 'networkgraph', 'openid_client',
    'openid_server', 'pshb', 'psyc', 'rdf_aair', 'salmon',
    'sitemetas', 'spotlight_lorea', 'tasks', 'theme_ald', 'videolist'
    )
for p in rhizomatik_elgg_plugins:
    package('plugins', p, 'hg', H.rhizomatik("elgg_%s" % p))

# Those are named <package> on bitbucket
rhizomatik_plugins = ('elggpg',)
for p in rhizomatik_plugins:
    package('plugins', p, 'hg', H.rhizomatik(p))

# Those are found on github
github_plugins = ('blogwatch',)
for p in github_plugins:
    package('plugins', p, 'git', H.github_dev(p))

# Those have specific repositories
package('plugins', 'beechat', 'git', H.github('caedesvvv', 'beechat'))
print " !  Warning: beechat repo in read-only"

package('tools', 'miyamoto', 'git', H.github('caedesvvv', 'miyamoto'))
print " !  Warning: miyamoto repo in read-only"

# Those are zip or tarballs

package('plugins', 'autobox', 'zip', 'http://community.elgg.org/mod/community_plugins/download.php?release_guid=85281')

# Those SHOULD have a repo
for p in ( 'custom_index', 'custom_index_widget', 'dutch_translation',  'event_calendar', 'externalpages', 'faq', 'file_multigroup_upload', 'flagged', 'friend_request', 'gifts', 'groupmembers', 'groupriver', 'identica', 'jsinbox', 'lorea_framework', 'minify', 'network_graph', 'oauth', 'online', 'opensearch', 'ostatus', 'plugin_manager', 'powered', 'relatedgroups', 'reportedcontent', 'river_comments', 'river_index', 'showprivacy', 'sidetagcloud', 'simplepie', 'stats', 'subgoups', 'suicide', 'theme_dark_beauty', 'theme_loreahub', 'theme_n1', 'theme_simpleblackbluetech', 'theme_simpleneutral', 'threaded_forums', 'tidypics', 'translationbrowser', 'twitterservice', 'xrd'):
    print " !  Missing repository for %s" % p

# Perform Updates
Packages.update_all()
Packages.save()
print "== Saved %s packages to %s" % (Packages.count(), Packages._config_path)
