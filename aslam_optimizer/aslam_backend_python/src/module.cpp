// It is extremely important to use this header
// if you are using the numpy_eigen interface
#include <numpy_eigen/boost_python_headers.hpp>
#include <numpy/arrayobject.h>
#include <stdexcept>

void exportBackend();
void exportCompressedColumnMatrix() ;
void exportLinearSystemSolver();
void exportErrorTermTransformation();
void exportTrustRegionPolicies();
void exportSBM();
// The title of this library must match exactly
BOOST_PYTHON_MODULE(libaslam_backend_python)
{
  if (_import_array() < 0) {
    PyErr_Print();
    throw std::runtime_error("numpy.core.multiarray failed to import");
  }
  // fill this in with boost::python export code
  exportBackend();
  exportCompressedColumnMatrix();
  exportLinearSystemSolver();
  exportErrorTermTransformation();
  exportTrustRegionPolicies();
  exportSBM();
}
