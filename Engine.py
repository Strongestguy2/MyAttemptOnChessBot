from Board import Board, Move
from tables import PAWN_TABLE, KNIGHT_TABLE, BISHOP_TABLE, ROOK_TABLE, QUEEN_TABLE, KING_MID_TABLE, KING_END_TABLE

TRANSPOSITIONAL_TABLE = {}
TRANSPOSITION_HITS = 0

def Evaluate_Position (board: Board) -> float:
    "point: 10 for pawn, 30 for knight, 30 for bishop, 50 for rook, 90 for queen, 900 for king, white + black -"

    piece_values = {
        'P': 10, 'N': 30, 'B': 30, 'R': 50, 'Q': 90, 'K': 900,
        'p': -10, 'n': -30, 'b': -30, 'r': -50, 'q': -90, 'k': -900
    }

    score = 0
    endgame = Is_Endgame(board)

    tempo_bonus = 10 if board.white_to_move else -10
    score += tempo_bonus

    white_pawn_files = [[] for _ in range(8)]
    black_pawn_files = [[] for _ in range(8)]

    for row in range (8):
        for col in range (8):
            piece = board.board[row][col]
            if piece == "P":
                white_pawn_files[col].append(row)
            elif piece == "p":
                black_pawn_files[col].append(row)
            
    for row in range (8):
        for col in range (8):
            piece = board.board[row][col]
            if piece == ".":
                continue

            value = piece_values.get(piece, 0)
            score += piece_values[piece]

            if piece == "P":
                score += PAWN_TABLE[row][col]
            elif piece == "p":
                score -= PAWN_TABLE[7 - row][col]
            elif piece == "N":
                score += KNIGHT_TABLE[row][col]
            elif piece == "n":
                score -= KNIGHT_TABLE[7 - row][col]
            elif piece == "B":
                score += BISHOP_TABLE[row][col]
            elif piece == "b":
                score -= BISHOP_TABLE[7 - row][col]
            elif piece == "R":
                score += ROOK_TABLE[row][col]
            elif piece == "r":
                score -= ROOK_TABLE[7 - row][col]
            elif piece == "Q":
                score += QUEEN_TABLE[row][col]
            elif piece == "q":
                score -= QUEEN_TABLE[7 - row][col]
            elif piece == "K":
                table = KING_END_TABLE if endgame else KING_MID_TABLE
                score += table[row][col]
            elif piece == "k":
                table = KING_END_TABLE if endgame else KING_MID_TABLE
                score -= table[7 - row][col]

            center_squares = {(3, 3), (3, 4), (4, 3), (4, 4)}

            if (row, col) in center_squares:
                if piece.isupper():
                    score += 0.5
                else:
                    score -= 0.5

            if piece in ("N", "B") and row < 7:
                score += 0.5
            elif piece in ("n", "b") and row > 0:
                score -= 0.5

            score += Evaluate_King_Safety(board)
            score += Evaluate_Space(board)

            if piece == "P":
                is_passed = all(
                    all(enemy_row < row for enemy_row in black_pawn_files[c])
                    for c in range(max(0, col - 1), min(8, col + 2))
                )

                if is_passed:
                    score += 0.5

                if len (white_pawn_files[col]) > 1:
                    score -= 0.25
            elif piece == "p":
                is_passed = all(
                    all(enemy_row > row for enemy_row in white_pawn_files[c])
                    for c in range(max(0, col - 1), min(8, col + 2))
                )

                if is_passed:
                    score -= 0.5

                if len(black_pawn_files[col]) > 1:
                    score += 0.25

            
    developed_white = sum (1 for row in board.board for p in row if p in "NBRQ")
    developed_black = sum (1 for row in board.board for p in row if p in "nbrq")
    score += 0.1 * (developed_white - developed_black)

    return score

