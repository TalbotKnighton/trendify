"""Verifies the current tag being pushed is documented in changelog. Only applies to tags with format `vX.Y.Z`"""

import datetime
import re
import sys
from pathlib import Path


def main() -> int:
    changelog_path = Path("CHANGELOG.md")
    if not changelog_path.exists():
        print("ERROR: CHANGELOG.md file not found!", file=sys.stderr)
        return 1

    # Get today's local date in YYYY-MM-DD format
    today_str = datetime.date.today().isoformat()

    pushed_tags: list[str] = []

    # Git passes pushed refs via stdin in the format:
    # <local ref> <local sha> <remote ref> <remote sha>
    for line in sys.stdin.read().splitlines():
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) < 3:
            continue

        local_ref = parts[0]

        # Extract the version string ONLY if a tag ref is currently being pushed (e.g. refs/tags/v2.6.8 or refs/tags/2.6.8)
        tag_match = re.match(r"^refs/tags/v?([0-9]+\.[0-9]+\.[0-9]+)", local_ref)
        if tag_match:
            pushed_tags.append(tag_match.group(1))

    # If no version tag is being pushed in this command (e.g. normal branch push), pass cleanly
    if not pushed_tags:
        return 0

    changelog_text = changelog_path.read_text()
    errors = []

    for version in pushed_tags:
        # STRICT MATCH ONLY: ## Version X.X.X (YYYY-MM-DD)
        expected_header = f"## Version {version} ({today_str})"

        # Exact regex search for the strict header format at line start
        pattern = re.compile(
            rf"^##\s+Version\s+{re.escape(version)}\s*\((?P<date>\d{{4}}-\d{{2}}-\d{{2}})\)",
            re.MULTILINE,
        )

        match = pattern.search(changelog_text)

        if not match:
            errors.append(
                f"ERROR: Pushed tag 'v{version}' does not have a matching heading in CHANGELOG.md!\n"
                f"  Expected exact format: {expected_header}"
            )
            continue

        tag_date = match.group("date")
        if tag_date != today_str:
            errors.append(
                f"ERROR: Date mismatch for tag 'v{version}' in CHANGELOG.md!\n"
                f"  Found date:   {tag_date}\n"
                f"  Today's date: {today_str}\n"
                f"  Expected exact format: {expected_header}"
            )

    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
