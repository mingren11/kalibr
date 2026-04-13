"""
Helpers to adapt fixed folder layouts into the existing folder readers.
"""
import os


_PREPARED_IMAGE_ENTRIES = {}
_PREPARED_IMAGE_SUMMARIES = {}
_PREPARED_IMU_SUMMARIES = {}

_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff')


def topic_to_folder(topic):
    parts = [p for p in str(topic).split('/') if p]
    return parts[0] if parts else 'cam0'


def _parse_timestamp_ns(value):
    value = str(value).strip()
    if not value:
        raise ValueError("empty timestamp")

    if '.' in value:
        ts_val = float(value)
        return int(ts_val * 1e9) if ts_val < 1e12 else int(ts_val)

    return int(value)


def _image_summary_from_entries(folder, entries, duplicate_timestamps, invalid_files):
    summary = {
        'folder': folder,
        'count': len(entries),
        'duplicate_timestamps': sorted(duplicate_timestamps),
        'invalid_files': sorted(invalid_files),
    }
    if entries:
        summary['start_ns'] = entries[0][0]
        summary['end_ns'] = entries[-1][0]
    else:
        summary['start_ns'] = None
        summary['end_ns'] = None
    return summary


def scan_image_folder(folder):
    folder = os.path.abspath(folder)
    timestamps_file = os.path.join(folder, 'timestamps.txt')
    data_subdir = os.path.join(folder, 'data')
    entries = []
    duplicate_timestamps = set()
    invalid_files = []

    if os.path.exists(timestamps_file) and os.path.isdir(data_subdir):
        with open(timestamps_file, 'r') as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith('#'):
                    continue
                try:
                    ts_ns = _parse_timestamp_ns(line)
                except ValueError:
                    invalid_files.append(line)
                    continue
                entries.append((ts_ns, '{0}.png'.format(ts_ns)))
    else:
        csv_file = os.path.join(folder, 'images.csv')
        if os.path.exists(csv_file):
            with open(csv_file, 'r') as handle:
                for raw_line in handle:
                    line = raw_line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) < 2:
                        invalid_files.append(line)
                        continue
                    try:
                        ts_ns = _parse_timestamp_ns(parts[0])
                    except ValueError:
                        invalid_files.append(line)
                        continue
                    entries.append((ts_ns, parts[1]))
        else:
            try:
                filenames = sorted(os.listdir(folder))
            except OSError as exc:
                raise RuntimeError("Failed to list image folder '{0}': {1}".format(folder, exc))

            for filename in filenames:
                path = os.path.join(folder, filename)
                if not os.path.isfile(path):
                    continue
                stem, ext = os.path.splitext(filename)
                if ext.lower() not in _IMAGE_EXTENSIONS:
                    continue
                try:
                    ts_ns = _parse_timestamp_ns(stem)
                except ValueError:
                    invalid_files.append(filename)
                    continue
                entries.append((ts_ns, filename))

    if not entries:
        raise RuntimeError(
            "No valid images found in '{0}'. Supported layouts: direct <timestamp>.png, "
            "images.csv, or timestamps.txt + data/".format(folder))

    dedup = {}
    for ts_ns, filename in entries:
        if ts_ns in dedup:
            duplicate_timestamps.add(ts_ns)
            continue
        dedup[ts_ns] = filename

    ordered_entries = sorted(dedup.items(), key=lambda item: item[0])
    ordered_entries = [(ts_ns, filename) for ts_ns, filename in ordered_entries]
    return ordered_entries, _image_summary_from_entries(folder, ordered_entries, duplicate_timestamps, invalid_files)


