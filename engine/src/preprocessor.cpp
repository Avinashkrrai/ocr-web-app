#include "ocr_engine.h"
#include <leptonica/allheaders.h>
#include <filesystem>
#include <stdexcept>

namespace fs = std::filesystem;

namespace ocr {

std::string Preprocessor::preprocess(const std::string& input_path,
                                     const std::string& output_dir) {
    PIX* pix = pixRead(input_path.c_str());
    if (!pix)
        throw std::runtime_error("Failed to read image: " + input_path);

    // Convert to grayscale if needed
    PIX* gray = nullptr;
    if (pixGetDepth(pix) == 32) {
        gray = pixConvertRGBToGray(pix, 0.0f, 0.0f, 0.0f);
        pixDestroy(&pix);
        pix = gray;
    } else if (pixGetDepth(pix) != 8) {
        gray = pixConvertTo8(pix, FALSE);
        pixDestroy(&pix);
        pix = gray;
    }

    // Deskew
    l_float32 angle = 0.0f;
    l_float32 conf = 0.0f;
    PIX* deskewed = pixFindSkewAndDeskew(pix, 2, &angle, &conf);
    if (deskewed && conf > 2.5f) {
        pixDestroy(&pix);
        pix = deskewed;
    } else if (deskewed) {
        pixDestroy(&deskewed);
    }

    // Normalize DPI to 300 if set and low
    l_int32 xres = pixGetXRes(pix);
    l_int32 yres = pixGetYRes(pix);
    if (xres > 0 && xres < 250) {
        float scale = 300.0f / static_cast<float>(xres);
        PIX* scaled = pixScale(pix, scale, scale);
        if (scaled) {
            pixSetResolution(scaled, 300, 300);
            pixDestroy(&pix);
            pix = scaled;
        }
    }

    // Adaptive threshold (Otsu)
    PIX* binary = nullptr;
    pixOtsuAdaptiveThreshold(pix, 2000, 2000, 0, 0, 0.0f, nullptr, &binary);
    if (binary) {
        pixDestroy(&pix);
        pix = binary;
    }

    // Noise removal — remove small connected components
    PIX* cleaned = pixSelectBySize(pix, 3, 3, 8, L_SELECT_IF_BOTH,
                                   L_SELECT_IF_GTE, nullptr);
    if (cleaned) {
        pixDestroy(&pix);
        pix = cleaned;
    }

    // Write preprocessed image
    fs::path out = fs::path(output_dir) / "preprocessed.tif";
    fs::create_directories(output_dir);
    if (pixWrite(out.c_str(), pix, IFF_TIFF_G4) != 0) {
        pixDestroy(&pix);
        throw std::runtime_error("Failed to write preprocessed image");
    }

    pixDestroy(&pix);
    return out.string();
}

} // namespace ocr
