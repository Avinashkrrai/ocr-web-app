#!/usr/bin/env bash
set -euo pipefail

#
# Fine-tune Tesseract LSTM model using collected user corrections.
#
# Usage:
#   ./train.sh [--lang eng] [--max-iterations 400]
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRAINING_DATA_DIR="$SCRIPT_DIR/training_data"
TRAIN_LIST="$TRAINING_DATA_DIR/training_files.txt"
MODEL_DIR="$SCRIPT_DIR/model"
TESSDATA_DIR="${TESSDATA_PREFIX:-/usr/share/tesseract-ocr/4.00/tessdata}"

LANG="${1:-eng}"
MAX_ITERATIONS="${2:-400}"

echo "=== Tesseract Fine-Tuning Pipeline ==="
echo "Language:        $LANG"
echo "Max iterations:  $MAX_ITERATIONS"
echo "Tessdata:        $TESSDATA_DIR"
echo ""

# Step 0: Validate training data exists
if [ ! -f "$TRAIN_LIST" ]; then
    echo "ERROR: Training file list not found at $TRAIN_LIST"
    echo "Run 'python prepare_training_data.py' first."
    exit 1
fi

NUM_FILES=$(wc -l < "$TRAIN_LIST")
echo "Training files: $NUM_FILES"

if [ "$NUM_FILES" -eq 0 ]; then
    echo "ERROR: No training files listed. Nothing to train on."
    exit 1
fi

# Step 1: Prepare model directory
mkdir -p "$MODEL_DIR"

TRAINEDDATA="$TESSDATA_DIR/${LANG}.traineddata"
if [ ! -f "$TRAINEDDATA" ]; then
    echo "ERROR: Base traineddata not found: $TRAINEDDATA"
    exit 1
fi

cp "$TRAINEDDATA" "$MODEL_DIR/${LANG}.traineddata"

# Step 2: Extract LSTM model from traineddata
echo ""
echo "--- Extracting LSTM component ---"
cd "$MODEL_DIR"
combine_tessdata -e "${LANG}.traineddata" "${LANG}.lstm"

if [ ! -f "${LANG}.lstm" ]; then
    echo "ERROR: Failed to extract LSTM component."
    exit 1
fi

# Step 3: Run LSTM fine-tuning
echo ""
echo "--- Starting fine-tuning (max $MAX_ITERATIONS iterations) ---"
lstmtraining \
    --continue_from "$MODEL_DIR/${LANG}.lstm" \
    --traineddata "$MODEL_DIR/${LANG}.traineddata" \
    --train_listfile "$TRAIN_LIST" \
    --model_output "$MODEL_DIR/${LANG}_finetuned" \
    --max_iterations "$MAX_ITERATIONS" \
    --debug_interval 100

# Step 4: Find the best checkpoint
BEST_CHECKPOINT=$(ls -t "$MODEL_DIR/${LANG}_finetuned"_checkpoint 2>/dev/null | head -1)
if [ -z "$BEST_CHECKPOINT" ]; then
    BEST_CHECKPOINT="$MODEL_DIR/${LANG}_finetuned_checkpoint"
fi

if [ ! -f "$BEST_CHECKPOINT" ]; then
    echo "WARNING: No checkpoint found, using last iteration output"
    BEST_CHECKPOINT=$(ls -t "$MODEL_DIR/${LANG}_finetuned"*.checkpoint 2>/dev/null | head -1)
fi

# Step 5: Package into new .traineddata
echo ""
echo "--- Packaging fine-tuned model ---"
lstmtraining \
    --stop_training \
    --continue_from "$BEST_CHECKPOINT" \
    --traineddata "$MODEL_DIR/${LANG}.traineddata" \
    --model_output "$MODEL_DIR/${LANG}_finetuned.traineddata"

OUTPUT="$MODEL_DIR/${LANG}_finetuned.traineddata"

if [ -f "$OUTPUT" ]; then
    echo ""
    echo "=== Fine-tuning complete ==="
    echo "Output model: $OUTPUT"
    echo ""
    echo "To use the fine-tuned model, copy it to your tessdata directory:"
    echo "  sudo cp $OUTPUT $TESSDATA_DIR/"
    echo ""
    echo "Or set TESSDATA_PREFIX to point to the model directory:"
    echo "  export TESSDATA_PREFIX=$MODEL_DIR"
else
    echo "ERROR: Fine-tuned model was not created."
    exit 1
fi
