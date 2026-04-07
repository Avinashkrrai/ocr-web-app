#include "ocr_engine.h"
#include <tesseract/baseapi.h>
#include <leptonica/allheaders.h>
#include <filesystem>
#include <stdexcept>
#include <cstring>

namespace fs = std::filesystem;

namespace ocr {

struct OCREngine::Impl {
    tesseract::TessBaseAPI api;
    bool initialized = false;
};

OCREngine::OCREngine() : impl_(std::make_unique<Impl>()) {}

OCREngine::~OCREngine() {
    if (impl_ && impl_->initialized)
        impl_->api.End();
}

bool OCREngine::init(const std::string& lang, const std::string& datapath) {
    const char* dp = datapath.empty() ? nullptr : datapath.c_str();
    int rc = impl_->api.Init(dp, lang.c_str(), tesseract::OEM_LSTM_ONLY);
    if (rc != 0)
        return false;
    impl_->api.SetPageSegMode(tesseract::PSM_AUTO);
    impl_->initialized = true;
    return true;
}

void OCREngine::set_variable(const std::string& key, const std::string& value) {
    if (!impl_->initialized)
        throw std::runtime_error("Engine not initialized");
    impl_->api.SetVariable(key.c_str(), value.c_str());
}

static OCRResult extract_result(tesseract::TessBaseAPI& api) {
    OCRResult result;

    char* text = api.GetUTF8Text();
    if (text) {
        result.full_text = text;
        delete[] text;
    }

    // Extract word-level info
    tesseract::ResultIterator* ri = api.GetIterator();
    if (ri) {
        do {
            const char* word = ri->GetUTF8Text(tesseract::RIL_WORD);
            if (!word) continue;

            WordInfo wi;
            wi.text = word;
            wi.confidence = ri->Confidence(tesseract::RIL_WORD);
            delete[] word;

            int x1, y1, x2, y2;
            ri->BoundingBox(tesseract::RIL_WORD, &x1, &y1, &x2, &y2);
            wi.bbox = {x1, y1, x2 - x1, y2 - y1};

            result.words.push_back(std::move(wi));
        } while (ri->Next(tesseract::RIL_WORD));
    }

    // Extract block-level info (fresh iterator)
    ri = api.GetIterator();
    if (ri) {
        do {
            const char* block_text = ri->GetUTF8Text(tesseract::RIL_BLOCK);
            if (!block_text) continue;

            BlockInfo blk;
            blk.text = block_text;
            delete[] block_text;

            int x1, y1, x2, y2;
            ri->BoundingBox(tesseract::RIL_BLOCK, &x1, &y1, &x2, &y2);
            blk.bbox = {x1, y1, x2 - x1, y2 - y1};

            result.blocks.push_back(std::move(blk));
        } while (ri->Next(tesseract::RIL_BLOCK));
    }

    return result;
}

OCRResult OCREngine::process_image(const std::string& image_path) {
    if (!impl_->initialized)
        throw std::runtime_error("Engine not initialized");

    // Preprocess
    std::string tmp_dir = "/tmp/ocr_preprocess";
    std::string preprocessed;
    try {
        preprocessed = Preprocessor::preprocess(image_path, tmp_dir);
    } catch (...) {
        preprocessed = image_path;
    }

    PIX* pix = pixRead(preprocessed.c_str());
    if (!pix) {
        pix = pixRead(image_path.c_str());
        if (!pix)
            throw std::runtime_error("Failed to read image: " + image_path);
    }

    impl_->api.SetImage(pix);
    impl_->api.Recognize(nullptr);

    OCRResult result = extract_result(impl_->api);

    pixDestroy(&pix);
    impl_->api.Clear();

    return result;
}

OCRResult OCREngine::process_image_bytes(const char* data, size_t length) {
    if (!impl_->initialized)
        throw std::runtime_error("Engine not initialized");

    PIX* pix = pixReadMem(reinterpret_cast<const l_uint8*>(data), length);
    if (!pix)
        throw std::runtime_error("Failed to read image from memory");

    impl_->api.SetImage(pix);
    impl_->api.Recognize(nullptr);

    OCRResult result = extract_result(impl_->api);

    pixDestroy(&pix);
    impl_->api.Clear();

    return result;
}

} // namespace ocr
