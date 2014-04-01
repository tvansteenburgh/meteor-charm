#!/usr/bin/python

from contextlib import contextmanager
import json
import os
import shutil
import subprocess
import sys
import textwrap

sys.path.insert(0, os.path.join(os.environ['CHARM_DIR'], 'lib'))

from charmhelpers import fetch
from charmhelpers.core import (
        hookenv,
        host,
        )

hooks = hookenv.Hooks()

USER = 'meteor'
SERVICE = 'meteor'
BASE_DIR = '/srv/meteor'
CODE_DIR = BASE_DIR + '/code'
BUNDLE_DIR = BASE_DIR + '/bundle'
BUNDLE_ARCHIVE = BASE_DIR + '/bundle.tgz'
METEOR_CONFIG = BASE_DIR + '/.juju-config'
NODEJS_REPO = 'ppa:chris-lea/node.js'
PACKAGES = ['nodejs', 'build-essential', 'curl']
DOWNLOAD_CMD = 'curl http://install.meteor.com -o /tmp/meteor-install'
INSTALL_CMD = '/bin/sh /tmp/meteor-install'


class Config(object):
    """A Juju config dictionary that can write itself to
    disk (json) and track which values have changed since
    the previous write.

    """
    def __init__(self, path=None):
        """Initialize a `hookenv.config(), with an optional
        "previous" copy loaded from `path`.

        """
        self.cur_dict = hookenv.config()
        self.prev_dict = None
        if path:
            self.load_previous(path)

    def load_previous(self, path):
        """Load a previous copy of config so that current values
        can be compares to previous values.

        """
        try:
            with open(path) as f:
                self.prev_dict = json.load(f)
        except IOError:
            pass

    def changed(self, key):
        """Return true if the value for this key has changed since
        the last save.

        """
        if self.prev_dict is None:
            return True
        return self.prev_dict.get(key) != self.cur_dict.get(key)

    def previous(self, key):
        """Return previous value for this key, or None if there
        is no "previous" value.

        """
        if self.prev_dict:
            return self.prev_dict.get(key)
        return None

    def save(self, path):
        """Save this config to `path`.

        """
        with open(path, 'w') as f:
            json.dump(self.cur_dict, f)

    def get(self, key, default=None):
        return self.cur_dict.get(key, default)

    def __getitem__(self, key):
        return self.cur_dict[key]

    def __setitem__(self, key, val):
        self.cur_dict[key] = val


def write_upstart(config):
    upstart = textwrap.dedent("""\
    description "Meteor app '{app_name}'"

    start on (net-device-up
              and local-filesystems
              and runlevel [2345])
    stop on runlevel [!2345]

    respawn

    setuid {app_user}

    env PORT={port}
    env MONGO_URL={mongo_url}
    env ROOT_URL={root_url}

    exec node {app_dir}/bundle/main.js
    """)
    with open('/etc/init/{}.conf'.format(SERVICE), 'w') as f:
        f.write(upstart.format(
            app_user=USER,
            app_dir=BASE_DIR,
            app_name=config['app-name'],
            mongo_url=config.get('mongo_url', ''),
            port=config['port'],
            root_url='http://{}:{}/'.format(
                hookenv.unit_private_ip(), config['port']),
            ))


@contextmanager
def chdir(path):
    """Temporarily os.chdir(), returning to original dir when done.

    """
    cwd = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(cwd)


def clone(repo_type, url, dest=None, rev=None):
    """Clone a git or hg repo.

    :param repo_type: 'git' or 'hg'
    :param url: url of repo to clone from
    :param dest: destination directory (None for default)
    :param rev: revision to checkout after clone (None for repo default)

    """
    clone_args = [repo_type, 'clone', url]
    if dest:
        clone_args.append(dest)
    subprocess.check_call(clone_args)
    if dest and rev:
        checkout(repo_type, dest, rev)


def checkout(repo_type, path, rev):
    """Checkout a specific revision of an existing git or hg repo.

    :param repo_type: 'git' or 'hg'
    :param path: path to existing repo
    :param rev: revision to checkout

    """
    cmds = {
        'git': 'checkout',
        'hg': 'update',
        }
    checkout_cmd = cmds[repo_type]
    with chdir(path):
        update_args = [repo_type, checkout_cmd, rev]
        subprocess.check_call(update_args)


def ensure_rmtree(path):
    """Make sure `path` does not exist.

    """
    try:
        shutil.rmtree(path)
    except OSError:
        pass


def init_code(config):
    """Clone the application code for this meteor service.

    """
    if config['repo-url']:
        hookenv.log('Cloning app from %s' % config['repo-url'])
        pkg = {
            'git': 'git',
            'hg': 'mercurial',
            }[config['repo-type']]
        fetch.apt_install(pkg)
        clone(config['repo-type'], config['repo-url'], CODE_DIR,
                config['repo-revision'])
    else:
        hookenv.log('Creating demo app')
        subprocess.check_call(['mrt', 'create', '--example',
            config['demo-app'], CODE_DIR])


