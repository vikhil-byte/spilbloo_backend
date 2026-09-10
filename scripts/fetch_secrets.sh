#!/usr/bin/env bash
# scripts/fetch_secrets.sh
# Fetches environment variables from AWS Secrets Manager and writes to .env
# Usage: ./scripts/fetch_secrets.sh <secret_name> [region] [output_file]

set -e

SECRET_NAME="${1:-${AWS_SECRET_NAME:-spilbloo/dev/env}}"
REGION="${2:-${AWS_REGION:-ap-south-1}}"
OUTPUT_FILE="${3:-.env}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FETCH_PY="$SCRIPT_DIR/fetch_secrets.py"

echo "[-] Fetching secret '$SECRET_NAME' from AWS Secrets Manager (Region: $REGION)..."

# 1. Locate a python binary that has boto3 installed
PYTHON_BIN=""
for candidate in python3 "$SCRIPT_DIR/../venv/bin/python3" "$SCRIPT_DIR/../venv/bin/python" /home/ubuntu/spilbloo_backend/venv/bin/python3; do
    if command -v "$candidate" &>/dev/null; then
        if "$candidate" -c "import boto3" &>/dev/null; then
            PYTHON_BIN="$candidate"
            break
        fi
    fi
done

# If python with boto3 is available, use fetch_secrets.py
if [ -n "$PYTHON_BIN" ] && [ -f "$FETCH_PY" ]; then
    "$PYTHON_BIN" "$FETCH_PY" --secret-name "$SECRET_NAME" --region "$REGION" --output "$OUTPUT_FILE"
    exit 0
fi

# 2. Fallback to AWS CLI if installed
if command -v aws &>/dev/null; then
    echo "[-] Using AWS CLI fallback to retrieve secret..."
    SECRET_STRING=$(aws secretsmanager get-secret-value \
        --secret-id "$SECRET_NAME" \
        --region "$REGION" \
        --query SecretString \
        --output text 2>&1) || {
        echo "[!] ERROR: Failed to retrieve secret via AWS CLI: $SECRET_STRING" >&2
        exit 1
    }

    # Format output: if JSON, parse keys; if plaintext, output directly
    TMP_FILE="${OUTPUT_FILE}.tmp"
    printf '%s\n' "$SECRET_STRING" | python3 -c "
import sys, json

data_str = sys.stdin.read().strip()
if data_str.startswith('{') and data_str.endswith('}'):
    try:
        obj = json.loads(data_str)
        if isinstance(obj, dict):
            for k, v in obj.items():
                val = str(v)
                if any(ch in val for ch in (' ', '\t', '\n', '\"', \"'\", '=', '#')):
                    val = '\"' + val.replace('\\\\', '\\\\\\\\').replace('\"', '\\\\\"') + '\"'
                print(f'{k}={val}')
            sys.exit(0)
    except Exception:
        pass

print(data_str)
" > "$TMP_FILE"

    chmod 600 "$TMP_FILE"
    mv "$TMP_FILE" "$OUTPUT_FILE"
    chmod 600 "$OUTPUT_FILE"
    echo "[+] Successfully fetched '$SECRET_NAME' via AWS CLI into '$OUTPUT_FILE' (mode 0600)."
    exit 0
fi

# 3. Neither tool is available
echo "[!] ERROR: Neither 'boto3' (in Python) nor the 'aws' CLI was found on this host." >&2
echo "    Please install the AWS CLI or boto3 on your EC2 instance:" >&2
echo "      sudo apt-get update && sudo apt-get install -y awscli" >&2
echo "    OR" >&2
echo "      pip install boto3" >&2
exit 1
