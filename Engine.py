from Board import Board
from Move import Move
from tables import PAWN_TABLE, KNIGHT_TABLE, BISHOP_TABLE, ROOK_TABLE, QUEEN_TABLE, KING_MID_TABLE, KING_END_TABLE
import math
import time
import datetime
from dataclasses import dataclass
from typing import Callable


@dataclass
class TTEntry:
    depth: int
    score: float
    flag: str
    move: Move
    generation: int


class EngineSearchContext:
    def __init__(self):
        self.transposition_table = {}
        self.killer_moves = {}
        self.history_heuristic = {}
        self.nodes_searched = 0
        self.quiescence_nodes = 0
        self.transposition_hits = 0
        self.transposition_cutoffs = 0
        self.nmp_used = 0
        self.lmr_count = 0
        self.minimax_time = 0.0
        self.quiescence_time = 0.0
        self.see_time = 0.0
        self.evaluate_position_time = 0.0
        self.last_search_depth = 0
        self.last_root_score = 0.0
        self.last_pv = []
        self.last_best_move_uci = "0000"
        self.total_time_taken = 0.0
        self.tt_generation = 0
        self.search_deadline = None
        self.stop_checker: Callable[[], bool] | None = None
        self.root_pv_move = None
        self.max_seldepth = 0
        self.aspiration_fail_lows = 0
        self.aspiration_fail_highs = 0
        self.aspiration_window_expansions = 0

ctx = EngineSearchContext()

def __getattr__(name):
    _mapping = {
        'TRANSPOSITION_TABLE': 'transposition_table',
        'KILLER_MOVES': 'killer_moves',
        'HISTORY_HEURISTIC': 'history_heuristic',
        'NODES_SEARCHED': 'nodes_searched',
        'QUIESCENCE_NODES': 'quiescence_nodes',
        'TRANSPOSITION_HITS': 'transposition_hits',
        'TRANSPOSITION_CUTOFFS': 'transposition_cutoffs',
        'NMP_USED': 'nmp_used',
        'LMR_COUNT': 'lmr_count',
        'MINIMAX_TIME': 'minimax_time',
        'QUIESCENCE_TIME': 'quiescence_time',
        'SEE_TIME': 'see_time',
        'EVALUATE_POSITION_TIME': 'evaluate_position_time',
        'LAST_SEARCH_DEPTH': 'last_search_depth',
        'LAST_ROOT_SCORE': 'last_root_score',
        'LAST_PV': 'last_pv',
        'LAST_BEST_MOVE_UCI': 'last_best_move_uci',
        'TOTAL_TIME_TAKEN': 'total_time_taken'
    }
    if name in _mapping:
        return getattr(ctx, _mapping[name])
    raise AttributeError(f'module has no attribute {name}')

Q_DEPTH_LIMIT = 2
MATE_SCORE = 10000
SEE_ENABLED = False
MAX_TT_SIZE = 200000
TEMPO_BONUS = 10
ENABLE_NULL_MOVE_PRUNING = True
ENABLE_LATE_MOVE_PRUNING = False
LOGGING_ENABLED = True
DETAILED_LOG_ENABLED = False
LOG_FILE = "chess_engine_log.txt"
VERBOSE_SEARCH = True
TT_MOVE_BONUS = 30000
CHECK_MOVE_BONUS = 1200

def Reset_Search_Stats():

    ctx.transposition_hits = 0
    ctx.transposition_cutoffs = 0
    ctx.nodes_searched = 0
    ctx.quiescence_nodes = 0
    ctx.lmr_count = 0
    ctx.nmp_used = 0
    ctx.killer_moves = {}
    ctx.history_heuristic = {}
    ctx.minimax_time = 0.0
    ctx.quiescence_time = 0.0
    ctx.see_time = 0.0
    ctx.evaluate_position_time = 0.0
    ctx.last_search_depth = 0
    ctx.last_root_score = 0.0
    ctx.last_pv = []
    ctx.last_best_move_uci = "0000"
    ctx.total_time_taken = 0.0
    ctx.search_deadline = None
    ctx.stop_checker = None
    ctx.root_pv_move = None
    ctx.max_seldepth = 0
    ctx.aspiration_fail_lows = 0
    ctx.aspiration_fail_highs = 0
    ctx.aspiration_window_expansions = 0
    Board.FIND_LEGAL_MOVES_TIME = 0


def Has_Non_Pawn_Material(board: Board, white: bool) -> bool:
    for row in board.board:
        for piece in row:
            if piece == "." or piece.isupper() != white:
                continue
            if piece.upper() in ("N", "B", "R", "Q"):
                return True
    return False


def _Search_Should_Stop() -> bool:
    if ctx.stop_checker and ctx.stop_checker():
        return True
    if ctx.search_deadline is not None and time.perf_counter() >= ctx.search_deadline:
        return True
    return False


