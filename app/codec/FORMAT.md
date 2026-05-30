# vSQL video format v1 (backend)

Compatible with the reference prototype in `docs/vsql/lib/vsql.ts` for core frame layout.

## Constants

- `FRAME_WIDTH` = 1280
- `FRAME_HEIGHT` = 720
- `PIXELS_PER_FRAME` = 921_600
- `BYTES_PER_PIXEL` = 3 (payload uses R, G, B only)
- `FRAME_CAPACITY` = 2_764_800 bytes per frame (RGB stream before packing to RGBA)
- `HEADER_SIZE` = 44 bytes at the start of the byte stream
- `MAX_PAYLOAD_FRAME_0` = `FRAME_CAPACITY - HEADER_SIZE` (payload bytes in frame 0 after header)
- Optional **`LOGICAL_TOTAL_FRAMES`** = 108_000 for a 1-hour @ 30fps black shell (exported video length). Extra frames are all-black (RGB 0,0,0).

## Byte stream layout

The encoded stream is `zlib.compress(video_database_payload_bytes)` (raw zlib wrapper, default `zlib.compress` in Python / `pako.deflate` in JS).

Stream = `header (44)` + `compressed_payload`.

### Header (big-endian integers where noted)

| Offset | Size | Description                                                                                       |
| ------ | ---- | ------------------------------------------------------------------------------------------------- |
| 0      | 4    | Magic ASCII: `VSQC` (zlib-compressed DB) or `VSQL` (legacy uncompressed; decode uses raw payload) |
| 4      | 4    | **payload_frame_count**: number of frames that contain stream bytes (starting at frame 0)         |
| 8      | 4    | **compressed_length**: length in bytes of compressed_payload only (not including header)          |
| 12     | 32   | SHA-256 over **compressed_payload** only                                                          |

**Note:** Reference JS stores `totalFrames` and `dbLength`; we use the same semantics: `dbLength` = compressed_length, `totalFrames` = payload_frame_count.

## Packing bytes into frames

- For each frame, a linear buffer of `FRAME_CAPACITY` bytes is filled; then packed to `HxWx4` RGBA uint8: for pixel `p`, channel offsets `4*p+0..2` = three consecutive payload bytes, `4*p+3` = 255.
- Frame 0: first `HEADER_SIZE` bytes of the stream are header; remaining bytes in frame 0 fill up to `FRAME_CAPACITY`.
- Frame `k > 0`: next `FRAME_CAPACITY` bytes of the stream.

`payload_frame_count` = smallest `n` such that all stream bytes fit in frames `0..n-1`.

## Black padding (1-hour shell)

When `LOGICAL_TOTAL_FRAMES` > `payload_frame_count`, frames `payload_frame_count .. LOGICAL_TOTAL_FRAMES-1` are solid black: all RGB 0 and alpha 255.

## Checksum

On decode: reassemble `compressed_payload` from frames 0..`payload_frame_count-1`, verify SHA-256, then `zlib.decompress` to recover the video-database payload bytes.

## RGBA data mode (optional)

Not used in v1 default. Using 4 payload bytes per pixel would require a different magic and layout; default matches JS prototype (3 bytes + fixed alpha).
