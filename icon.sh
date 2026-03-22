#!/usr/bin/env bash


# dump svg xml
uv run \
    python discourse_sprite_dump.py https://forum.dirtbikechina.com \
        -o assets/sprite-dbc.xml


# generate icons
uv run --with cairosvg \
    python discourse_sprite_icons.py \
        -i assets/sprite-dbc.xml \
        -o assets/icons/ \
        --pdf \
        --xcassets DiscourseIcon.xcassets \
        --swift DiscourseIcon.swift \
        --enum-name DiscourseIcon


# overwrite icons in Xcode project
cp -r DiscourseIcons.xcassets/ ../../App/DiscourseIcons.xcassets/


# watch for duplicate icons
# manual copy of DiscourseIcon.swift enum content to ../../App/Views/DesignSystem/Icon/DiscourseIcon.swift