#!/bin/sh
# usage: ablate.sh 'from' 'to' — restore dist, then edit the CSP meta in every page
set -e; cd /Users/cansin/code/noggin-spike-csp/site; rm -rf dist; cp -R ../dist.orig dist
find dist -name '*.html' -exec perl -pi -e "s/\Q$1\E/$2/g if /content-security-policy/" {} +
grep -o 'content-security-policy" content="[^;]*;[^;]*;[^;]*;[^;]*;' dist/index.html
