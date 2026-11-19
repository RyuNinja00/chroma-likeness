#!/bin/sh
# Builds releases/Chroma-Likeness-Marinara-<version>.zip with the "Chroma Likeness/" folder at the root.
set -e
cd "$(dirname "$0")/../extension"
version=$(sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' "Chroma Likeness/manifest.json")
out="../releases/Chroma-Likeness-Marinara-$version.zip"
rm -f "$out"
zip -qr "$out" "Chroma Likeness"
echo "Built releases/Chroma-Likeness-Marinara-$version.zip"
