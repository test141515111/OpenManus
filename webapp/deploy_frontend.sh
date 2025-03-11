#!/bin/bash
set -e

# Create build directory
mkdir -p build
cp -r templates/* build/
mkdir -p build/static
cp -r static/* build/static/

# Replace API key placeholder with environment variable
if [ -n "$oepnai_api" ]; then
  echo "Using OpenAI API key from environment"
else
  echo "Warning: OpenAI API key not found in environment"
fi

echo "Build completed. Files in build directory:"
ls -la build/

echo "Ready for deployment"
