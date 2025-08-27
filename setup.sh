#!/usr/bin/env bash
set -euo pipefail

# Clone into a temp folder
git clone https://github.com/Yeeloman/Katesthe-core.git tmp-core

# Remove git history
rm -rf tmp-core/.git

# Move contents (including hidden files like .env.example, .pre-commit-config.yaml)
shopt -s dotglob
mv tmp-core/* .
shopt -u dotglob

# Remove the temporary folder
rm -rf tmp-core

echo "Ouuuuff... finally, the starting point is here!"
echo "Enjoy the starter project & happy coding!"

