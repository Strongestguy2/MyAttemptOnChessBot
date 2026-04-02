import random
from dataclasses import dataclass
from typing import Callable

import Engine
from Board import Board


@dataclass
class MatchStats:
    wins: int = 0
    losses: int = 0
    draws: int = 0


def _material_value(piece: str) -> int:
    values = {
        "P": 100,
        "N": 300,
        "B": 300,
        "R": 500,
        "Q": 900,
        "K": 0,
    }
    return values.get(piece.upper(), 0)


def _random_policy(board: Board, _depth: int) -> object:
    legal = board.Generate_Legal_Moves()
    if not legal:
        return None
    return random.choice(legal)


def _material_only_policy(board: Board, _depth: int) -> object:
    legal = board.Generate_Legal_Moves()
    if not legal:
        return None

    best = None
    best_gain = -10**9
    for move in legal:
        gain = _material_value(move.piece_captured) if move.piece_captured else 0
        if gain > best_gain:
            best_gain = gain
            best = move
    return best


def _engine_policy(board: Board, depth: int) -> object:
    return Engine.Find_Best_Move(board, depth)


def _game_result(board: Board) -> str:
    result, _ = board.Get_Game_Result()
    return result


def _play_single_game(
    start_fen: str,
    white_policy: Callable[[Board, int], object],
    black_policy: Callable[[Board, int], object],
    white_depth: int,
    black_depth: int,
    max_plies: int = 80,
    clear_tt_before_game: bool = True,
) -> str:
    board = Board()
    board.Load_FEN(start_fen)

    if clear_tt_before_game:
        Engine.Clear_Transposition_Table()

    for _ in range(max_plies):
        if board.Is_Fifty_Move_Rule() or board.Is_Threefold_Repetition():
            return "draw"

        result = _game_result(board)
        if result != "ongoing":
            return result

        if board.white_to_move:
            move = white_policy(board, white_depth)
        else:
            move = black_policy(board, black_depth)

        if move is None:
            return _game_result(board)

        legal_moves = board.Generate_Legal_Moves()
        if not any(m == move or m.To_UCI() == move.To_UCI() for m in legal_moves):
            return "draw"

        if not board.Make_Move(move):
            return "draw"

    return "draw"


def _run_match_block(
    name: str,
    openings: list[str],
    games_per_opening: int,
    current_is_white: bool,
    opponent_policy: Callable[[Board, int], object],
    current_depth: int,
    baseline_depth: int,
    max_plies: int,
    clear_tt_before_game: bool,
) -> tuple[MatchStats, list[str]]:
    stats = MatchStats()
    lines = [f"[{name}] current_as={'white' if current_is_white else 'black'}"]

    for opening_index, fen in enumerate(openings):
        for game_index in range(games_per_opening):
            if current_is_white:
                result = _play_single_game(
                    fen,
                    _engine_policy,
                    opponent_policy,
                    current_depth,
                    baseline_depth,
                    max_plies,
                    clear_tt_before_game,
                )
                current_score_result = result
            else:
                result = _play_single_game(
                    fen,
                    opponent_policy,
                    _engine_policy,
                    baseline_depth,
                    current_depth,
                    max_plies,
                    clear_tt_before_game,
                )
                if result == "black":
                    current_score_result = "white"
                elif result == "white":
                    current_score_result = "black"
                else:
                    current_score_result = "draw"

            if current_score_result == "white":
                stats.wins += 1
                label = "W"
            elif current_score_result == "black":
                stats.losses += 1
                label = "L"
            else:
                stats.draws += 1
                label = "D"

            lines.append(
                f"  opening#{opening_index + 1} game#{game_index + 1}: {label}"
            )

    lines.append(f"  summary W/L/D = {stats.wins}/{stats.losses}/{stats.draws}")
    return stats, lines


def run_structured_games(
    current_depth: int = 4,
    games_per_opening: int = 2,
    max_plies: int = 80,
    clear_tt_before_game: bool = True,
) -> bool:
    random.seed(42)
    Engine.Toggle_Logging(False)
    previous_verbose = Engine.VERBOSE_SEARCH
    Engine.VERBOSE_SEARCH = False

    openings = [
        Board.START_FEN,
        "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 2 3",
        "rnbqkbnr/pppp1ppp/8/4p3/3PP3/8/PPP2PPP/RNBQKBNR b KQkq - 0 2",
    ]

    all_lines = ["=== Structured Games ==="]
    all_ok = True

    blocks = [
        ("current-vs-random", _random_policy, 1),
        ("current-vs-material-only", _material_only_policy, 1),
        ("current-vs-baseline-depth2", _engine_policy, 2),
    ]

    for name, opponent_policy, baseline_depth in blocks:
        white_stats, white_lines = _run_match_block(
            name,
            openings,
            games_per_opening,
            True,
            opponent_policy,
            current_depth,
            baseline_depth,
            max_plies,
            clear_tt_before_game,
        )
        black_stats, black_lines = _run_match_block(
            name,
            openings,
            games_per_opening,
            False,
            opponent_policy,
            current_depth,
            baseline_depth,
            max_plies,
            clear_tt_before_game,
        )

        total_w = white_stats.wins + black_stats.wins
        total_l = white_stats.losses + black_stats.losses
        total_d = white_stats.draws + black_stats.draws

        all_lines.extend(white_lines)
        all_lines.extend(black_lines)
        all_lines.append(f"[{name}] total W/L/D = {total_w}/{total_l}/{total_d}")
        all_ok = all_ok and (total_w >= total_l)

    print("\n".join(all_lines))
    print("\n=== Structured Summary ===")
    print(f"overall={'PASS' if all_ok else 'FAIL'}")
    Engine.VERBOSE_SEARCH = previous_verbose
    return all_ok


if __name__ == "__main__":
    ok = run_structured_games(current_depth=4, games_per_opening=2, max_plies=80)
    raise SystemExit(0 if ok else 1)
