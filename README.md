# stegshare

<<<<<<< HEAD
<<<<<<< HEAD
stegshare は、機密ファイルを FLAC 音声ファイルへ埋め込み、Shamir の秘密分散を使って k-out-of-n で分割し、必要数の FLAC を揃えれば元ファイルを復元できる Python ツールです。

主な特徴:
- ファイルをそのまま FLAC の LSB（Least Significant Bit）領域へ埋め込む
- Shamir 秘密分散で 1 つの秘密を複数の共有へ分割
- 復元時に指定した k 個以上の FLAC から元ファイルを再構築
- CLI と Python API の両方を提供

## できること

このプロジェクトでは、以下の 2 つの操作を行えます。

### 1. ファイルを FLAC 共有へ分割

- 秘密ファイルを指定
- FLAC ファイルが入ったディレクトリを指定
- しきい値 `k` と総数 `n` を指定
- `n` 枚の FLAC 共有ファイルを自動生成

内部的には、秘密データの長さヘッダーを付加したうえで Shamir 分割し、各 share を FLAC の音声サンプル LSB に埋め込みます。

### 2. FLAC 共有から元ファイルを復元

- 復元に必要な FLAC ファイルを複数指定
- `k` 以上の share を使用して元ファイルを生成
- 元のデータを元のバイト列として出力

## 必要条件

- Python 3.12 以上
- FLAC ファイルが含まれるディレクトリ
- 生成元となる FLAC ファイルの音声容量が、埋め込むデータサイズに対して十分であること

## インストール

```bash
mise install it+https://github.com/helmenov/stegshare.git" = "latest"
```

インストール後は `stegshare` コマンドを使えます。

## CLI の利用方法

### ヘルプ表示

```bash
stegshare --help
```

### 分割（秘密ファイルを FLAC 共有へ）

```bash
stegshare split \
  -s ./secret_file \
  -w ./base_flacs \
  -o ./flac_shares \
  -k 3 \
  -n 5
```

- `-s` / `--secret`: 秘密ファイルのパス
- `-w` / `--flacdir`: FLAC ファイルが格納されたディレクトリ
- `-o` / `--outdir`: 生成される FLAC 共有の出力ディレクトリ
- `-k`: 復元に必要な最小ファイル数
- `-n`: 生成する総共有数

実行後、出力先に次のような FLAC が生成されます。

```text
./flac_shares/
  flac_share_1.flac
  flac_share_2.flac
  flac_share_3.flac
  flac_share_4.flac
  flac_share_5.flac
```

配信する場合には各 FLAC ファイルの名前は変更しても構いません。


### 復元（FLAC 共有から元ファイルを取り出す）

```bash
stegshare combine \
  -i flac_share_1.flac \
     flac_share_2.flac \
     flac_share_3.flac \
  -o ./recovered_file
```

- `-i` / `--inputs`: 復元に用いる FLAC ファイル群
- `-o` / `--output`: 復元したファイルの出力先

分割時の `k` 以上の共有を用意できれば、`recovered_file` の内容は，元の `secret_file` と同一に復元できます。

## Python API での利用

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

または、より直接的に LSB の埋め込み・抽出を使うこともできます。

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

## 仕組みの要点

- `split` は秘密ファイルを 16 バイトごとに分割します
- 各ブロックを Shamir により `k` から `n` の共有へ変換
- 共有データを既存の FLAC の音声サンプルの LSB に埋め込む
- `combine` は各 FLAC から LSB を抽出し、Shamir で再構成し、最終的に元ファイルを復元する

## 制約と注意

- FLAC ディレクトリには `.flac` ファイルが少なくとも 1 個必要です
- FLAC の音声データの容量が足りない場合、埋め込み時に `ValueError` になります
- `k` は `n` 以下である必要があります
- 元の FLAC をそのまま再生用として利用する前提のため、埋め込みには音声データの変化が伴います
- これは「秘匿したいファイルを FLAC に隠す」用途を想定しており、通常のファイル暗号化と同等の用途ではありません

## 例: 実行フロー

```bash
mkdir -p ./base_flacs ./flac_shares
# 1. 共有用の FLAC を準備する
# 2. シークレットを分割
stegshare split -s ./important.txt -w ./base_flacs -o ./flac_shares -k 2 -n 4
# 3. 2 枚以上の FLAC を持って元ファイルを復元
stegshare combine -i ./flac_shares/flac_share_1.flac ./flac_shares/flac_share_2.flac -o ./restored.txt
```

## 参考

- Python パッケージ名: `stegshare`
- 実行コマンド: `stegshare`
- 依存ライブラリ: `numpy`, `soundfile`, `pycryptodome`

