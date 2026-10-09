import struct

ROM_SIZE = 32 * 1024
rom = bytearray(ROM_SIZE)

rom[0x000:0x004] = struct.pack(">I", 0x00FFFE00)  # SP
rom[0x004:0x008] = struct.pack(">I", 0x00000200)  # Entry

# --- Header SEGA bem formado ---
h = bytearray(256)
h[0x00:0x10] = b"SEGA GENESIS    "
h[0x10:0x20] = b"(C)TMT 2026.JAN "
h[0x20:0x50] = b"RED BACKDROP ROM".ljust(48, b" ")
h[0x50:0x80] = b"RED BACKDROP ROM".ljust(48, b" ")
h[0x80:0x8E] = b"GM 00000000-00"
h[0x8E:0x90] = b"\x00\x00"                       # checksum (preenchido depois)
h[0x90:0xA0] = b"J               "               # I/O support
h[0xA0:0xA4] = struct.pack(">I", 0x00000000)     # ROM start
h[0xA4:0xA8] = struct.pack(">I", ROM_SIZE - 1)   # ROM end
h[0xA8:0xAC] = struct.pack(">I", 0x00FF0000)     # RAM start
h[0xAC:0xB0] = struct.pack(">I", 0x00FFFFFF)     # RAM end
h[0xF0:0xF3] = b"JUE"                            # região
rom[0x100:0x200] = h


def movea_l_imm_an(val, an):
    return struct.pack(">H", 0x207C | (an << 9)) + struct.pack(">I", val)

def move_w_imm_anind(imm, an):
    return struct.pack(">H", 0x30BC | (an << 9)) + struct.pack(">H", imm & 0xFFFF)


code = b""
code += movea_l_imm_an(0xC00004, 0)   # A0 = VDP ctrl
code += movea_l_imm_an(0xC00000, 1)   # A1 = VDP data

# Registradores VDP
code += move_w_imm_anind(0x8004, 0)   # reg 0  = 0x04
code += move_w_imm_anind(0x8104, 0)   # reg 1  = 0x04  (display OFF, H32)
code += move_w_imm_anind(0x8230, 0)   # reg 2  = 0x30  (Plane A @ 0xC000)
code += move_w_imm_anind(0x8700, 0)   # reg 7  = 0x00  (backdrop = CRAM[0])
code += move_w_imm_anind(0x8C00, 0)   # reg 12 = 0x00  (H32)
code += move_w_imm_anind(0x8F02, 0)   # reg 15 = 0x02  (auto-increment)

# CRAM[0] = vermelho puro (bits: 0000 BBB0 GGG0 RRR0)
# 0x000E = B=0, G=0, R=7 (puro vermelho em 3 bits)
code += move_w_imm_anind(0xC000, 0)   # first half: CD=11, addr = 0x0000
code += move_w_imm_anind(0x0000, 0)   # second half
code += move_w_imm_anind(0x000E, 1)   # data

# Liga display
code += move_w_imm_anind(0x8144, 0)   # reg 1 = 0x44 (display ON)

# Loop
code += b"\x60\xFE"

rom[0x200:0x200 + len(code)] = code

# Checksum
total = 0
for i in range(0x200, len(rom), 2):
    w = (rom[i] << 8) | rom[i+1]
    total = (total + w) & 0xFFFF
rom[0x18E] = (total >> 8) & 0xFF
rom[0x18F] = total & 0xFF

with open("red_test.md", "wb") as f:
    f.write(rom)

print(f"OK: {len(rom)} bytes, code = {len(code)} bytes")