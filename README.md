# Overview

This charm deploys a Meteor [http://meteor.com] application from source
control (git or hg repo).

# Usage

If you deploy this charm without overriding any of the default
configuration, a sample Meteor app will be deployed.

When deploying a real app, the charm assumes that you've created a
Meteor app by running `meteor create <app_name>` and pushed the contents
of the `<app_name>` directory to a publicly accessible git or hg repo.

Create a ~/meteor-app.yaml config file:

  meteor:
    app-name: <app_name>
    repo-url: <clone url>

Deploy the app:

  juju deploy --config ~/meteor-app.yaml meteor

Once `juju status` reports that the service is started, browse the app:

  http://ip-address:3000

# Contact Information

Author: Tim Van Steenburgh `<tim.van.steenburgh@canonical.com>`
Report bugs at: http://bugs.launchpad.net/charms/+source/meteor
Location: http://jujucharms.com/charms/precise/meteor
