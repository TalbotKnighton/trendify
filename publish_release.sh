#!/bin/bash
echo "Publish script started"
set -e  # Exit immediately if a command exits with a non-zero status
echo "Version argument: $1"

# Check if a version argument was provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 v0.1.1"
    exit 1
fi

VERSION=$1
VERSION_NO_V="${VERSION#v}"  # Remove the 'v' prefix for use in pyproject.toml

# Validate version format
if ! [[ $VERSION =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Version must be in format vX.Y.Z (e.g., v0.1.1)"
    exit 1
fi

echo "This script will complete the release process for version $VERSION"
echo "Make sure the PR has been reviewed and merged to main before proceeding."
read -p "Has the PR been merged to main? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Please complete the PR process first, then run this script again."
    exit 1
fi

# Clean up test output files to ensure branch switching works
echo "Cleaning up test output files..."
rm -f discriminator_tests.json discriminator_tests.log .coverage coverage.xml

# Switch to main and pull latest changes
echo "Switching to main branch and pulling latest changes..."
git checkout main
git pull origin main

# Create and push the tag
echo "Creating and pushing tag $VERSION..."
git tag -a $VERSION -m "Release $VERSION"
git push origin $VERSION

# Wait for the package to be published to PyPI
echo "Waiting for package to be published to PyPI..."
echo "This may take a few minutes. The GitHub Actions workflow should be building and publishing your package."
echo "You can check the progress here: https://github.com/TalbotKnighton/trendify/actions"

read -p "Has the package been published to PyPI? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Push documentation to GitHub Pages
    echo "Pushing documentation to GitHub Pages..."
    mike deploy "$VERSION_NO_V" latest --update-aliases --push
    mike set-default latest --push
else
    echo "Skipping documentation push. You can do this manually later with:"
    echo "mike deploy \"$VERSION_NO_V\" --alias latest --update-aliases --push"
    echo "mike set-default latest --push"
fi

# Switch back to dev branch
echo "Switching back to dev branch..."
git checkout dev

echo "Release process completed successfully!"
echo "Documentation has been deployed to GitHub Pages."