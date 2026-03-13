"""
Folder-based image dataset reader (ROS-independent).
Format: folder with images.csv (timestamp_ns,filename) and image files.
"""
import cv2
import os
import numpy as np
import aslam_cv as acv


class FolderImageDatasetReaderIterator(object):
    def __init__(self, dataset, indices=None):
        self.dataset = dataset
        if indices is None:
            self.indices = np.arange(dataset.numImages())
        else:
            self.indices = indices
        self.iter = self.indices.__iter__()

    def __iter__(self):
        return self

    def __next__(self):
        idx = next(self.iter)
        return self.dataset.getImage(idx)


class FolderImageDatasetReader(object):
    """
    Read images from a folder with images.csv.
    CSV format: timestamp_ns,filename (header optional)
    """
    def __init__(self, folder, csv_path=None, folder_from_to=None, folder_freq=None):
        """
        Args:
            folder: Path to folder containing images and images.csv
            csv_path: Optional path to CSV (default: folder/images.csv)
            folder_from_to: Optional (start_offset_sec, end_offset_sec) to truncate
            folder_freq: Optional max frequency (Hz) to subsample
        """
        self.folder = os.path.abspath(folder)
        self.topic = self.folder  # for compatibility with display/logging
        self.bagfile = self.folder  # for compatibility with RsCalibrator

        csv_file = csv_path or os.path.join(self.folder, 'images.csv')
        if not os.path.exists(csv_file):
            raise RuntimeError("images.csv not found in {0}".format(self.folder))

        # Parse CSV: timestamp_ns (or timestamp_sec), filename
        self.entries = []
        with open(csv_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(',')
                if len(parts) >= 2:
                    try:
                        ts_val = float(parts[0].strip())
                        # If value < 1e12, assume seconds; else nanoseconds
                        ts_ns = int(ts_val * 1e9) if ts_val < 1e12 else int(ts_val)
                        fname = parts[1].strip()
                        self.entries.append((ts_ns, fname))
                    except ValueError:
                        continue  # skip header or malformed lines

        if not self.entries:
            raise RuntimeError("No valid entries in images.csv")

        # Sort by timestamp
        self.entries.sort(key=lambda x: x[0])
        self.indices = np.arange(len(self.entries))

        # Truncate by time range
        if folder_from_to:
            self.indices = self._truncateFromTime(self.indices, folder_from_to)

        # Subsample by frequency
        if folder_freq and folder_freq > 0:
            self.indices = self._truncateFromFreq(self.indices, folder_freq)

    def _truncateFromTime(self, indices, from_to):
        timestamps = [self.entries[i][0] / 1e9 for i in indices]
        bagstart = min(timestamps)
        valid = [i for i, ts in zip(indices, timestamps)
                 if (bagstart + from_to[0]) <= ts <= (bagstart + from_to[1])]
        return valid

    def _truncateFromFreq(self, indices, freq):
        timestamps = [self.entries[i][0] / 1e9 for i in indices]
        valid = []
        last_ts = -1
        for idx, ts in zip(indices, timestamps):
            if last_ts < 0 or (ts - last_ts) >= 1.0 / freq:
                valid.append(idx)
                last_ts = ts
        return valid

    @property
    def index(self):
        """Compatibility: list of indices (same as BagImageDatasetReader.index semantics)"""
        return list(self.indices)

    def __iter__(self):
        return self.readDataset()

    def readDataset(self):
        return FolderImageDatasetReaderIterator(self, self.indices)

    def readDatasetShuffle(self):
        indices = list(self.indices)
        np.random.shuffle(indices)
        return FolderImageDatasetReaderIterator(self, indices)

    def numImages(self):
        return len(self.indices)

    def getImage(self, idx):
        ts_ns, fname = self.entries[idx]
        timestamp = acv.Time(ts_ns // 10**9, ts_ns % 10**9)

        img_path = os.path.join(self.folder, fname)
        if not os.path.exists(img_path):
            raise RuntimeError("Image not found: {0}".format(img_path))

        img = cv2.imread(img_path)
        if img is None:
            raise RuntimeError("Failed to load image: {0}".format(img_path))

        if len(img.shape) == 3:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        elif len(img.shape) == 2:
            pass
        else:
            raise RuntimeError("Unsupported image format: {0}".format(img_path))

        return (timestamp, np.array(img, dtype=np.uint8))
