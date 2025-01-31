import numpy as np

def Board_To_Bitboard(pieces):
    bitboards = {
        'P': np.uint64(0), 'N': np.uint64(0), 'B': np.uint64(0), 'R': np.uint64(0), 'Q': np.uint64(0), 'K': np.uint64(0),
        'p': np.uint64(0), 'n': np.uint64(0), 'b': np.uint64(0), 'r': np.uint64(0), 'q': np.uint64(0), 'k': np.uint64(0),
        'all': np.uint64(0)
    }

    for piece, (col, row) in pieces.items():
        piece_type = piece[1].lower() if piece[0] == 'b' else piece[1].upper()
        bit_position = np.uint64(1) << (row * 8 + col)
        bitboards[piece_type] |= bit_position
        bitboards['all'] |= bit_position
        print(f"Piece {piece} at ({col}, {row}) -> bit_position: {bit_position}")

    return bitboards

def Print_Bitboard(bitboard):
    for rank in range(8):
        line = ""
        for file in range(8):
            if bitboard & (np.uint64(1) << (rank * 8 + file)):
                line += "1"
            else:
                line += "0"
        print(line)
    print()

def Print_All_Bitboards(bitboards):
    for piece, bitboard in bitboards.items():
        print(f"{piece}:")
        Print_Bitboard(bitboard)

MAGIC_BISHOP_MASKS = [0] * 64
MAGIC_ROOK_MASKS = [0] * 64

def generate_pawn_moves(pawns, color, occupancy):
    moves = np.uint64(0)
    if color == "w":
        # Single step forward
        single_step = (pawns >> 8) & ~occupancy
        print(f"Single step bitboard for white: {single_step}")

        # Double step forward from rank 6 -> rank 4
        # Use mask 0x00FF000000000000 for bits 48..55
        double_step_candidates = (pawns & np.uint64(0x00FF000000000000)) >> 8
        print(f"Double step candidates bitboard for white: {double_step_candidates}")
        double_step = (double_step_candidates & ~occupancy) >> 8 & ~occupancy
        print(f"Double step bitboard for white: {double_step}")

        moves |= single_step | double_step
    else:
        # Single step forward
        single_step = (pawns << 8) & ~occupancy
        print(f"Single step bitboard for black: {single_step}")

        # Double step forward from rank 1 -> rank 3
        # Use mask 0x000000000000FF00 for bits 8..15
        double_step_candidates = (pawns & np.uint64(0x000000000000FF00)) << 8
        print(f"Double step candidates bitboard for black: {double_step_candidates}")
        double_step = (double_step_candidates & ~occupancy) << 8 & ~occupancy
        print(f"Double step bitboard for black: {double_step}")

        moves |= single_step | double_step

    print(f"Generated pawn moves for color {color}: {moves}")
    return moves


def generate_pawn_attacks(pawns, color, en_passant_target=np.uint64(0)):
    attacks = np.uint64(0)
    if color == 'w':
        attacks |= (pawns << 7) & ~np.uint64(0x0101010101010101)  # Capture left
        attacks |= (pawns << 9) & ~np.uint64(0x8080808080808080)  # Capture right
    else:
        attacks |= (pawns >> 7) & ~np.uint64(0x8080808080808080)  # Capture left
        attacks |= (pawns >> 9) & ~np.uint64(0x0101010101010101)  # Capture right
    attacks |= en_passant_target
    return attacks

def generate_knight_moves(knights, occupancy):
    moves = np.uint64(0)
    knight_moves = [
        17, 15, 10, 6, -17, -15, -10, -6
    ]
    for knight in range(64):
        if (knights >> knight) & np.uint64(1):
            for move in knight_moves:
                target = knight + move
                if 0 <= target < 64:
                    # Ensure the move stays within the same row or column constraints
                    if abs((target % 8) - (knight % 8)) <= 2 and abs((target // 8) - (knight // 8)) <= 2:
                        if not (occupancy >> target) & np.uint64(1):
                            moves |= np.uint64(1) << target
    return moves

def generate_bishop_moves(bishops, occupancy):
    moves = np.uint64(0)
    for bishop in range(64):
        if (bishops >> bishop) & np.uint64(1):
            moves |= MAGIC_BISHOP_MASKS[bishop] & occupancy
    return moves

def generate_rook_moves(rooks, occupancy):
    moves = np.uint64(0)
    for rook in range(64):
        if (rooks >> rook) & np.uint64(1):
            moves |= MAGIC_ROOK_MASKS[rook] & occupancy
    return moves

def generate_queen_moves(queens, occupancy):
    return generate_bishop_moves(queens, occupancy) | generate_rook_moves(queens, occupancy)

def generate_king_moves(kings, occupancy):
    moves = np.uint64(0)
    king_moves = [
        1, -1, 8, -8, 9, -9, 7, -7
    ]
    for king in range(64):
        if (kings >> king) & np.uint64(1):
            for move in king_moves:
                target = king + move
                if 0 <= target < 64 and not (occupancy >> target) & np.uint64(1):
                    moves |= np.uint64(1) << target
    return moves
