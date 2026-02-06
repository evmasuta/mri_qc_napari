# MRI Slice QC Napari GUI

A simple Napari-based reviewer tool for scoring cardiac MRI slices (0–3) per slice (dataset) stored in a single HDF5 file.

## Data assumptions

- Input is an HDF5 file.
- Each dataset key is formatted:

  `{phonetic_id}_{series}_slice_{slice_number}`

- Each dataset is a 3D array shaped:

  `(rows, cols, timepoints)` where `timepoints >= 1`

The GUI will display time as a Napari time axis (frames).

## What it does

- Prompts on startup to **create a new CSV** or **load an existing CSV**
- Prompts to select the **HDF5 file**
- Lists all HDF5 dataset keys (alphabetized)
- Navigate keys via:
  - Dropdown (color-coded: green = viewed, red = not-viewed)
  - Previous / Next buttons
- Rate each slice on a **0–3** scale (radio buttons; single choice)
- Marks a slice as **viewed** when it is loaded
- **Writes/overwrites the CSV** whenever:
  - You change the rating, or
  - You navigate to a different slice

## Install

Create an environment with Python 3.9 (3.7–3.9 should work). Example:

1) conda create -n qc-gui python=3.9 -y
2) conda activate qc-gui
3) conda install -c conda-forge napari pyqt -y
4) cd /path/to/qg-gui
5) pip install -e .



> Napari installs can be heavy; if you hit Qt issues, consider using `conda`.

## Run

```bash
mri-slice-qc
```

## Output CSV schema

The tool writes only rows for slices that have been viewed.

Columns:
- `key`
- `phonetic_id`
- `series`
- `slice_number`
- `rating` (0–3)
- `viewed` (True/False)
- `first_viewed_at`
- `last_updated_at`
