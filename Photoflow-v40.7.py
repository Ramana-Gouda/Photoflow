#!/usr/bin/env python3
"""
FOTO WORKFLOW AUTOMATISERING (v40.7)
- STABILITEIT: Toont grafische foutmeldingen bij ontbrekende software.
- STABILITEIT: Native KDE/GNOME dialoog ondersteuning via xdg-desktop-portal.
- STAP 1: Sorteer RAW's naar 'geordend_op_reeks'.
- STAP 2: Batch HDR (Enfuse/HDRmerge).
- STAP 3: Verplaats resultaten en schoont reeksen op.
"""

import sys
import os
import shutil
import subprocess
from datetime import datetime
import glob
import uuid

# --- CONFIGURATIE ---
CONFIG = {
    "SORTED_DIR_NAME": "geordend_op_reeks",
    "HDR_COLLECT_NAME": "Verzamelde_HDR_bestanden",
    "HDRMERGE_DIR_NAME": "hdr_dng_files",
    "RAW_EXTENSION": "RW2",
    "MAX_GAP_SECONDS": 4,
    "DT_XMP_FILE": "oppepper.xmp"
}

RAW_FORMATS = ["AUTO (Alle RAWs)", "ARW (Sony)", "CR2 (Canon)", "CR3 (Canon)", "NEF (Nikon)", "ORF (Olympus)", "RAF (Fuji)", "DNG (Adobe)", "RW2 (Panasonic)"]

ENV_STABLE = os.environ.copy()
ENV_STABLE["OMP_NUM_THREADS"] = "12"

try:
    from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                                 QHBoxLayout, QPushButton, QLabel, QLineEdit,
                                 QFileDialog, QProgressBar, QTextEdit, QTabWidget,
                                 QComboBox, QCheckBox, QMessageBox)
    from PySide6.QtCore import QThread, QObject, Signal, Slot, Qt
except ImportError:
    print("Fout: PySide6 niet gevonden. Installeer met: sudo pacman -S pyside6")
    sys.exit(1)

def get_missing_dependencies():
    """Controleert op benodigde software en het XMP-bestand."""
    missing_tools = []
    required_tools = {
        'exiftool': 'perl-image-exiftool',
        'darktable-cli': 'darktable',
        'align_image_stack': 'hugin',
        'enfuse': 'enblend-enfuse',
        'hdrmerge': 'hdrmerge'
    }

    for tool, pkg in required_tools.items():
        if shutil.which(tool) is None:
            missing_tools.append(f"<b>{tool}</b> (pakket: <i>{pkg}</i>)")

    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    xmp_path = os.path.join(script_dir, CONFIG["DT_XMP_FILE"])

    xmp_error = ""
    if not os.path.exists(xmp_path):
        xmp_error = f"<br><br>Bestand <b>{CONFIG['DT_XMP_FILE']}</b> niet gevonden in:<br><i>{script_dir}</i>"

    if missing_tools or xmp_error:
        msg = "De volgende onderdelen ontbreken om dit script te kunnen gebruiken:<br><ul>"
        for m in missing_tools:
            msg += f"<li>{m}</li>"
        msg += "</ul>" + xmp_error
        return msg
    return None

def smart_copy(src, dst):
    try:
        subprocess.run(['cp', '--reflink=auto', src, dst], check=True, capture_output=True)
    except:
        shutil.copy2(src, dst)