def _Store_TT_Entry(key: str, depth: int, score: float, flag: str, move: Move):
    new_entry = TTEntry(depth, score, flag, move, ctx.tt_generation)
    old_entry = ctx.transposition_table.get(key)
    if old_entry is not None:
        if depth > old_entry.depth or (depth == old_entry.depth and flag == 'EXACT' and old_entry.flag != 'EXACT'):
            ctx.transposition_table[key] = new_entry
        return

    if len(ctx.transposition_table) < MAX_TT_SIZE:
        ctx.transposition_table[key] = new_entry
        return

    victim_key = None
    victim_entry = None
    for index, (cand_key, cand_entry) in enumerate(ctx.transposition_table.items()):
        if index >= 64:
            break
        if victim_entry is None:
            victim_key = cand_key
            victim_entry = cand_entry
            continue
        if cand_entry.depth < victim_entry.depth:
            victim_key = cand_key
            victim_entry = cand_entry
            continue
        if cand_entry.depth == victim_entry.depth and cand_entry.generation < victim_entry.generation:
            victim_key = cand_key
            victim_entry = cand_entry

    if victim_key is not None:
        del ctx.transposition_table[victim_key]
    ctx.transposition_table[key] = new_entry


def _Extract_PV(board: Board, depth: int) -> list[str]:
    pv_board = board.Copy_For_Color(board.white_to_move)
    pv = []
    visited = set()

    for _ in range(max(0, depth)):
        key = pv_board.Hash_Board()
        if key in visited:
            break
        visited.add(key)

        entry = ctx.transposition_table.get(key)
        if entry is None or entry.move is None:
            break

        legal_moves = pv_board.Generate_Legal_Moves()
        matched_move = None
        for legal_move in legal_moves:
            if legal_move == entry.move or legal_move.To_UCI() == entry.move.To_UCI():
                matched_move = legal_move
                break

        if matched_move is None:
            break

        pv.append(matched_move.To_UCI())
        pv_board.Make_Move(matched_move)

    return pv


def _Prioritize_Root_Move(moves: list[Move], preferred_move: Move | None):
    if preferred_move is None:
        return
    for i, move in enumerate(moves):
        if move == preferred_move or move.To_UCI() == preferred_move.To_UCI():
            if i != 0:
                moves.insert(0, moves.pop(i))
            return


def _Square_To_Alg(square: tuple[int, int] | None) -> str:
    if square is None:
        return "-"
    row, col = square
    return f"{chr(ord('a') + col)}{8 - row}"


def _Board_To_FEN(board: Board) -> str:
    fen_rows = []
    for row in board.board:
        empty = 0
        out = []
        for piece in row:
            if piece == ".":
                empty += 1
            else:
                if empty:
                    out.append(str(empty))
                    empty = 0
                out.append(piece)
        if empty:
            out.append(str(empty))
        fen_rows.append("".join(out))

    active = "w" if board.white_to_move else "b"
    castling = "".join([flag for flag in "KQkq" if flag in board.castling_rights]) or "-"
    ep = _Square_To_Alg(board.en_passant_square)
    halfmove = getattr(board, "halfmove_clock", 0)
    fullmove = getattr(board, "fullmove_number", 1)
    return f"{'/'.join(fen_rows)} {active} {castling} {ep} {halfmove} {fullmove}"