def init_bundle(config):
    """Create meteor bundle for this application.

    """
    ensure_rmtree(BUNDLE_DIR)
    if not config['bundled']:
        hookenv.log('Bundling app')
        with chdir(CODE_DIR):
            subprocess.check_call(['mrt', 'bundle', BUNDLE_ARCHIVE])
        with chdir(BASE_DIR):
            subprocess.check_call(['tar', '-xzf', BUNDLE_ARCHIVE])
        os.remove(BUNDLE_ARCHIVE)
    else:
        hookenv.log('Copying bundle from repo')
        shutil.copytree(os.path.join(CODE_DIR, 'bundle'), BUNDLE_DIR)


@hooks.hook('install')
def install():
    config = Config()

    host.adduser(USER, password='')
    host.mkdir(BASE_DIR, owner=USER, group=USER)

    # Meteor install script needs this
    os.environ['HOME'] = os.path.expanduser('~' + USER)

    hookenv.log('Installing dependencies')
    fetch.add_source(NODEJS_REPO)
    fetch.apt_update()
    fetch.apt_install(PACKAGES)

    hookenv.log('Installing Meteor')
    subprocess.check_call(DOWNLOAD_CMD.split())
    subprocess.check_call(INSTALL_CMD.split())
    subprocess.check_call('npm install -g meteorite'.split())

    init_code(config)
    init_bundle(config)

    hookenv.open_port(config['port'])
    subprocess.check_call(['chown', '-R', '{user}:{user}'.format(user=USER),
        BASE_DIR])

    config['mongo_url'] = ''
    write_upstart(config)
    config.save(METEOR_CONFIG)
    # wait for mongodb to join before starting


@hooks.hook('config-changed')
def config_changed():
    config = Config(METEOR_CONFIG)
    os.environ['HOME'] = os.path.expanduser('~' + USER)

    if config.changed('repo-url') or config.changed('demo-app'):
        hookenv.log('repo-url changed')
        ensure_rmtree(CODE_DIR)
        init_code(config)
    elif config.changed('repo-revision') and config['repo-url']:
        with chdir(CODE_DIR):
            subprocess.check_call([config['repo-type'], 'pull'])
        checkout(config['repo-type'], CODE_DIR, config['repo-revision'])

    if (config.changed('repo-url') or
            config.changed('repo-revision') or
            config.changed('bundled') or
            config.changed('demo-app')):
        init_bundle(config)

    if config.changed('port'):
        hookenv.open_port(config['port'])
        if config.previous('port'):
            hookenv.close_port(config.previous('port'))

    subprocess.check_call(['chown', '-R', '{user}:{user}'.format(user=USER),
        BASE_DIR])

    if config.previous('mongo_url'):
        mongo_host = config.previous('mongo_url').rsplit('/', 1)[0]
        mongo_url = '{}/{}'.format(mongo_host, config['app-name'])
        config['mongo_url'] = mongo_url

    write_upstart(config)
    config.save(METEOR_CONFIG)
    start()


@hooks.hook('mongodb-relation-changed')
def mongodb_relation_changed():
    config = Config()
    db_host = hookenv.relation_get('private-address')
    if not db_host:
        return
    db_port = hookenv.relation_get('port') or '27017'
    config['mongo_url'] = 'mongodb://{host}:{port}/{app_name}'.format(
            host=db_host, port=db_port, app_name=config['app-name'])
    write_upstart(config)
    config.save(METEOR_CONFIG)
    start()


@hooks.hook('mongodb-relation-departed')
def mongodb_relation_departed():
    host.service_stop(SERVICE)


@hooks.hook('upgrade-charm')
def upgrade_charm():
    hookenv.log('Upgrading Meteor')
    config = Config(METEOR_CONFIG)

    subprocess.check_call(DOWNLOAD_CMD.split())
    subprocess.check_call(INSTALL_CMD.split())
    init_bundle(config)
    if host.service_running(SERVICE):
        start()


@hooks.hook('start')
def start():
    if hookenv.is_relation_made('mongodb'):
        host.service_restart(SERVICE) or host.service_start(SERVICE)
    else:
        hookenv.log('Not starting - mongodb relation not present')


@hooks.hook('stop')
def stop():
    host.service_stop(SERVICE)


@hooks.hook('website-relation-changed')
def website_relation_changed():
    config = Config()
    hookenv.relation_set(port=config['port'],
            hostname=hookenv.unit_private_ip())


if __name__ == "__main__":
    # execute a hook based on the name the program is called by
    hooks.execute(sys.argv)
