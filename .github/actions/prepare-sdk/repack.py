#!/usr/bin/env python3

# - repack the binaries into assets ready for upload to a GitHub release
# - collect the examples source code
# - collect the headers
# - collect the documentation ready for publication on GitHub Pages (gh-pages branch)
# - create Xcode frameworks bundles

# Expected directory structure of the zip files:
#
#   .
#   ├── doc
#   ├── examples
#   ├── include
#   └── ...


import argparse
import fnmatch
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path


def parse_arguments():
    parser = argparse.ArgumentParser(description="Repack the binaries into assets ready for upload to a GitHub release")
    parser.add_argument("sdk", type=str, help="SDK name")
    parser.add_argument("tag", type=str, help="Tag version")
    parser.add_argument("input_dir", type=str, help="Input directory")
    parser.add_argument("output_dir", type=str, help="Output directory with assets, examples, headers and documentation")
    parser.add_argument("--bundle-frameworks", action="store_true", help="Bundle Xcode frameworks (must run on macOS)")
    return parser.parse_args()

args = parse_arguments()

version = re.compile(r"v(\d+\.\d+\.\d+)").sub(r"\1", args.tag)
assert version >= "11.3.3", f"Current version is too old (minimum: 11.3.3, current: {version})"

print(f"Bundle frameworks? {args.bundle_frameworks}")
print(f"Scanning dir '{args.input_dir}'")

def ensure_dir(*args):
    dir = Path(*args)
    if not dir.exists():
        Path.mkdir(dir, parents=True)
    return dir

sdk = args.sdk

assets_dir = ensure_dir(args.output_dir, "assets")
examples_dir = ensure_dir(args.output_dir, "examples")
headers_dir = ensure_dir(args.output_dir, "include")
documentation_dir = ensure_dir(args.output_dir, "doc")

tmp_dir = Path(tempfile.mkdtemp(dir=ensure_dir("tmp")))

known_zips = {
    # Map an artifact name (from the builder) to an asset name (to GitHub)
    f"{sdk}_sdk_aar_Android.*.aarch64*": f"{sdk}-{version}-aar-android.arm64-v8a",
    f"{sdk}_sdk_aar_Android.*.armv7-a*": f"{sdk}-{version}-aar-android.armeabi-v7a",
    f"{sdk}_sdk_aar_Android.*.i686*": f"{sdk}-{version}-aar-android.x86",
    f"{sdk}_sdk_aar_Android.*.x86_64*": f"{sdk}-{version}-aar-android.x86_64",
    f"{sdk}_sdk_Android.*.aarch64*": f"{sdk}-{version}-android.arm64-v8a",
    f"{sdk}_sdk_Android.*.armv7-a*": f"{sdk}-{version}-android.armeabi-v7a",
    f"{sdk}_sdk_Android.*.i686*": f"{sdk}-{version}-android.x86",
    f"{sdk}_sdk_Android.*.x86_64*": f"{sdk}-{version}-android.x86_64",
    f"{sdk}_sdk_Darwin.*.arm64*": f"{sdk}-{version}-macos.arm64",
    f"{sdk}_sdk_Darwin.*.x86_64*": f"{sdk}-{version}-macos.x86_64",
    f"{sdk}_sdk_Windows.*.AMD64*": f"{sdk}-{version}-windows.x86_64",
    f"{sdk}_sdk_Windows.*MSVC*": f"{sdk}-{version}-windows.x86_64",
    f"{sdk}_sdk_Linux.ubuntu-20.04.GNU-*.x86_64*": f"{sdk}-{version}-linux.x86_64-gcc_ubuntu_20.04",
    f"{sdk}_sdk_Linux.ubuntu-22.04.GNU-*.x86_64*": f"{sdk}-{version}-linux.x86_64-gcc_ubuntu_22.04",
    f"{sdk}_sdk_Linux.ubuntu-23.10.GNU-*.x86_64*": f"{sdk}-{version}-linux.x86_64-gcc_ubuntu_23.10",
    f"{sdk}_sdk_Linux.ubuntu-24.04.GNU-*.x86_64*": f"{sdk}-{version}-linux.x86_64-gcc_ubuntu_24.04",
    f"{sdk}_sdk_Linux.ubuntu-20.04.GNU-*.aarch64*": f"{sdk}-{version}-linux.aarch64-gcc_ubuntu_20.04",
    f"{sdk}_sdk_Linux.ubuntu-22.04.GNU-*.aarch64*": f"{sdk}-{version}-linux.aarch64-gcc_ubuntu_22.04",
    f"{sdk}_sdk_Linux.ubuntu-23.10.GNU-*.aarch64*": f"{sdk}-{version}-linux.aarch64-gcc_ubuntu_23.10",
    f"{sdk}_sdk_Linux.ubuntu-24.04.GNU-*.aarch64*": f"{sdk}-{version}-linux.aarch64-gcc_ubuntu_24.04",
}

