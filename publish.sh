#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

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

# Ensure we're on the dev branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "dev" ]; then
    echo "Error: You must be on the dev branch to publish a new version"
    exit 1
fi

# Make sure test output files are in .gitignore
if ! grep -q "discriminator_tests.json" .gitignore 2>/dev/null; then
    echo "Adding test output files to .gitignore..."
    cat >> .gitignore << EOF
# Test output files
discriminator_tests.json
discriminator_tests.log
.coverage
coverage.xml
EOF
    git add .gitignore
    git commit -m "Add test output files to .gitignore"
    echo "Updated .gitignore and committed changes."
fi

# Clean up any test output files that might interfere with branch switching
echo "Cleaning up test output files..."
rm -f discriminator_tests.json discriminator_tests.log .coverage coverage.xml

# Make sure the working directory is clean (except for ignored files)
if ! git diff-index --quiet HEAD --; then
    echo "Error: Working directory has uncommitted changes"
    exit 1
fi

# Pull the latest changes from the dev branch
echo "Pulling latest changes from dev branch..."
git pull origin dev

# Run unit tests before proceeding
echo "Running unit tests..."
echo "Installing package with development dependencies..."
pip install -e ".[dev]"  # Install the package with dev dependencies

if ! python -m pytest; then
    echo "Error: Tests failed. Please fix the failing tests before publishing."
    exit 1
fi
echo "All tests passed successfully!"

# Clean up test output files again
echo "Cleaning up test output files..."
rm -f discriminator_tests.json discriminator_tests.log .coverage coverage.xml

# Update version in pyproject.toml
echo "Updating version in pyproject.toml to $VERSION_NO_V..."
sed -i.bak "s/^version = \".*\"/version = \"$VERSION_NO_V\"/" pyproject.toml
rm pyproject.toml.bak  # Remove backup file

# Update version in __init__.py (accounting for src layout)
INIT_PATH="src/pydantic_discriminated/__init__.py"
if [ -f "$INIT_PATH" ]; then
    if grep -q "__version__" "$INIT_PATH"; then
        # Update existing version
        echo "Updating version in $INIT_PATH..."
        sed -i.bak "s/__version__ = \".*\"/__version__ = \"$VERSION_NO_V\"/" "$INIT_PATH"
    else
        # Add version if it doesn't exist
        echo "Adding version to $INIT_PATH..."
        echo "" >> "$INIT_PATH"  # Add a newline
        echo "__version__ = \"$VERSION_NO_V\"" >> "$INIT_PATH"
    fi
    rm -f "${INIT_PATH}.bak"  # Remove backup file if it exists
else
    echo "Warning: $INIT_PATH not found, skipping version update in __init__.py"
fi

# Update documentation URL in pyproject.toml to point to the docs site
echo "Updating documentation URL in pyproject.toml..."
sed -i.bak 's|"Documentation" = ".*"|"Documentation" = "https://talbotknighton.github.io/trendify/"|' pyproject.toml
rm pyproject.toml.bak  # Remove backup file

# Check if email in pyproject.toml contains .org and fix it if needed
if grep -q "talbotknighton@gmail.org" pyproject.toml; then
    echo "Fixing email address in pyproject.toml..."
    sed -i.bak 's/talbotknighton@gmail.org/talbotknighton@gmail.com/g' pyproject.toml
    rm pyproject.toml.bak  # Remove backup file
fi

# Update README.md if it contains badge.fury.io badges
if [ -f "README.md" ] && grep -q "badge.fury.io" README.md; then
    echo "Updating badges in README.md..."
    sed -i.bak 's|https://badge.fury.io/py/trendify.svg|https://img.shields.io/pypi/v/trendify.svg|g' README.md
    sed -i.bak 's|https://badge.fury.io/py/trendify|https://pypi.org/project/trendify/|g' README.md
    rm README.md.bak  # Remove backup file
fi

# Make sure to add README.md to the commit
git add README.md

