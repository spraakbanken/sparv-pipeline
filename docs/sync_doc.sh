#!/usr/bin/env bash
# Script for syncing documentation to server

# Exit on any errors
set -e

# Read variables user, host, path from config.sh
source config.sh

# Update version number
./set_version.sh

# Build docs
mkdocs build

# Sync files
rsync -rcLv --delete site/* $user@$host:${path:?}
