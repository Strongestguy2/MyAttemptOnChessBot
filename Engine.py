from Board import Board, Move
from tables import PAWN_TABLE, KNIGHT_TABLE, BISHOP_TABLE, ROOK_TABLE, QUEEN_TABLE, KING_MID_TABLE, KING_END_TABLE

TRANSPOSITION_TABLE = {}
TRANSPOSITION_HITS = 0
NODES_SEARCHED = 0
QUIESCENCE_NODES = 0
LMR_COUNT = 0
NMP_USED = 0
KILLER_MOVES = {}
HISTORY_HEURISTIC = {}

def Evaluate_Position(board: Board) -> float:
    piece_values = {
        'P': 10, 'N': 30, 'B': 30, 'R': 50, 'Q': 90, 'K': 900,
        'p': -10, 'n': -30, 'b': -30, 'r': -50, 'q': -90, 'k': -900
    }

    score = 0
    endgame = Is_Endgame(board)
    score += 10 if board.white_to_move else -10  # tempo bonus

    white_pawn_files = [[] for _ in range(8)]
    black_pawn_files = [[] for _ in range(8)]

    for row in range(8):
        for col in range(8):
            piece = board.board[row][col]
            if piece == "P":
                white_pawn_files[col].append(row)
            elif piece == "p":
                black_pawn_files[col].append(row)

    for row in range(8):
        for col in range(8):
            piece = board.board[row][col]
            if piece == ".":
                continue

            score += piece_values.get(piece, 0)

            # Piece-square tables
            table_row = row if piece.isupper() else 7 - row
            if piece.upper() == "P":
                score += PAWN_TABLE[table_row][col] * (1 if piece.isupper() else -1)
            elif piece.upper() == "N":
                score += KNIGHT_TABLE[table_row][col] * (1 if piece.isupper() else -1)
            elif piece.upper() == "B":
                score += BISHOP_TABLE[table_row][col] * (1 if piece.isupper() else -1)
            elif piece.upper() == "R":
                score += ROOK_TABLE[table_row][col] * (1 if piece.isupper() else -1)
            elif piece.upper() == "Q":
                score += QUEEN_TABLE[table_row][col] * (1 if piece.isupper() else -1)
            elif piece.upper() == "K":
                king_table = KING_END_TABLE if endgame else KING_MID_TABLE
                score += king_table[table_row][col] * (1 if piece.isupper() else -1)

            # Center control
            if (row, col) in {(3, 3), (3, 4), (4, 3), (4, 4)}:
                score += 0.5 if piece.isupper() else -0.5

            # Early development bonus
            if piece in ("N", "B") and row < 7:
                score += 0.5
            elif piece in ("n", "b") and row > 0:
                score -= 0.5

            # Passed pawn check
            if piece == "P":
                if all(all(r < row for r in black_pawn_files[c])
                       for c in range(max(0, col - 1), min(8, col + 2))):
                    score += 0.5
                if len(white_pawn_files[col]) > 1:
                    score -= 0.25
            elif piece == "p":
                if all(all(r > row for r in white_pawn_files[c])
                       for c in range(max(0, col - 1), min(8, col + 2))):
                    score -= 0.5
                if len(black_pawn_files[col]) > 1:
                    score += 0.25

    score += Evaluate_Pawn_Structure(board)
    score += Evaluate_Open_Files_And_Rooks(board)
    score += Evaluate_King_Safety(board)
    score += Evaluate_Space(board)
    score += Evaluate_Mobility(board)
    score += Evaluate_Pins(board)
    score += Evaluate_Forks(board)
    score += Evaluate_Skewers(board)
    score += Evaluate_Development(board)

    # Bishop pair bonus
    if sum(p == "B" for row in board.board for p in row) >= 2:
        score += 0.5
    if sum(p == "b" for row in board.board for p in row) >= 2:
        score -= 0.5

    # Development count
    developed_white = sum(p in "NBRQ" for row in board.board for p in row)
    developed_black = sum(p in "nbrq" for row in board.board for p in row)
    score += 0.1 * (developed_white - developed_black)

    # SEE-based hanging piece check
    for row in range(8):
        for col in range(8):
            piece = board.board[row][col]
            if piece == ".":
                continue
            enemy = not piece.isupper()
            attackers = Get_Attackers(board, row, col, white=enemy)
            if attackers:
                dummy_move = Move((row, col), (row, col), piece_moved=piece, piece_captured=piece)
                see_score = Static_Exchange_Evaluation(board, dummy_move)
                if see_score < 0:
                    score += see_score / 10  # small penalty to avoid hanging

    return score

