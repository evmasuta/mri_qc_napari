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
  - Next unviewed button (skips reviewed slices)
- Rate each slice on a **0–3** scale (radio buttons; single choice)
- Marks a slice as **viewed** when it is loaded
- Auto-plays cine/time-series slices on load (when `timepoints > 1`)
- **Writes/overwrites the CSV** whenever:
  - You change the rating, or
  - You navigate to a different slice

## Install

Create an environment with Python 3.9 (3.7–3.9 should work). Example:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -U pip
pip install -e .
```

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

## Keyboard shortcuts

When the main window has focus (works even while the Napari viewer is focused):

- `0`, `1`, `2`, `3` — set the quality score for the current slice
- `←` / `→` — previous / next slice key
- `N` — jump to the next **unviewed** slice (wraps around)

Notes:
- The app continues to **auto-save** the CSV on navigation and score changes.
- Cine / time-series slices will auto-play on load (when `timepoints > 1`).
