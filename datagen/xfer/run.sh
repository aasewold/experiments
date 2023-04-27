#!/bin/bash

dirname=$(dirname "$0")

ssh-agent "$dirname/xfer.py" "$@"