def Evaluate_Pawn_Structure (board: Board) -> float:
    score = 0
    white_pawns = [[] for _ in range(8)]
    black_pawns = [[] for _ in range(8)]

    for row in range (8):
        for col in range (8):
            piece = board.board[row][col]
            if piece == "P":
                white_pawns[col].append(row)
            elif piece == "p":
                black_pawns[col].append(row)

    for col in range (8):
        wp = white_pawns[col]
        bp = black_pawns[col]

        if len (wp) > 1:
            score -= 0.5 * (len(wp) - 1)
        if len (bp) > 1:
            score += 0.5 * (len(bp) - 1)

        for row in wp:
            #isolated pawn
            if (col == 0 or not white_pawns[col - 1]) and (col == 7 or not white_pawns[col + 1]):
                score -= 0.5
            #backward
            if all (r > row for adj in [col - 1, col, col + 1] if 0 <= adj < 8 for r in white_pawns[adj]):
                score -= 0.25
            #connected
            if any ((r == row or r == row + 1) for adj in [col - 1, col + 1] if 0 <= adj < 8 for r in white_pawns[adj]):
                score += 0.3

        for row in bp:
            if (col == 0 or not black_pawns[col - 1]) and (col == 7 or not black_pawns[col + 1]):
                score += 0.5
            if all(r < row for adj in [col - 1, col + 1] if 0 <= adj < 8 for r in black_pawns[adj]):
                score += 0.25
            if any((r == row or r == row - 1) for adj in [col - 1, col + 1] if 0 <= adj < 8 for r in black_pawns[adj]):
                score -= 0.3
    
    return score
        
def Evaluate_Open_Files_And_Rooks (board: Board) -> float:
    score = 0

    for col in range (8):
        white_pawn_present = any(board.board[row][col] == "P" for row in range(8))
        black_pawn_present = any(board.board[row][col] == "p" for row in range(8))

        #open file
        if not white_pawn_present and not black_pawn_present:
            for row in range (8):
                if board.board[row][col] == "R":
                    score += 0.5
                elif board.board[row][col] == "r":
                    score -= 0.5

        #semi-open file
        elif not white_pawn_present:
            for row in range (8):
                if board.board[row][col] == "R":
                    score += 0.25
        elif not black_pawn_present:
            for row in range (8):
                if board.board[row][col] == "r":
                    score -= 0.25

    for col in range (8):
        if board.board[6][col] == "R":
            score += 0.4
        elif board.board[1][col] == "r":
            score -= 0.4

    for col in range (8):
        white_rooks = sum(1 for row in range (8) if board.board[row][col] == "R")
        black_rooks = sum(1 for row in range (8) if board.board[row][col] == "r")

        if white_rooks > 2:
            score += 0.5
        if black_rooks > 2:
            score -= 0.5

    return score

