# Prepare public SDK files

Extract assets from the artifact files and reorganize the files for publication on GitHub.

## Inputs

- `sdk`: Name of SDK to release (e.g. cast)
- `tag`: Release tag (e.g. v10.4.0)
- `dir`: Path to the folder containing the build artifacts

## Outputs

- `assets_dir`: Path to the directory containing all the generated assets
- `examples_dir`: Path to the directory containing the example source code
- `headers_dir`: Path to the directory containing the headers
- `documentation_dir`: Path to the directory containing the documentation, if any

## Example usage

    - uses: ./.github/actions/prepare-sdk
      with:
        sdk: cast
        tag: v10.4.0
        dir: path/to/downloaded/zips

## Naming convention

This action tries to deduce the compiler/platform from the artifacts file names to generate the correct asset name.
Example:

    cast_sdk_framework_iOS.arm64...zip => cast-10.4.0-framework-ios.arm64.zip
