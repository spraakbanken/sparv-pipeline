#!/usr/bin/env bash

# Script for syncing documentation to server

# Read variables user, host, path from config.sh
source config.sh

# Update version number
./set_version.sh

# Sync files
rsync -rcLv --delete ./* $user@$host:${path:?} --exclude '*.sh' --exclude '.gitignore'