def prepare_image_datasets(dataset_root, topics, require_common_timestamps=False):
    root = os.path.abspath(dataset_root)
    topic_list = list(topics)
    entries_by_topic = {}
    summaries = {}

    for topic in topic_list:
        folder_name = topic_to_folder(topic)
        folder = os.path.join(root, folder_name)
        entries, summary = scan_image_folder(folder)
        entries_by_topic[topic] = entries
        summaries[topic] = summary

    if require_common_timestamps and len(topic_list) > 1:
        timestamp_sets = {
            topic: set(ts_ns for ts_ns, _ in entries_by_topic[topic])
            for topic in topic_list
        }
        common_timestamps = set.intersection(*timestamp_sets.values()) if timestamp_sets else set()
        dropped = []
        for ts_ns in sorted(set.union(*timestamp_sets.values()) if timestamp_sets else set()):
            missing_topics = [topic_to_folder(topic) for topic in topic_list if ts_ns not in timestamp_sets[topic]]
            if missing_topics:
                dropped.append((ts_ns, missing_topics))

        for ts_ns, missing_topics in dropped:
            print("[dataset_adapter] Dropping timestamp {0}: missing {1}".format(
                ts_ns, ", ".join(missing_topics)))

        for topic in topic_list:
            entries_by_topic[topic] = [
                entry for entry in entries_by_topic[topic]
                if entry[0] in common_timestamps
            ]
            summaries[topic]['aligned_count'] = len(entries_by_topic[topic])
            if entries_by_topic[topic]:
                summaries[topic]['start_ns'] = entries_by_topic[topic][0][0]
                summaries[topic]['end_ns'] = entries_by_topic[topic][-1][0]
            else:
                summaries[topic]['start_ns'] = None
                summaries[topic]['end_ns'] = None
        if not common_timestamps:
            raise RuntimeError(
                "No common timestamps across cameras: {0}".format(
                    ", ".join(topic_to_folder(topic) for topic in topic_list)))
        print("[dataset_adapter] Common timestamps across {0}: {1}".format(
            ", ".join(topic_to_folder(topic) for topic in topic_list),
            len(common_timestamps)))

    _PREPARED_IMAGE_ENTRIES[root] = entries_by_topic
    _PREPARED_IMAGE_SUMMARIES[root] = summaries
    return summaries


def get_prepared_image_entries(dataset_root, topic):
    root = os.path.abspath(dataset_root)
    return _PREPARED_IMAGE_ENTRIES.get(root, {}).get(topic)


def get_prepared_image_summary(dataset_root, topic):
    root = os.path.abspath(dataset_root)
    return _PREPARED_IMAGE_SUMMARIES.get(root, {}).get(topic)


def summarize_prepared_images(dataset_root, topics):
    root = os.path.abspath(dataset_root)
    summaries = _PREPARED_IMAGE_SUMMARIES.get(root, {})
    for topic in topics:
        summary = summaries.get(topic)
        if not summary:
            continue
        folder_name = topic_to_folder(topic)
        aligned_count = summary.get('aligned_count', summary['count'])
        print("[dataset_adapter] {0}: {1} images".format(folder_name, aligned_count))
        if summary['start_ns'] is not None:
            print("[dataset_adapter] {0}: range [{1}, {2}] ns".format(
                folder_name, summary['start_ns'], summary['end_ns']))
        if summary['duplicate_timestamps']:
            print("[dataset_adapter] WARNING: {0} duplicate timestamps in {1}: {2}".format(
                len(summary['duplicate_timestamps']), folder_name,
                ", ".join(str(ts) for ts in summary['duplicate_timestamps'])))
        if summary['invalid_files']:
            print("[dataset_adapter] WARNING: ignored {0} invalid files in {1}".format(
                len(summary['invalid_files']), folder_name))


def _find_imu_csv(dataset_root, topic):
    root = os.path.abspath(dataset_root)
    topic_folder = os.path.join(root, topic_to_folder(topic))
    candidates = []
    if os.path.isdir(topic_folder):
        candidates.extend([
            os.path.join(topic_folder, 'imu.csv'),
            os.path.join(topic_folder, 'data.csv'),
        ])
    candidates.extend([
        os.path.join(root, 'imu.csv'),
        os.path.join(root, 'data.csv'),
    ])
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    raise RuntimeError("IMU CSV not found in '{0}'".format(root))


def prepare_imu_dataset(dataset_root, topic):
    csv_file = _find_imu_csv(dataset_root, topic)
    entries = []
    duplicate_timestamps = set()
    invalid_lines = 0
    seen = set()
    with open(csv_file, 'r') as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith('#'):
                continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 7:
                invalid_lines += 1
                continue
            try:
                ts_ns = _parse_timestamp_ns(parts[0])
                omega = [float(parts[1]), float(parts[2]), float(parts[3])]
                alpha = [float(parts[4]), float(parts[5]), float(parts[6])]
            except ValueError:
                invalid_lines += 1
                continue
            if ts_ns in seen:
                duplicate_timestamps.add(ts_ns)
                continue
            seen.add(ts_ns)
            entries.append((ts_ns, omega, alpha))

    if not entries:
        raise RuntimeError("No valid IMU entries in '{0}'".format(csv_file))

    entries.sort(key=lambda item: item[0])
    summary = {
        'csv_file': csv_file,
        'count': len(entries),
        'start_ns': entries[0][0],
        'end_ns': entries[-1][0],
        'duplicate_timestamps': sorted(duplicate_timestamps),
        'invalid_lines': invalid_lines,
    }
    _PREPARED_IMU_SUMMARIES[os.path.abspath(dataset_root)] = summary
    return summary


def get_prepared_imu_summary(dataset_root):
    return _PREPARED_IMU_SUMMARIES.get(os.path.abspath(dataset_root))
