#!/bin/bash
set -eu

cp index.html gh-pages/.
cp details-*.html gh-pages/.

cd gh-pages

# Need to use the GitHub authentication token to cause a gh-pages build.  More
# details here;
# https://www.innoq.com/en/blog/github-actions-automation/
repo_uri="https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"

git config user.name "richengguy"
git config user.email "richengguy@users.noreply.github.com"

git remote set-url origin "$repo_uri"

git add *.html
git commit -m "Updated on $(date)."
git push
