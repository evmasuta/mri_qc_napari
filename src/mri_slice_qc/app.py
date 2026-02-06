import os
import re
import sys
import datetime
from typing import Optional, Tuple, List

import numpy as np
import pandas as pd
import h5py

from qtpy import QtWidgets, QtCore, QtGui

import napari


KEY_RE = re.compile(r"^(?P<phonetic>.+?)_(?P<series>.+?)_slice_(?P<slice>\d+)$")


def now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def parse_key(key: str) -> Tuple[str, str, Optional[int]]:
    """Returns (phonetic_id, series, slice_number or None)."""
    m = KEY_RE.match(key)
    if not m:
        return key, "", None
    phonetic = m.group("phonetic")
    series = m.group("series")
    slice_number = int(m.group("slice"))
    return phonetic, series, slice_number


class CsvStore(object):
    """Stores only viewed keys. Overwrites CSV on each update."""

    COLS = [
        "key",
        "phonetic_id",
        "series",
        "slice_number",
        "rating",
        "viewed",
        "first_viewed_at",
        "last_updated_at",
    ]

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.df = pd.DataFrame(columns=self.COLS)
        self.df.set_index("key", inplace=True, drop=False)

        if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
            try:
                loaded = pd.read_csv(csv_path)
                if "key" in loaded.columns:
                    # Ensure required cols exist
                    for c in self.COLS:
                        if c not in loaded.columns:
                            loaded[c] = np.nan
                    loaded = loaded[self.COLS]
                    loaded.set_index("key", inplace=True, drop=False)
                    self.df = loaded
            except Exception:
                # If CSV can't be read, keep empty
                pass

    def has_key(self, key: str) -> bool:
        return key in self.df.index

    def get_rating(self, key: str) -> int:
        if key in self.df.index:
            try:
                v = self.df.loc[key, "rating"]
                if pd.isna(v):
                    return 0
                return int(v)
            except Exception:
                return 0
        return 0

    def is_viewed(self, key: str) -> bool:
        if key in self.df.index:
            v = self.df.loc[key, "viewed"]
            if isinstance(v, (bool, np.bool_)):
                return bool(v)
            if isinstance(v, str):
                return v.strip().lower() in ("true", "1", "yes", "y")
            if pd.isna(v):
                return False
            try:
                return bool(int(v))
            except Exception:
                return False
        return False

    def mark_viewed(self, key: str) -> None:
        if key not in self.df.index:
            phonetic, series, slice_number = parse_key(key)
            self.df.loc[key, "key"] = key
            self.df.loc[key, "phonetic_id"] = phonetic
            self.df.loc[key, "series"] = series
            self.df.loc[key, "slice_number"] = slice_number if slice_number is not None else np.nan
            self.df.loc[key, "rating"] = 0
            self.df.loc[key, "viewed"] = True
            ts = now_iso()
            self.df.loc[key, "first_viewed_at"] = ts
            self.df.loc[key, "last_updated_at"] = ts
        else:
            self.df.loc[key, "viewed"] = True
            if pd.isna(self.df.loc[key, "first_viewed_at"]):
                self.df.loc[key, "first_viewed_at"] = now_iso()
            self.df.loc[key, "last_updated_at"] = now_iso()

    def set_rating(self, key: str, rating: int) -> None:
        rating = int(rating)
        if rating < 0:
            rating = 0
        if rating > 3:
            rating = 3
        if key not in self.df.index:
            self.mark_viewed(key)
        self.df.loc[key, "rating"] = rating
        self.df.loc[key, "last_updated_at"] = now_iso()

    def save(self) -> None:
        outdir = os.path.dirname(os.path.abspath(self.csv_path))
        if outdir and not os.path.exists(outdir):
            os.makedirs(outdir, exist_ok=True)
        self.df.to_csv(self.csv_path, index=False)


class KeyComboBox(QtWidgets.QComboBox):
    """QComboBox with per-item coloring for viewed vs not-viewed."""

    def __init__(self, parent=None):
        super(KeyComboBox, self).__init__(parent)
        self.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)

    def set_item_viewed(self, idx: int, viewed: bool) -> None:
        if idx < 0:
            return
        bg = QtGui.QColor(200, 255, 200) if viewed else QtGui.QColor(255, 220, 220)
        self.setItemData(idx, bg, QtCore.Qt.BackgroundRole)