def Evaluate_King_Safety (board):
    score = 0
    kr, kc = board.Find_King(True)
    if kr == 7:
        for dc in [-1, 0, 1]:
            c = kc + dc
            if 0 <= c < 8 and board.board[6][c] != "P":
                score -= 15
    kr, kc = board.Find_King(False)
    if kr == 0:
        for dc in [-1, 0, 1]:
            c = kc + dc
            if 0 <= c < 8 and board.board[1][c] != "p":
                score += 15
    return score

def Evaluate_Space (board):
    whtie_space = 0
    black_space = 0
    for r in range (8):
        for c in range (8):
            piece = board.board[r][c]
            if piece == "." or piece.upper() == "P":
                continue
            if piece.isupper() and r < 4:
                whtie_space += 1
            elif piece.islower() and r > 3:
                black_space += 1
    return (whtie_space - black_space) * 5

def Minimax (board: Board, depth: int, alpha: float, beta: float, maximizing: bool) -> float:
    global TRANSPOSITION_TABLE, TRANSPOSITION_HITS

    if depth == 0:
        return Quiescence_Search (board, alpha, beta, maximizing)
    
    key = Hash_Board(board)
    if key in TRANSPOSITIONAL_TABLE:
        TRANSPOSITION_HITS += 1
    
    legal_moves = board.Generate_Legal_Moves()
    legal_moves.sort(key = lambda m: Score_Move (board, m), reverse=maximizing)

    if not legal_moves:
        if board.Is_King_In_Check():
            return -10000 if maximizing else 10000 - depth
        else:
            score = 0
        TRANSPOSITIONAL_TABLE[key] = score
        return score
    
    if maximizing:
        max_eval = float('-inf')
        for move in legal_moves:
            board.Make_Move(move)
            score = Minimax(board, depth - 1, alpha, beta, False)
            board.Undo_Move()
            max_eval = max(max_eval, score)
            alpha = max(alpha, score)
            if beta <= alpha:
                break
        TRANSPOSITIONAL_TABLE[key] = max_eval
        return max_eval
    else:
        min_eval = float('inf')
        for move in legal_moves:
            board.Make_Move(move)
            score = Minimax(board, depth - 1, alpha, beta, True)
            board.Undo_Move()
            min_eval = min(min_eval, score)
            beta = min(beta, score)
            if beta <= alpha:
                break
        TRANSPOSITIONAL_TABLE[key] = min_eval
        return min_eval
    
def Quiescence_Search (board: Board, alpha: float, beta: float, maximizing: bool) -> float:
    stand_pat = Evaluate_Position(board)
    
    if maximizing:
        if stand_pat >= beta:
            return beta
        alpha = max(alpha, stand_pat)
    else:
        if stand_pat <= alpha:
            return alpha
        beta = min(beta, stand_pat)

    capture_moves = [m for m in board.Generate_Legal_Moves() if m.piece_captured]
    capture_moves.sort(key = lambda m: Score_Move (board, m), reverse=maximizing)

    for move in capture_moves:
        board.Make_Move(move)
        score = Quiescence_Search(board, alpha, beta, not maximizing)
        board.Undo_Move()

        if maximizing:
            alpha = max(alpha, score)
            if alpha >= beta:
                break
        else:
            beta = min(beta, score)
            if beta <= alpha:
                break
    
    return alpha if maximizing else beta

def Get_Attackers (board: Board, target_row: int, target_col: int, white: bool):
    "return list of position(row, col piece) that are attacking"

    attackers = []
    for r in range (8):
        for c in range (8):
            piece = board.board[r][c]
            if piece == "." or (piece.isupper() != white):
                continue
            
            if piece.upper() == "P":
                direction = -1 if piece.isupper() else 1
                for dx in [-1, 1]:
                    nr, nc = r + direction, c + dx
                    if 0 <= nr < 8 and 0 <= nc < 8:
                        if (nr, nc) == (target_row, target_col):
                            attackers.append((r, c, piece))
            else:
                pseudo_moves = []
                board._Generate_Piece_Moves (piece, r, c, pseudo_moves, include_castling=False)
                for m in pseudo_moves:
                    if m.end == (target_row, target_col):
                        attackers.append((r, c, piece))

    print(f"Attackers on {(target_row, target_col)}: {attackers}")
    if (target_row, target_col) == (3, 1):
        print("Check point - board position at (4, 2):", board.board[4][2])
    return attackers

