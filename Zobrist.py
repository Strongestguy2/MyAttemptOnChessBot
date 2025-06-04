import random

random.seed(0)

ZOBRIST_PIECES = {
    (piece, row, col): random.getrandbits(64)
    for piece in "PNBRQKpnbrqk"
    for row in range(8)
    for col in range(8)
}

ZOBRIST_CASTLING = {
    "K": random.getrandbits(64),
    "Q": random.getrandbits(64),
    "k": random.getrandbits(64),
    "q": random.getrandbits(64),
}

ZOBRIST_EN_PASSANT = [random.getrandbits(64) for _ in range(8)]

ZOBRIST_TURN = random.getrandbits(64)

def hash_board (board) -> int:
    h = 0

    for row in range(8):
        for col in range(8):
            piece = board.board[row][col]
            if piece != '.':
                h ^= ZOBRIST_PIECES.get ((piece, row, col), 0)

    for right in board.castling_rights:
        h ^= ZOBRIST_CASTLING.get (right, 0)

    if board.en_passant_square:
        file = board.en_passant_square [1]
        if 0 <= file < 8:
            h ^= ZOBRIST_EN_PASSANT[file]

    if board.white_to_move:
        h ^= ZOBRIST_TURN

    return h
