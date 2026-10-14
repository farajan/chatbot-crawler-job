#!/bin/bash
set -e

VERSION="0.1.2"

git tag -a "v${VERSION}" -m "Release v${VERSION}"
git push origin "v${VERSION}"

echo "Tag v${VERSION} created and pushed."
