#!/usr/bin/env bash

# Script for syncing documentation to server

user="fksparv"
host="k2"
path="/var/www/html_sb/sparv/docs"

# Update version number
./set_version.sh

# Sync files
rsync -av --delete ./ $user@$host:$path --exclude '_media' --exclude 'developers-guide' --exclude 'user-manual' --exclude '*.sh'
rsync -av --delete ../user-manual $user@$host:$path
rsync -av --delete ../developers-guide $user@$host:$path
rsync -av --delete ../images $user@$host:$path/_images