def Evaluate_King_Safety (board: Board) -> float:
    score = 0

    kr, kc = board.Find_King (True)
    if kr == 7:
        shield_pawns = 0
        for dc in [-1, 0, 1]:
            c = kc + dc
            if 0 <= c < 8 and board.board[6][c] == "P":
                shield_pawns += 1
        score -= (3 - shield_pawns) * 5

        for dc in [-1, 0, 1]:
            c = kc + dc
            if 0 <= c < 8:
                file_has_white_pawn = any(board.board[r][c] == "P" for r in range(8))
                file_has_black_pawn = any(board.board[r][c] == "p" for r in range(8))
                if not file_has_white_pawn and not file_has_black_pawn:
                    score -= 5
                elif not file_has_white_pawn:
                    score -= 3
    
    kr, kc = board.Find_King (False)
    if kr == 0:
        shield_pawns = 0
        for dc in [-1, 0, 1]:
            c = kc + dc
            if 0 <= c < 8 and board.board[1][c] == "p":
                shield_pawns += 1
        score += (3 - shield_pawns) * 5

        for dc in [-1, 0, 1]:
            c = kc + dc
            if 0 <= c < 8:
                file_has_white_pawn = any(board.board[r][c] == "P" for r in range(8))
                file_has_black_pawn = any(board.board[r][c] == "p" for r in range(8))
                if not file_has_white_pawn and not file_has_black_pawn:
                    score += 5
                elif not file_has_black_pawn:
                    score += 3
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
    return (whtie_space - black_space) * 2

def Evaluate_Mobility (board: Board) -> float:
    score = 0

    for row in range (8):
        for col in range (8):
            piece = board.board[row][col]
            if piece == "." or piece.upper () in ("K", "P"):
                continue

            mobility_moves = []
            board._Generate_Piece_Moves (piece, row, col, mobility_moves, include_castling=False)

            mobility_score = 0.1 * len (mobility_moves)
            score  += mobility_score if piece.isupper() else -mobility_score
    return score

def Evaluate_Development (board: Board) -> float:
    score = 0
    undeveloped_white = 0
    undeveloped_black = 0

    for col in [1, 2, 5, 6]:
        if board.board[7][col] in ("N", "B"):
            undeveloped_white += 1
        if board.board[0][col] in ("n", "b"):
            undeveloped_black += 1

    score -= undeveloped_white * 0.5
    score -= undeveloped_black * 0.5

    white_rooks = [(r, c) for r in range (8) for c in range (8) if board.board[r][c] == "R"]
    black_rooks = [(r, c) for r in range (8) for c in range (8) if board.board[r][c] == "r"]

    if len(white_rooks) == 2 and all (board.board[7][c] == "." for c in range (white_rooks[0][1] + 1, white_rooks[1][1])):
        score += 0.5
    if len(black_rooks) == 2 and all (board.board[0][c] == "." for c in range (black_rooks[0][1] + 1, black_rooks[1][1])):
        score -= 0.5
    return score

def Evaluate_Pins (board: Board) -> float:
    score = 0
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]

    for is_white in [True, False]:
        king_pos = board.Find_King(is_white)
        if not king_pos:
            continue

        for dr, dc in directions:
            r, c = king_pos
            pinned_piece = None

            for step in range (1, 8):
                r += dr
                c += dc

                if not (0 <= r < 8 and 0 <= c < 8):
                    break

                piece = board.board[r][c]
                if piece == ".":
                    continue

                if piece.isupper() == is_white:
                    if pinned_piece is None:
                        pinned_piece = (r, c, piece)
                    else:
                        break
                else:
                    if pinned_piece:
                        if piece.upper() in ("Q", "R", "B"):
                            is_diagonal = dr != 0 and dc != 0
                            is_straight = dr == 0 or dc == 0
                            if (piece.upper() == "Q") or (piece.upper() == "B" and is_diagonal) or (piece.upper() == "R" and is_straight):
                                if pinned_piece[2].upper() != "P":
                                    score += 1.0 if not is_white else -1.0
                    break
    return score

def Evaluate_Forks (board: Board) -> float:
    score = 0
    knight_moves = [(2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)]

    for row in range (8):
        for col in range (8):
            piece = board.board[row][col]
            if piece.upper() != "N":
                continue

            fork_targets = 0
            for dr, dc in knight_moves:
                r, c = row + dr, col + dc
                if 0 <= r < 8 and 0 <= c < 8:
                    target = board.board[r][c]
                    if target != "." and target.isupper() != piece.isupper():
                        if target.upper() in ("Q", "R", "K"):
                            fork_targets += 1
            
            if fork_targets >= 2:
                score += 1.5 if piece.isupper() else -1.5
    return score