class ControlPanel(QtWidgets.QWidget):
    sig_prev = QtCore.Signal()
    sig_next = QtCore.Signal()
    sig_select_idx = QtCore.Signal(int)
    sig_rating_changed = QtCore.Signal(int)

    def __init__(self, parent=None):
        super(ControlPanel, self).__init__(parent)

        self.combo = KeyComboBox()
        self.btn_prev = QtWidgets.QPushButton("◀ Prev")
        self.btn_next = QtWidgets.QPushButton("Next ▶")

        self.lbl_status = QtWidgets.QLabel("Status: —")
        self.lbl_status.setWordWrap(True)

        self.grp = QtWidgets.QGroupBox("Quality score (0–3)")
        self.grp_layout = QtWidgets.QVBoxLayout(self.grp)

        self.rb0 = QtWidgets.QRadioButton("0 (default)")
        self.rb1 = QtWidgets.QRadioButton("1")
        self.rb2 = QtWidgets.QRadioButton("2")
        self.rb3 = QtWidgets.QRadioButton("3")

        for rb in [self.rb0, self.rb1, self.rb2, self.rb3]:
            rb.setMinimumHeight(30)
            f = rb.font()
            f.setPointSize(max(12, f.pointSize()))
            rb.setFont(f)
            self.grp_layout.addWidget(rb)

        self.rb0.setChecked(True)

        nav_layout = QtWidgets.QHBoxLayout()
        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.btn_next)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Slice key"))
        layout.addWidget(self.combo)
        layout.addLayout(nav_layout)
        layout.addSpacing(10)
        layout.addWidget(self.lbl_status)
        layout.addSpacing(10)
        layout.addWidget(self.grp)
        layout.addStretch(1)

        self.btn_prev.clicked.connect(self.sig_prev.emit)
        self.btn_next.clicked.connect(self.sig_next.emit)
        self.combo.currentIndexChanged.connect(self._on_combo_changed)

        self.rb0.toggled.connect(lambda checked: self._emit_rating(0, checked))
        self.rb1.toggled.connect(lambda checked: self._emit_rating(1, checked))
        self.rb2.toggled.connect(lambda checked: self._emit_rating(2, checked))
        self.rb3.toggled.connect(lambda checked: self._emit_rating(3, checked))

    def _on_combo_changed(self, idx: int) -> None:
        if idx >= 0:
            self.sig_select_idx.emit(idx)

    def _emit_rating(self, rating: int, checked: bool) -> None:
        if checked:
            self.sig_rating_changed.emit(rating)

    def set_keys(self, keys: List[str]) -> None:
        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItems(keys)
        self.combo.blockSignals(False)

    def set_current_index(self, idx: int) -> None:
        self.combo.blockSignals(True)
        self.combo.setCurrentIndex(idx)
        self.combo.blockSignals(False)

    def set_status(self, key: str, viewed: bool, rating: int, idx: int, n: int) -> None:
        s_viewed = "VIEWED" if viewed else "NOT viewed"
        self.lbl_status.setText(f"Status: {s_viewed} | Rating: {rating} | {idx+1}/{n}\n{key}")

    def set_rating_buttons(self, rating: int) -> None:
        rating = int(rating)
        if rating <= 0:
            self.rb0.setChecked(True)
        elif rating == 1:
            self.rb1.setChecked(True)
        elif rating == 2:
            self.rb2.setChecked(True)
        else:
            self.rb3.setChecked(True)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, h5_path: str, csv_path: str):
        super(MainWindow, self).__init__()
        self.setWindowTitle("MRI Slice QC (0–3)")

        self.h5_path = h5_path
        self.h5 = h5py.File(h5_path, "r")

        keys = []

        def _visit(name, obj):
            if isinstance(obj, h5py.Dataset):
                keys.append(name)

        self.h5.visititems(_visit)
        self.keys = sorted(keys)

        if len(self.keys) == 0:
            raise RuntimeError("No datasets found in the HDF5 file.")

        self.store = CsvStore(csv_path)

        self.viewer = napari.Viewer(title="MRI Slice QC Viewer")
        self.img_layer = None

        self.panel = ControlPanel()
        self.panel.set_keys(self.keys)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(central)
        layout.addWidget(self.panel, stretch=0)
        layout.addWidget(self.viewer.window._qt_window, stretch=1)
        self.setCentralWidget(central)

        self.cur_idx = 0
        self._loading = False

        self.panel.sig_prev.connect(self.on_prev)
        self.panel.sig_next.connect(self.on_next)
        self.panel.sig_select_idx.connect(self.on_select_idx)
        self.panel.sig_rating_changed.connect(self.on_rating_changed)

        self.load_idx(0)

    def closeEvent(self, event):
        try:
            self.store.save()
        except Exception:
            pass
        try:
            self.h5.close()
        except Exception:
            pass
        return super(MainWindow, self).closeEvent(event)

    def on_prev(self):
        if self.cur_idx > 0:
            self.load_idx(self.cur_idx - 1)

    def on_next(self):
        if self.cur_idx < len(self.keys) - 1:
            self.load_idx(self.cur_idx + 1)

    def on_select_idx(self, idx: int):
        if idx == self.cur_idx:
            return
        if 0 <= idx < len(self.keys):
            self.load_idx(idx)

    def on_rating_changed(self, rating: int):
        if self._loading:
            return
        key = self.keys[self.cur_idx]
        self.store.set_rating(key, rating)
        self._refresh_item_colors()
        self._refresh_status()
        self.store.save()

    def _refresh_item_colors(self):
        for i, k in enumerate(self.keys):
            self.panel.combo.set_item_viewed(i, self.store.is_viewed(k))

    def _refresh_status(self):
        key = self.keys[self.cur_idx]
        viewed = self.store.is_viewed(key)
        rating = self.store.get_rating(key)
        self.panel.set_status(key, viewed, rating, self.cur_idx, len(self.keys))
        self.panel.set_rating_buttons(rating)

    def load_idx(self, idx: int):
        if idx < 0 or idx >= len(self.keys):
            return

        # Overwrite CSV on advance (as requested)
        try:
            self.store.save()
        except Exception:
            pass

        self._loading = True
        self.cur_idx = idx
        key = self.keys[idx]

        arr = self.h5[key][()]
        if arr.ndim != 3:
            raise RuntimeError("Dataset is not 3D (rows, cols, timepoints): %s (shape=%s)" % (key, arr.shape))

        # (rows, cols, time) -> (time, rows, cols)
        arr_tyx = np.transpose(arr, (2, 0, 1))

        if self.img_layer is None:
            self.img_layer = self.viewer.add_image(arr_tyx, name="slice", axis_labels=("t", "y", "x"))
        else:
            self.img_layer.data = arr_tyx
            self.img_layer.name = "slice"

        # Mark as viewed on load
        self.store.mark_viewed(key)

        # Sync selection + UI
        self.panel.set_current_index(idx)
        self._refresh_item_colors()
        self._refresh_status()

        # Overwrite CSV on view
        self.store.save()

        self._loading = False


