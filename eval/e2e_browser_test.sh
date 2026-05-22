#!/bin/bash
# End-to-end browser test for Basis frontend
# Tests 4-5 real-world prompts and records results

set -e

URL="https://meraki.prateekjain.io"
PROMPTS=(
  "Thesis on AI infrastructure buildout"
  "Is NVDA overvalued at current P/E?"
  "DeepSeek impact on GPU demand"
  "Renewable energy stocks in India"
  "Best cybersecurity stocks for 2025"
)

echo "============================================================"
echo "BASIS FRONTEND E2E TEST"
echo "============================================================"
echo "URL: $URL"
echo "Prompts: ${#PROMPTS[@]}"
echo ""

# Navigate to page
agent-browser --auto-connect open "$URL" > /dev/null 2>&1
sleep 3

total_start=$(date +%s)

for i in "${!PROMPTS[@]}"; do
  prompt="${PROMPTS[$i]}"
  echo "--- Test $((i+1))/$((${#PROMPTS[@]})): $prompt ---"
  
  # Send prompt
  agent-browser --auto-connect fill @e15 "$prompt" > /dev/null 2>&1
  agent-browser --auto-connect click @e19 > /dev/null 2>&1
  
  start=$(date +%s)
  status="pending"
  
  # Poll for up to 120 seconds
  for poll in $(seq 1 12); do
    sleep 10
    snapshot=$(agent-browser --auto-connect snapshot 2>/dev/null || echo "")
    
    if echo "$snapshot" | grep -q "STATUS: error"; then
      status="error"
      error_msg=$(echo "$snapshot" | grep "ERR:" | head -1)
      echo "  FAILED after $(( $(date +%s) - start ))s"
      echo "  Error: $error_msg"
      break
    fi
    
    if echo "$snapshot" | grep -q "Conviction:"; then
      status="success"
      score=$(echo "$snapshot" | grep -o "Score: [0-9.]*" | head -1)
      echo "  SUCCESS after $(( $(date +%s) - start ))s"
      echo "  $score"
      break
    fi
    
    if echo "$snapshot" | grep -q "Thinking"; then
      echo "  Poll $poll: Thinking... ($(( $(date +%s) - start ))s elapsed)"
    fi
  done
  
  if [ "$status" = "pending" ]; then
    echo "  TIMEOUT after 120s"
  fi
  
  # Start new chat for next prompt
  agent-browser --auto-connect click @e9 > /dev/null 2>&1
  sleep 2
  echo ""
done

total_end=$(date +%s)
echo "============================================================"
echo "Total time: $(( total_end - total_start ))s"
echo "============================================================"