def Evaluate_Skewers(board: Board) -> float:
    score = 0
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1),
                  (1, 1), (-1, -1), (1, -1), (-1, 1)]

    for row in range(8):
        for col in range(8):
            piece = board.board[row][col]
            if piece.upper() not in ("Q", "R", "B"):
                continue

            is_white = piece.isupper()

            for dr, dc in directions:
                r, c = row + dr, col + dc
                line = []

                while 0 <= r < 8 and 0 <= c < 8:
                    target = board.board[r][c]
                    if target == ".":
                        r += dr
                        c += dc
                        continue

                    if target.isupper() != is_white:
                        line.append((r, c, target))
                        r += dr
                        c += dc
                    else:
                        break

                    if len(line) >= 2:
                        front = line[0][2]
                        back = line[1][2]
                        if front.upper() in ("K", "Q") and back.upper() in ("R", "Q"):
                            score += 1.0 if is_white else -1.0
                        break

    return score
                        
def Minimax(board: Board, depth: int, alpha: float, beta: float, maximizing: bool) -> float:
    global TRANSPOSITION_TABLE, TRANSPOSITION_HITS
    global KILLER_MOVES, HISTORY_HEURISTIC
    global NODES_SEARCHED, QUIESCENCE_NODES, LMR_COUNT, NMP_USED
    NODES_SEARCHED += 1

    if depth == 0:
        return Quiescence_Search(board, alpha, beta, maximizing)
    
    key = board.Hash_Board()
    if key in TRANSPOSITION_TABLE:
        TRANSPOSITION_HITS += 1
        return TRANSPOSITION_TABLE[key]
    
    legal_moves = board.Generate_Legal_Moves()
    legal_moves.sort(key=lambda m: Score_Move(board, m, depth), reverse=maximizing)

    #null move pruning
    if not board.Is_King_In_Check() and depth >= 3:
        white_pieces = sum (1 for row in board.board for p in row if p.isupper() and p not in "KP.")
        black_pieces = sum (1 for row in board.board for p in row if p.islower() and p not in "kp.")
        if white_pieces > 5 and black_pieces > 5:
            R = 2 if depth < 6 else 3
            board.white_to_move = not board.white_to_move
            null_score = -Minimax(board, depth - R, -beta, -beta + 1, not maximizing)
            board.white_to_move = not board.white_to_move
            if null_score >= beta:
                NMP_USED += 1
                return beta
            
    if not legal_moves:
        score = -10000 if board.Is_King_In_Check() else 0
        TRANSPOSITION_TABLE[key] = score
        return score
    
    best_score = float('-inf') if maximizing else float('inf')

    for move_index, move in enumerate(legal_moves):
        board.Make_Move(move)
        
        is_quiet = not move.piece_captured
        do_lmr = is_quiet and depth >= 3 and move_index >= 3
        search_depth = depth - 1 if do_lmr else depth\
        
        if do_lmr:
            LMR_COUNT += 1

        if move_index == 0:
            score = Minimax(board, search_depth - 1, alpha, beta, not maximizing)
        else:
            score = Minimax(board, search_depth - 1, alpha + 1, alpha, not maximizing)
            if alpha < score < beta:
                score = Minimax(board, search_depth - 1, alpha, beta, not maximizing)

        board.Undo_Move()

        if maximizing:
            if score > best_score:
                best_score = score
            alpha = max(alpha, score)
        else:
            if score < best_score:
                best_score = score
            beta = min(beta, score)
        
        if beta <= alpha:
            if is_quiet:
                if depth not in KILLER_MOVES:
                    KILLER_MOVES[depth] = []
                if move not in KILLER_MOVES[depth]:
                    KILLER_MOVES[depth].append(move)
                    if len (KILLER_MOVES[depth]) > 2:
                        KILLER_MOVES[depth].pop(0)
            key_history = (move.start, move.end)
            HISTORY_HEURISTIC[key_history] = HISTORY_HEURISTIC.get(key_history, 0) + (depth * depth)
            break

    TRANSPOSITION_TABLE[key] = best_score
    return best_score

