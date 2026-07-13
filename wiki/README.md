# Wiki source

This directory is the version-controlled source of truth for the GitHub Wiki. Keeping the pages in the main repository makes documentation changes reviewable and prevents the wiki from drifting away from the code.

The repository includes a manual `publish-wiki.yml` workflow. GitHub requires the Wiki to be initialized once through the repository UI before its Git remote exists. After initialization, run the workflow to replace the Wiki with these pages.
