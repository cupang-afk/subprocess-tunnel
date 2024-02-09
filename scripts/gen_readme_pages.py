"""Generate the code reference pages and navigation."""

from pathlib import Path

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()

src = Path(__file__).parent.parent

with mkdocs_gen_files.open("README.md", "w") as readme_file:
    readme_file.writelines((src / "README.md").read_text())
