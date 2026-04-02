from Board import Board
from Move import Move
from EvalBackend import FeatureVector, StubNNUEBackend, extract_features_from_board
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
        self.eval_cache = {}
        self.killer_moves = {}
        self.history_heuristic = {}
        self.nodes_searched = 0
        self.quiescence_nodes = 0
        self.transposition_hits = 0
        self.transposition_cutoffs = 0
        self.nmp_used = 0
        self.lmr_count = 0
        self.lmr_candidates = 0
        self.lmr_applied = 0
        self.lmr_researches = 0
        self.minimax_time = 0.0
        self.quiescence_time = 0.0
        self.see_time = 0.0
        self.evaluate_position_time = 0.0
        self.total_eval_calls = 0
        self.static_eval_calls = 0
        self.full_eval_calls = 0
        self.qsearch_eval_calls = 0
        self.main_search_eval_calls = 0
        self.qsearch_noisy_accepted = 0
        self.qsearch_noisy_rejected = 0
        self.qsearch_noisy_considered = 0
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
        'TOTAL_EVAL_CALLS': 'total_eval_calls',
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
MATE_TT_THRESHOLD = MATE_SCORE - 1000
SEE_ENABLED = False
MAX_TT_SIZE = 200000
MAX_EVAL_CACHE_SIZE = 50000
TEMPO_BONUS = 10
EVAL_MODE = "classical"
ENABLE_NULL_MOVE_PRUNING = True
ENABLE_LATE_MOVE_PRUNING = True
LOGGING_ENABLED = True
DETAILED_LOG_ENABLED = False
LOG_FILE = "chess_engine_log.txt"
VERBOSE_SEARCH = True
TT_MOVE_BONUS = 30000
CHECK_MOVE_BONUS = 1200
PIECE_VALUES_CP = {
    'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 0,
    'p': -100, 'n': -320, 'b': -330, 'r': -500, 'q': -900, 'k': 0,
}
ABS_PIECE_VALUES = {
    'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 0,
    'p': 100, 'n': 320, 'b': 330, 'r': 500, 'q': 900, 'k': 0,
}
PHASE_WEIGHTS = {'N': 1, 'B': 1, 'R': 2, 'Q': 4}
KNIGHT_DIRS = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
BISHOP_DIRS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
ROOK_DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
CENTER_SQUARES = ((3, 3), (3, 4), (4, 3), (4, 4))
EXTENDED_CENTER_SQUARES = (
    (2, 2), (2, 3), (2, 4), (2, 5),
    (3, 2), (3, 3), (3, 4), (3, 5),
    (4, 2), (4, 3), (4, 4), (4, 5),
    (5, 2), (5, 3), (5, 4), (5, 5),
)
EXTENDED_CENTER_SET = frozenset(EXTENDED_CENTER_SQUARES)
NNUE_BACKEND = StubNNUEBackend()

def Reset_Search_Stats():

    ctx.transposition_hits = 0
    ctx.transposition_cutoffs = 0
    ctx.nodes_searched = 0
    ctx.quiescence_nodes = 0
    ctx.lmr_count = 0
    ctx.lmr_candidates = 0
    ctx.lmr_applied = 0
    ctx.lmr_researches = 0
    ctx.nmp_used = 0
    ctx.killer_moves = {}
    ctx.history_heuristic = {}
    ctx.minimax_time = 0.0
    ctx.quiescence_time = 0.0
    ctx.see_time = 0.0
    ctx.evaluate_position_time = 0.0
    ctx.total_eval_calls = 0
    ctx.static_eval_calls = 0
    ctx.full_eval_calls = 0
    ctx.qsearch_eval_calls = 0
    ctx.main_search_eval_calls = 0
    ctx.qsearch_noisy_accepted = 0
    ctx.qsearch_noisy_rejected = 0
    ctx.qsearch_noisy_considered = 0
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


def _Current_QRatio() -> float:
    return ctx.quiescence_nodes / max(1, ctx.nodes_searched)


def _Score_To_TT(score: float, ply: int) -> float:
    if score >= MATE_TT_THRESHOLD:
        return score + ply
    if score <= -MATE_TT_THRESHOLD:
        return score - ply
    return score


def _Score_From_TT(score: float, ply: int) -> float:
    if score >= MATE_TT_THRESHOLD:
        return score - ply
    if score <= -MATE_TT_THRESHOLD:
        return score + ply
    return score


def _Probe_TT(key: int, depth: int, alpha: float, beta: float, ply: int) -> tuple[TTEntry | None, float, float, float | None]:
    entry = ctx.transposition_table.get(key)
    if entry is None:
        return None, alpha, beta, None

    ctx.transposition_hits += 1
    tt_score = _Score_From_TT(entry.score, ply)

    if entry.depth >= depth:
        if entry.flag == 'EXACT':
            ctx.transposition_cutoffs += 1
            return entry, alpha, beta, tt_score
        if entry.flag == 'LOWER':
            alpha = max(alpha, tt_score)
        elif entry.flag == 'UPPER':
            beta = min(beta, tt_score)

        if alpha >= beta:
            ctx.transposition_cutoffs += 1
            return entry, alpha, beta, tt_score

    return entry, alpha, beta, None


