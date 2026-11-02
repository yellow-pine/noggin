#!/bin/sh
# The sim reports (model/build/reports, once just sim made them) into the built site's site/dist/reports with an index:
# just site-reports, and Site Deploy (pages.yml) on main's site with the reports Checks saved, where just is not set up.
[ ! -d model/build/reports ] || { rm -rf site/dist/reports && cp -R model/build/reports site/dist/reports && cd site/dist/reports && ls *.json *.xml | sed 's|.*|<a href="&">&</a><br>|' > index.html; }
