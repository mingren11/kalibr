# Import the numpy to Eigen type conversion.
import numpy_eigen
from .ConfigReader import *
from .FolderImageDatasetReader import *
from .FolderImuDatasetReader import *
from .DatasetFactory import create_image_dataset, create_imu_dataset
from .TargetExtractor import *

# Lazy import of ROS-dependent readers (only when using bag format)
def __getattr__(name):
    if name == 'BagImageDatasetReader':
        from .ImageDatasetReader import BagImageDatasetReader
        return BagImageDatasetReader
    if name == 'BagImuDatasetReader':
        from .ImuDatasetReader import BagImuDatasetReader
        return BagImuDatasetReader
    raise AttributeError("module {!r} has no attribute {!r}".format(__name__, name))
