"""
Folder-based image dataset reader (ROS-independent).
Format: folder with images.csv (timestamp_ns,filename) and image files.
Headless: image reading via C++ (aslam_cv.imreadGrayscale), no Python cv2/PIL.
"""
import os
import numpy as np
import aslam_cv as acv


def _parse_timestamp_ns(value):
    value = str(value).strip()
    if '.' in value:
        ts_val = float(value)
        return int(ts_val * 1e9) if ts_val < 1e12 else int(ts_val)
    return int(value)


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
    Read images from a folder.

    Supported layouts
    -----------------
    New format (preferred)::

        cam0/
          timestamps.txt   <- one timestamp_ns per line
          data/
            <ts>.png
            ...

    Legacy format::

        cam0/
          images.csv       <- timestamp_ns,filename  (header optional)
          <images>
    """
    def __init__(self, folder, csv_path=None, folder_from_to=None, folder_freq=None, entries=None):
        self.folder = os.path.abspath(folder)
        self.topic = self.folder  # for compatibility with display/logging
        self.bagfile = self.folder  # for compatibility with RsCalibrator

        if entries is not None:
            self._image_dir = self.folder
            self.entries = list(entries)
        else:
            timestamps_file = os.path.join(self.folder, 'timestamps.txt')
            data_subdir     = os.path.join(self.folder, 'data')

            if os.path.exists(timestamps_file) and os.path.isdir(data_subdir):
            # --- New format: timestamps.txt + data/<ts>.png ---
                self._image_dir = data_subdir
                self.entries = []
                with open(timestamps_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        try:
                            ts_ns = int(line)
                            self.entries.append((ts_ns, '{0}.png'.format(ts_ns)))
                        except ValueError:
                            continue
                if not self.entries:
                    raise RuntimeError("No valid timestamps in {0}".format(timestamps_file))
            else:
            # --- Legacy format: images.csv ---
                self._image_dir = self.folder
                csv_file = csv_path or os.path.join(self.folder, 'images.csv')
                if not os.path.exists(csv_file):
                    self.entries = self._scan_direct_timestamp_images()
                else:
                    self.entries = []
                    with open(csv_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith('#'):
                                continue
                            parts = line.split(',')
                            if len(parts) >= 2:
                                try:
                                    ts_ns = _parse_timestamp_ns(parts[0].strip())
                                    fname = parts[1].strip()
                                    self.entries.append((ts_ns, fname))
                                except ValueError:
                                    continue
                if not self.entries:
                    raise RuntimeError("No valid image entries in {0}".format(self.folder))

        # Sort by timestamp
        self.entries.sort(key=lambda x: x[0])
        self.indices = np.arange(len(self.entries))

        # Truncate by time range
        if folder_from_to:
            self.indices = self._truncateFromTime(self.indices, folder_from_to)

        # Subsample by frequency
        if folder_freq and folder_freq > 0:
            self.indices = self._truncateFromFreq(self.indices, folder_freq)

    def _scan_direct_timestamp_images(self):
        entries = []
        for fname in sorted(os.listdir(self.folder)):
            img_path = os.path.join(self.folder, fname)
            if not os.path.isfile(img_path):
                continue
            stem, ext = os.path.splitext(fname)
            if ext.lower() not in ['.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff']:
                continue
            try:
                ts_ns = _parse_timestamp_ns(stem.strip())
            except ValueError:
                continue
            entries.append((ts_ns, fname))
        return entries

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
        timestamp = acv.Time(ts_ns / 1e9)

        img_path = os.path.join(self._image_dir, fname)
        if not os.path.exists(img_path):
            raise RuntimeError("Image not found: {0}".format(img_path))

        img = acv.imreadGrayscale(img_path)
        return (timestamp, np.ascontiguousarray(np.array(img, dtype=np.uint8)))
