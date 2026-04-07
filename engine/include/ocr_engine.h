#pragma once

#include <string>
#include <vector>
#include <memory>

namespace ocr {

struct BBox {
    int x, y, w, h;
};

struct WordInfo {
    std::string text;
    float confidence;
    BBox bbox;
};

struct BlockInfo {
    std::string text;
    BBox bbox;
};

struct OCRResult {
    std::string full_text;
    std::vector<WordInfo> words;
    std::vector<BlockInfo> blocks;
};

class Preprocessor {
public:
    static std::string preprocess(const std::string& input_path,
                                  const std::string& output_dir);
};

class OCREngine {
public:
    OCREngine();
    ~OCREngine();

    bool init(const std::string& lang = "eng",
              const std::string& datapath = "");

    OCRResult process_image(const std::string& image_path);
    OCRResult process_image_bytes(const char* data, size_t length);

    void set_variable(const std::string& key, const std::string& value);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace ocr
