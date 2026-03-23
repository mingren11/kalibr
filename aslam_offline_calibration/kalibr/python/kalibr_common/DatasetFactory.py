"""
Dataset factory: create image/IMU dataset readers from folder (ROS-independent).
"""
import os

def _topic_to_folder(topic):
    """Extract folder name from topic/path, e.g. /cam0/image_raw -> cam0, or cam0 -> cam0"""
    parts = [p for p in topic.split('/') if p]
    return parts[0] if parts else 'cam0'

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
    folder = os.path.join(path, _topic_to_folder(topic))
    from .FolderImageDatasetReader import FolderImageDatasetReader
    return FolderImageDatasetReader(folder, folder_from_to=bag_from_to, folder_freq=bag_freq)

def create_imu_dataset(path, topic, bag_from_to=None, perform_synchronization=False):
    """
    Create IMU dataset reader from folder.
    path: folder containing imu.csv.
    """
    if not os.path.isdir(path):
        raise RuntimeError(
            "Expected a folder dataset, got: '{0}'. "
            "Only folder-based datasets are supported (no ROS bag).".format(path))
    from .FolderImuDatasetReader import FolderImuDatasetReader
    return FolderImuDatasetReader(path, folder_from_to=bag_from_to)