def prompt_csv_path() -> Optional[str]:
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Question)
    msg.setWindowTitle("MRI Slice QC")
    msg.setText("Choose output CSV option:")
    btn_new = msg.addButton("Create new CSV", QtWidgets.QMessageBox.AcceptRole)
    btn_load = msg.addButton("Load existing CSV", QtWidgets.QMessageBox.AcceptRole)
    msg.addButton("Cancel", QtWidgets.QMessageBox.RejectRole)

    msg.exec_()
    clicked = msg.clickedButton()

    if clicked == btn_new:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            None, "Create new output CSV", "", "CSV Files (*.csv);;All Files (*)"
        )
        return path if path else None

    if clicked == btn_load:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            None, "Select existing output CSV", "", "CSV Files (*.csv);;All Files (*)"
        )
        return path if path else None

    return None


def prompt_h5_path() -> Optional[str]:
    path, _ = QtWidgets.QFileDialog.getOpenFileName(
        None, "Select HDF5 file", "", "HDF5 Files (*.h5 *.hdf5);;All Files (*)"
    )
    return path if path else None


def main():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    csv_path = prompt_csv_path()
    if not csv_path:
        return

    h5_path = prompt_h5_path()
    if not h5_path:
        return

    if not os.path.exists(h5_path):
        QtWidgets.QMessageBox.critical(None, "Error", "HDF5 file does not exist.")
        return

    try:
        win = MainWindow(h5_path=h5_path, csv_path=csv_path)
    except Exception as e:
        QtWidgets.QMessageBox.critical(None, "Error", str(e))
        return

    win.resize(1300, 850)
    win.show()
    napari.run()


if __name__ == "__main__":
    main()
