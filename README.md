# cub-scout-advancement-reporting
A script to help Den Leaders and Cubmasters track which requirements their scouts still need to complete to make rank. Also creates report cards for dens!

This script should be run in a folder and creates several different documents which are helpful for your Den Leaders and Cubmaster to manage advancement for your Pack!

1. Den Reports - Contains an overview of all the scouts in a Den, a sorted list of remaining requirements to be completed (sorted by the requirements needed by the most scouts, and listing which scouts still need that requirement), and containing "report cards" that spell out which requirements each scout still needs. Copies are written to the directory where you run the script from, and to the rank-specific folder
2. Individual report cards - each rank will have a folder created for it, and in there will be written a "report card" file for each scout, outlining the requirements they still need to complete to make rank. Useful for emailing to parents as we get closer to the end of the scouting year!

## 🗂 Generating Reports

1. Go to https://advancements.scouting.org/reports#custom
2. Create a "New Custom Report (Report Builder)"
3. Check the following boxes:
  - Settings
    - Show Empty Requirements
    - Show Requirement Descriptions
    - Show CS Adventure Requirements (Version: Latest)
    - Show Next Rank
  - Selections
    - All Scouts (deselect any who you may have dropped/you don't want included)
    - For Each Rank:
      - Rank Status
      - Rank Requirements
      - Required Adventures
      - Elective Adventures
4. Save it (So you can run it again in the future)
5. Click "Run" (If it fails with a message saying that it took too long, reduce the number of scouts)
6. Click the CSV button to download the file
7. Copy the CSV file into the folder where you have the script
8. Rename the file to `reportbuilder.csv`
9. Install [uv](https://docs.astral.sh/uv/)
10. Run `uv run python reports.py`


## ⚙️ Development

- `requirements.json` lists each adventure with a `url` (Scouting America adventure page). The report shows the adventure loop/pin image next to each adventure title when the image exists in the `img/` directory.
