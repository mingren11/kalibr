// It is extremely important to use this header
// if you are using the numpy_eigen interface
#include <numpy_eigen/boost_python_headers.hpp>
#include <numpy/arrayobject.h>
#include <stdexcept>

void exportCameraGeometries();
void exportTimeAndDuration();
void exportFrontend();
//void exportCameraSystemClasses();
//void exportMatchingAlgorithms();
//void exportImageContainer();
void exportGridCalibration();
//void exportLandmark();
void exportUndistorters();
//void exportNCameras();
void exportPinholeUndistorter();
void exportOmniUndistorter();
void exportImageIO();


// The title of this library must match exactly
BOOST_PYTHON_MODULE(libaslam_cv_python)
{
  if (_import_array() < 0) {
    PyErr_Print();
    throw std::runtime_error("numpy.core.multiarray failed to import");
  }
  // fill this in with boost::python export code
  exportCameraGeometries();
  exportTimeAndDuration();
  exportFrontend();
//  exportCameraSystemClasses();
//  exportMatchingAlgorithms();
//  exportImageContainer();
  exportGridCalibration();
//  exportLandmark();
  exportUndistorters();
//  exportNCameras();
  exportPinholeUndistorter();
  exportOmniUndistorter();
  exportImageIO();
}
