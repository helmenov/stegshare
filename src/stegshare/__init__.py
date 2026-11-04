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
    """Decode a FLAC file and embed data into the LSB of the audio samples before re-encoding it."""
    audio_data, samplerate = sf.read(str(base_flac_path), dtype='int16')

    original_shape = audio_data.shape
    flat_audio = audio_data.flatten()

    bits = []
    for byte in data_bytes:
        for i in range(8):
            bits.append((byte >> i) & 1)

    if len(bits) > len(flat_audio):
        raise ValueError(
            f"The FLAC file '{base_flac_path.name}' does not have enough audio capacity.\n"
            f"At least {len(bits)} samples are required for the payload, but only {len(flat_audio)} are available.\n"
            f"Please use a longer FLAC file with more audio data."
        )

    for i in range(len(bits)):
        flat_audio[i] = (flat_audio[i] & ~1) | bits[i]

    reshaped_audio = flat_audio.reshape(original_shape)
    sf.write(str(output_flac_path), reshaped_audio, samplerate, format='FLAC', subtype='PCM_16')

def extract_data_from_flac(flac_path: Path, data_len: int) -> bytes:
    """Extract a byte sequence of the specified length from the LSB of the FLAC audio samples."""
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
    """Split a file entirely using Shamir secret sharing and embed it into n FLAC files."""
    secret_path = Path(secret_file)
    flac_dir_path = Path(base_flac_dir)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not flac_dir_path.is_dir():
        raise FileNotFoundError(f"The specified path is not a directory: {base_flac_dir}")

    flac_files = [p for p in flac_dir_path.iterdir() if p.suffix.lower() == '.flac']
    if not flac_files:
        raise FileNotFoundError(f"No FLAC files (.flac) were found in the specified directory: {base_flac_dir}")

    base_path = random.choice(flac_files)
    print(f"[*] Randomly selected the following base audio source:\n    {base_path.resolve()}")

    with open(secret_path, 'rb') as f:
        original_data = f.read()

    # Add a 4-byte header containing the original data length so it can be restored later.
    data_len = len(original_data)
    header = data_len.to_bytes(4, byteorder='big')
    raw_payload = header + original_data

    # Important: pad to a multiple of 16 bytes to avoid Shamir errors.
    chunk_size = 16
    payload = pad(raw_payload, chunk_size, style='pkcs7')

    music_buffers = [bytearray() for _ in range(n)]

    print(f"[*] Splitting the target file ({data_len} bytes) using Shamir secret sharing... (threshold k={k}, total n={n})")

    for offset in range(0, len(payload), chunk_size):
        chunk = payload[offset:offset+chunk_size]
        # This guarantees each chunk is exactly 16 bytes, preventing Shamir errors.
        shares = Shamir.split(k, n, chunk)

        for idx, (share_id, share_value) in enumerate(shares):
            if len(music_buffers[idx]) == 0:
                music_buffers[idx].append(share_id)
            music_buffers[idx].extend(share_value)

    print("[*] Embedding all shares directly into the LSB of each FLAC waveform...")
    for idx, buf in enumerate(music_buffers):
        output_flac = out_dir / f"flac_share_{idx + 1}.flac"
        embed_data_to_flac(base_path, bytes(buf), output_flac)
        print(f"  [+] Created: {output_flac}")
    print("[+] Secret sharing completed successfully.")

def combine_flac_into_file(chosen_flac_paths: list, recovered_file: str):
    """Extract embedded data from the specified FLAC files and reconstruct the original file."""
    print(f"[*] Analyzing {len(chosen_flac_paths)} FLAC files...")

    # 1. Read only the first chunk (16 bytes + 1 share ID byte = 17 bytes)
    # The padding ensures the first block includes the header and is always 16 bytes long.
    temp_extract_len = 1 + 16
    temp_shares = []

    for path in chosen_flac_paths:
        raw_payload = extract_data_from_flac(Path(path), temp_extract_len)
        share_id = raw_payload[0]
        share_value = raw_payload[1:]
        temp_shares.append((share_id, share_value))

    recovered_first_chunk = Shamir.combine(temp_shares)

    # Restore the original data length from the first 4 bytes.
    secret_data_len = int.from_bytes(recovered_first_chunk[:4], byteorder='big')

    # 2. Calculate the padded total block size.
    header_len = 4
    raw_payload_len = header_len + secret_data_len
    chunk_size = 16
    # Reverse-calculate the padded size.
    padded_payload_len = ((raw_payload_len + chunk_size - 1) // chunk_size) * chunk_size
    total_flac_data_len = 1 + padded_payload_len

    # 3. Extract the full payload.
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

    # Remove padding and discard the 4-byte header.
    try:
        unpadded_payload = unpad(fully_recovered_payload, chunk_size, style='pkcs7')
        original_data = unpadded_payload[4:]
    except ValueError as e:
        raise ValueError("Data recovery or padding removal failed. Shares may be missing or corrupted.") from e

    with open(recovered_file, 'wb') as rf:
        rf.write(original_data)
    print(f"[+] Recovery completed: {recovered_file}")

def main():
    parser = argparse.ArgumentParser(
        description="Tool that hides an entire file inside FLAC files using Shamir secret sharing (k-out-of-N) instead of encrypting it."
    )
    subparsers = parser.add_subparsers(dest="mode", required=True, help="Select the execution mode")

    # Split mode
    split_parser = subparsers.add_parser("split", help="Split a file into multiple FLAC files using secret sharing")
    split_parser.add_argument("-s", "--secret", required=True, help="Path to the file to hide")
    split_parser.add_argument("-w", "--flacdir", required=True, help="Path to the directory containing the FLAC files to use as carriers")
    split_parser.add_argument("-o", "--outdir", default="./flac_shares", help="Directory where generated FLAC files will be saved (default: ./flac_shares)")
    split_parser.add_argument("-k", type=int, required=True, help="Minimum number of FLAC files required to recover the original data (threshold)")
    split_parser.add_argument("-n", type=int, required=True, help="Total number of FLAC files to generate")

    # Combine mode
    combine_parser = subparsers.add_parser("combine", help="Recover the original file from multiple FLAC files")
    combine_parser.add_argument("-i", "--inputs", nargs="+", required=True, help="Paths to the FLAC files (.flac) to use for recovery")
    combine_parser.add_argument("-o", "--output", required=True, help="Output path for the recovered file")

    args = parser.parse_args()

    try:
        if args.mode == "split":
            if args.k > args.n:
                print("[-] Error: threshold (k) must be less than or equal to the total number of files (n).", file=sys.stderr)
                sys.exit(1)
            split_file_completely_into_flac(args.secret, args.flacdir, args.outdir, args.k, args.n)

        elif args.mode == "combine":
            combine_flac_into_file(args.inputs, args.output)

    except Exception as e:
        print(f"[-] Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
