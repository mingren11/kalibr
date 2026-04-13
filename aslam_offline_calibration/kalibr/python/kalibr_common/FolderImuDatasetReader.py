"""
Folder-based IMU dataset reader (ROS-independent).
Format: imu.csv with columns timestamp_ns,gx,gy,gz,ax,ay,az (rad/s, m/s^2).
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


class FolderImuDatasetReaderIterator(object):
    def __init__(self, dataset, indices=None):
        self.dataset = dataset
        if indices is None:
            self.indices = np.arange(dataset.numMessages())
        else:
            self.indices = indices
        self.iter = self.indices.__iter__()

    def __iter__(self):
        return self

    def __next__(self):
        idx = next(self.iter)
        return self.dataset.getMessage(idx)


class FolderImuDatasetReader(object):
    """
    Read IMU data from imu.csv.
    CSV format: timestamp_ns,gx,gy,gz,ax,ay,az
    Units: gx,gy,gz in rad/s; ax,ay,az in m/s^2
    """
    def __init__(self, folder_or_csv, csv_path=None, folder_from_to=None):
        """
        Args:
            folder_or_csv: Path to folder containing imu.csv, or direct path to imu.csv
            csv_path: Optional explicit path to CSV (overrides folder_or_csv if both are dirs)
            folder_from_to: Optional (start_offset_sec, end_offset_sec) to truncate
        """
        if os.path.isfile(folder_or_csv):
            csv_file = folder_or_csv
            self.folder = os.path.dirname(folder_or_csv)
        else:
            self.folder = os.path.abspath(folder_or_csv)
            if csv_path:
                csv_file = csv_path
            else:
                # Try imu.csv (legacy) then data.csv (new format)
                candidate_legacy = os.path.join(self.folder, 'imu.csv')
                candidate_new    = os.path.join(self.folder, 'data.csv')
                if os.path.exists(candidate_legacy):
                    csv_file = candidate_legacy
                elif os.path.exists(candidate_new):
                    csv_file = candidate_new
                else:
                    raise RuntimeError(
                        "IMU CSV not found in {0} (tried imu.csv and data.csv)".format(self.folder))

        self.topic = self.folder  # for compatibility

        # Parse CSV: timestamp_ns, gx, gy, gz, ax, ay, az
        self.entries = []
        duplicate_timestamps = set()
        invalid_lines = 0
        seen_timestamps = set()
        with open(csv_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 7:
                    try:
                        ts_ns = _parse_timestamp_ns(parts[0])
                        gx, gy, gz = float(parts[1]), float(parts[2]), float(parts[3])
                        ax, ay, az = float(parts[4]), float(parts[5]), float(parts[6])
                        if ts_ns in seen_timestamps:
                            duplicate_timestamps.add(ts_ns)
                            continue
                        seen_timestamps.add(ts_ns)
                        self.entries.append((ts_ns, np.array([gx, gy, gz]), np.array([ax, ay, az])))
                    except (ValueError, IndexError):
                        invalid_lines += 1
                        continue
                else:
                    invalid_lines += 1

        if not self.entries:
            raise RuntimeError("No valid IMU entries in {0}".format(csv_file))

        self.entries.sort(key=lambda x: x[0])
        self.indices = np.arange(len(self.entries))
        self.csv_file = csv_file
        self.duplicate_timestamps = sorted(duplicate_timestamps)
        self.invalid_lines = invalid_lines

        if folder_from_to:
            self.indices = self._truncateFromTime(self.indices, folder_from_to)

    def _truncateFromTime(self, indices, from_to):
        timestamps = [self.entries[i][0] / 1e9 for i in indices]
        bagstart = min(timestamps)
        valid = [i for i, ts in zip(indices, timestamps)
                 if (bagstart + from_to[0]) <= ts <= (bagstart + from_to[1])]
        return valid

    @property
    def index(self):
        """Compatibility: list of indices"""
        return list(self.indices)

    def __iter__(self):
        return self.readDataset()

    def readDataset(self):
        return FolderImuDatasetReaderIterator(self, self.indices)

    def readDatasetShuffle(self):
        indices = list(self.indices)
        np.random.shuffle(indices)
        return FolderImuDatasetReaderIterator(self, indices)

    def numMessages(self):
        return len(self.indices)

    def getMessage(self, idx):
        ts_ns, omega, alpha = self.entries[idx]
        timestamp = acv.Time(ts_ns / 1e9)
        return (timestamp, omega, alpha)
