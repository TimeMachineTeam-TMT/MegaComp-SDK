from pathlib import Path
import hashlib

input_file = Path("Sonic & Knuckles.smd")
output_file = Path("Sonic & Knuckles.bin")

data = input_file.read_bytes()

# SMD: 512-byte header + dados intercalados
if len(data) == 0x200 + 0x200000:
    data = data[0x200:]
else:
    raise ValueError(f"Tamanho inesperado: {len(data)} bytes")

# Desinterleave SMD
output = bytearray()

for block_start in range(0, len(data), 0x4000):
    block = data[block_start:block_start + 0x4000]

    # SMD armazena os bytes pares/ímpares separados.
    for i in range(0, len(block), 2):
        output.append(block[0x2000 + i // 2])
        output.append(block[i // 2])

output_file.write_bytes(output)

md5 = hashlib.md5(output).hexdigest()

print(f"Arquivo criado: {output_file}")
print(f"Tamanho: {len(output):,} bytes")
print(f"MD5: {md5}")
print()
print("MD5 esperado para sk.bin:")
print("4ea493ea4e9f6c9ebfccbdb15110367e")