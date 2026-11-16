"""Refuse a firmware manifest that would let an older app install newer firmware.

Rule (Shane, 2026-11-16): customers must not be able to update controller
firmware until they have the app version that matches it.

How that is enforced:
  * afterglo2_manifest.json is read by apps OLDER than 5.2.0+67, which ignore
    minAppBuild. It stays frozen at roofline 1.3.1 for good.
  * afterglo2_manifest_v2.json is read by 5.2.0+67 and later, which refuse an
    image whose minAppBuild is above their own build ("update the app first").
    Every roofline image there must carry minAppBuild >= app_compat.json.

Run before every manifest commit:   python tools/check_manifest.py
Exit code 1 and a reason on any violation.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGACY_FROZEN = "1.3.1"


def ver(s):
    return tuple(int(x) for x in str(s).split("."))


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def main():
    errors = []
    compat = load("app_compat.json")["roofline"]

    legacy = load("afterglo2_manifest.json")["images"].get("roofline", {})
    if legacy and ver(legacy.get("version", "0")) > ver(LEGACY_FROZEN):
        errors.append("afterglo2_manifest.json roofline is %s; it must stay at %s "
                      "(apps older than build 67 read it and ignore minAppBuild)"
                      % (legacy.get("version"), LEGACY_FROZEN))

    v2 = load("afterglo2_manifest_v2.json")
    top_min = v2.get("minAppBuild")
    roof = v2.get("images", {}).get("roofline")
    if roof:
        v = roof.get("version")
        have = roof.get("minAppBuild", top_min)
        need = compat.get(v)
        if need is None:
            errors.append("roofline %s is not in app_compat.json; add it with the "
                          "build of the app released alongside it" % v)
        elif have is None:
            errors.append("roofline %s has no minAppBuild (needs >= %d)" % (v, need))
        elif int(have) < need:
            errors.append("roofline %s has minAppBuild %s but needs >= %d"
                          % (v, have, need))
        app = v2.get("app")
        if app and need is not None and int(app.get("build", 0)) < need:
            errors.append("app pop-up offers build %s, older than the %d that "
                          "roofline %s needs" % (app.get("build"), need, v))

    if errors:
        print("MANIFEST REFUSED:")
        for e in errors:
            print("  - " + e)
        return 1
    print("manifest OK: roofline %s, minAppBuild %s"
          % (roof and roof.get("version"), roof and roof.get("minAppBuild", top_min)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
