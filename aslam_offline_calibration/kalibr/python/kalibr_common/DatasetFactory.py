"""
Dataset factory: create image/IMU dataset readers from bag or folder (ROS-independent).
"""
import os

def _topic_to_folder(topic):
    """Extract folder name from ROS topic, e.g. /cam0/image_raw -> cam0"""
    parts = [p for p in topic.split('/') if p]
    return parts[0] if parts else 'cam0'

def _is_folder_dataset(path):
    return os.path.isdir(path) and os.path.exists(os.path.join(path, 'imu.csv'))

def create_image_dataset(path, topic, bag_from_to=None, bag_freq=None, perform_synchronization=False):
    """
    Create image dataset reader from bag file or folder.
    Returns BagImageDatasetReader (ROS) or FolderImageDatasetReader (no ROS).
    """
    if os.path.isdir(path):
        folder = os.path.join(path, _topic_to_folder(topic))
        from .FolderImageDatasetReader import FolderImageDatasetReader
        return FolderImageDatasetReader(folder, folder_from_to=bag_from_to, folder_freq=bag_freq)
    else:
        from .ImageDatasetReader import BagImageDatasetReader
        return BagImageDatasetReader(path, topic, bag_from_to=bag_from_to, bag_freq=bag_freq,
                                     perform_synchronization=perform_synchronization)

def create_imu_dataset(path, topic, bag_from_to=None, perform_synchronization=False):
    """
    Create IMU dataset reader from bag file or folder.
    Returns BagImuDatasetReader (ROS) or FolderImuDatasetReader (no ROS).
    """
    if os.path.isdir(path):
        from .FolderImuDatasetReader import FolderImuDatasetReader
        return FolderImuDatasetReader(path, folder_from_to=bag_from_to)
    else:
        from .ImuDatasetReader import BagImuDatasetReader
        return BagImuDatasetReader(path, topic, bag_from_to=bag_from_to,
                                   perform_synchronization=perform_synchronization)
