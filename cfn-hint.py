#!/usr/bin/env python3

import sys
import argparse
import logging
import re
from pathlib import Path
from difflib import unified_diff
from colorama import init, Fore

# === Exit Code Constants ===
EXIT_SUCCESS = 0
EXIT_GENERAL_FAILURE = 1
EXIT_NO_FILES_MATCHED = 2
EXIT_FILE_READ_ERROR = 3
EXIT_FILE_WRITE_ERROR = 4
EXIT_REGEX_ERROR = 6
EXIT_INTERNAL_ERROR = 8

def setup_logging(log_file=None, quiet=False):
    """Configures logging to file or stderr."""
    if quiet:
        logging.disable(logging.CRITICAL)
        return

    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    log_level = logging.INFO

    if log_file:
        logging.basicConfig(filename=log_file, level=log_level, format=log_format)
    else:
        logging.basicConfig(level=log_level, format=log_format, stream=sys.stderr)


def parse_hint(hint_line):
    """
    Parses a hint comment to extract the regex pattern and replacement string.
    Expected format: '# cfn-hint: replace: <pattern> with: <replacement>'
    """
    try:
        # Get text after the second colon (i.e., after "cfn-hint: replace:")
        parts = hint_line.split(':', 2)[-1].strip()
        # Split on the first ' with: ' to separate pattern and replacement
        pattern, replacement = parts.split(' with: ', 1)
        return pattern, replacement
    except (ValueError, IndexError) as e:
        raise ValueError(
            "Invalid hint format. Expected '# cfn-hint: replace: <pattern> with: <replacement>'."
            f" Error: {e}"
        )


def replace_line(line, pattern, replacement):
    """Applies a regex substitution to a single line."""
    try:
        # Validate pattern compiles
        re.compile(pattern)
        return re.sub(pattern, replacement, line)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: '{pattern}'. Details: {e}")


def process_content(content):
    """
    Processes the input content line by line, applies hints, and returns modified content.
    Preserves original line endings by using splitlines(keepends=True).
    """
    modified_lines = []
    lines_iter = iter(content.splitlines(keepends=True))

    for line in lines_iter:
        if "# cfn-hint: replace:" in line:
            # Keep the hint line itself
            modified_lines.append(line)
            # Attempt to parse the hint
            try:
                pattern, replacement = parse_hint(line)
            except ValueError as e:
                logging.error(f"Skipping hint due to error: {e}")
                # Do not consume the next line; continue so next line is processed normally
                continue

            # Consume the next line to apply replacement
            try:
                next_line = next(lines_iter)
            except StopIteration:
                logging.warning(f"Hint at EOF with no subsequent line to process: {line.strip()}")
                continue

            # Attempt to apply regex replacement
            try:
                modified_line = replace_line(next_line, pattern, replacement)
            except ValueError as e:
                logging.error(f"Skipping replacement due to invalid regex: {e}")
                # Append the unmodified next line
                modified_lines.append(next_line)
                continue

            # Append the replaced line
            modified_lines.append(modified_line)
        else:
            modified_lines.append(line)

    return "".join(modified_lines)


def print_diff(original_content, modified_content, file_name=""):
    """Generates and prints a colored unified diff."""
    display_name = f" ({file_name})" if file_name else ""
    diff_lines = unified_diff(
        original_content.splitlines(keepends=True),
        modified_content.splitlines(keepends=True),
        fromfile=f'original{display_name}',
        tofile=f'modified{display_name}',
    )

    diff_output = list(diff_lines)
    if not diff_output:
        print(Fore.GREEN + f"No changes detected for{display_name}.")
        return

    for line in diff_output:
        if line.startswith('+++') or line.startswith('---'):
            # Print file header lines without color
            print(line, end='')
        elif line.startswith('@@'):
            # Hunk header in cyan
            print(Fore.CYAN + line, end='')
        elif line.startswith('+'):
            # Added line in green
            print(Fore.GREEN + line, end='')
        elif line.startswith('-'):
            # Removed line in red
            print(Fore.RED + line, end='')
        else:
            # Context line or other metadata
            print(line, end='')


