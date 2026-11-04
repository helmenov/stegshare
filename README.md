# stegshare

stegshare is a Python tool that embeds a confidential file into a FLAC audio file, splits it using Shamir's secret sharing in a k-out-of-n scheme, and restores the original file when enough FLAC files are gathered.

Key features:
- Embed a file directly into the FLAC LSB (Least Significant Bit) layer
- Split a single secret into multiple shares using Shamir secret sharing
- Reconstruct the original file from k or more FLAC files during recovery
- Provide both a CLI and a Python API

## What it can do

This project supports two main operations.

### 1. Split a file into FLAC shares

- Specify a secret file
- Specify a directory containing FLAC files
- Specify the threshold `k` and total count `n`
- Automatically generate `n` FLAC share files

Internally, it adds a length header to the secret data, splits it with Shamir, and embeds each share into the LSB of the FLAC audio samples.

### 2. Recover the original file from FLAC shares

- Provide multiple FLAC files needed for recovery
- Reconstruct the original file using `k` or more shares
- Output the original data in its original byte form

## Requirements

- Python 3.12 or later
- A directory containing FLAC files
- The source FLAC files must have enough audio capacity for the data being embedded

## Installation

```bash
mise install it+https://github.com/helmenov/stegshare.git" = "latest"
```

After installation, the `stegshare` command is available.

## CLI usage

### Show help

```bash
stegshare --help
```

### Split (secret file into FLAC shares)

```bash
stegshare split \
  -s ./secret_file \
  -w ./base_flacs \
  -o ./flac_shares \
  -k 3 \
  -n 5
```

- `-s` / `--secret`: path to the secret file
- `-w` / `--flacdir`: directory containing FLAC files
- `-o` / `--outdir`: output directory for generated FLAC shares
- `-k`: minimum number of files required for recovery
- `-n`: total number of shares to generate

After execution, FLAC files are generated in the output directory like this:

```text
./flac_shares/
  flac_share_1.flac
  flac_share_2.flac
  flac_share_3.flac
  flac_share_4.flac
  flac_share_5.flac
```

When distributing them, you may rename each FLAC file as needed.

### Recover (restore the original file from FLAC shares)

```bash
stegshare combine \
  -i flac_share_1.flac \
     flac_share_2.flac \
     flac_share_3.flac \
  -o ./recovered_file
```

- `-i` / `--inputs`: FLAC files to be used for recovery
- `-o` / `--output`: output path for the recovered file

If you prepare `k` or more shares from the split operation, the contents of `recovered_file` can be restored to match the original `secret_file` exactly.

## Python API usage

```python
from pathlib import Path
from stegshare import split_file_completely_into_flac, combine_flac_into_file

split_file_completely_into_flac(
    secret_file="./secret.txt",
    base_flac_dir="./base_flacs",
    output_dir="./flac_shares",
    k=3,
    n=5,
)

combine_flac_into_file(
    chosen_flac_paths=[
        "./flac_shares/flac_share_1.flac",
        "./flac_shares/flac_share_2.flac",
        "./flac_shares/flac_share_3.flac",
    ],
    recovered_file="./recovered.txt",
)
```

You can also use the lower-level LSB embedding and extraction directly:

```python
from pathlib import Path
from stegshare import embed_data_to_flac, extract_data_from_flac

embed_data_to_flac(
    base_flac_path=Path("./source.flac"),
    data_bytes=b"hello world",
    output_flac_path=Path("./embedded.flac"),
)

payload = extract_data_from_flac(Path("./embedded.flac"), data_len=11)
print(payload)
```

## Key implementation details

- `split` divides the secret file into 16-byte chunks
- Each chunk is converted into `k`-of-`n` shares using Shamir secret sharing
- The share data is embedded into the LSB of existing FLAC audio samples
- `combine` extracts the LSB from each FLAC file, reconstructs the data with Shamir, and restores the original file

## Constraints and warnings

- The FLAC directory must contain at least one `.flac` file
- If the FLAC audio data does not have enough capacity, embedding raises a `ValueError`
- `k` must be less than or equal to `n`
- Because the original FLAC is reused as a carrier for audio playback, the embedded data changes the audio waveform
- This tool is intended for hiding secret files inside FLAC files, not as a general-purpose encryption solution

## Example workflow

```bash
mkdir -p ./base_flacs ./flac_shares
# 1. Prepare FLAC files to use as shares
# 2. Split the secret
stegshare split -s ./important.txt -w ./base_flacs -o ./flac_shares -k 2 -n 4
# 3. Recover the original file using at least two FLAC files
stegshare combine -i ./flac_shares/flac_share_1.flac ./flac_shares/flac_share_2.flac -o ./restored.txt
```

## Reference

- Python package name: `stegshare`
- Command: `stegshare`
- Dependencies: `numpy`, `soundfile`, `pycryptodome`
