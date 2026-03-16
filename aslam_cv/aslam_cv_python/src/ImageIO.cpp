#include <numpy_eigen/boost_python_headers.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/core/eigen.hpp>
#include <boost/cstdint.hpp>
#include <stdexcept>

namespace bp = boost::python;

/**
 * Read image as grayscale using C++ OpenCV (imgcodecs, no highgui/GTK).
 * Returns Eigen::Matrix<boost::uint8_t,...> for numpy_eigen converter (matches image_t).
 */
Eigen::Matrix<boost::uint8_t, Eigen::Dynamic, Eigen::Dynamic> imreadGrayscale(const std::string& path) {
  cv::Mat img = cv::imread(path, cv::IMREAD_GRAYSCALE);
  if (img.empty()) {
    throw std::runtime_error("Failed to load image: " + path);
  }
  Eigen::Matrix<boost::uint8_t, Eigen::Dynamic, Eigen::Dynamic> out(img.rows, img.cols);
  cv2eigen(img, out);
  return out;
}

void exportImageIO() {
  bp::def("imreadGrayscale", &imreadGrayscale,
          (bp::arg("path")),
          "Read image as grayscale (C++ OpenCV imgcodecs, no GTK). Returns numpy uint8 array.");
}
