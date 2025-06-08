# CFN Hint Processor

A Python CLI tool for processing AWS CloudFormation YAML templates by applying `# cfn-hint: replace: <regex> with: <text>` directives. It supports reading from files (with glob patterns) or from stdin, outputs modified content (or a unified diff), offers logging, and returns detailed exit codes for automation and diagnostics.

---

## Table of Contents

1. [Requirements](#requirements)  
2. [Solution Architecture](#solution-architecture)  
3. [Constraints](#constraints)  
4. [Assumptions](#assumptions)  
5. [Design Decisions](#design-decisions)  
6. [QuickStart Guide](#quickstart-guide)  
7. [Detailed Usage Guide](#detailed-usage-guide)  
8. [Return Results / Exit Codes](#return-results--exit-codes)  
9. [Examples (Before / After)](#examples-before--after)  
10. [Contribution Guide](#contribution-guide)

---

## Requirements

- Python version: ≥ 3.7  
- Dependencies: `colorama`  
- Platforms: Linux, macOS, Windows  

Install dependencies:

```bash
pip install colorama
```

---

## Solution Architecture

**Script:** `cfn-hint.py`

### Key Components

- `main()`: CLI entry point  
- `parse_args()`: CLI parser with mutually exclusive `--input` or `--stdin`  
- `setup_logging()`: Optional file logging or stderr  
- `parse_hint()`: Parses `# cfn-hint: replace:` lines  
- `replace_line()`: Applies regex substitution  
- `process_content()`: Applies all hints to file content  
- `print_diff()`: Shows unified diff  
- File mode loop: Processes files from globs  
- Exit codes: Returned to shell/CI

---

## Constraints

- Only `# cfn-hint: replace: <pattern> with: <text>` format is supported  
- Replacements apply only to the next line  
- UTF-8 input only  
- Diff logic assumes ANSI terminal  
- Globs are resolved relative to current working directory  
- Output is skipped for unchanged files  

---

## Assumptions

- Regex patterns are Python-compatible  
- No multiline or lookbehind  
- Input files are valid YAML (but not parsed as YAML)  
- Hints must be properly formatted  
- Users are responsible for meaningful patterns  

---

## Design Decisions

- One file, no external config  
- Precise diff output for debugging  
- Replacements are line-by-line only  
- Invalid hints are skipped with logs  
- Globs follow Unix-like rules  
- Preserves original line endings  

---

## QuickStart Guide

```bash
# Create a test file
cat <<EOF > template.yml
Resources:
  MyBucket:
    Type: AWS::S3::Bucket
    Properties:
      # cfn-hint: replace: old-name with: new-name
      BucketName: old-name
EOF

# Run the tool
python cfn-hint.py --input template.yml
```

---

## Detailed Usage Guide

### Arguments

| Argument        | Description                                                 |
|----------------|-------------------------------------------------------------|
| `--input`       | Files or globs (e.g., `'templates/*.yml'`)                 |
| `--stdin`       | Accept input from stdin                                    |
| `--output-dir`  | Directory to save modified files                           |
| `--diff`        | Print unified diff instead of full output                  |
| `--log`         | Log file path (optional)                                   |
| `--quiet`       | Suppress all output/logs; only exit code is returned       |

### Behavior

- Input mode: `--input` OR `--stdin`, not both  
- Output mode: `--output-dir` OR stdout  
- Diff mode: if `--diff` is passed, print unified diffs  
- Quiet mode: suppresses all logs and stdout  

---

## Return Results / Exit Codes

| Code | Meaning                      |
|------|------------------------------|
| 0    | Success                      |
| 1    | General failure              |
| 2    | No files matched             |
| 3    | File read error              |
| 4    | File write error             |
| 6    | Invalid regex                |
| 8    | Internal exception           |

---

## Examples (Before / After)

### 1. Basic Replacement

**Input (`template.yml`):**
```yaml
# cfn-hint: replace: old-bucket with: new-bucket
BucketName: old-bucket
```

**Command:**
```bash
python cfn-hint.py --input template.yml
```

**Output:**
```yaml
# cfn-hint: replace: old-bucket with: new-bucket
BucketName: new-bucket
```

---

### 2. Stdin Mode

```bash
cat template.yml | python cfn-hint.py --stdin
```

---

### 3. Output to Directory

```bash
python cfn-hint.py --input 'configs/**/*.yml' --output-dir out/
```

---

### 4. Diff Mode

```bash
python cfn-hint.py --input template.yml --diff
```

---

### 5. Invalid Hint Format

```yaml
# cfn-hint: replace this with that
```

**Behavior:** Skipped and logged, exit code remains 0.

---

### 6. Invalid Regex

```yaml
# cfn-hint: replace: [ with x
```

**Behavior:** Logs regex error, continues processing other hints.

---

## Contribution Guide

### Steps

1. Fork the repository  
2. Clone your fork  
3. Create a feature branch  
4. Install dependencies  
5. Make changes  
6. Add or modify tests in `tests/`  
7. Run all tests before committing  
8. Commit using semantic messages (e.g., `fix:`, `feat:`)  
9. Push and open a pull request  

### Guidelines

- Keep CLI changes backward compatible  
- Add docstrings and comments for complex logic  
- Format using `black` and `isort`  
- Be clear in PR titles and bodies

---

## Summary

This tool provides a fast, reliable way to apply `# cfn-hint` directives to CloudFormation templates. It integrates well with CI/CD pipelines, enforces consistency, and supports interactive or batch workflows.

Pull requests and issues welcome!
