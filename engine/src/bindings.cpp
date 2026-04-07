#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "ocr_engine.h"

namespace py = pybind11;

PYBIND11_MODULE(ocr_engine, m) {
    m.doc() = "C++ OCR Engine wrapping Tesseract API";

    py::class_<ocr::BBox>(m, "BBox")
        .def(py::init<>())
        .def_readwrite("x", &ocr::BBox::x)
        .def_readwrite("y", &ocr::BBox::y)
        .def_readwrite("w", &ocr::BBox::w)
        .def_readwrite("h", &ocr::BBox::h)
        .def("__repr__", [](const ocr::BBox& b) {
            return "BBox(x=" + std::to_string(b.x) + ", y=" +
                   std::to_string(b.y) + ", w=" + std::to_string(b.w) +
                   ", h=" + std::to_string(b.h) + ")";
        });

    py::class_<ocr::WordInfo>(m, "WordInfo")
        .def(py::init<>())
        .def_readwrite("text", &ocr::WordInfo::text)
        .def_readwrite("confidence", &ocr::WordInfo::confidence)
        .def_readwrite("bbox", &ocr::WordInfo::bbox);

    py::class_<ocr::BlockInfo>(m, "BlockInfo")
        .def(py::init<>())
        .def_readwrite("text", &ocr::BlockInfo::text)
        .def_readwrite("bbox", &ocr::BlockInfo::bbox);

    py::class_<ocr::OCRResult>(m, "OCRResult")
        .def(py::init<>())
        .def_readwrite("full_text", &ocr::OCRResult::full_text)
        .def_readwrite("words", &ocr::OCRResult::words)
        .def_readwrite("blocks", &ocr::OCRResult::blocks);

    py::class_<ocr::Preprocessor>(m, "Preprocessor")
        .def_static("preprocess", &ocr::Preprocessor::preprocess,
                     py::arg("input_path"), py::arg("output_dir"));

    py::class_<ocr::OCREngine>(m, "OCREngine")
        .def(py::init<>())
        .def("init", &ocr::OCREngine::init,
             py::arg("lang") = "eng", py::arg("datapath") = "")
        .def("process_image", &ocr::OCREngine::process_image,
             py::arg("image_path"))
        .def("process_image_bytes",
             [](ocr::OCREngine& self, py::bytes data) {
                 std::string s = data;
                 return self.process_image_bytes(s.data(), s.size());
             },
             py::arg("data"))
        .def("set_variable", &ocr::OCREngine::set_variable,
             py::arg("key"), py::arg("value"));
}