def parse_args():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Process CloudFormation YAML templates with hints.")

    # Mutually exclusive group: either --input or --stdin
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--input",
        help="One or more input files or glob patterns (e.g., 'templates/*.yml').",
        nargs='+',
        default=None
    )
    input_group.add_argument(
        "-", "--stdin",
        help="Accept input from stdin. Use '-' or '--stdin'.",
        action="store_true"
    )

    parser.add_argument(
        "--output-dir",
        help="Directory to save modified files. If not provided, prints to stdout.",
        type=Path,
        default=None
    )
    parser.add_argument(
        "--log",
        help="Path to a file for logging. If not set, logs to stderr.",
        default=None
    )
    parser.add_argument(
        "--diff",
        help="Show a unified diff of changes instead of full output.",
        action="store_true"
    )
    parser.add_argument(
        "--quiet",
        help="Suppress all output (including logs). Exit code only.",
        action="store_true"
    )

    return parser.parse_args()


def main():
    """Main execution function."""
    args = parse_args()

    # Initialize colorama for colored diff output
    init(autoreset=True)
    # Configure logging
    setup_logging(log_file=args.log, quiet=args.quiet)

    overall_exit_code = EXIT_SUCCESS

    if args.stdin:
        # === STDIN MODE ===
        logging.info("Reading from stdin...")
        try:
            original_content = sys.stdin.read()
        except Exception as e:
            logging.error(f"Error reading stdin: {e}", exc_info=True)
            return EXIT_FILE_READ_ERROR

        try:
            modified_content = process_content(original_content)
        except Exception as e:
            logging.error(f"An internal error occurred while processing stdin: {e}", exc_info=True)
            return EXIT_INTERNAL_ERROR

        if args.diff:
            print_diff(original_content, modified_content)
        else:
            print(modified_content)

        return EXIT_SUCCESS

    # === FILE MODE ===
    cwd = Path.cwd()
    files_to_process = set()

    # Expand each input pattern
    for pattern in args.input:
        p = Path(pattern)
        if p.is_absolute():
            # If absolute path, use parent.glob on the final name
            matched = list(p.parent.glob(p.name))
        else:
            # If pattern contains '**', use rglob; else use glob
            glob_method = cwd.rglob if "**" in pattern else cwd.glob
            matched = list(glob_method(pattern))

        if not matched:
            logging.warning(f"No files matched the pattern: {pattern}")

        for f in matched:
            if f.is_file():
                files_to_process.add(f)

    if not files_to_process:
        logging.error("No input files were found matching the provided patterns.")
        return EXIT_NO_FILES_MATCHED

    # If output directory is requested, create it
    if args.output_dir:
        try:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            logging.info(f"Output directory set to: {args.output_dir}")
        except OSError as e:
            logging.error(f"Could not create output directory '{args.output_dir}': {e}")
            return EXIT_FILE_WRITE_ERROR

    # Process each file
    for file_path in sorted(files_to_process):
        logging.info(f"Processing file: {file_path}")
        try:
            original_content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logging.error(f"Error reading file {file_path}: {e}")
            overall_exit_code = max(overall_exit_code, EXIT_FILE_READ_ERROR)
            continue

        try:
            modified_content = process_content(original_content)
        except Exception as e:
            logging.error(f"An internal error occurred while processing {file_path}: {e}", exc_info=True)
            overall_exit_code = max(overall_exit_code, EXIT_INTERNAL_ERROR)
            continue

        # If no changes, skip writing or printing
        if original_content == modified_content:
            logging.info(f"No changes made to {file_path}.")
            continue

        # If diff was requested, print colored diff
        if args.diff:
            print_diff(original_content, modified_content, file_name=str(file_path))

        # Else if output directory specified, write out the modified file
        elif args.output_dir:
            output_path = args.output_dir / file_path.name
            try:
                output_path.write_text(modified_content, encoding="utf-8")
                logging.info(f"Successfully wrote modified file to {output_path}")
            except Exception as e:
                logging.error(f"Failed to write to output file {output_path}: {e}")
                overall_exit_code = max(overall_exit_code, EXIT_FILE_WRITE_ERROR)

        # Otherwise, print the modified content to stdout
        else:
            print(f"--- # Modified content for {file_path}\n{modified_content}")

    return overall_exit_code


if __name__ == "__main__":
    sys.exit(main())
