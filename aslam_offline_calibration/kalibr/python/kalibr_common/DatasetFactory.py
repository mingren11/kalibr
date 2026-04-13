"""
Dataset factory: create image/IMU dataset readers from folder (ROS-independent).
"""
import os
from .FolderDatasetAdapter import get_prepared_image_entries, topic_to_folder


def create_image_dataset(path, topic, bag_from_to=None, bag_freq=None, perform_synchronization=False):
    """
    Create image dataset reader from folder.
    path: folder containing cam0/, cam1/, etc. with images.csv per camera.
    topic: camera name (e.g. 'cam0') or ROS-style topic (e.g. '/cam0/image_raw').
    """
    if not os.path.isdir(path):
        raise RuntimeError(
            "Expected a folder dataset, got: '{0}'. "
            "Only folder-based datasets are supported (no ROS bag).".format(path))
    folder = os.path.join(path, topic_to_folder(topic))
    prepared_entries = get_prepared_image_entries(path, topic)
    from .FolderImageDatasetReader import FolderImageDatasetReader
    return FolderImageDatasetReader(
        folder,
        folder_from_to=bag_from_to,
        folder_freq=bag_freq,
        entries=prepared_entries)

def create_imu_dataset(path, topic, bag_from_to=None, perform_synchronization=False):
    """
    Create IMU dataset reader from folder.

    Looks for the IMU data in the following order:
    1. <path>/<topic_folder>/  (e.g. imu0/data.csv)
    2. <path>/                 (legacy: imu.csv in dataset root)
    """
    if not os.path.isdir(path):
        raise RuntimeError(
            "Expected a folder dataset, got: '{0}'. "
            "Only folder-based datasets are supported (no ROS bag).".format(path))
    from .FolderImuDatasetReader import FolderImuDatasetReader
    imu_subfolder = os.path.join(path, topic_to_folder(topic))
    if os.path.isdir(imu_subfolder):
        return FolderImuDatasetReader(imu_subfolder, folder_from_to=bag_from_to)
    return FolderImuDatasetReader(path, folder_from_to=bag_from_to)
