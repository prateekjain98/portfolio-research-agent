#!/bin/bash
# End-to-end test via curl (full API pipeline)

URL="https://basis-backend-751102854690.us-central1.run.app/chat"
PROMPTS=(
  "Thesis on AI infrastructure buildout"
  "Is NVDA overvalued at current P/E?"
  "DeepSeek impact on GPU demand"
  "Renewable energy stocks in India"
  "Best cybersecurity stocks for 2025"
)

echo "============================================================"
echo "BASIS E2E API TEST (4-5 real-world prompts)"
echo "URL: $URL"
echo "============================================================"

success_count=0

for i in "${!PROMPTS[@]}"; do
  prompt="${PROMPTS[$i]}"
  echo ""
  echo "--- Test $((i+1))/$((${#PROMPTS[@]})): $prompt ---"
  
  start=$(date +%s)
  response=$(curl -s --max-time 120 -X POST "$URL" \
    -H "Content-Type: application/json" \
    -d "{\"messages\":[{\"role\":\"user\",\"content\":\"$prompt\"}],\"session_id\":null}")
  end=$(date +%s)
  
  duration=$((end - start))
  
  # Extract key info (macOS-compatible grep)
  thesis_id=$(echo "$response" | grep 'Thesis ID:' | sed 's/.*Thesis ID:.*`\([^`]*\)`.*/\1/' | head -1)
  conviction=$(echo "$response" | grep 'Conviction:' | sed 's/.*Conviction:[^A-Za-z]*\([A-Za-z]*\).*/\1/' | head -1)
  score=$(echo "$response" | grep 'Score:' | sed 's/.*Score: \([0-9.]*\).*/\1/' | head -1)
  has_thesis=$(echo "$response" | grep -c 'Thesis ID')
  
  if [ "$has_thesis" -gt 0 ]; then
    echo "  SUCCESS in ${duration}s"
    echo "  Thesis ID: $thesis_id"
    echo "  Conviction: $conviction"
    echo "  Top Score: $score"
    ((success_count++))
  else
    echo "  FAILED after ${duration}s"
    echo "  Response (first 300 chars): ${response:0:300}"
  fi
done

echo ""
echo "============================================================"
echo "Results: $success_count/${#PROMPTS[@]} passed"
echo "============================================================"
