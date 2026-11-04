import os
import sys
import argparse
import random
from pathlib import Path
import soundfile as sf
import numpy as np
from Crypto.Protocol.SecretSharing import Shamir
from Crypto.Util.Padding import pad, unpad

def embed_data_to_flac(base_flac_path: Path, data_bytes: bytes, output_flac_path: Path):
    """FLACファイルをデコードし、音声サンプルのLSBにデータを埋め込んで再エンコードする"""
    audio_data, samplerate = sf.read(str(base_flac_path), dtype='int16')

    original_shape = audio_data.shape
    flat_audio = audio_data.flatten()

    bits = []
    for byte in data_bytes:
        for i in range(8):
            bits.append((byte >> i) & 1)

    if len(bits) > len(flat_audio):
        raise ValueError(
            f"FLACファイル '{base_flac_path.name}' の音声容量が足りません。\n"
            f"データサイズに対して最低 {len(bits)} サンプル必要ですが、{len(flat_audio)} サンプルしかありません。\n"
            f"もっと演奏時間の長い（サイズの大きい）FLACファイルを用意してください。"
        )

    for i in range(len(bits)):
        flat_audio[i] = (flat_audio[i] & ~1) | bits[i]

    reshaped_audio = flat_audio.reshape(original_shape)
    sf.write(str(output_flac_path), reshaped_audio, samplerate, format='FLAC', subtype='PCM_16')

def extract_data_from_flac(flac_path: Path, data_len: int) -> bytes:
    """FLACファイルの音声サンプルのLSBから指定された長さのデータを抽出する"""
    audio_data, _ = sf.read(str(flac_path), dtype='int16')
    flat_audio = audio_data.flatten()

    bits_count = data_len * 8
    bits = [int(flat_audio[i] & 1) for i in range(bits_count)]

    extracted_bytes = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for bit_idx in range(8):
            byte |= (bits[i + bit_idx] << bit_idx)
        extracted_bytes.append(byte)

    return bytes(extracted_bytes)

def split_file_completely_into_flac(secret_file: str, base_flac_dir: str, output_dir: str, k: int, n: int):
    """ファイルを丸ごとシャミア法で分割し、完全にN個のFLACファイルの中に格納する"""
    secret_path = Path(secret_file)
    flac_dir_path = Path(base_flac_dir)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not flac_dir_path.is_dir():
        raise FileNotFoundError(f"指定されたパスはディレクトリではありません: {base_flac_dir}")

    flac_files = [p for p in flac_dir_path.iterdir() if p.suffix.lower() == '.flac']
    if not flac_files:
        raise FileNotFoundError(f"指定されたフォルダ内にFLACファイル(.flac)が見つかりません: {base_flac_dir}")

    base_path = random.choice(flac_files)
    print(f"[*] ベース音源として以下をランダムに選択しました:\n    {base_path.resolve()}")

    with open(secret_path, 'rb') as f:
        original_data = f.read()

    # 復元用に元のデータサイズ（4バイト）をヘッダーとして付与
    data_len = len(original_data)
    header = data_len.to_bytes(4, byteorder='big')
    raw_payload = header + original_data

    # 【重要】シャミアのエラーを防ぐため、16バイトの倍数になるようパディングを施す
    chunk_size = 16
    payload = pad(raw_payload, chunk_size, style='pkcs7')

    music_buffers = [bytearray() for _ in range(n)]

    print(f"[*] 対象ファイル ({data_len} バイト) を秘密分散中... (しきい値 k={k}, 総数 n={n})")

    for offset in range(0, len(payload), chunk_size):
        chunk = payload[offset:offset+chunk_size]
        # これですべてのチャンクが確実に16バイトになり、エラーが解消されます
        shares = Shamir.split(k, n, chunk)

        for idx, (share_id, share_value) in enumerate(shares):
            if len(music_buffers[idx]) == 0:
                music_buffers[idx].append(share_id)
            music_buffers[idx].extend(share_value)

    print("[*] 各FLACの音声波形（LSB領域）へ完全インライン埋め込み中...")
    for idx, buf in enumerate(music_buffers):
        output_flac = out_dir / f"flac_share_{idx + 1}.flac"
        embed_data_to_flac(base_path, bytes(buf), output_flac)
        print(f"  [+] 生成完了: {output_flac}")
    print("[+] すべての秘密分散処理が正常に完了しました。")

