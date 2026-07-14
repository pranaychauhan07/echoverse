import argparse
import sys
from pathlib import Path

from echoverse.agents.intake import load_text
from echoverse.graph import run


def main():
    parser = argparse.ArgumentParser(description="EchoVerse: turn text into narrated audio.")
    parser.add_argument("--file", type=str, help="Path to a .txt or .pdf file to narrate.")
    parser.add_argument("--text", type=str, help="Raw text to narrate (alternative to --file).")
    parser.add_argument(
        "--tone",
        type=str,
        default="neutral",
        choices=["neutral", "suspenseful", "inspiring"],
        help="Narration tone.",
    )
    parser.add_argument("--out", type=str, default="narration.wav", help="Output filename (in data/output/).")
    args = parser.parse_args()

    if args.file:
        raw_text = load_text(Path(args.file))
    elif args.text:
        raw_text = args.text
    else:
        print("Reading text from stdin. Paste your text, then press Enter, Ctrl+Z, Enter:")
        raw_text = sys.stdin.read()

    run(raw_text, tone=args.tone, out_name=args.out)


if __name__ == "__main__":
    main()
