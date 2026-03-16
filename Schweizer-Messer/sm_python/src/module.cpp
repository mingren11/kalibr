#include <numpy_eigen/boost_python_headers.hpp>
#include <numpy_eigen/NumpyEigenConverter.hpp>
#include <boost/python/suite/indexing/vector_indexing_suite.hpp>
#include <boost/cstdint.hpp>
#include <sm/timing/Timer.hpp>
#include <stdexcept>
using namespace boost::python;

//typedef UniformCubicBSpline<Eigen::Dynamic> UniformCubicBSplineX;


void import_rotational_kinematics_python();
void export_rotations();
void export_transformations();
void export_quaternion_algebra();
void export_homogeneous_coordinates();
void exportTransformation();
void exportHomogeneousPoint();
void exportTimestampCorrectors();
void exportPropertyTree();
void exportEigen();
void exportUncertainVector();
void exportMatrixArchive();
void exportLogging();
void exportNsecTime();
void exportRandom();
void export_eigen_property_tree();
void export_kinematics_property_tree();

void printTiming()
{
    sm::timing::Timing::print(std::cout);
}

BOOST_PYTHON_MODULE(libsm_python)
{
  if (_import_array() < 0) {
    PyErr_Print();
    throw std::runtime_error("numpy.core.multiarray failed to import");
  }
  // Register Eigen<->numpy converters for standalone (numpy_eigen may not load correctly)
  NumpyEigenConverter<Eigen::Matrix<double, 2, 1> >::register_converter();
  NumpyEigenConverter<Eigen::Matrix<double, 2, 2> >::register_converter();  // invR covariance
  NumpyEigenConverter<Eigen::Matrix<double, 3, 1> >::register_converter();
  NumpyEigenConverter<Eigen::Matrix<double, 3, 3> >::register_converter();  // rotation matrix C()
  NumpyEigenConverter<Eigen::Matrix<double, 4, 1> >::register_converter();
  NumpyEigenConverter<Eigen::Matrix<double, 4, 4> >::register_converter();  // transformation matrix T
  NumpyEigenConverter<Eigen::Matrix<double, Eigen::Dynamic, 1> >::register_converter();
  NumpyEigenConverter<Eigen::Matrix<double, 6, Eigen::Dynamic> >::register_converter();  // BSplinePose curve
  NumpyEigenConverter<Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic> >::register_converter();
  NumpyEigenConverter<Eigen::Matrix<int, Eigen::Dynamic, 1> >::register_converter();
  NumpyEigenConverter<Eigen::Matrix<boost::uint8_t, Eigen::Dynamic, Eigen::Dynamic> >::register_converter();

  def("printTiming", &printTiming);
  import_rotational_kinematics_python();
  export_rotations();
  export_transformations();
  export_quaternion_algebra();
  export_homogeneous_coordinates();
  exportTransformation();
  exportHomogeneousPoint();
  exportTimestampCorrectors();
  exportPropertyTree();
  exportEigen();
  exportUncertainVector();
  exportMatrixArchive();
  exportLogging();
  exportNsecTime();
  exportRandom();
  export_eigen_property_tree();
  export_kinematics_property_tree();
}