def combine_flac_into_file(chosen_flac_paths: list, recovered_file: str):
    """指定されたFLACファイルから内部データを抽出し、元のファイルを復元する"""
    print(f"[*] {len(chosen_flac_paths)} 個のFLACファイルを解析中...")

    # 1. まず先頭の1チャンク分（16バイト＋シェアID1バイト＝17バイト）を取り出す
    # パディングによってヘッダー部分を含む最初のブロックは確実に16バイト存在します
    temp_extract_len = 1 + 16
    temp_shares = []

    for path in chosen_flac_paths:
        raw_payload = extract_data_from_flac(Path(path), temp_extract_len)
        share_id = raw_payload[0]
        share_value = raw_payload[1:]
        temp_shares.append((share_id, share_value))

    recovered_first_chunk = Shamir.combine(temp_shares)

    # 先頭4バイトから元のデータサイズを復元
    secret_data_len = int.from_bytes(recovered_first_chunk[:4], byteorder='big')

    # 2. パディングされた全体のブロックサイズを計算
    header_len = 4
    raw_payload_len = header_len + secret_data_len
    chunk_size = 16
    # パディング後のサイズを逆算
    padded_payload_len = ((raw_payload_len + chunk_size - 1) // chunk_size) * chunk_size
    total_flac_data_len = 1 + padded_payload_len

    # 3. 本番のデータ全抽出
    final_shares_buffers = [None for _ in range(len(chosen_flac_paths))]
    share_ids = []

    for idx, path in enumerate(chosen_flac_paths):
        full_payload = extract_data_from_flac(Path(path), total_flac_data_len)
        share_ids.append(full_payload[0])
        final_shares_buffers[idx] = full_payload[1:]

    fully_recovered_payload = bytearray()

    for offset in range(0, padded_payload_len, chunk_size):
        current_chunk_shares = []
        for idx in range(len(chosen_flac_paths)):
            val_fragment = final_shares_buffers[idx][offset:offset+chunk_size]
            current_chunk_shares.append((share_ids[idx], val_fragment))

        recovered_chunk = Shamir.combine(current_chunk_shares)
        fully_recovered_payload.extend(recovered_chunk)

    # パディングを解除してヘッダー（4バイト）を削る
    try:
        unpadded_payload = unpad(fully_recovered_payload, chunk_size, style='pkcs7')
        original_data = unpadded_payload[4:]
    except ValueError as e:
        raise ValueError("データの復元、またはパディングの解除に失敗しました。シェアが不足しているか破損しています。") from e

    with open(recovered_file, 'wb') as rf:
        rf.write(original_data)
    print(f"[+] 復元が完了しました: {recovered_file}")

def main():
    parser = argparse.ArgumentParser(
        description="ファイルを暗号化する代わりにFLACファイルへ丸ごと秘密分散(k-out-of-N)するツール"
    )
    subparsers = parser.add_subparsers(dest="mode", required=True, help="実行モードを選択")

    # 分割（split）モード
    split_parser = subparsers.add_parser("split", help="ファイルを複数のFLACファイルに秘密分散します")
    split_parser.add_argument("-s", "--secret", required=True, help="隠蔽したい機密ファイルのパス")
    split_parser.add_argument("-w", "--flacdir", required=True, help="土台となるFLACファイル群が格納されたフォルダのパス")
    split_parser.add_argument("-o", "--outdir", default="./flac_shares", help="生成されたFLACファイルを保存するディレクトリ (デフォルト: ./flac_shares)")
    split_parser.add_argument("-k", type=int, required=True, help="復元に必要な最小限のFLACファイル数（しきい値）")
    split_parser.add_argument("-n", type=int, required=True, help="生成する総FLACファイル数")

    # 復元（combine）モード
    combine_parser = subparsers.add_parser("combine", help="複数のFLACファイルから元のファイルを復元します")
    combine_parser.add_argument("-i", "--inputs", nargs="+", required=True, help="復元に使用するFLACファイル(.flac)のパス（複数指定可）")
    combine_parser.add_argument("-o", "--output", required=True, help="復元されたファイルの出力パス")

    args = parser.parse_args()

    try:
        if args.mode == "split":
            if args.k > args.n:
                print("[-] エラー: しきい値 (k) は総ファイル数 (n) 以下である必要があります。", file=sys.stderr)
                sys.exit(1)
            split_file_completely_into_flac(args.secret, args.flacdir, args.outdir, args.k, args.n)

        elif args.mode == "combine":
            combine_flac_into_file(args.inputs, args.output)

    except Exception as e:
        print(f"[-] エラーが発生しました: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
