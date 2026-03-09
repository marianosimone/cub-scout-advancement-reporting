# cub-scout-advancement-reporting
A script to help Den Leaders and Cubmasters track which requirements their scouts still need to complete to make rank. Also creates report cards for dens!

A note:
  This started as a quick and dirty project. Half of it is vibe coded, and I haven't put a ton of effort at the moment into making it the most efficient or the most beautiful code. This is really a quick and dirty MVP, but it works and I thought I'd share with the community so you can all help improve/make it better!

  See the "Sample Output" folder for what these reports look like when generated

This script should be run in a folder and creates several different documents which are helpful for your Den Leaders and Cubmaster to manage advancement for your Pack!
1. Pack Report - contains an overview of scouts at all ranks and the percent complete towards their rank. Written to the directory where you run the script from.
2. Den Reports - Contains an overview of all the scouts in a den, a sorted list of remaining requirements to be completed (sorted by the requirements needed by the most scouts, and listing which scouts still need that requirement), and containing "report cards" that spell out which requirements each scout still needs. Copies are written to the directory where you run the script from, and to the rank-specific folder
3. Individual report cards - each rank will have a folder created for it, and in there will be written a "report card" file for each scout, outlining the requirements they still need to complete to make rank. Useful for emailing to parents as we get closer to the end of the scouting year!

**In order to personalize the reports**
1. Replace "logo.png" in the logos folder with your pack logo, if you have one
2. Look for all instances of "logo.png" in the advancement reports script (there's about 3 places): you may have to adjust the radio on height/width if your pack logo is not perfectly square
3. Replace the PACK_NUM variable with your pack's number

**Adventure URLs and images**
- `requirements.json` lists each adventure with a `url` (Scouting America adventure page). The report shows the adventure loop/pin image next to each adventure title when the image exists in the `img/` directory.
- One-off setup: download images into `img/` with: `uv run python download_adventure_images.py --browser`. This uses Playwright (headless Chromium) to pass Cloudflare’s check, then fetches each image. Requires `uv add playwright` and `uv run playwright install chromium` once. Without `--browser`, the script tries direct HTTP (often 403 from scouting.org).

**In order to run the script,**
1. You will need to generate a report from Internet Advancement (see below)
2. Put the csv report into the same directory as the script. Make sure it's titled "reportbuilder.csv"
3. Run the script from the command line:
   - **With [uv](https://docs.astral.sh/uv/)** (recommended): `uv run python AdvancementReports.py`
   - Or with a regular Python env: `python AdvancementReports.py`

**In order to generate the report from Internet Advancement**
In Internet Advancement:
<ol><li>Go to Reports on the sidebar</li>
<li>Click "New Report" and select "New Custom Report (Report Builder)"</li>
<li>Check the following boxes:
<ul><li>Abbreviate last names (recommended, not required)</li>
  <li>Show Empty Requirements</li>
<li>Show Requirement Descriptions</li>
<li>Show CS Adventure Requirements (Version: Latest)</li>
<li>Show Current Rank</li>
<li>Show Next Rank</li>
<li>All Scouts (deselect any who you may have dropped/you don't want included)</li>
<li>For Each Rank:
<ul><li>Rank Status</li>
<li>Rank Requirements</li>
<li>Required Adventures</li></ul></li></ul></li>
<li>Click "Run"</li>
<li>Click the CSV button to download the file</li>
<li>Copy the csv file into the folder where you have the script</li>
<li>Rename the file to "reportbuilder.csv" </li>