# --- WORKER: STAP 1 (SORTEREN) ---
class SortWorker(QObject):
    finished, progress, log = Signal(), Signal(int), Signal(str)

    def __init__(self, source_dir, stack_mode, keep_mode, raw_ext_idx):
        super().__init__()
        self.source_dir, self.stack_mode, self.keep_mode = source_dir, stack_mode, keep_mode
        self.ext_filter = None if raw_ext_idx == 0 else RAW_FORMATS[raw_ext_idx].split(' ')[0].lower()

    @Slot()
    def run(self):
        try:
            allowed = [3] if self.stack_mode == 1 else [5] if self.stack_mode == 2 else [7] if self.stack_mode == 3 else [7, 5, 3]
            self.log.emit(f"Stap 1: Analyseren en sorteren...")
            cmd = ['exiftool', '-q', '-S3', '-T', '-n', '-FileName', '-DateTimeOriginal', '-ExposureTime', '-FNumber']
            if self.ext_filter:
                cmd += ['-ext', self.ext_filter]
            else:
                for fmt in RAW_FORMATS[1:]: cmd += ['-ext', fmt.split(' ')[0].lower()]
            cmd.append(self.source_dir)
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            photo_list = []
            for line in filter(None, result.stdout.strip().split('\n')):
                parts = line.split('\t')
                if len(parts) < 4: continue
                dt = datetime.strptime(parts[1], "%Y:%m:%d %H:%M:%S")
                photo_list.append({'name': parts[0], 'ts': int(dt.timestamp()), 'exp': f"S{parts[2]}A{parts[3]}"})
            if not photo_list:
                self.log.emit("Geen RAW-bestanden gevonden."); self.finished.emit(); return
            photo_list.sort(key=lambda x: (x['ts'], x['name']))
            dest_base = os.path.join(self.source_dir, CONFIG["SORTED_DIR_NAME"])
            os.makedirs(dest_base, exist_ok=True)
            curr_group = []
            for i, photo in enumerate(photo_list):
                if not curr_group or (photo['ts'] - curr_group[-1]['ts'] <= CONFIG["MAX_GAP_SECONDS"]):
                    curr_group.append(photo)
                else:
                    self._process_group(curr_group, dest_base, allowed)
                    curr_group = [photo]
                self.progress.emit(int((i / len(photo_list)) * 100))
            if curr_group: self._process_group(curr_group, dest_base, allowed)
            self.log.emit("Sorteren voltooid.")
        except Exception as e: self.log.emit(f"Fout: {e}")
        finally: self.finished.emit()

    def _process_group(self, group, base, allowed):
        total = len(group)
        for s in allowed:
            if s > 0 and total % s == 0:
                for i in range(total // s):
                    subset = group[i*s:(i+1)*s]
                    if len(set([p['exp'] for p in subset])) > 1:
                        target = os.path.join(base, datetime.fromtimestamp(subset[0]['ts']).strftime('%Y-%m-%d_%H-%M-%S_reeks'))
                        os.makedirs(target, exist_ok=True)
                        for idx, f in enumerate(subset):
                            src = os.path.join(self.source_dir, f['name'])
                            smart_copy(src, os.path.join(target, f['name']))
                            if self.keep_mode == 1 or (self.keep_mode == 0 and idx > 0):
                                if os.path.exists(src): os.remove(src)
                return

# --- WORKER: STAP 2 (HDR VERWERKING) ---
class HdrWorker(QObject):
    finished, progress, log = Signal(), Signal(int), Signal(str)
    def __init__(self, base_dir, method, bit_depth):
        super().__init__(); self.base_dir, self.method, self.bit_depth = base_dir, method, bit_depth

    @Slot()
    def run(self):
        subdirs = sorted([d.path for d in os.scandir(self.base_dir) if d.is_dir() and not d.name.startswith('_')])
        if not subdirs: self.log.emit("Geen reeksen gevonden."); self.finished.emit(); return
        for i, path in enumerate(subdirs):
            name = os.path.basename(path)
            self.log.emit(f"\n--- Verwerken: {name} ---")
            if self.method == 'enfuse': self._do_enfuse_stable(path, name)
            else: self._do_hdrmerge(path, name)
            self.progress.emit(int(((i + 1) / len(subdirs)) * 100))
        self.log.emit("\nHDR-taken voltooid.")
        self.finished.emit()

    def _do_enfuse_stable(self, path, name):
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        xmp = os.path.join(script_dir, CONFIG["DT_XMP_FILE"])
        raw_files = [f for f in os.listdir(path) if f.split('.')[-1].upper() in [fmt.split(' ')[0] for fmt in RAW_FORMATS[1:]]]
        if not raw_files: return
        tmp_dir = os.path.join(path, ".tmp_hdr"); os.makedirs(tmp_dir, exist_ok=True)
        cfg_dir = os.path.join(tmp_dir, "dt_cfg"); os.makedirs(cfg_dir, exist_ok=True)
        tifs = []
        for r in sorted(raw_files):
            self.log.emit(f"  > Converteren: {r}")
            out = os.path.join(tmp_dir, f"{os.path.splitext(r)[0]}.tif")
            cmd = ['darktable-cli', os.path.join(path, r), xmp, out, '--core', '--configdir', cfg_dir, '--library', ':memory:', '--disable-opencl']
            subprocess.run(cmd, capture_output=True)
            if os.path.exists(out): tifs.append(out)
        if len(tifs) >= 2:
            ali = os.path.join(tmp_dir, "ali_")
            subprocess.run(['align_image_stack', '-v', '-C', '-a', ali] + tifs, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            out_h = os.path.join(path, f"{name}_HDR_{self.bit_depth}bit.tif")
            cmd = ['enfuse', '--exposure-weight=1', '--saturation-weight=0.2', '--hard-mask', '--output', out_h]
            subprocess.run(cmd + sorted(glob.glob(f"{ali}*.tif")), env=ENV_STABLE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.log.emit(f"  ✓ TIFF Gereed.")
        shutil.rmtree(tmp_dir)

    def _do_hdrmerge(self, path, name):
        raw_files = [os.path.join(path, f) for f in os.listdir(path) if f.split('.')[-1].upper() in [fmt.split(' ')[0] for fmt in RAW_FORMATS[1:]]]
        out_d = os.path.join(path, CONFIG["HDRMERGE_DIR_NAME"]); os.makedirs(out_d, exist_ok=True)
        out_f = os.path.join(out_d, f"{name}_HDR.dng")
        res = subprocess.run(['hdrmerge', '-o', out_f] + raw_files, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0: self.log.emit(f"  ✓ DNG Gereed.")

# --- WORKER: STAP 3 (VERZAMELEN & OPSCHONEN) ---
class PanoWorker(QObject):
    finished, log = Signal(), Signal(str)
    def __init__(self, sorted_dir, cleanup_enabled):
        super().__init__()
        self.sorted_dir = os.path.abspath(sorted_dir); self.cleanup_enabled = cleanup_enabled
    @Slot()
    def run(self):
        parent_dir = os.path.dirname(self.sorted_dir)
        dest = os.path.join(parent_dir, CONFIG["HDR_COLLECT_NAME"]); os.makedirs(dest, exist_ok=True)
        files_found, dirs_to_delete = 0, set()
        all_files = []
        for p in [os.path.join(self.sorted_dir, '**', '*_HDR_*.tif'), os.path.join(self.sorted_dir, '**', '*_HDR.dng')]:
            all_files.extend(glob.glob(p, recursive=True))
        for f in list(set(all_files)):
            if dest in f: continue
            if self.cleanup_enabled and f.lower().endswith('.dng'):
                parent = os.path.dirname(f)
                if os.path.basename(parent) == CONFIG["HDRMERGE_DIR_NAME"]: dirs_to_delete.add(os.path.dirname(parent))
            try:
                shutil.move(f, os.path.join(dest, os.path.basename(f))); files_found += 1
            except: pass
        self.log.emit(f"Gereed: {files_found} bestanden verzameld.")
        if self.cleanup_enabled and dirs_to_delete:
            for d in dirs_to_delete:
                try: shutil.rmtree(d)
                except: pass
            if os.path.exists(self.sorted_dir) and not os.listdir(self.sorted_dir): shutil.rmtree(self.sorted_dir)
        self.finished.emit()

# --- GUI ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Workflow Foto Automatisering v40.7"); self.setGeometry(100, 100, 800, 650)
        self.tabs = QTabWidget(); self.setCentralWidget(self.tabs)
        self.t1, self.t2, self.t3 = QWidget(), QWidget(), QWidget()
        self.tabs.addTab(self.t1, "1. Sorteer"); self.tabs.addTab(self.t2, "2. HDR"); self.tabs.addTab(self.t3, "3. Verzamelen")
        self.setup_t1(); self.setup_t2(); self.setup_t3()

    def setup_t1(self):
        l = QVBoxLayout(self.t1); h = QHBoxLayout(); self.s1 = QLineEdit(os.path.expanduser("~")); b = QPushButton("...")
        b.clicked.connect(lambda: self.sel(self.s1)); h.addWidget(QLabel("Bron:")); h.addWidget(self.s1); h.addWidget(b); l.addLayout(h)
        self.rf = QComboBox(); self.rf.addItems(RAW_FORMATS); l.addWidget(QLabel("Raw Formaat:")); l.addWidget(self.rf)
        self.sc = QComboBox(); self.sc.addItems(["Auto (3, 5, 7)", "Vast op 3", "Vast op 5", "Vast op 7"]); l.addWidget(QLabel("Stack-grootte:")); l.addWidget(self.sc)
        self.kc = QComboBox(); self.kc.addItems(["Bewaar de 1e foto van elke reeks en alle enkele foto's", "Bewaar alleen de losse foto's (verplaats alle reeksen)"]); l.addWidget(QLabel("Hoofdmap opschonen:")); l.addWidget(self.kc)
        self.b1 = QPushButton("Start Sorteren"); self.b1.clicked.connect(self.go1); l.addWidget(self.b1)
        self.p1 = QProgressBar(); l.addWidget(self.p1); self.log1 = QTextEdit(); self.log1.setReadOnly(True); l.addWidget(self.log1)

    def setup_t2(self):
        l = QVBoxLayout(self.t2); h = QHBoxLayout(); self.s2 = QLineEdit(); b = QPushButton("...")
        b.clicked.connect(lambda: self.sel(self.s2)); h.addWidget(QLabel("Map:")); h.addWidget(self.s2); h.addWidget(b); l.addLayout(h)
        self.m2 = QComboBox(); self.m2.addItems(["Enfuse (TIFF)", "HDRmerge (DNG)"]); l.addWidget(self.m2)
        self.enf_o = QWidget(); el = QVBoxLayout(self.enf_o); el.setContentsMargins(0,5,0,5); el.addWidget(QLabel("Bit Diepte:")); self.bd = QComboBox(); self.bd.addItems(["8", "16"]); el.addWidget(self.bd); l.addWidget(self.enf_o)
        self.m2.currentIndexChanged.connect(lambda i: self.enf_o.setVisible(i==0))
        self.b2 = QPushButton("Start HDR Verwerking"); self.b2.clicked.connect(self.go2); l.addWidget(self.b2)
        self.p2 = QProgressBar(); l.addWidget(self.p2); self.log2 = QTextEdit(); self.log2.setReadOnly(True); l.addWidget(self.log2)

    def setup_t3(self):
        l = QVBoxLayout(self.t3); h = QHBoxLayout(); self.s3 = QLineEdit(); b = QPushButton("...")
        b.clicked.connect(lambda: self.sel(self.s3)); h.addWidget(QLabel("Bron:")); h.addWidget(self.s3); h.addWidget(b); l.addLayout(h)
        self.cl_ch = QCheckBox("Verwijder RAW-reeksen na verzamelen (alleen na DNG workflow)"); self.cl_ch.setChecked(True); l.addWidget(self.cl_ch)
        self.b3 = QPushButton("Verzamel resultaten & Ruim op"); self.b3.clicked.connect(self.go3); l.addWidget(self.b3)
        self.log3 = QTextEdit(); self.log3.setReadOnly(True); l.addWidget(self.log3)

    def sel(self, e):
        d = QFileDialog.getExistingDirectory(self, "Kies map", e.text()); e.setText(d) if d else None

    def go1(self):
        self.log1.clear(); self.thread = QThread(); self.worker = SortWorker(self.s1.text(), self.sc.currentIndex(), self.kc.currentIndex(), self.rf.currentIndex())
        self.worker.moveToThread(self.thread); self.thread.started.connect(self.worker.run); self.worker.finished.connect(self.thread.quit)
        self.worker.log.connect(self.log1.append); self.worker.progress.connect(self.p1.setValue); self.thread.start()
        p = os.path.join(self.s1.text(), CONFIG["SORTED_DIR_NAME"]); self.s2.setText(p); self.s3.setText(p)

    def go2(self):
        self.log2.clear(); self.thread = QThread(); self.worker = HdrWorker(self.s2.text(), 'enfuse' if self.m2.currentIndex()==0 else 'hdrmerge', self.bd.currentText())
        self.worker.moveToThread(self.thread); self.thread.started.connect(self.worker.run); self.worker.finished.connect(self.thread.quit)
        self.worker.log.connect(self.log2.append); self.worker.progress.connect(self.p2.setValue); self.thread.start()

    def go3(self):
        self.log3.clear(); self.thread = QThread(); self.worker = PanoWorker(self.s3.text(), self.cl_ch.isChecked())
        self.worker.moveToThread(self.thread); self.thread.started.connect(self.worker.run); self.worker.finished.connect(self.thread.quit)
        self.worker.log.connect(self.log3.append); self.thread.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Gebruik systeem-stijl dialogen (belangrijk voor KDE/GNOME/Portal)
    app.setStyle("Fusion")

    error_msg = get_missing_dependencies()
    if error_msg:
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Software ontbreekt")
        msg_box.setText(error_msg)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()
        sys.exit(1)

    w = MainWindow()
    w.show()
    sys.exit(app.exec())