def Quiescence_Search (board: Board, alpha: float, beta: float, maximizing: bool) -> float:
    global QUIESCENCE_NODES
    QUIESCENCE_NODES += 1
    stand_pat = Evaluate_Position(board)
    
    if maximizing:
        if stand_pat >= beta:
            return beta
        alpha = max(alpha, stand_pat)
    else:
        if stand_pat <= alpha:
            return alpha
        beta = min(beta, stand_pat)

    capture_moves = [m for m in board.Generate_Legal_Moves() if m.piece_captured and Static_Exchange_Evaluation(board, m) > 0]
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
    for r in range(8):
        for c in range(8):
            piece = board.board[r][c]
            if piece == "." or piece.isupper() != white:
                continue

            if piece.upper() == "P":
                direction = -1 if piece.isupper() else 1
                for dx in [-1, 1]:
                    nr, nc = r + direction, c + dx
                    if 0 <= nr < 8 and 0 <= nc < 8 and (nr, nc) == (target_row, target_col):
                        attackers.append((r, c, piece))
            else:
                pseudo_moves = []
                board._Generate_Piece_Moves(piece, r, c, pseudo_moves, include_castling=False)
                for m in pseudo_moves:
                    if m.end == (target_row, target_col):
                        attackers.append((r, c, piece))

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

        if len(gain_stack) > 10:
            return gain_stack[-1]
        
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

def Score_Move (board: Board, move: Move, depth: int = 0) -> int:
    "mvv-lva most valuable victim - least valuable attacker"
    piece_values = {
        'P':100, 'N':300, 'B':300, 'R':500, 'Q':900, 'K':10000,
        'p':100, 'n':300, 'b':300, 'r':500, 'q':900, 'k':10000
    }

    victim = move.piece_captured
    attacker = move.piece_moved

    if victim:
        victim_value = piece_values.get(victim, 0)
        attacker_value = piece_values.get(attacker, 1)
        see_bonus = Static_Exchange_Evaluation (board, move)
        tactical_bonus = 20 if see_bonus >= victim_value else 0
        return (10 * victim_value) - attacker_value + see_bonus + tactical_bonus
    
    if depth in KILLER_MOVES and move in KILLER_MOVES[depth]:
        return 10000
    
    key = (move.start, move.end)
    return HISTORY_HEURISTIC.get(key, 0)

def Find_Best_Move (board: Board, depth: int) -> Move:
    best_move = None
    best_score = float('-inf') if board.white_to_move else float('inf')

    if board.Is_Threefold_Repetition():
        print("Threefold repetition detected. Stalemate.")
        return None
    
    for current_depth in range (1, depth + 1):
        legal_moves = board.Generate_Legal_Moves()
        best_this_depth = None
        score_this_depth = float('-inf') if board.white_to_move else float('inf')

        for move in legal_moves:
            board.Make_Move(move)
            score = Minimax(board, current_depth - 1, float('-inf'), float('inf'), not board.white_to_move)
            board.Undo_Move()

            if (board.white_to_move and score > score_this_depth) or (not board.white_to_move and score < score_this_depth):
                score_this_depth = score
                best_this_depth = move

        if (board.white_to_move and score_this_depth > best_score) or (not board.white_to_move and score_this_depth < best_score):
            best_score = score_this_depth
            best_move = best_this_depth
    return best_move

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

def Print_Profiling_Stats():
    print ("Search profiling:")
    print (f"Nodes searched: {NODES_SEARCHED}")
    print (f"Quiescence nodes: {QUIESCENCE_NODES}")
    print (f"Transposition hits: {TRANSPOSITION_HITS}")
    print (f"Null move pruning: {NMP_USED}")
    print (f"Late move reduction: {LMR_COUNT}")