# Update docs/index.md badges if needed
if [ -f "docs/index.md" ]; then
    echo "Checking badges in docs/index.md..."
    if grep -q "badge.fury.io" docs/index.md; then
        echo "Updating PyPI badge in docs/index.md..."
        sed -i.bak 's|https://badge.fury.io/py/trendify.svg|https://img.shields.io/pypi/v/trendify.svg|g' docs/index.md
        sed -i.bak 's|https://badge.fury.io/py/trendify|https://pypi.org/project/trendify/|g' docs/index.md
        rm docs/index.md.bak  # Remove backup file
    fi
    
    # Update documentation badge to be more useful (not link to itself)
    if grep -q "docs-mkdocs-blue" docs/index.md; then
        echo "Updating documentation badge in docs/index.md..."
        sed -i.bak 's|[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://talbotknighton.github.io/trendify/)|[![API Reference](https://img.shields.io/badge/api-reference-blue.svg)](https://talbotknighton.github.io/trendify/api-reference/)|g' docs/index.md
        rm docs/index.md.bak  # Remove backup file
    fi
fi

# Update changelog if it exists
if [ -f "CHANGELOG.md" ]; then
    echo "Adding new version entry to CHANGELOG.md..."
    DATE=$(date +%Y-%m-%d)
    sed -i.bak "s/^# Changelog/# Changelog\n\n## $VERSION ($DATE)\n\n- TODO: Add release notes\n/" CHANGELOG.md
    rm CHANGELOG.md.bak  # Remove backup file
    
    # Open the changelog for editing
    echo "Opening CHANGELOG.md for editing. Please add release notes and save..."
    ${EDITOR:-vi} CHANGELOG.md
fi

# Check for consistency in version numbers
echo "Checking for version consistency..."
PYPROJECT_VERSION=$(grep "^version = " pyproject.toml | sed 's/version = "\(.*\)"/\1/')
INIT_VERSION=$(grep "__version__" "$INIT_PATH" 2>/dev/null | sed 's/__version__ = "\(.*\)"/\1/')

if [ "$PYPROJECT_VERSION" != "$VERSION_NO_V" ]; then
    echo "Error: Version in pyproject.toml ($PYPROJECT_VERSION) doesn't match requested version ($VERSION_NO_V)"
    exit 1
fi

if [ -n "$INIT_VERSION" ] && [ "$INIT_VERSION" != "$VERSION_NO_V" ]; then
    echo "Error: Version in $INIT_PATH ($INIT_VERSION) doesn't match requested version ($VERSION_NO_V)"
    exit 1
fi

echo "Version consistency check passed."

# Commit the version changes
echo "Committing version changes..."
git add pyproject.toml README.md docs/index.md
if [ -f "$INIT_PATH" ]; then
    git add "$INIT_PATH"
fi
if [ -f "CHANGELOG.md" ]; then
    git add CHANGELOG.md
fi
git commit -m "Bump version to $VERSION"

# Push changes to dev branch
echo "Pushing changes to dev branch..."
git push origin dev

# Build and deploy documentation locally
echo "Building and deploying documentation version $VERSION_NO_V locally..."
mike deploy "$VERSION_NO_V" latest --update-aliases
mike set-default latest

echo "Documentation built and deployed locally."
echo "To view the documentation locally, run: mike serve"

# Create pull request from dev to main
echo "Creating a pull request from dev to main..."
echo "Please go to GitHub and create the PR: https://github.com/TalbotKnighton/trendify/compare/main...dev"
echo "After the PR is reviewed and merged, run the following commands:"
echo "git checkout main"
echo "git pull origin main"
echo "git tag -a $VERSION -m \"Release $VERSION\""
echo "git push origin $VERSION"

# Ask if the PR has been merged
read -p "Has the PR been merged to main? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Clean up test output files again to ensure branch switching works
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
else
    echo "Please complete the PR process and then run:"
    echo "git checkout main"
    echo "git pull origin main"
    echo "git tag -a $VERSION -m \"Release $VERSION\""
    echo "git push origin $VERSION"
    echo "mike deploy \"$VERSION_NO_V\" latest --update-aliases --push --allow-empty"
    echo "mike set-default latest --push --allow-empty"
    echo "git checkout dev"
fi
