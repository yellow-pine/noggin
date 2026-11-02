#!/bin/sh
# The sim reports (model/build/reports, once just sim made them) into the built site's site/dist/reports, each listed on
# its page (site/src/pages/reports.astro) in place of the line saying there are none: just site-reports, and Checks'
# Deploy (checks.yml) on main's site with the reports Checks saved, where just is not set up.
[ ! -d model/build/reports ] || {
  cp -R model/build/reports/. site/dist/reports/ && cd site/dist/reports &&
    links=$(ls *.json *.xml 2>/dev/null | sed 's|.*|<li><a href="&">&</a></li>|' | tr -d '\n') &&
    sed "s|<li data-reports[^>]*>[^<]*</li>|$links|" index.html > index.html.new && mv index.html.new index.html
}