known_frameworks = {
    # note there are some duplicates because we are going to merge similar frameworks into a single asset
    f"{sdk}_sdk_framework_iOS.*.arm64_*": f"{sdk}-{version}-framework-arm64",
    f"{sdk}_sdk_framework_iphonesimulator.iOS.*.arm64_*": f"{sdk}-{version}-framework-arm64",
    f"{sdk}_sdk_framework_Darwin.*.arm64_*": f"{sdk}-{version}-framework-arm64",
    f"{sdk}_sdk_framework_Darwin.*.x86_64_*": f"{sdk}-{version}-framework-x86_64",
}

known_binaries = [f"{sdk}-*.aar", f"lib{sdk}.*", f"{sdk}.lib", f"{sdk}.dll"]

known_wheels = {
    # Map a python artifact name (from the builder) to an asset name (to GitHub)
    "pyclariuscast*-wheel_Darwin.*.arm64*": f"cast-{version}-macos.arm64",
    "pyclariuscast*-wheel_Darwin.*.x86_64*": f"cast-{version}-macos.x86_64",
    "pyclariuscast*-wheel_Linux.ubuntu-20.04.GNU-*.x86_64*": f"cast-{version}-linux.x86_64-gcc_ubuntu_20.04",
    "pyclariuscast*-wheel_Linux.ubuntu-22.04.GNU-*.x86_64*": f"cast-{version}-linux.x86_64-gcc_ubuntu_22.04",
    "pyclariuscast*-wheel_Linux.ubuntu-23.10.GNU-*.x86_64*": f"cast-{version}-linux.x86_64-gcc_ubuntu_23.10",
    "pyclariuscast*-wheel_Linux.ubuntu-24.04.GNU-*.x86_64*": f"cast-{version}-linux.x86_64-gcc_ubuntu_24.04",
    "pyclariuscast*-wheel_Linux.ubuntu-20.04.GNU-*.aarch64*": f"cast-{version}-linux.aarch64-gcc_ubuntu_20.04",
    "pyclariuscast*-wheel_Linux.ubuntu-22.04.GNU-*.aarch64*": f"cast-{version}-linux.aarch64-gcc_ubuntu_22.04",
    "pyclariuscast*-wheel_Linux.ubuntu-23.10.GNU-*.aarch64*": f"cast-{version}-linux.aarch64-gcc_ubuntu_23.10",
    "pyclariuscast*-wheel_Linux.ubuntu-24.04.GNU-*.aarch64*": f"cast-{version}-linux.aarch64-gcc_ubuntu_24.04",
    "pyclariuscast*-wheel_Windows.*.AMD64*": f"cast-{version}-windows.x86_64",
    "pyclariuscast*-wheel_Windows.*MSVC*": f"cast-{version}-windows.x86_64",
}


def assert_no_duplicates(zips):
    """Ensure that no pattern matches more than one artifact (to avoid overwriting assets)"""
    all_files = [x.name for x in zips]
    for glob_pattern in known_zips.keys():
        assert (
            len(fnmatch.filter(all_files, glob_pattern)) <= 1
        ), "Pattern matched by multiple artifacts, aborting to prevent overwrites"


def find_known_file(filename: str, table: dict):
    for glob_pattern, asset_name in table.items():
        if fnmatch.fnmatch(filename, glob_pattern):
            return asset_name
    return None


def extract_zip(zip_file: Path, dest: Path, files=None):
    # using the zip command because the zipfile module doesn't support symbolic links
    cmd = ["unzip", zip_file.resolve()]
    if files:
        cmd += files if isinstance(files, list) else [files]
    cmd += ["-d", dest.resolve()]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL)


def compress_dir(zip_file: Path, dir: Path, tmp_dir: Path):
    # using the zip command because the zipfile module doesn't support symbolic links
    subprocess.check_call(
        ["zip", zip_file.resolve(), "--temp-path", tmp_dir.resolve(), "--symlinks", "-r", "."],
        cwd=dir,
        stdout=subprocess.DEVNULL,
    )


def sync_folder(source: Path, *destinations):
    """Sync the folder's content into the destination(s)"""
    if not source.exists():
        print(f"\tSkipping '{source.name}' because it is missing")
        return
    resolved_source = f"{source.resolve()}/"  # trailing slash to tell rsync to sync the content only
    for dest in destinations:
        Path(dest).mkdir(parents=True, exist_ok=True)
        subprocess.check_call(["rsync", "-azvh", resolved_source, dest], stdout=subprocess.DEVNULL)