def _Append_Log_Line(line: str):
    if not LOGGING_ENABLED:
        return
    with open(LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write(line + "\n")


def Format_UCI_Score(score: float) -> str:
    cp_score = int(round(score))
    mate_margin = MATE_SCORE - abs(cp_score)
    if mate_margin <= 200:
        plies_to_mate = max(1, (mate_margin + 1) // 2)
        if cp_score < 0:
            plies_to_mate = -plies_to_mate
        return f"mate {plies_to_mate}"
    return f"cp {cp_score}"


def Get_Hashfull_Permill() -> int:
    if MAX_TT_SIZE <= 0:
        return 0
    return min(1000, int((len(ctx.transposition_table) * 1000) / MAX_TT_SIZE))


def Get_Search_Stats() -> dict:
    elapsed = max(1e-9, ctx.total_time_taken)
    total_nodes = ctx.nodes_searched + ctx.quiescence_nodes
    return {
        "depth": ctx.last_search_depth,
        "seldepth": max(ctx.max_seldepth, ctx.last_search_depth),
        "score_cp": int(round(ctx.last_root_score)),
        "bestmove": ctx.last_best_move_uci,
        "pv": list(ctx.last_pv),
        "nodes": ctx.nodes_searched,
        "qnodes": ctx.quiescence_nodes,
        "total_nodes": total_nodes,
        "time_s": ctx.total_time_taken,
        "time_ms": int(ctx.total_time_taken * 1000),
        "nps": int(total_nodes / elapsed),
        "tt_hits": ctx.transposition_hits,
        "tt_cutoffs": ctx.transposition_cutoffs,
        "hashfull_permille": Get_Hashfull_Permill(),
        "asp_fail_low": ctx.aspiration_fail_lows,
        "asp_fail_high": ctx.aspiration_fail_highs,
        "asp_expands": ctx.aspiration_window_expansions,
    }


def Estimate_Auto_Depth(board: Board, min_depth: int = 3, max_depth: int = 8) -> int:
    min_depth = max(1, int(min_depth))
    max_depth = max(min_depth, int(max_depth))

    legal_moves = board.Generate_Legal_Moves()
    if not legal_moves:
        return min_depth

    move_count = len(legal_moves)
    in_check = board.Is_King_In_Check(board.white_to_move)
    captures = board._Generate_Pseudo_Legal_Capture_Moves()

    non_pawn_pieces = 0
    total_pieces = 0
    for row in board.board:
        for piece in row:
            if piece == ".":
                continue
            total_pieces += 1
            if piece.upper() in ("N", "B", "R", "Q"):
                non_pawn_pieces += 1

    if move_count >= 36:
        depth = min_depth
    elif move_count >= 24:
        depth = min_depth + 1
    elif move_count >= 14:
        depth = min_depth + 2
    else:
        depth = min_depth + 3

    if in_check:
        depth += 1
    if len(captures) >= 8:
        depth += 1
    if non_pawn_pieces <= 6:
        depth += 1
    if total_pieces <= 10:
        depth += 1

    return max(min_depth, min(max_depth, depth))

def Order_Moves(board: Board, moves: list, depth: int):
    tt_move = None
    key = board.Hash_Board()
    entry = ctx.transposition_table.get(key)
    if entry is not None:
        tt_move = entry.move

    scored_moves = []
    for move in moves:
        score = Score_Move(board, move, depth)
        if tt_move is not None and move == tt_move:
            score += TT_MOVE_BONUS
        scored_moves.append((score, move))

    scored_moves.sort(key=lambda item: item[0], reverse=True)
    moves[:] = [move for _, move in scored_moves]

def Order_Quiescence_Moves(board: Board, moves: list):
    PIECE_VALUES = {
        'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 0,
        'p': -100, 'n': -320, 'b': -330, 'r': -500, 'q': -900, 'k': 0,
    }
    moves.sort(key=lambda m: PIECE_VALUES.get((m.piece_captured or "").upper(), 0) * 10 - PIECE_VALUES.get((m.piece_moved or "").upper(), 0), reverse=True)

def Move_Gives_Check(board: Board, move: Move, cache: dict) -> bool:
    cache_key = hash(move)
    if cache_key in cache:
        return cache[cache_key]

    if not board.Make_Move(move):
        cache[cache_key] = False
        return False

    # After making the move, side-to-move is the opponent.
    gives_check = board.Is_King_In_Check(board.white_to_move)
    board.Undo_Move()
    cache[cache_key] = gives_check
    return gives_check

def Get_PVS_Window(alpha: float, beta: float, maximizing: bool) -> tuple[float, float]:
    if maximizing:
        return alpha, min(beta, alpha + 1)
    return max(alpha, beta - 1), beta

def Evaluate_Position(board: Board) -> float:
    import time
    t0 = time.perf_counter()

    piece_values = {
        'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 0,
        'p': -100, 'n': -320, 'b': -330, 'r': -500, 'q': -900, 'k': 0,
    }
    phase_weights = {'N': 1, 'B': 1, 'R': 2, 'Q': 4}

    mg_score = TEMPO_BONUS if board.white_to_move else -TEMPO_BONUS
    eg_score = mg_score
    phase = 0
    white_bishop_count = 0
    black_bishop_count = 0

    for row in range(8):
        for col in range(8):
            piece = board.board[row][col]
            if piece == ".":
                continue

            # Material in centipawns.
            mg_score += piece_values.get(piece, 0)
            eg_score += piece_values.get(piece, 0)

            phase += phase_weights.get(piece.upper(), 0)

            # Piece-square tables from tables.py are pawn=10 scale; convert to cp.
            table_row = row if piece.isupper() else 7 - row
            if piece.upper() == "P":
                pst = PAWN_TABLE[table_row][col] * 10
                mg_score += pst if piece.isupper() else -pst
                eg_score += pst if piece.isupper() else -pst
            elif piece.upper() == "N":
                pst = KNIGHT_TABLE[table_row][col] * 10
                mg_score += pst if piece.isupper() else -pst
                eg_score += pst if piece.isupper() else -pst
            elif piece.upper() == "B":
                pst = BISHOP_TABLE[table_row][col] * 10
                mg_score += pst if piece.isupper() else -pst
                eg_score += pst if piece.isupper() else -pst
                if piece.isupper():
                    white_bishop_count += 1
                else:
                    black_bishop_count += 1
            elif piece.upper() == "R":
                pst = ROOK_TABLE[table_row][col] * 10
                mg_score += pst if piece.isupper() else -pst
                eg_score += pst if piece.isupper() else -pst
            elif piece.upper() == "Q":
                pst = QUEEN_TABLE[table_row][col] * 10
                mg_score += pst if piece.isupper() else -pst
                eg_score += pst if piece.isupper() else -pst
            elif piece.upper() == "K":
                mg_pst = KING_MID_TABLE[table_row][col] * 10
                eg_pst = KING_END_TABLE[table_row][col] * 10
                if piece.isupper():
                    mg_score += mg_pst
                    eg_score += eg_pst
                else:
                    mg_score -= mg_pst
                    eg_score -= eg_pst
            
    
    pawn_structure_score = Evaluate_Pawn_Structure(board)
    open_file_score = Evaluate_Open_Files_And_Rooks(board)
    king_safety_score = Evaluate_King_Safety(board)
    mobility_score = Evaluate_Mobility(board)
    development_score = Evaluate_Development(board)

    mg_score += (
        pawn_structure_score
        + open_file_score
        + 0.75 * king_safety_score
        + 0.60 * mobility_score
        + development_score
    )
    eg_score += (
        pawn_structure_score
        + open_file_score
        + 0.20 * king_safety_score
        + 0.80 * mobility_score
        + 0.20 * development_score
    )
    

    #if not earlygame:
    #    score += Evaluate_Pins(board)
    #    score += Evaluate_Forks(board)
    #    score += Evaluate_Skewers(board)
    

    # Bishop pair bonus
    if white_bishop_count >= 2:
        mg_score += 30
        eg_score += 30
    if black_bishop_count >= 2:
        mg_score -= 30
        eg_score -= 30

    # SEE-based hanging piece check - REMOVED for performance
    """
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
    """

    t1 = time.perf_counter()
    ctx.evaluate_position_time += t1 - t0

    phase = max(0, min(24, phase))
    score = (mg_score * phase + eg_score * (24 - phase)) / 24
    return score

def Evaluate_Pawn_Structure (board: Board) -> float:
    score = 0
    white_pawns = [[] for _ in range(8)]
    black_pawns = [[] for _ in range(8)]
    white_passed = []
    black_passed = []

    phase = 0
    phase_weights = {'N': 1, 'B': 1, 'R': 2, 'Q': 4}

    for row in range(8):
        for col in range(8):
            piece = board.board[row][col]
            if piece == "P":
                white_pawns[col].append(row)
            elif piece == "p":
                black_pawns[col].append(row)
            elif piece != ".":
                phase += phase_weights.get(piece.upper(), 0)

    phase = max(0, min(24, phase))
    endgame_factor = (24 - phase) / 24.0
    white_king = board.Find_King(True)
    black_king = board.Find_King(False)

    for col in range(8):
        wp = white_pawns[col]
        bp = black_pawns[col]

        if len(wp) > 1:
            score -= 12 * (len(wp) - 1)
        if len(bp) > 1:
            score += 12 * (len(bp) - 1)

        for row in wp:
            if (col == 0 or not white_pawns[col - 1]) and (col == 7 or not white_pawns[col + 1]):
                score -= 15
            if any((r == row or r == row + 1) for adj in [col - 1, col + 1] if 0 <= adj < 8 for r in white_pawns[adj]):
                score += 6

            is_passed = True
            for adj in range(max(0, col - 1), min(8, col + 2)):
                if any(enemy_row < row for enemy_row in black_pawns[adj]):
                    is_passed = False
                    break
            if is_passed:
                white_passed.append((row, col))
                advance = 6 - row
                score += 20 + advance * 6

                clear_path = all(board.board[r][col] == "." for r in range(row - 1, -1, -1))
                if clear_path:
                    score += 8 + int(10 * endgame_factor)

                if white_king != (-1, -1) and black_king != (-1, -1):
                    own_dist = abs(white_king[0] - row) + abs(white_king[1] - col)
                    enemy_dist = abs(black_king[0] - row) + abs(black_king[1] - col)
                    score += (enemy_dist - own_dist) * (1.5 + endgame_factor)

        for row in bp:
            if (col == 0 or not black_pawns[col - 1]) and (col == 7 or not black_pawns[col + 1]):
                score += 15
            if any((r == row or r == row - 1) for adj in [col - 1, col + 1] if 0 <= adj < 8 for r in black_pawns[adj]):
                score -= 6

            is_passed = True
            for adj in range(max(0, col - 1), min(8, col + 2)):
                if any(enemy_row > row for enemy_row in white_pawns[adj]):
                    is_passed = False
                    break
            if is_passed:
                black_passed.append((row, col))
                advance = row - 1
                score -= 20 + advance * 6

                clear_path = all(board.board[r][col] == "." for r in range(row + 1, 8))
                if clear_path:
                    score -= 8 + int(10 * endgame_factor)

                if white_king != (-1, -1) and black_king != (-1, -1):
                    own_dist = abs(black_king[0] - row) + abs(black_king[1] - col)
                    enemy_dist = abs(white_king[0] - row) + abs(white_king[1] - col)
                    score -= (enemy_dist - own_dist) * (1.5 + endgame_factor)

    white_passed_set = set(white_passed)
    for row, col in white_passed:
        if ((row, col - 1) in white_passed_set) or ((row, col + 1) in white_passed_set):
            score += 10 + int(8 * endgame_factor)

    black_passed_set = set(black_passed)
    for row, col in black_passed:
        if ((row, col - 1) in black_passed_set) or ((row, col + 1) in black_passed_set):
            score -= 10 + int(8 * endgame_factor)

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
                    score += 18
                elif board.board[row][col] == "r":
                    score -= 18

        #semi-open file
        elif not white_pawn_present:
            for row in range (8):
                if board.board[row][col] == "R":
                    score += 10
        elif not black_pawn_present:
            for row in range (8):
                if board.board[row][col] == "r":
                    score -= 10

    return score

def Evaluate_King_Safety (board: Board) -> float:
    def side_king_safety(white: bool) -> int:
        king_row, king_col = board.Find_King(white)
        if king_row == -1:
            return 0

        own_pawn = "P" if white else "p"
        enemy_is_white = not white
        shield_row = king_row - 1 if white else king_row + 1
        side_score = 0

        if 0 <= shield_row < 8:
            shield = 0
            for dc in (-1, 0, 1):
                c = king_col + dc
                if 0 <= c < 8 and board.board[shield_row][c] == own_pawn:
                    shield += 1
            side_score += shield * 8
            side_score -= (3 - shield) * 6

        for dc in (-1, 0, 1):
            c = king_col + dc
            if not (0 <= c < 8):
                continue
            has_own_pawn = any(board.board[r][c] == own_pawn for r in range(8))
            if not has_own_pawn:
                side_score -= 5

        piece_danger = {'N': 5, 'B': 5, 'R': 7, 'Q': 10}
        for r in range(8):
            for c in range(8):
                piece = board.board[r][c]
                if piece == "." or piece.isupper() != enemy_is_white:
                    continue
                p = piece.upper()
                if p not in piece_danger:
                    continue

                dist = abs(r - king_row) + abs(c - king_col)
                if dist <= 3:
                    side_score -= piece_danger[p] * (4 - dist)

        if king_col in (3, 4):
            if white and king_row <= 5:
                side_score -= 12
            if (not white) and king_row >= 2:
                side_score -= 12

        for c in range(max(0, king_col - 1), min(8, king_col + 2)):
            if any(board.board[r][c] == own_pawn for r in range(8)):
                continue
            for r in range(8):
                piece = board.board[r][c]
                if piece == "." or piece.isupper() != enemy_is_white:
                    continue
                if piece.upper() in ("R", "Q"):
                    side_score -= 8

        return side_score

    white_score = side_king_safety(True)
    black_score = side_king_safety(False)
    score = white_score - black_score
    return max(-60, min(60, score))

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
    knight_dirs = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
    bishop_dirs = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    rook_dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    weights = {'N': 4, 'B': 3, 'R': 2, 'Q': 1}

    white_mobility = 0
    black_mobility = 0

    def add_mobility(is_white: bool, amount: int):
        nonlocal white_mobility, black_mobility
        if is_white:
            white_mobility += amount
        else:
            black_mobility += amount

    for row in range(8):
        for col in range(8):
            piece = board.board[row][col]
            if piece == ".":
                continue

            is_white = piece.isupper()
            p = piece.upper()
            if p not in ("N", "B", "R", "Q"):
                continue

            if p == "N":
                count = 0
                for dr, dc in knight_dirs:
                    r, c = row + dr, col + dc
                    if 0 <= r < 8 and 0 <= c < 8:
                        target = board.board[r][c]
                        if target == "." or target.isupper() != is_white:
                            count += 1
                add_mobility(is_white, count * weights[p])
                continue

            directions = []
            if p in ("B", "Q"):
                directions.extend(bishop_dirs)
            if p in ("R", "Q"):
                directions.extend(rook_dirs)

            reachable = 0
            for dr, dc in directions:
                r, c = row + dr, col + dc
                while 0 <= r < 8 and 0 <= c < 8:
                    target = board.board[r][c]
                    if target == ".":
                        reachable += 1
                    else:
                        if target.isupper() != is_white:
                            reachable += 1
                        break
                    r += dr
                    c += dc

            add_mobility(is_white, reachable * weights[p])

    return white_mobility - black_mobility

def Evaluate_Development (board: Board) -> float:
    # Simple opening development in centipawns.
    score = 0

    white_home_minors = [(7, 1, "N"), (7, 6, "N"), (7, 2, "B"), (7, 5, "B")]
    black_home_minors = [(0, 1, "n"), (0, 6, "n"), (0, 2, "b"), (0, 5, "b")]

    for row, col, piece in white_home_minors:
        if board.board[row][col] == piece:
            score -= 8
    for row, col, piece in black_home_minors:
        if board.board[row][col] == piece:
            score += 8

    # Small reward for central pawn presence in the opening.
    for sq in [(4, 3), (4, 4)]:
        if board.board[sq[0]][sq[1]] == "P":
            score += 5
    for sq in [(3, 3), (3, 4)]:
        if board.board[sq[0]][sq[1]] == "p":
            score -= 5

    return score

def Evaluate_Pins (board: Board) -> float:
    score = 0
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]

    for is_white in [True, False]:
        king_pos = board.Find_King(is_white)
        if king_pos == (-1, -1):
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


def Terminal_Score(board: Board, ply: int) -> float:
    if not board.Is_King_In_Check(board.white_to_move):
        return 0.0
    return -(MATE_SCORE - ply)

def Evaluate_Node(board: Board) -> float:
    score = Evaluate_Position(board)
    return score if board.white_to_move else -score

def Negamax(board: Board, depth: int, alpha: float, beta: float, ply: int = 0) -> float:
    if _Search_Should_Stop():
        return Evaluate_Node(board)

    ctx.nodes_searched += 1
    if ply > ctx.max_seldepth:
        ctx.max_seldepth = ply
    t0 = time.perf_counter()

    if board.Is_Threefold_Repetition() or board.Is_Fifty_Move_Rule():
        t1 = time.perf_counter()
        ctx.minimax_time += t1 - t0
        return 0.0

    alpha_orig = alpha

    if depth <= 0:
        score = Quiescence_Search(board, alpha, beta, ply)
        t1 = time.perf_counter()
        ctx.minimax_time += t1 - t0
        return score if score is not None else 0.0

    legal_moves = board.Generate_Legal_Moves()
    if not legal_moves:
        score = Terminal_Score(board, ply)
        t1 = time.perf_counter()
        ctx.minimax_time += t1 - t0
        return score
        
    Order_Moves(board, legal_moves, depth)

    key = board.Hash_Board()
    if key in ctx.transposition_table:
        entry = ctx.transposition_table[key]
        ctx.transposition_hits += 1

        if entry.move in legal_moves:
            legal_moves.remove(entry.move)
            legal_moves.insert(0, entry.move)

        if entry.depth >= depth:
            if entry.flag == 'EXACT':
                ctx.transposition_cutoffs += 1
                t1 = time.perf_counter()
                ctx.minimax_time += t1 - t0
                return entry.score
            elif entry.flag == 'LOWER':
                alpha = max(alpha, entry.score)
            elif entry.flag == 'UPPER':
                beta = min(beta, entry.score)
            if alpha >= beta:
                ctx.transposition_cutoffs += 1
                t1 = time.perf_counter()
                ctx.minimax_time += t1 - t0
                return entry.score

    node_in_check = board.Is_King_In_Check(board.white_to_move)

    if node_in_check and ply < 15:
        depth += 1

    if ENABLE_NULL_MOVE_PRUNING and depth >= 3 and not node_in_check and Has_Non_Pawn_Material(board, board.white_to_move):
        reduction = 2
        board.Make_Null_Move()
        null_score = -Negamax(board, depth - 1 - reduction, -beta, -beta + 1, ply + 1)
        board.Undo_Null_Move()

        if null_score >= beta:
            ctx.nmp_used += 1
            t1 = time.perf_counter()
            ctx.minimax_time += t1 - t0
            return beta

    best_move = None
    best_score = float('-inf')

    for move_index, move in enumerate(legal_moves):
        if not board.Make_Move(move):
            continue

        is_quiet = not move.piece_captured and not move.is_pawn_promotion
        gives_check = move.gives_check

        if ENABLE_LATE_MOVE_PRUNING and depth >= 4 and move_index >= 4 and is_quiet and not node_in_check and not gives_check:
            board.Undo_Move()
            continue

        lmr_reduction = 0
        if is_quiet and move_index >= 3 and depth >= 4 and not node_in_check and not gives_check:
            import math
            base_reduction = int((math.log(depth) * math.log(move_index + 1)) / 2)
            lmr_reduction = max(1, min(depth - 2, base_reduction))

        if move_index == 0 or depth < 4:
            score = -Negamax(board, depth - 1, -beta, -alpha, ply + 1)
        else:
            if lmr_reduction > 0:
                ctx.lmr_count += 1
                reduced_depth = max(0, depth - 1 - lmr_reduction)
                score = -Negamax(board, reduced_depth, -alpha - 1, -alpha, ply + 1)
                if alpha < score < beta:
                    score = -Negamax(board, depth - 1, -beta, -alpha, ply + 1)
            else:
                score = -Negamax(board, depth - 1, -alpha - 1, -alpha, ply + 1)
                if alpha < score < beta:
                    score = -Negamax(board, depth - 1, -beta, -alpha, ply + 1)

        board.Undo_Move()

        if score > best_score:
            best_score = score
            best_move = move
            
        if score > alpha:
            alpha = score

        if alpha >= beta:
            if is_quiet:
                if depth not in ctx.killer_moves:
                    ctx.killer_moves[depth] = []
                if move not in ctx.killer_moves[depth]:
                    ctx.killer_moves[depth].append(move)
                    if len(ctx.killer_moves[depth]) > 2:
                        ctx.killer_moves[depth].pop(0)

                key_history = (move.start, move.end)
                ctx.history_heuristic[key_history] = ctx.history_heuristic.get(key_history, 0) + (depth * depth)
            break

    if best_score <= alpha_orig:
        flag = 'UPPER'
    elif best_score >= beta:
        flag = 'LOWER'
    else:
        flag = 'EXACT'
        
    _Store_TT_Entry(key, depth, best_score, flag, best_move)

    t1 = time.perf_counter()
    ctx.minimax_time += t1 - t0
    return best_score

def Quiescence_Search(board: Board, alpha: float, beta: float, ply: int) -> float:
    if _Search_Should_Stop():
        return Evaluate_Node(board)

    ctx.quiescence_nodes += 1
    if ply > ctx.max_seldepth:
        ctx.max_seldepth = ply
    t0 = time.perf_counter()

    if ctx.quiescence_nodes > 50000:
        t1 = time.perf_counter()
        ctx.quiescence_time += t1 - t0
        return Evaluate_Node(board)

    in_check = board.Is_King_In_Check(board.white_to_move)
    if in_check:
        stand_pat = None
        noisy_moves = board.Generate_Legal_Moves(include_castling=False)
        if not noisy_moves:
            t1 = time.perf_counter()
            ctx.quiescence_time += t1 - t0
            return Terminal_Score(board, ply)
    else:
        stand_pat = Evaluate_Node(board)

        if stand_pat >= beta:
            t1 = time.perf_counter()
            ctx.quiescence_time += t1 - t0
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

        # Q_DEPTH_LIMIT effectively ignored by removing it or keeping it large, let's keep it safe
        if ply >= 30: # 30 is deep enough
            t1 = time.perf_counter()
            ctx.quiescence_time += t1 - t0
            return stand_pat

        noisy_moves = board._Generate_Pseudo_Legal_Capture_Moves()

    Order_Quiescence_Moves(board, noisy_moves)

    for move in noisy_moves:
        if not board.Make_Move(move):
            continue
        if board.Is_King_In_Check(not board.white_to_move):
            board.Undo_Move()
            continue

        score = -Quiescence_Search(board, -beta, -alpha, ply + 1)
        board.Undo_Move()

        if score >= beta:
            t1 = time.perf_counter()
            ctx.quiescence_time += t1 - t0
            return beta
        if score > alpha:
            alpha = score

    t1 = time.perf_counter()
    ctx.quiescence_time += t1 - t0
    return alpha

def Get_Attackers (board: Board, target_row: int, target_col: int, white: bool):
    "return list of position(row, col piece) that are attacking"

    
    attackers = []
    for r in range(8):
        for c in range(8):
            piece = board.board[r][c]
            if piece == "." or piece.isupper() != white:
                continue

            if piece.upper() == 'K' and target_row == r and target_col == c:
                continue  # King cannot attack king
    

            if piece.upper() == "P":
                direction = -1 if piece.isupper() else 1
                for dx in [-1, 1]:
                    nr, nc = r + direction, c + dx
                    if 0 <= nr < 8 and 0 <= nc < 8 and (nr, nc) == (target_row, target_col):
                        attackers.append((r, c, piece))
            else:
                pseudo_moves = []
                board._Generate_Piece_Moves(piece, r, c, pseudo_moves, include_castling=False, white=white)
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

    def see_recursive(square, attackers_w, attackers_b, side, gain_stack):
        global SEE_TIME
        import time 
        t0 = time.perf_counter()
        attackers = attackers_w if side else attackers_b
        if not attackers:
            t1 = time.perf_counter()
            SEE_TIME += t1 - t0
            return gain_stack[-1] if gain_stack else 0

        attacker = min(attackers, key=lambda x: value_map.get(x[2], 10000))
        attackers.remove(attacker)

        capturing_piece_value = value_map.get(temp_board.board[square[0]][square[1]], 0)
        gain = value_map.get(attacker[2], 0) - capturing_piece_value
        gain_stack.append(gain_stack[-1] - gain if gain_stack else -gain)

        # 🔥 Limit SEE recursion depth to prevent infinite recursion
        if len(gain_stack) > 4:
            t1 = time.perf_counter()
            SEE_TIME += t1 - t0
            return gain_stack[-1]

        temp_board.board[attacker[0]][attacker[1]] = "."
        temp_board.board[square[0]][square[1]] = attacker[2]

        new_attackers = Get_Attackers(temp_board, *square, white=side)
        t1 = time.perf_counter()
        SEE_TIME += t1 - t0
        return max(-see_recursive(square, attackers_b, new_attackers, not side, gain_stack), gain_stack[-1])

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

    if move.is_pawn_promotion:
        return 20000
    
    if victim:
        victim_value = piece_values.get(victim, 0)
        attacker_value = piece_values.get(attacker, 1)
        trade_delta = victim_value - attacker_value
        capture_score = 10000 + 12 * victim_value - 2 * attacker_value
        capture_score += 1500 if trade_delta >= 0 else -1500
        if SEE_ENABLED:
            capture_score += Static_Exchange_Evaluation(board, move)
        return capture_score
    
    if depth in ctx.killer_moves and move in ctx.killer_moves[depth]:
        index = ctx.killer_moves[depth].index(move)
        return 8500 - (index * 300)
    
    key = (move.start, move.end)
    return ctx.history_heuristic.get(key, 0)


def Find_Best_Move(
    board: Board,
    max_depth: int,
    time_limit: float = None,
    stop_checker: Callable[[], bool] | None = None,
    info_callback: Callable[[int, float, list[str], float], None] | None = None,
) -> Move:
    start_time = time.perf_counter()
    Reset_Search_Stats()
    ctx.tt_generation = (ctx.tt_generation + 1) % 1024
    ctx.stop_checker = stop_checker
    ctx.search_deadline = (start_time + time_limit) if time_limit else None

    guess = Evaluate_Node(board)
    window_size = 50

    completed_best_move = None
    completed_score = guess
    completed_pv = []
    completed_depth = 0

    def root_should_stop() -> bool:
        if stop_checker and stop_checker():
            return True
        if time_limit and (time.perf_counter() - start_time) >= time_limit:
            return True
        return False

    for current_depth in range(1, max_depth + 1):
        if root_should_stop():
            break

        window = window_size
        alpha = guess - window
        beta = guess + window
        iteration_best_move = None
        iteration_best_score = float('-inf')
        iteration_complete = False

        while True:
            if root_should_stop():
                break

            legal_moves = board.Generate_Legal_Moves()
            if not legal_moves:
                elapsed = time.perf_counter() - start_time
                ctx.total_time_taken = elapsed
                ctx.last_search_depth = 0
                ctx.last_root_score = Terminal_Score(board, 0)
                ctx.last_pv = []
                ctx.search_deadline = None
                ctx.stop_checker = None
                return None

            Order_Moves(board, legal_moves, current_depth)
            _Prioritize_Root_Move(legal_moves, ctx.root_pv_move)

            best_score = float('-inf')
            best_move = None
            aborted = False

            for move in legal_moves:
                if root_should_stop():
                    aborted = True
                    break

                if not board.Make_Move(move):
                    continue

                score = -Negamax(board, current_depth - 1, -beta, -alpha, 1)
                board.Undo_Move()

                if root_should_stop():
                    aborted = True
                    break

                if score > best_score:
                    best_score = score
                    best_move = move

                if score > alpha:
                    alpha = score

            if aborted or best_move is None:
                break

            iteration_best_move = best_move
            iteration_best_score = best_score

            if best_score <= guess - window:
                ctx.aspiration_fail_lows += 1
                ctx.aspiration_window_expansions += 1
                alpha = float('-inf')
                window *= 2
            elif best_score >= guess + window:
                ctx.aspiration_fail_highs += 1
                ctx.aspiration_window_expansions += 1
                beta = float('inf')
                window *= 2
            else:
                guess = best_score
                iteration_complete = True
                break

        if not iteration_complete:
            break

        completed_best_move = iteration_best_move
        completed_score = iteration_best_score
        completed_depth = current_depth
        completed_pv = _Extract_PV(board, current_depth)
        if completed_best_move is not None:
            root_uci = completed_best_move.To_UCI()
            if not completed_pv or completed_pv[0] != root_uci:
                completed_pv = [root_uci] + completed_pv
        ctx.root_pv_move = completed_best_move
        ctx.last_search_depth = completed_depth
        ctx.last_root_score = completed_score
        ctx.last_pv = completed_pv
        ctx.last_best_move_uci = completed_best_move.To_UCI() if completed_best_move else "0000"

        if info_callback:
            elapsed = time.perf_counter() - start_time
            info_callback(current_depth, completed_score, completed_pv, elapsed)

    ctx.total_time_taken = time.perf_counter() - start_time
    ctx.last_search_depth = completed_depth
    ctx.last_root_score = completed_score
    ctx.last_pv = completed_pv
    ctx.last_best_move_uci = completed_best_move.To_UCI() if completed_best_move else "0000"
    ctx.search_deadline = None
    ctx.stop_checker = None

    _Print_Search_Stats(board, completed_best_move)
    return completed_best_move

def Toggle_Logging(enabled: bool):
    global LOGGING_ENABLED
    LOGGING_ENABLED = bool(enabled)


def Toggle_Detailed_Log(enabled: bool):
    global DETAILED_LOG_ENABLED
    DETAILED_LOG_ENABLED = bool(enabled)

def Clear_Transposition_Table():
    ctx.transposition_table.clear()


def _Print_Search_Stats(board: Board, best_move: Move | None):
    if not LOGGING_ENABLED:
        return

    stats = Get_Search_Stats()
    best_move_uci = best_move.To_UCI() if best_move else "0000"
    score_text = Format_UCI_Score(ctx.last_root_score)
    pv_text = " ".join(ctx.last_pv)
    fen = _Board_To_FEN(board)

    if VERBOSE_SEARCH:
        print(
            "nodes={nodes} qnodes={qnodes} tt_hits={hits} tt_cutoffs={cuts} "
            "depth={depth} seldepth={seldepth} score={score} time={time_s:.3f}s "
            "nps={nps} asp={fl}/{fh}/{exp} pv={pv}".format(
                nodes=ctx.nodes_searched,
                qnodes=ctx.quiescence_nodes,
                hits=ctx.transposition_hits,
                cuts=ctx.transposition_cutoffs,
                depth=ctx.last_search_depth,
                seldepth=ctx.max_seldepth,
                score=score_text,
                time_s=ctx.total_time_taken,
                nps=stats["nps"],
                fl=ctx.aspiration_fail_lows,
                fh=ctx.aspiration_fail_highs,
                exp=ctx.aspiration_window_expansions,
                pv=pv_text,
            )
        )

    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    line = (
        f"[{timestamp}] fen={fen} best={best_move_uci} depth={ctx.last_search_depth} "
        f"seldepth={ctx.max_seldepth} score={score_text} pv=\"{pv_text}\" "
        f"nodes={ctx.nodes_searched} qnodes={ctx.quiescence_nodes} total_nodes={stats['total_nodes']} "
        f"nps={stats['nps']} time_ms={stats['time_ms']} tt_hits={ctx.transposition_hits} "
        f"tt_cutoffs={ctx.transposition_cutoffs} hashfull={Get_Hashfull_Permill()} "
        f"asp_fail_low={ctx.aspiration_fail_lows} asp_fail_high={ctx.aspiration_fail_highs} "
        f"asp_expands={ctx.aspiration_window_expansions}"
    )
    _Append_Log_Line(line)

    if DETAILED_LOG_ENABLED:
        _Append_Log_Line(
            "  timings_ms: minimax={:.2f} quiescence={:.2f} eval={:.2f} see={:.2f} find_legal={:.2f}".format(
                ctx.minimax_time * 1000.0,
                ctx.quiescence_time * 1000.0,
                ctx.evaluate_position_time * 1000.0,
                ctx.see_time * 1000.0,
                Board.FIND_LEGAL_MOVES_TIME * 1000.0,
            )
        )
