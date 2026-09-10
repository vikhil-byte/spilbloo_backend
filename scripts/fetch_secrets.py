#!/usr/bin/env python3
"""
AWS Secrets Manager to .env Fetcher
Spilbloo Backend

Fetches environment variables stored in AWS Secrets Manager and writes them
securely to a .env file on the host before Docker containers are started.

Supports two secret formats in AWS Secrets Manager:
1. Plaintext format (raw .env file pasted into the Plaintext tab)
2. JSON key-value format (standard Key/Value pairs configured in AWS Console)
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path


def format_env_value(val) -> str:
    """Format a value safely for inclusion in a .env file."""
    if isinstance(val, (dict, list)):
        val_str = json.dumps(val)
    elif isinstance(val, bool):
        val_str = "True" if val else "False"
    elif val is None:
        val_str = ""
    else:
        val_str = str(val)

    # If value contains spaces, quotes, newlines, hashes, or equals signs, quote it
    if any(ch in val_str for ch in (" ", "\t", "\n", '"', "'", "=", "#")):
        escaped = val_str.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return val_str


def parse_secret_string(secret_string: str) -> str:
    """
    Parse the raw secret string into valid .env file content.
    If it's valid JSON dict, convert key-values to KEY=VALUE lines.
    If it's plaintext, return as-is (with trailing newline).
    """
    secret_string = secret_string.strip()
    if not secret_string:
        return ""

    if secret_string.startswith("{") and secret_string.endswith("}"):
        try:
            data = json.loads(secret_string)
            if isinstance(data, dict):
                lines = [f"{k}={format_env_value(v)}" for k, v in data.items()]
                return "\n".join(lines) + "\n"
        except (json.JSONDecodeError, TypeError):
            pass

    # Plaintext .env lines
    return secret_string + "\n"


def fetch_secret(secret_name: str, region: str) -> str:
    """Fetch secret string from AWS Secrets Manager using boto3."""
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
    except ImportError:
        print(
            "[!] ERROR: 'boto3' is not installed in the current Python environment.",
            file=sys.stderr,
        )
        sys.exit(2)

    try:
        session = boto3.session.Session()
        client = session.client(
            service_name="secretsmanager",
            region_name=region,
        )
        response = client.get_secret_value(SecretId=secret_name)
    except NoCredentialsError:
        print(
            f"[!] ERROR: No AWS credentials found to fetch secret '{secret_name}'.\n"
            "    Ensure an IAM Role with Secrets Manager permissions is attached\n"
            "    to this EC2 instance, or AWS credentials are configured.",
            file=sys.stderr,
        )
        sys.exit(3)
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        print(
            f"[!] ERROR: AWS Secrets Manager error ({error_code}): {error_msg}",
            file=sys.stderr,
        )
        sys.exit(4)
    except Exception as e:
        print(f"[!] ERROR: Failed to retrieve secret '{secret_name}': {e}", file=sys.stderr)
        sys.exit(5)

    if "SecretString" in response:
        return parse_secret_string(response["SecretString"])
    elif "SecretBinary" in response:
        binary_data = base64.b64decode(response["SecretBinary"]).decode("utf-8")
        return parse_secret_string(binary_data)
    else:
        print(f"[!] ERROR: Secret '{secret_name}' has no string or binary content.", file=sys.stderr)
        sys.exit(6)


def write_env_file(content: str, output_path: str):
    """Write content to output file atomically and enforce strict 0600 permissions."""
    path = Path(output_path).resolve()
    temp_path = path.with_suffix(".tmp")

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.chmod(temp_path, 0o600)
        temp_path.replace(path)
        os.chmod(path, 0o600)
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        print(f"[!] ERROR: Failed to write env file to '{output_path}': {e}", file=sys.stderr)
        sys.exit(7)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch environment variables from AWS Secrets Manager and write to .env"
    )
    parser.add_argument(
        "--secret-name",
        "-s",
        required=True,
        help="AWS Secrets Manager secret name or ARN (e.g., spilbloo/dev/env)",
    )
    parser.add_argument(
        "--region",
        "-r",
        default=os.environ.get("AWS_REGION", "ap-south-1"),
        help="AWS Region (defaults to $AWS_REGION or ap-south-1)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=".env",
        help="Target output file path (defaults to .env in current directory)",
    )

    args = parser.parse_args()

    content = fetch_secret(args.secret_name, args.region)
    if not content:
        print(f"[!] WARNING: Retrieved secret '{args.secret_name}' is empty.")
    write_env_file(content, args.output)
    print(f"[+] Successfully fetched '{args.secret_name}' and wrote to '{args.output}' (mode 0600).")


if __name__ == "__main__":
    main()
