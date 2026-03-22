#!/usr/bin/env bash


# generate emojis
uv run \
    python discourse_emojis.py \
    --html emojis.html \
    --out assets/emojis \
    --base-url https://forum.dirtbikechina.com \
    --download
