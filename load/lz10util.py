def decompress_lz10(data: bytes) -> bytes:
    if not data or data[0] != 16:
        return data
    dst_size = data[1] | data[2] << 8 | data[3] << 16
    src_i = 4
    out = bytearray()
    while len(out) < dst_size and src_i < len(data):
        flags = data[src_i]
        src_i += 1
        for bit in range(8):
            if len(out) >= dst_size or src_i >= len(data):
                break
            if flags & 128 >> bit == 0:
                out.append(data[src_i])
                src_i += 1
            else:
                if src_i + 1 >= len(data):
                    break
                b1 = data[src_i]
                b2 = data[src_i + 1]
                src_i += 2
                disp = (b1 & 15) << 8 | b2
                length = (b1 >> 4) + 3
                copy_pos = len(out) - (disp + 1)
                for _ in range(length):
                    if copy_pos < 0 or copy_pos >= len(out):
                        break
                    out.append(out[copy_pos])
                    copy_pos += 1
    return bytes(out[:dst_size])

def compress_lz10(data: bytes) -> bytes:
    n = len(data)
    output = bytearray()
    output.append(16)
    output.append(n & 255)
    output.append(n >> 8 & 255)
    output.append(n >> 16 & 255)
    if n == 0:
        return bytes(output)
    HASH_SIZE = 1 << 15
    head = [-1] * HASH_SIZE
    lru = [-1] * HASH_SIZE

    def hash3(pos: int) -> int:
        if pos + 2 >= n:
            return 0
        return (data[pos] << 16 | data[pos + 1] << 8 | data[pos + 2]) & HASH_SIZE - 1

    def find_best_match(pos: int) -> tuple:
        if pos + 2 >= n:
            return (0, 0)
        best_len = 0
        best_dist = 0
        h = hash3(pos)
        j = head[h]
        checked = 0
        max_checks = 64
        while j >= 0 and checked < max_checks:
            if pos - j > 4096:
                break
            if j >= pos:
                break
            match_len = 0
            limit = min(18, n - pos)
            while match_len < limit and data[j + match_len] == data[pos + match_len]:
                match_len += 1
            if match_len >= 3 and match_len > best_len:
                best_len = match_len
                best_dist = pos - j - 1
                if best_len == 18:
                    break
            j = lru[j & HASH_SIZE - 1]
            checked += 1
        return (best_len, best_dist)
    for i in range(min(4096, n - 2)):
        h = hash3(i)
        lru[i & HASH_SIZE - 1] = head[h]
        head[h] = i
    pos = 0
    while pos < n:
        block_header_pos = len(output)
        output.append(0)
        flags = 0
        for bit in range(8):
            if pos >= n:
                break
            look_ahead = pos + 4096
            if look_ahead < n - 2:
                h = hash3(look_ahead)
                lru[look_ahead & HASH_SIZE - 1] = head[h]
                head[h] = look_ahead
            best_match_len, best_match_dist = find_best_match(pos)
            if best_match_len >= 3:
                flags |= 1 << 7 - bit
                length_part = best_match_len - 3 & 15
                dist_high = best_match_dist >> 8 & 15
                dist_low = best_match_dist & 255
                output.append(length_part << 4 | dist_high)
                output.append(dist_low)
                for skip in range(1, best_match_len):
                    if pos + skip < n - 2:
                        h = hash3(pos + skip)
                        idx = pos + skip & HASH_SIZE - 1
                        lru[idx] = head[h]
                        head[h] = pos + skip
                pos += best_match_len
            else:
                output.append(data[pos])
                if pos < n - 2:
                    h = hash3(pos)
                    idx = pos & HASH_SIZE - 1
                    lru[idx] = head[h]
                    head[h] = pos
                pos += 1
        output[block_header_pos] = flags
    return bytes(output)
