# tools/make_test_rom.py
from pathlib import Path
import struct


def _dw(buf, addr, v):
    buf[addr:addr + 2] = struct.pack(">H", v & 0xFFFF)


def _dl(buf, addr, v):
    buf[addr:addr + 4] = struct.pack(">I", v & 0xFFFFFFFF)


def make_rom(path):
    buf = bytearray(0x400)

    # Vetores
    _dl(buf, 0x000, 0x00FFFE00)   # SP inicial
    _dl(buf, 0x004, 0x00000200)   # PC inicial
    for i in range(0x008, 0x100, 4):
        _dl(buf, i, 0x00000300)   # handler dummy

    # Header (0x100-0x1FF)
    header = (
        b"SEGA GENESIS    "
        b"(C)TMT 2026.JAN "
        b"TEST ROM                                        "
        b"TEST ROM                                        "
        b"GM 00000000-00  "
    )
    buf[0x100:0x1A0] = header.ljust(0xA0, b" ")

    # Programa
    _dw(buf, 0x200, 0x702A)   # MOVEQ #42, D0
    _dw(buf, 0x202, 0x7208)   # MOVEQ #8, D1
    _dw(buf, 0x204, 0xD081)   # ADD.L D1, D0
    _dw(buf, 0x206, 0x4E75)   # RTS

    # Handler dummy
    _dw(buf, 0x300, 0x4E73)   # RTE

    path = Path(path)
    path.write_bytes(buf)
    print(f"ROM de teste: {path} ({len(buf)} bytes)")
    return path


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "test.bin"
    make_rom(target)