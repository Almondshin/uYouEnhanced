#!/usr/bin/env python3
"""Add (or refresh) a release entry in the SideStore/AltStore source JSON.

Usage: update_sidestore_source.py SOURCE_JSON IPA TAG [DATE]

Reads version info straight out of the IPA's Info.plist so the entry matches
what SideStore sees on the installed app, and derives the public download URL
from the release tag and the IPA filename.

Note: SideStore decides "update available" by comparing version/buildVersion
with the installed app's CFBundleShortVersionString/CFBundleVersion. A rebuild
that keeps the same YouTube version (only the uYou version changed) will not
show as an update unless buildapp.yml bumps CFBundleVersion.
"""
import hashlib
import json
import plistlib
import sys
import zipfile
from datetime import date
from pathlib import Path
from urllib.parse import quote

REPO = "Almondshin/uYouEnhanced"


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__, file=sys.stderr)
        return 2
    source_path, ipa_path, tag = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    published = sys.argv[4] if len(sys.argv) > 4 else date.today().isoformat()

    with zipfile.ZipFile(ipa_path) as ipa:
        plist_name = next(n for n in ipa.namelist()
                          if n.count("/") == 2 and n.endswith(".app/Info.plist"))
        info = plistlib.loads(ipa.read(plist_name))

    digest = hashlib.sha256()
    with ipa_path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)

    entry = {
        "version": info["CFBundleShortVersionString"],
        "buildVersion": info.get("CFBundleVersion", info["CFBundleShortVersionString"]),
        "date": published,
        "localizedDescription": tag,
        "downloadURL": f"https://github.com/{REPO}/releases/download/"
                       f"{quote(tag, safe='')}/{quote(ipa_path.name, safe='')}",
        "size": ipa_path.stat().st_size,
        "sha256": digest.hexdigest(),
        "minOSVersion": info.get("MinimumOSVersion", "16.0"),
    }

    source = json.loads(source_path.read_text())
    app = next(a for a in source["apps"] if a["bundleIdentifier"] == info["CFBundleIdentifier"])
    app["versions"] = [entry] + [v for v in app["versions"] if v["downloadURL"] != entry["downloadURL"]]
    source_path.write_text(json.dumps(source, indent=2, ensure_ascii=False) + "\n")
    print(f"{source_path}: added {entry['version']} ({entry['buildVersion']}) -> {entry['downloadURL']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
