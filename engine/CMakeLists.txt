cmake_minimum_required(VERSION 3.16)
project(ocr_engine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

find_package(PkgConfig REQUIRED)
pkg_check_modules(TESSERACT REQUIRED tesseract)
pkg_check_modules(LEPTONICA REQUIRED lept)

find_package(pybind11 REQUIRED)
find_package(Python3 REQUIRED COMPONENTS Interpreter Development)

pybind11_add_module(ocr_engine
    src/ocr_engine.cpp
    src/preprocessor.cpp
    src/bindings.cpp
)

target_include_directories(ocr_engine PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${TESSERACT_INCLUDE_DIRS}
    ${LEPTONICA_INCLUDE_DIRS}
)

target_link_libraries(ocr_engine PRIVATE
    ${TESSERACT_LIBRARIES}
    ${LEPTONICA_LIBRARIES}
)

target_compile_definitions(ocr_engine PRIVATE
    VERSION_INFO="${PROJECT_VERSION}"
)