def _Store_TT_Entry(key: str, depth: int, score: float, flag: str, move: Move, ply: int):
    new_entry = TTEntry(depth, _Score_To_TT(score, ply), flag, move, ctx.tt_generation)
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
    qratio = _Current_QRatio()
    tt_hit_rate = (ctx.transposition_hits / max(1, total_nodes))
    tt_cutoff_rate = (ctx.transposition_cutoffs / max(1, ctx.transposition_hits))
    avg_eval_time_us = (ctx.evaluate_position_time * 1_000_000.0 / max(1, ctx.total_eval_calls))
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
        "tt_hit_rate": tt_hit_rate,
        "tt_cutoffs": ctx.transposition_cutoffs,
        "tt_cutoff_rate": tt_cutoff_rate,
        "hashfull_permille": Get_Hashfull_Permill(),
        "qratio": qratio,
        "nmp_used": ctx.nmp_used,
        "lmr_count": ctx.lmr_count,
        "lmr_candidates": ctx.lmr_candidates,
        "lmr_applied": ctx.lmr_applied,
        "lmr_researches": ctx.lmr_researches,
        "eval_calls": ctx.total_eval_calls,
        "static_eval_calls": ctx.static_eval_calls,
        "full_eval_calls": ctx.full_eval_calls,
        "qsearch_eval_calls": ctx.qsearch_eval_calls,
        "main_eval_calls": ctx.main_search_eval_calls,
        "avg_eval_time_us": avg_eval_time_us,
        "qsearch_noisy_considered": ctx.qsearch_noisy_considered,
        "qsearch_noisy_accepted": ctx.qsearch_noisy_accepted,
        "qsearch_noisy_rejected": ctx.qsearch_noisy_rejected,
        "asp_fail_low": ctx.aspiration_fail_lows,
        "asp_fail_high": ctx.aspiration_fail_highs,
        "asp_expands": ctx.aspiration_window_expansions,
    }


def _Record_Eval_Call(is_static: bool, caller: str, elapsed: float):
    ctx.total_eval_calls += 1
    if is_static:
        ctx.static_eval_calls += 1
    else:
        ctx.full_eval_calls += 1

    if caller == "qsearch":
        ctx.qsearch_eval_calls += 1
    else:
        ctx.main_search_eval_calls += 1

    ctx.evaluate_position_time += elapsed


def Estimate_Auto_Depth(board: Board, min_depth: int = 3, max_depth: int = 8, last_time: float = 0.0, last_nodes: int = 0) -> int:
    min_depth = max(1, int(min_depth))
    max_depth = max(min_depth, int(max_depth))

    legal_moves = board.Generate_Legal_Moves()
    if not legal_moves:
        return min_depth

    move_count = len(legal_moves)
    in_check = board.Is_King_In_Check(board.white_to_move)

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

    # Soft time adaptation
    target_time = 2.0  # target 2 seconds per move
    if last_time > 0:
        if last_time > target_time * 2:
            depth -= 1
        elif last_time < target_time * 0.5:
            depth += 1

    return max(min_depth, min(max_depth, depth))

def Capture_Quality_Tier(move: Move) -> int:
    if move.is_pawn_promotion:
        return 3

    victim_value = ABS_PIECE_VALUES.get(move.piece_captured or "", 0)
    attacker_value = ABS_PIECE_VALUES.get(move.piece_moved or "", 0)
    trade_delta = victim_value - attacker_value

    if trade_delta > 80:
        return 2
    if trade_delta >= -40:
        return 1
    return 0


def _Capture_Order_Score(move: Move) -> int:
    tier = Capture_Quality_Tier(move)
    victim_value = ABS_PIECE_VALUES.get(move.piece_captured or "", 0)
    attacker_value = ABS_PIECE_VALUES.get(move.piece_moved or "", 0)
    check_bonus = CHECK_MOVE_BONUS if move.gives_check else 0

    if move.is_pawn_promotion:
        return 24000 + victim_value + check_bonus
    if tier == 2:
        return 18000 + victim_value * 10 - attacker_value + check_bonus
    if tier == 1:
        return 13000 + victim_value * 8 - attacker_value + check_bonus
    return 2000 + victim_value * 4 - attacker_value + check_bonus


def _Quiescence_Delta_Margin(move: Move, qratio: float) -> int:
    tier = Capture_Quality_Tier(move)
    if move.is_pawn_promotion:
        return 140
    if tier >= 2:
        return 100 if qratio > 2.5 else 130
    if tier == 1:
        return 70 if qratio > 2.5 else 100
    return 30 if qratio > 1.7 else 50


