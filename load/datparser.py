from typing import Dict, List
from load.lz10util import decompress_lz10
from load.narcutil import parse_narc
LAYER_NAMES = {1: '0X01 LAYER', 2: '0X02 LAYER', 3: '0X03 LAYER', 4: '0X04 LAYER', 5: '0X05 LAYER', 6: '0X06 LAYER', 7: '0X07 LAYER', 8: '0X08 LAYER', 9: '0X09 LAYER', 10: '0X0A LAYER', 13: '0X0D LAYER', 14: '0X0E LAYER'}

def parse_dat_map(dat_path: str) -> Dict:
    with open(dat_path, 'rb') as f:
        raw = f.read()
    dec = decompress_lz10(raw)
    outer_files = parse_narc(dec)
    mpif = None
    txif = None
    lyr = None
    cta = None
    for bf in outer_files:
        sig = bf[:4]
        if sig == b'MPIF':
            mpif = bf
        elif sig == b'TXIF':
            txif = bf
        elif sig == b'LYR\x00':
            lyr = bf
        elif sig == b'CTA\x00':
            cta = bf
    layers = []
    if lyr:
        if lyr[:4] == b'LYR\x00':
            lyr = lyr[4:]
        lyr_stage1 = parse_narc(lyr)
        final_candidates = []
        for blob in lyr_stage1:
            if blob[:4] == b'NARC':
                inner = parse_narc(blob)
                final_candidates.extend(inner)
            else:
                final_candidates.append(blob)
        for lb in final_candidates:
            if len(lb) >= 4:
                ltype = int.from_bytes(lb[0:4], 'little')
            else:
                ltype = -1
            name = LAYER_NAMES.get(ltype, f'UNKNOWN_{ltype:02X}')
            layers.append({'type': ltype, 'name': name, 'data': lb})
    return {'mpif': mpif, 'txif': txif, 'layers': layers, 'cta': cta}
