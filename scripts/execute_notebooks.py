"""Validate and execute submitted notebooks into outputs/notebooks."""
from pathlib import Path

import nbformat
from nbclient import NotebookClient

OUTPUT = Path("outputs/notebooks")
OUTPUT.mkdir(parents=True, exist_ok=True)
for source in [Path("notebooks/task1_bestbuy_reviews.ipynb"), Path("notebooks/task2_advanced_eda_text_mining.ipynb")]:
    notebook = nbformat.read(source, as_version=4)
    notebook = nbformat.validator.normalize(notebook)[1]
    nbformat.validate(notebook)
    nbformat.write(notebook, source)
    NotebookClient(notebook, timeout=180, kernel_name="python3", resources={"metadata": {"path": "notebooks"}}).execute()
    target = OUTPUT / f"{source.stem}_executed.ipynb"
    nbformat.write(notebook, target)
    print(f"Executed {source} -> {target}")