def _Approx_Capture_Risk(board: Board, move: Move) -> tuple[bool, bool, bool]:
    if move.is_pawn_promotion:
        return False, True, False

    friendly_is_white = board.white_to_move
    defended_by_enemy = board._Is_Square_Attacked(move.end, not friendly_is_white)
    supported_by_friendly = board._Is_Square_Attacked(move.end, friendly_is_white)
    victim_value = ABS_PIECE_VALUES.get(move.piece_captured or "", 0)
    attacker_value = ABS_PIECE_VALUES.get(move.piece_moved or "", 0)
    risky = defended_by_enemy and (not supported_by_friendly) and attacker_value > victim_value
    return defended_by_enemy, supported_by_friendly, risky


def _QCapture_Order_Score(board: Board, move: Move) -> int:
    score = _Capture_Order_Score(move)
    defended, supported, risky = _Approx_Capture_Risk(board, move)
    if risky:
        score -= 2400
    elif defended and not supported:
        score -= 900
    elif supported:
        score += 250
    return score


def _Should_Search_QCapture(board: Board, move: Move, qratio: float) -> tuple[bool, bool]:
    if move.is_pawn_promotion:
        return True, False

    tier = Capture_Quality_Tier(move)
    defended, supported, risky = _Approx_Capture_Risk(board, move)
    attacker_value = ABS_PIECE_VALUES.get(move.piece_moved or "", 0)
    victim_value = ABS_PIECE_VALUES.get(move.piece_captured or "", 0)

    if tier == 0:
        return False, risky or defended
    if tier == 1 and risky:
        return False, True
    if tier == 1 and defended and not supported and attacker_value >= victim_value and qratio > 0.35:
        return False, True
    if tier == 1 and defended and not supported and qratio > 0.8:
        return False, True
    return True, risky


def _Is_Promising_Quiet(move: Move, depth: int) -> bool:
    if depth in ctx.killer_moves and move in ctx.killer_moves[depth]:
        return True
    history_score = ctx.history_heuristic.get((move.start, move.end), 0)
    return history_score >= max(100, depth * depth * 4)


def Order_Moves(board: Board, moves: list, depth: int, tt_move: Move | None = None):
    scored_moves = []
    for move in moves:
        score = Score_Move(board, move, depth)
        if tt_move is not None and (move == tt_move or move.To_UCI() == tt_move.To_UCI()):
            score += TT_MOVE_BONUS
        scored_moves.append((score, move))

    scored_moves.sort(key=lambda item: item[0], reverse=True)
    moves[:] = [move for _, move in scored_moves]

def Order_Quiescence_Moves(board: Board, moves: list):
    moves.sort(key=lambda move: _QCapture_Order_Score(board, move), reverse=True)

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

def _Store_Eval_Cache(key: int, score: float):
    if len(ctx.eval_cache) >= MAX_EVAL_CACHE_SIZE:
        ctx.eval_cache.pop(next(iter(ctx.eval_cache)))
    ctx.eval_cache[key] = score


def extract_features(board: Board) -> FeatureVector:
    return extract_features_from_board(board)


def Load_NNUE_Backend(weights_path: str | None = None):
    NNUE_BACKEND.load(weights_path)


def Set_Eval_Mode(mode: str):
    global EVAL_MODE
    normalized = str(mode).strip().lower()
    if normalized not in {"classical", "nnue"}:
        raise ValueError(f"Unsupported eval mode: {mode}")
    EVAL_MODE = normalized


def Evaluate_Endgame_King_Activity(board: Board, phase: int, white_piece_map: dict, black_piece_map: dict) -> float:
    if phase > 10:
        return 0.0

    white_king = board.Find_King(True)
    black_king = board.Find_King(False)
    if white_king == (-1, -1) or black_king == (-1, -1):
        return 0.0

    endgame_weight = (10 - phase) / 10.0

    def king_center_bonus(square: tuple[int, int]) -> float:
        row, col = square
        return 7 - (abs(row - 3.5) + abs(col - 3.5))

    queen_count = len(white_piece_map["Q"]) + len(black_piece_map["Q"])
    scale = 1.0 if queen_count == 0 else 0.5
    return (
        (king_center_bonus(white_king) - king_center_bonus(black_king))
        * 4.0
        * endgame_weight
        * scale
    )


def Evaluate_Mop_Up(board: Board, phase: int, white_material: int, black_material: int) -> float:
    if phase > 8:
        return 0.0

    white_king = board.Find_King(True)
    black_king = board.Find_King(False)
    if white_king == (-1, -1) or black_king == (-1, -1):
        return 0.0

    material_edge = white_material - black_material
    if abs(material_edge) < 350:
        return 0.0

    winning_white = material_edge > 0
    winner_king = white_king if winning_white else black_king
    loser_king = black_king if winning_white else white_king
    king_distance = abs(winner_king[0] - loser_king[0]) + abs(winner_king[1] - loser_king[1])
    loser_from_center = abs(loser_king[0] - 3.5) + abs(loser_king[1] - 3.5)
    endgame_weight = (8 - phase) / 8.0
    score = (14 - king_distance) * 8 + loser_from_center * 12
    return score * endgame_weight if winning_white else -score * endgame_weight