def main(zip_dir: Path, with_frameworks: bool):
    zips = list(zip_dir.glob("*.zip"))
    assert_no_duplicates(zips)
    zip_count = len(zips)
    asset_dirs = set()
    frameworks = {}
    print(f"Found {zip_count} zip file(s)")
    for index, zip in enumerate(zips):
        print(f"[{index+1}/{zip_count}] Found: {zip.name}")
        if asset_name := find_known_file(zip.name, known_zips):
            path = extract_lib_zip(zip, asset_name)
            asset_dirs.add(path)
            print(f"\tAsset folder: {asset_name}")
        elif asset_name := find_known_file(zip.name, known_frameworks):
            path = extract_framework_zip(zip)
            frameworks.setdefault(asset_name, []).append(path)
            print(f"\tAsset folder: {asset_name}")
        elif asset_name := find_known_file(zip.name, known_wheels):
            path = extract_wheel_zip(zip, asset_name)
            asset_dirs.add(path)
            print(f"\tAsset folder: {asset_name}")
        else:
            print("\tSkipping unknown file")
            continue
    if with_frameworks:
        framework_count = len(frameworks)
        for index, (asset_name, paths) in enumerate(frameworks.items()):
            print(f"[{index+1}/{framework_count}] Bundling framework: {asset_name}")
            path = bundle_frameworks(asset_name, paths)
            asset_dirs.add(path)
    asset_count = len(asset_dirs)
    for index, asset_dir in enumerate(asset_dirs):
        asset_file = assets_dir / f"{asset_dir.name}.zip"
        print(f"[{index+1}/{asset_count}] Compressing asset: {asset_file.name}")
        compress_dir(asset_file, asset_dir, tmp_dir)


def bundle_frameworks(asset_name: str, paths: list):
    """
    Create a multi-platform framework
    """
    asset_dir = ensure_dir(tmp_dir / asset_name)
    output = f"{asset_dir}/clarius_{sdk}.xcframework"
    cmd = ["xcodebuild", "-create-xcframework"]
    for path in paths:
        cmd += ["-framework", path]
    cmd += ["-output", output]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL)
    return asset_dir


def compute_doc_folders(zip: Path, artifact_dir: Path, basedir: Path):
    """
    Compute the source and destination folders for the documentation
    """
    if "sdk_aar_Android" in zip.name:
        return {
            "from_dir": artifact_dir / "doc" / "javadoc",
            "to_dir": basedir / "reference" / "android" / version,
        }


def extract_lib_zip(zip: Path, asset_name: str):
    """
    Extract artifacts that are C/C++ archives
    """
    asset_dir = ensure_dir(tmp_dir / asset_name)
    artifact_dir = ensure_dir(tmp_dir / zip.stem)
    extract_zip(zip, artifact_dir)
    sync_folder(artifact_dir.joinpath("include"), asset_dir, headers_dir)
    sync_folder(artifact_dir.joinpath("examples"), examples_dir)
    if doc_folder := compute_doc_folders(zip, artifact_dir, documentation_dir):
        sync_folder(doc_folder["from_dir"], ensure_dir(doc_folder["to_dir"]))
    # find binaries
    for glob_pattern in known_binaries:
        for binary in artifact_dir.rglob(glob_pattern):
            shutil.move(binary, asset_dir)
    return asset_dir


def extract_framework_zip(zip: Path):
    artifact_dir = ensure_dir(tmp_dir / zip.stem)
    extract_zip(zip, artifact_dir)
    sync_folder(artifact_dir.joinpath("examples"), examples_dir)
    frameworks = list(artifact_dir.glob(f"**/{sdk}_framework.framework"))
    assert len(frameworks) == 1, "Expected exactly one framework folder"
    return frameworks[0]


python_wheel_re = re.compile(r"pyclariuscast(\d+)-wheel")


def extract_wheel_zip(zip: Path, asset_name: str):
    """
    Extract artifacts that are python wheels

    The function finds the shared library in the given wheel and moves it to the asset directory,
    inside a subfolder corresponding to the python version found in the wheel name.
    Run this function several times with the same asset name to merge the wheels for different python versions.

    Expected input: a zip file containing a single wheel file, which is itself a zip file with the shared library.
    """
    match = python_wheel_re.match(zip.name)
    assert match, "Could not get python version from the wheel file"
    python_version = match.group(1)
    # extract the wheel from the zip
    asset_dir = ensure_dir(tmp_dir / asset_name)
    artifact_dir = ensure_dir(tmp_dir / zip.stem)
    extract_zip(zip, artifact_dir, files="*.whl")
    extracted = list(artifact_dir.glob("*.whl"))
    assert len(extracted) == 1, "Did not extract exactly one wheel file as expected"
    # extract the shared library from the wheel
    wheel_file = extracted[0]
    wheel_subdir = ensure_dir(artifact_dir / "wheel")
    extract_zip(wheel_file, wheel_subdir, files="pyclarius*/lib/*")
    extracted = list(wheel_subdir.glob("pyclarius*/lib/*"))
    assert len(extracted) == 1, "Did not extract exactly one shared library file as expected"
    # move the shared library to the asset directory
    lib_dir = Path(extracted[0]).parent
    dest_dir = asset_dir / f"python{python_version}"
    shutil.move(lib_dir, dest_dir)
    return asset_dir


try:
    zip_dir = Path(args.input_dir)
    with_frameworks = args.with_frameworks
    main(zip_dir, with_frameworks)
except Exception:
    print("-" * 60)
    traceback.print_exc(file=sys.stderr)
    print("-" * 60)
    sys.exit(1)
