# Overview

This charm deploys a Meteor [http://meteor.com] application.

You can deploy your own app by providing a Git or Mercurial repo url,
or you can deploy any of the five built-in demo apps.

# Usage

The quickest way to get started is to deploy the charm with the default
configuration:

  juju deploy meteor
  juju deploy mongodb
  juju add-relation meteor mongodb
  juju expose meteor

Alternatively, you can deploy behind HAProxy:

  juju deploy meteor
  juju deploy mongodb
  juju deploy haproxy
  juju add-relation meteor mongodb
  juju add-relation meteor haproxy
  juju expose haproxy

After deploying with the default configuration, the "todos" demo app
will be accessible over http on the public ip and port of the exposed
service. Use `juju status` to find the public ip and port.

## Deploying Demo Apps

To run a different demo app, try any of the following:

  juju set meteor demo-app=leaderboard
  juju set meteor demo-app=wordplay
  juju set meteor demo-app=parties
  juju set meteor demo-app=clock
  juju set meteor demo-app=todos

## Deploying from Git or Mercurial

To run your own app, you must provide a Git or Mercurial clone url,
e.g.:

  juju set meteor repo-type=git repo-url=https://github.com/SachaG/Telescope.git
  juju set meteor repo-type=hg repo-url=https://tvansteenburgh@bitbucket.org/tvansteenburgh/planning-poker

If you push new changes to your repo, you can update the running app to
the new version:

  juju set meteor repo-revision=39a85df

The revision can be a branch name, tag name, or commit hash.

# Contact Information

Author: Tim Van Steenburgh <tim.van.steenburgh@canonical.com>
Report bugs at: https://github.com/tvansteenburgh/meteor-charm/issues
Location: http://jujucharms.com/charms/precise/meteor