||||||| parent of 00e5eb8 (initial committ)
=======
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
>>>>>>> 00e5eb8 (initial committ)
||||||| e581f81
=======
stegshare は、機密ファイルを FLAC 音声ファイルへ埋め込み、Shamir の秘密分散を使って k-out-of-n で分割し、必要数の FLAC を揃えれば元ファイルを復元できる Python ツールです。

主な特徴:
- ファイルをそのまま FLAC の LSB（Least Significant Bit）領域へ埋め込む
- Shamir 秘密分散で 1 つの秘密を複数の共有へ分割
- 復元時に指定した k 個以上の FLAC から元ファイルを再構築
- CLI と Python API の両方を提供

## できること

このプロジェクトでは、以下の 2 つの操作を行えます。

### 1. ファイルを FLAC 共有へ分割

- 秘密ファイルを指定
- FLAC ファイルが入ったディレクトリを指定
- しきい値 `k` と総数 `n` を指定
- `n` 枚の FLAC 共有ファイルを自動生成

内部的には、秘密データの長さヘッダーを付加したうえで Shamir 分割し、各 share を FLAC の音声サンプル LSB に埋め込みます。

### 2. FLAC 共有から元ファイルを復元

- 復元に必要な FLAC ファイルを複数指定
- `k` 以上の share を使用して元ファイルを生成
- 元のデータを元のバイト列として出力

## 必要条件

- Python 3.12 以上
- FLAC ファイルが含まれるディレクトリ
- 生成元となる FLAC ファイルの音声容量が、埋め込むデータサイズに対して十分であること

## インストール

```bash
mise install it+https://github.com/helmenov/stegshare.git" = "latest"
```

インストール後は `stegshare` コマンドを使えます。

## CLI の利用方法

### ヘルプ表示

```bash
stegshare --help
```

### 分割（秘密ファイルを FLAC 共有へ）

```bash
stegshare split \
  -s ./secret_file \
  -w ./base_flacs \
  -o ./flac_shares \
  -k 3 \
  -n 5
```

- `-s` / `--secret`: 秘密ファイルのパス
- `-w` / `--flacdir`: FLAC ファイルが格納されたディレクトリ
- `-o` / `--outdir`: 生成される FLAC 共有の出力ディレクトリ
- `-k`: 復元に必要な最小ファイル数
- `-n`: 生成する総共有数

実行後、出力先に次のような FLAC が生成されます。

```text
./flac_shares/
  flac_share_1.flac
  flac_share_2.flac
  flac_share_3.flac
  flac_share_4.flac
  flac_share_5.flac
```

配信する場合には各 FLAC ファイルの名前は変更しても構いません。


### 復元（FLAC 共有から元ファイルを取り出す）

```bash
stegshare combine \
  -i flac_share_1.flac \
     flac_share_2.flac \
     flac_share_3.flac \
  -o ./recovered_file
```

- `-i` / `--inputs`: 復元に用いる FLAC ファイル群
- `-o` / `--output`: 復元したファイルの出力先

分割時の `k` 以上の共有を用意できれば、`recovered_file` の内容は，元の `secret_file` と同一に復元できます。

## Python API での利用

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

または、より直接的に LSB の埋め込み・抽出を使うこともできます。

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

## 仕組みの要点

- `split` は秘密ファイルを 16 バイトごとに分割します
- 各ブロックを Shamir により `k` から `n` の共有へ変換
- 共有データを既存の FLAC の音声サンプルの LSB に埋め込む
- `combine` は各 FLAC から LSB を抽出し、Shamir で再構成し、最終的に元ファイルを復元する

## 制約と注意

- FLAC ディレクトリには `.flac` ファイルが少なくとも 1 個必要です
- FLAC の音声データの容量が足りない場合、埋め込み時に `ValueError` になります
- `k` は `n` 以下である必要があります
- 元の FLAC をそのまま再生用として利用する前提のため、埋め込みには音声データの変化が伴います
- これは「秘匿したいファイルを FLAC に隠す」用途を想定しており、通常のファイル暗号化と同等の用途ではありません

## 例: 実行フロー

```bash
mkdir -p ./base_flacs ./flac_shares
# 1. 共有用の FLAC を準備する
# 2. シークレットを分割
stegshare split -s ./important.txt -w ./base_flacs -o ./flac_shares -k 2 -n 4
# 3. 2 枚以上の FLAC を持って元ファイルを復元
stegshare combine -i ./flac_shares/flac_share_1.flac ./flac_shares/flac_share_2.flac -o ./restored.txt
```

## 参考

- Python パッケージ名: `stegshare`
- 実行コマンド: `stegshare`
- 依存ライブラリ: `numpy`, `soundfile`, `pycryptodome`

>>>>>>> origin/main
