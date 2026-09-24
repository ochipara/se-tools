#!/bin/bash
set -e

echo "Verifying basic-python example..."
cd examples/basic-python
setool validate setool.json
setool analyze setool.json --output report --no-ui
cd ../..

echo "Verifying typed-python example..."
cd examples/typed-python
setool validate setool.json
setool analyze setool.json --output report --no-ui
cd ../..

echo "Verifying pytorch-inference example..."
cd examples/pytorch-inference
setool validate setool.json
setool analyze setool.json --output report --no-ui
cd ../..

echo "Verifying pytorch-training example..."
cd examples/pytorch-training
setool validate setool.json
setool analyze setool.json --output report --no-ui
cd ../..

echo "All examples verified successfully!"