def evaluate_classical(board: Board) -> float:
    key = board.Hash_Board()
    cached_score = ctx.eval_cache.get(key)
    if cached_score is not None:
        return cached_score

    board_rows = board.board
    mg_score = TEMPO_BONUS if board.white_to_move else -TEMPO_BONUS
    eg_score = mg_score
    phase = 0
    white_bishop_count = 0
    black_bishop_count = 0
    white_material = 0
    black_material = 0

    white_pawns = [[] for _ in range(8)]
    black_pawns = [[] for _ in range(8)]
    white_piece_map = {"N": [], "B": [], "R": [], "Q": []}
    black_piece_map = {"N": [], "B": [], "R": [], "Q": []}
    white_rooks_by_col = [0] * 8
    black_rooks_by_col = [0] * 8

    for row, board_row in enumerate(board_rows):
        for col, piece in enumerate(board_row):
            if piece == ".":
                continue

            mg_score += PIECE_VALUES_CP[piece]
            eg_score += PIECE_VALUES_CP[piece]
            if piece == "P":
                white_pawns[col].append(row)
                white_material += 100
                pst = PAWN_TABLE[row][col] * 10
                mg_score += pst
                eg_score += pst
                continue
            if piece == "p":
                black_pawns[col].append(row)
                black_material += 100
                table_row = 7 - row
                pst = PAWN_TABLE[table_row][col] * 10
                mg_score -= pst
                eg_score -= pst
                continue
            if piece == "N":
                white_piece_map["N"].append((row, col))
                white_material += 320
                phase += 1
                pst = KNIGHT_TABLE[row][col] * 10
                mg_score += pst
                eg_score += pst
                continue
            if piece == "n":
                black_piece_map["N"].append((row, col))
                black_material += 320
                phase += 1
                table_row = 7 - row
                pst = KNIGHT_TABLE[table_row][col] * 10
                mg_score -= pst
                eg_score -= pst
                continue
            if piece == "B":
                white_piece_map["B"].append((row, col))
                white_bishop_count += 1
                white_material += 330
                phase += 1
                pst = BISHOP_TABLE[row][col] * 10
                mg_score += pst
                eg_score += pst
                continue
            if piece == "b":
                black_piece_map["B"].append((row, col))
                black_bishop_count += 1
                black_material += 330
                phase += 1
                table_row = 7 - row
                pst = BISHOP_TABLE[table_row][col] * 10
                mg_score -= pst
                eg_score -= pst
                continue
            if piece == "R":
                white_piece_map["R"].append((row, col))
                white_rooks_by_col[col] += 1
                white_material += 500
                phase += 2
                pst = ROOK_TABLE[row][col] * 10
                mg_score += pst
                eg_score += pst
                continue
            if piece == "r":
                black_piece_map["R"].append((row, col))
                black_rooks_by_col[col] += 1
                black_material += 500
                phase += 2
                table_row = 7 - row
                pst = ROOK_TABLE[table_row][col] * 10
                mg_score -= pst
                eg_score -= pst
                continue
            if piece == "Q":
                white_piece_map["Q"].append((row, col))
                white_material += 900
                phase += 4
                pst = QUEEN_TABLE[row][col] * 10
                mg_score += pst
                eg_score += pst
                continue
            if piece == "q":
                black_piece_map["Q"].append((row, col))
                black_material += 900
                phase += 4
                table_row = 7 - row
                pst = QUEEN_TABLE[table_row][col] * 10
                mg_score -= pst
                eg_score -= pst
                continue
            if piece == "K":
                mg_score += KING_MID_TABLE[row][col] * 10
                eg_score += KING_END_TABLE[row][col] * 10
                continue
            if piece == "k":
                table_row = 7 - row
                mg_score -= KING_MID_TABLE[table_row][col] * 10
                eg_score -= KING_END_TABLE[table_row][col] * 10

    pawn_structure_score = Evaluate_Pawn_Structure(board, white_pawns, black_pawns, phase)
    open_file_score = Evaluate_Open_Files_And_Rooks(
        board,
        white_pawns,
        black_pawns,
        white_rooks_by_col,
        black_rooks_by_col,
    )
    rook_activity_score = 0
    for row, _ in white_piece_map["R"]:
        if row == 1:
            rook_activity_score += 12
    for row, _ in black_piece_map["R"]:
        if row == 6:
            rook_activity_score -= 12

    king_safety_score = Evaluate_King_Safety(board, white_piece_map, black_piece_map, white_pawns, black_pawns)
    mobility_score = Evaluate_Mobility(board, white_piece_map, black_piece_map)
    development_score = Evaluate_Development(board, phase)
    endgame_king_score = Evaluate_Endgame_King_Activity(board, phase, white_piece_map, black_piece_map)
    mop_up_score = Evaluate_Mop_Up(board, phase, white_material, black_material)
    queen_activity_score = 0
    for row, col in white_piece_map["Q"]:
        if (row, col) in EXTENDED_CENTER_SET:
            queen_activity_score += 8
    for row, col in black_piece_map["Q"]:
        if (row, col) in EXTENDED_CENTER_SET:
            queen_activity_score -= 8

    mg_score += (
        pawn_structure_score
        + open_file_score
        + rook_activity_score
        + 0.75 * king_safety_score
        + 0.60 * mobility_score
        + development_score
        + 0.60 * queen_activity_score
    )
    eg_score += (
        pawn_structure_score
        + open_file_score
        + 1.25 * rook_activity_score
        + 0.20 * king_safety_score
        + 0.80 * mobility_score
        + 0.20 * development_score
        + endgame_king_score
        + mop_up_score
        + 0.25 * queen_activity_score
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

    phase = max(0, min(24, phase))
    score = (mg_score * phase + eg_score * (24 - phase)) / 24
    _Store_Eval_Cache(key, score)
    return score


def evaluate_nnue(board: Board) -> float:
    if not NNUE_BACKEND.is_ready():
        NNUE_BACKEND.load(None)
    features = extract_features(board)
    return NNUE_BACKEND.evaluate(features)


def static_eval(board: Board, caller: str = "main") -> float:
    t0 = time.perf_counter()
    if EVAL_MODE == "nnue":
        score = evaluate_nnue(board)
    else:
        score = evaluate_classical(board)
    _Record_Eval_Call(is_static=True, caller=caller, elapsed=time.perf_counter() - t0)
    return score


def full_eval(board: Board, caller: str = "main") -> float:
    t0 = time.perf_counter()
    if EVAL_MODE == "nnue":
        score = evaluate_nnue(board)
    else:
        score = evaluate_classical(board)
    _Record_Eval_Call(is_static=False, caller=caller, elapsed=time.perf_counter() - t0)
    return score


def Evaluate_Position(board: Board) -> float:
    return evaluate_classical(board)

def Evaluate_Pawn_Structure(board: Board, white_pawns: list, black_pawns: list, phase: float) -> float:
    score = 0
    white_passed = []
    black_passed = []

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
        
def Evaluate_Open_Files_And_Rooks(
    board: Board,
    white_pawns: list,
    black_pawns: list,
    white_rooks_by_col: list,
    black_rooks_by_col: list,
) -> float:
    score = 0

    for col in range (8):
        white_pawn_present = len(white_pawns[col]) > 0
        black_pawn_present = len(black_pawns[col]) > 0
        white_rooks = white_rooks_by_col[col]
        black_rooks = black_rooks_by_col[col]

        #open file
        if not white_pawn_present and not black_pawn_present:
            score += 18 * white_rooks
            score -= 18 * black_rooks

        #semi-open file
        elif not white_pawn_present:
            score += 10 * white_rooks
        elif not black_pawn_present:
            score -= 10 * black_rooks

    return score

def Evaluate_King_Safety(
    board: Board,
    white_piece_map: dict,
    black_piece_map: dict,
    white_pawns: list,
    black_pawns: list,
) -> float:
    def side_king_safety(white: bool) -> int:
        king_row, king_col = board.Find_King(white)
        if king_row == -1:
            return 0

        own_pawn = "P" if white else "p"
        shield_row = king_row - 1 if white else king_row + 1
        own_pawn_files = white_pawns if white else black_pawns
        enemy_piece_map = black_piece_map if white else white_piece_map
        side_score = 0

        # Pawn shield
        if 0 <= shield_row < 8:
            shield = 0
            for dc in (-1, 0, 1):
                c = king_col + dc
                if 0 <= c < 8 and board.board[shield_row][c] == own_pawn:
                    shield += 1
            side_score += shield * 8
            side_score -= (3 - shield) * 6

        # Semi-open / open files near king
        for dc in (-1, 0, 1):
            c = king_col + dc
            if not (0 <= c < 8):
                continue
            has_own_pawn = len(own_pawn_files[c]) > 0
            if not has_own_pawn:
                side_score -= 8  # Penalty for open file near king

        # Tactical threats into king zone
        king_zone_attackers = 0
        attack_weight = 0
        piece_danger = {'N': 20, 'B': 20, 'R': 40, 'Q': 70}
        
        for p, locations in enemy_piece_map.items():
            if p not in piece_danger:
                continue
            for r, c in locations:
                dist_to_king = max(abs(r - king_row), abs(c - king_col))
                if dist_to_king <= 3:  # Piece is close to king zone
                    king_zone_attackers += 1
                    # Base danger scaled by distance
                    weight = piece_danger[p] * (4 - dist_to_king)
                    
                    # Bonus penalty if attackers implies battery (R/Q on same file/rank/diag)
                    if p in ("R", "Q") and (c == king_col or r == king_row):
                        weight += 20
                    if p in ("B", "Q") and abs(r - king_row) == abs(c - king_col):
                        weight += 15
                        
                    attack_weight += weight

        if king_zone_attackers >= 2:
            # Nonlinear scaling if multiple pieces attack king zone
            side_score -= (attack_weight * king_zone_attackers) // 4
        else:
            side_score -= attack_weight // 4

        # King centralization penalty early game
        if king_col in (3, 4):
            if white and king_row <= 5:
                side_score -= 15
            if (not white) and king_row >= 2:
                side_score -= 15

        return side_score

    white_score = side_king_safety(True)
    black_score = side_king_safety(False)
    score = white_score - black_score
    return max(-150, min(150, score))

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

def Evaluate_Mobility (board: Board, white_piece_map: dict, black_piece_map: dict) -> float:
    weights = {'N': 4, 'B': 3, 'R': 2, 'Q': 1}

    white_mobility = 0
    black_mobility = 0

    def add_mobility(is_white: bool, amount: int):
        nonlocal white_mobility, black_mobility
        if is_white:
            white_mobility += amount
        else:
            black_mobility += amount

    def accumulate_side_mobility(piece_map: dict, is_white: bool):
        for p in ("N", "B", "R", "Q"):
            for row, col in piece_map[p]:
                if p == "N":
                    count = 0
                    for dr, dc in KNIGHT_DIRS:
                        r, c = row + dr, col + dc
                        if 0 <= r < 8 and 0 <= c < 8:
                            target = board.board[r][c]
                            if target == "." or target.isupper() != is_white:
                                count += 1
                    add_mobility(is_white, count * weights[p])
                    continue

                directions = []
                if p in ("B", "Q"):
                    directions.extend(BISHOP_DIRS)
                if p in ("R", "Q"):
                    directions.extend(ROOK_DIRS)

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

    accumulate_side_mobility(white_piece_map, True)
    accumulate_side_mobility(black_piece_map, False)

    return white_mobility - black_mobility

def Evaluate_Development (board: Board, phase: float) -> float:
    # Simple opening development in centipawns. Taper scaled down aggressively by phase.
    if phase < 16:  # Only mattered in opening/early midgame mostly
        return 0

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

    # Taper aggressively
    opening_weight = (phase - 16) / 8.0  # max 1.0 at phase 24 (opening), 0.0 at phase 16 (mid/end)
    return score * opening_weight

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
    result, reason = board.Get_Game_Result(legal_moves=[])
    if reason != "checkmate":
        return 0.0
    return -(MATE_SCORE - ply)

def Evaluate_Node(board: Board, caller: str = "main") -> float:
    if board.Is_Threefold_Repetition() or board.Is_Fifty_Move_Rule():
        return 0.0
    score = full_eval(board, caller=caller)
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
    key = board.Hash_Board()
    entry, alpha, beta, tt_score = _Probe_TT(key, depth, alpha, beta, ply)
    if tt_score is not None:
        t1 = time.perf_counter()
        ctx.minimax_time += t1 - t0
        return tt_score

    if depth <= 0:
        score = Quiescence_Search(board, alpha, beta, ply)
        t1 = time.perf_counter()
        ctx.minimax_time += t1 - t0
        return score if score is not None else 0.0

    node_in_check = board.Is_King_In_Check(board.white_to_move)
    if node_in_check and ply < 15:
        depth += 1

    legal_moves = board.Generate_Legal_Moves()
    if not legal_moves:
        score = Terminal_Score(board, ply)
        t1 = time.perf_counter()
        ctx.minimax_time += t1 - t0
        return score

    tt_move = entry.move if entry is not None else None
    Order_Moves(board, legal_moves, depth, tt_move=tt_move)

    if ENABLE_NULL_MOVE_PRUNING and depth >= 4 and not node_in_check and Has_Non_Pawn_Material(board, board.white_to_move):
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

        if (
            ENABLE_LATE_MOVE_PRUNING
            and depth >= 5
            and move_index >= 8
            and is_quiet
            and not node_in_check
            and not gives_check
            and alpha > -MATE_TT_THRESHOLD
            and best_score > -MATE_TT_THRESHOLD
        ):
            board.Undo_Move()
            continue

        lmr_reduction = 0
        lmr_candidate = (
            is_quiet
            and depth >= 3
            and move_index >= 2
            and not node_in_check
            and not gives_check
        )
        if lmr_candidate:
            ctx.lmr_candidates += 1
            if not _Is_Promising_Quiet(move, depth):
                base_reduction = 1 + int((math.log(depth) * math.log(move_index + 1)) / 3)
                lmr_reduction = max(1, min(depth - 2, base_reduction))

        if move_index == 0 or depth < 3:
            score = -Negamax(board, depth - 1, -beta, -alpha, ply + 1)
        else:
            if lmr_reduction > 0:
                ctx.lmr_count += 1
                ctx.lmr_applied += 1
                reduced_depth = max(0, depth - 1 - lmr_reduction)
                score = -Negamax(board, reduced_depth, -alpha - 1, -alpha, ply + 1)
                if alpha < score < beta:
                    ctx.lmr_researches += 1
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
        
    _Store_TT_Entry(key, depth, best_score, flag, best_move, ply)

    t1 = time.perf_counter()
    ctx.minimax_time += t1 - t0
    return best_score

def Quiescence_Search(board: Board, alpha: float, beta: float, ply: int) -> float:
    if _Search_Should_Stop():
        return Evaluate_Node(board, caller="qsearch")

    ctx.quiescence_nodes += 1
    if ply > ctx.max_seldepth:
        ctx.max_seldepth = ply
    t0 = time.perf_counter()
    if board.Is_Threefold_Repetition() or board.Is_Fifty_Move_Rule():
        t1 = time.perf_counter()
        ctx.quiescence_time += t1 - t0
        return 0.0

    qratio = _Current_QRatio()
    qnode_budget = min(50000, max(6000, ctx.nodes_searched * 4))
    if ctx.quiescence_nodes > qnode_budget:
        t1 = time.perf_counter()
        ctx.quiescence_time += t1 - t0
        static_score = static_eval(board, caller="qsearch")
        return static_score if board.white_to_move else -static_score

    if qratio > 3.5 and ply >= 1:
        t1 = time.perf_counter()
        ctx.quiescence_time += t1 - t0
        static_score = static_eval(board, caller="qsearch")
        return static_score if board.white_to_move else -static_score

    in_check = board.Is_King_In_Check(board.white_to_move)
    if in_check:
        stand_pat = None
        noisy_moves = board.Generate_Legal_Moves(include_castling=False)
        if not noisy_moves:
            t1 = time.perf_counter()
            ctx.quiescence_time += t1 - t0
            return Terminal_Score(board, ply)
    else:
        stand_pat = static_eval(board, caller="qsearch")
        if not board.white_to_move:
            stand_pat = -stand_pat

        if stand_pat >= beta:
            t1 = time.perf_counter()
            ctx.quiescence_time += t1 - t0
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

        if ply >= Q_DEPTH_LIMIT:
            t1 = time.perf_counter()
            ctx.quiescence_time += t1 - t0
            return stand_pat

        noisy_moves = board.Generate_Legal_Capture_Moves()

    Order_Quiescence_Moves(board, noisy_moves)

    for move in noisy_moves:
        if not in_check:
            ctx.qsearch_noisy_considered += 1
            should_search, risky_capture = _Should_Search_QCapture(board, move, qratio)
            if not should_search:
                ctx.qsearch_noisy_rejected += 1
                continue

            captured_val = ABS_PIECE_VALUES.get(move.piece_captured or "", 0)
            promotion_gain = 775 if move.is_pawn_promotion else 0
            delta_margin = _Quiescence_Delta_Margin(move, qratio)
            if risky_capture:
                delta_margin = max(0, delta_margin - 20)
            if alpha < (MATE_SCORE - 500) and stand_pat + captured_val + promotion_gain + delta_margin < alpha:
                ctx.qsearch_noisy_rejected += 1
                continue
        else:
            ctx.qsearch_noisy_considered += 1

        if not board.Make_Move(move):
            ctx.qsearch_noisy_rejected += 1
            continue
        ctx.qsearch_noisy_accepted += 1

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
    if move.piece_captured or move.is_pawn_promotion:
        return _Capture_Order_Score(move)
    
    if depth in ctx.killer_moves and move in ctx.killer_moves[depth]:
        index = ctx.killer_moves[depth].index(move)
        return 9000 - (index * 400) + (CHECK_MOVE_BONUS if move.gives_check else 0)
    
    key = (move.start, move.end)
    return 4000 + ctx.history_heuristic.get(key, 0) + (CHECK_MOVE_BONUS if move.gives_check else 0)


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
    window_size = 60

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

    def search_root_window(depth: int, alpha: float, beta: float) -> tuple[Move | None, float, bool]:
        legal_moves = board.Generate_Legal_Moves()
        if not legal_moves:
            return None, Terminal_Score(board, 0), True

        root_entry = ctx.transposition_table.get(board.Hash_Board())
        tt_move = root_entry.move if root_entry is not None else None
        Order_Moves(board, legal_moves, depth, tt_move=tt_move)
        _Prioritize_Root_Move(legal_moves, ctx.root_pv_move)

        best_score = float('-inf')
        best_move = None

        for move_index, move in enumerate(legal_moves):
            if root_should_stop():
                return None, best_score, False

            if not board.Make_Move(move):
                continue

            if move_index == 0 or depth < 3:
                score = -Negamax(board, depth - 1, -beta, -alpha, 1)
            else:
                score = -Negamax(board, depth - 1, -alpha - 1, -alpha, 1)
                if alpha < score < beta:
                    score = -Negamax(board, depth - 1, -beta, -alpha, 1)
            board.Undo_Move()

            if root_should_stop():
                return None, best_score, False

            if score > best_score:
                best_score = score
                best_move = move

            if score > alpha:
                alpha = score

            if alpha >= beta:
                break

        return best_move, best_score, True

    for current_depth in range(1, max_depth + 1):
        if root_should_stop():
            break

        if current_depth == 1:
            alpha = float('-inf')
            beta = float('inf')
        else:
            alpha = guess - window_size
            beta = guess + window_size

        window = window_size
        iteration_best_move = None
        iteration_best_score = float('-inf')
        iteration_complete = False

        while True:
            if root_should_stop():
                break

            best_move, best_score, completed = search_root_window(current_depth, alpha, beta)
            if not completed:
                break

            if best_move is None:
                elapsed = time.perf_counter() - start_time
                ctx.total_time_taken = elapsed
                ctx.last_search_depth = 0
                ctx.last_root_score = best_score
                ctx.last_pv = []
                ctx.search_deadline = None
                ctx.stop_checker = None
                return None

            iteration_best_move = best_move
            iteration_best_score = best_score

            if best_score <= alpha:
                ctx.aspiration_fail_lows += 1
                ctx.aspiration_window_expansions += 1
                window *= 2
                if window >= 4000:
                    alpha = float('-inf')
                    beta = float('inf')
                else:
                    alpha = guess - window
                    beta = guess + window
            elif best_score >= beta:
                ctx.aspiration_fail_highs += 1
                ctx.aspiration_window_expansions += 1
                window *= 2
                if window >= 4000:
                    alpha = float('-inf')
                    beta = float('inf')
                else:
                    alpha = guess - window
                    beta = guess + window
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
        window_size = 50 if abs(completed_score) < MATE_TT_THRESHOLD else 200

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
    ctx.eval_cache.clear()


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
            "nps={nps} lmr={lmr_a}/{lmr_r} qrej={qrej} evals={evals} asp={fl}/{fh}/{exp} pv={pv}".format(
                nodes=ctx.nodes_searched,
                qnodes=ctx.quiescence_nodes,
                hits=ctx.transposition_hits,
                cuts=ctx.transposition_cutoffs,
                depth=ctx.last_search_depth,
                seldepth=ctx.max_seldepth,
                score=score_text,
                time_s=ctx.total_time_taken,
                nps=stats["nps"],
                lmr_a=ctx.lmr_applied,
                lmr_r=ctx.lmr_researches,
                qrej=ctx.qsearch_noisy_rejected,
                evals=ctx.total_eval_calls,
                fl=ctx.aspiration_fail_lows,
                fh=ctx.aspiration_fail_highs,
                exp=ctx.aspiration_window_expansions,
                pv=pv_text,
            )
        )

    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    q_ratio = (ctx.quiescence_nodes / max(1, ctx.nodes_searched))
    line = (
        f"[{timestamp}] fen={fen} best={best_move_uci} depth={ctx.last_search_depth} "
        f"seldepth={ctx.max_seldepth} score={score_text} pv=\"{pv_text}\" "
        f"nodes={ctx.nodes_searched} qnodes={ctx.quiescence_nodes} qratio={q_ratio:.2f} total_nodes={stats['total_nodes']} "
        f"nps={stats['nps']} time_ms={stats['time_ms']} tt_hits={ctx.transposition_hits} "
        f"tt_cutoffs={ctx.transposition_cutoffs} hashfull={Get_Hashfull_Permill()} "
        f"eval_calls={ctx.total_eval_calls} static_eval_calls={ctx.static_eval_calls} full_eval_calls={ctx.full_eval_calls} "
        f"qsearch_eval_calls={ctx.qsearch_eval_calls} main_eval_calls={ctx.main_search_eval_calls} "
        f"avg_eval_us={stats['avg_eval_time_us']:.1f} "
        f"lmr_candidates={ctx.lmr_candidates} lmr_applied={ctx.lmr_applied} lmr_researches={ctx.lmr_researches} "
        f"qsearch_noisy_considered={ctx.qsearch_noisy_considered} qsearch_noisy_accepted={ctx.qsearch_noisy_accepted} "
        f"qsearch_noisy_rejected={ctx.qsearch_noisy_rejected} "
        f"asp_fail_low={ctx.aspiration_fail_lows} asp_fail_high={ctx.aspiration_fail_highs} "
        f"asp_expands={ctx.aspiration_window_expansions} "
        f"t_minimax={ctx.minimax_time:.3f} t_qsearch={ctx.quiescence_time:.3f} t_eval={ctx.evaluate_position_time:.3f}"
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
