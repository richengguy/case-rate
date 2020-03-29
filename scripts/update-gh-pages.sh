#!/bin/bash
set -eu

cp index.html gh-pages/.
cp details-*.html gh-pages/.

cd gh-pages

git config user.name "richengguy"
git config user.email "richengguy@users.noreply.github.com"
git add *.html
git commit -m "Updated on $(date)."
git push
