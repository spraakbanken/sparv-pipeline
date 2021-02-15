#!/usr/bin/env bash

# Script for syncing documentation to server

# Read variables user, host, path from config.sh
source config.sh

# Update version number
./set_version.sh

# Sync files
rsync -av ./ $user@$host:$path --exclude '_media' --exclude 'developers-guide' --exclude 'user-manual' --exclude '*.sh' --exclude '.gitignore'
rsync -av --delete ../user-manual $user@$host:$path
rsync -av --delete ../developers-guide $user@$host:$path
rsync -av --delete ../images/ $user@$host:$path/_media
