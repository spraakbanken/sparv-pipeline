#!/usr/bin/env bash
# Script for syncing documentation to server

DRYRUN=""
SUBDIR=""
while getopts "hnd" opt; do
    case $opt in
        h)
            echo "Usage: $0 [-n]"
            echo "  -n        Perform a dry run for rsync operations."
            echo "  -d        Sync to 'dev' subdirectory."
            echo "  -h        Display this help message."
            exit 0
            ;;
        n)
            DRYRUN="--dry-run"
            ;;
        d)
            SUBDIR="/dev"
            ;;
        *)
            echo "Invalid option. Use -h for help."
            exit 1
            ;;
    esac
done

# Exit on any errors
set -e

# Read variables user, host, path from config.sh and check if variables are set
source config.sh
if [[ -z "$user" || -z "$host" || -z "$path" ]]; then
  echo "Error: user, host, or path is not set in config.sh"
  exit 1
fi


# Extract version number from zensical.toml, ignore comments and trailing spaces
version=$(grep -oP -m 1 '^version =\s*\K[^#]+' zensical.toml | sed 's/[[:space:]]*$//')
echo -e "\nReleasing documentation for Sparv version: $version\n"

# Prompt user to continue
read -p "Continue with this version? [y/N] " answer
case "$answer" in
    [Yy]* ) ;;
    * ) echo "Aborted."; exit 1;;
esac


# Build docs
echo -e "\nBuilding documentation with Zensical ..."
cp ../CHANGELOG.md site/changelog.md
zensical build
rm site/changelog.md

# Sync files or do dry run
if [[ -n "$DRYRUN" ]]; then
    echo -e "\nPerforming a dry run for rsync operations. No files will be transferred.\n"
fi
echo -e "\nSyncing files to $user@$host:$path$SUBDIR ..."
rsync $DRYRUN -rcLv --delete build/* $user@$host:${path:?}$SUBDIR