def Static_Exchange_Evaluation (board: Board, move: Move) -> int:
    temp_board = Board()
    temp_board.board = [row.copy() for row in board.board]
    temp_board.white_to_move = board.white_to_move

    value_map = {
        'P': 100, 'N': 300, 'B': 300, 'R': 500, 'Q': 900, 'K': 10000,
        'p': 100, 'n': 300, 'b': 300, 'r': 500, 'q': 900, 'k': 10000
    }

    def see_recursive (square, attackers_w, attackers_b, side, gain_stack):
        attackers = attackers_w if side else attackers_b
        if not attackers:
            return gain_stack[-1] if gain_stack else 0
        
        attacker = min (attackers, key=lambda x: value_map.get(x[2], 10000))
        attackers.remove(attacker)

        capturing_piece_value = value_map.get(temp_board.board[square[0]][square[1]], 0)
        gain = value_map.get(attacker[2], 0) - capturing_piece_value
        gain_stack.append(gain_stack[-1] - gain if gain_stack else -gain)

        temp_board.board[attacker[0]][attacker[1]] = "."
        temp_board.board[square[0]][square[1]] = attacker[2]

        new_attackers = Get_Attackers(temp_board, *square, white = side)
        return max (-see_recursive(square, attackers_b, new_attackers, not side, gain_stack), gain_stack[-1])
    
    if not move.piece_captured:
        return 0
    
    target_square = move.end
    attackers_white = Get_Attackers(temp_board, *target_square, white = True)
    attackers_black = Get_Attackers(temp_board, *target_square, white = False)

    return see_recursive(target_square, attackers_white, attackers_black, board.white_to_move, [])

def Score_Move (board: Board, move: Move) -> int:
    "mvv-lva most valuable victim - least valuable attacker"
    piece_values = {
        'P':100, 'N':300, 'B':300, 'R':500, 'Q':900, 'K':10000,
        'p':100, 'n':300, 'b':300, 'r':500, 'q':900, 'k':10000
    }

    victim = move.piece_captured
    attacker = move.piece_moved

    if victim == '.':
        return 0
    
    victim_value = piece_values.get(victim, 0)
    attacker_value = piece_values.get(attacker, 1)

    see_bonus = Static_Exchange_Evaluation (board, move)
    return (10 * victim_value) - attacker_value + see_bonus

def Find_Best_Move (board: Board, depth: int) -> Move:
    global TRANSPOSITION_HITS
    TRANSPOSITION_HITS = 0
    best_eval = float('-inf') if board.white_to_move else float('inf')
    best_move = None

    for move in board.Generate_Legal_Moves():
        board.Make_Move(move)
        
        score = Minimax(board, depth - 1, float('-inf'), float('inf'), not board.white_to_move)
        board.Undo_Move()

        if board.white_to_move and score > best_eval:
            best_eval = score
            best_move = move
        elif not board.white_to_move and score < best_eval:
            best_eval = score
            best_move = move

    return best_move

def Hash_Board (board: Board) -> str:
    rows = ["".join(row) for row in board.board]
    board_str = "/".join(rows)
    castling = "".join(sorted(board.castling_rights))
    extras = f"{board.white_to_move}_{castling}_{board.en_passant_square}"
    return board_str + "_" + extras

def Is_Endgame (board: Board) -> bool:
    queens = 0
    minor_pieces = 0
    for row in board.board:
        for piece in row:
            if piece in "Qq":
                queens += 1
            elif piece in "RrBbNn":
                minor_pieces += 1
    return queens == 0 or minor_pieces <= 2
