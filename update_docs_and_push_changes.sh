#! /bin/bash

git add src
git commit -m 'updates'

python -m mkdocs build

git add --all
git commit -m 'updated docs and site'

python -m mkdocs gh-deploy

git push