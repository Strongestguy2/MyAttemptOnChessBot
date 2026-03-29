from dataclasses import dataclass, field
from typing import Optional

import Engine
from Board import Board


@dataclass
class SearchConfig:
    name: str
    depth: Optional[int] = None
    time_limit: Optional[float] = None


@dataclass
class SideMetrics:
    moves: int = 0
    nodes: int = 0
    qnodes: int = 0
    time_s: float = 0.0


@dataclass
class MatchResult:
    wins: int = 0
    losses: int = 0
    draws: int = 0
    white_metrics: SideMetrics = field(default_factory=SideMetrics)
    black_metrics: SideMetrics = field(default_factory=SideMetrics)


OPENINGS = [
    Board.START_FEN,
    "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 2 3",
    "rnbqkbnr/pppp1ppp/8/4p3/3PP3/8/PPP2PPP/RNBQKBNR b KQkq - 0 2",
    "r2qk2r/pp2bppp/2n2n2/2bp4/2B5/2NP1NP1/PPP2PBP/R1BQ1RK1 w kq - 2 9",
]


def _make_engine_move(board: Board, cfg: SearchConfig):
    depth = cfg.depth if cfg.depth is not None else 64
    return Engine.Find_Best_Move(board, max_depth=depth, time_limit=cfg.time_limit)


def _game_outcome(board: Board) -> str:
    legal = board.Generate_Legal_Moves()
    if legal:
        return "ongoing"
    if board.Is_King_In_Check(board.white_to_move):
        return "black" if board.white_to_move else "white"
    return "draw"


def _play_game(
    fen: str,
    white_cfg: SearchConfig,
    black_cfg: SearchConfig,
    max_plies: int = 160,
    clear_tt_before_game: bool = True,
) -> tuple[str, SideMetrics, SideMetrics]:
    board = Board()
    board.Load_FEN(fen)

    if clear_tt_before_game:
        Engine.Clear_Transposition_Table()

    white_m = SideMetrics()
    black_m = SideMetrics()

    for _ in range(max_plies):
        if board.Is_Fifty_Move_Rule() or board.Is_Threefold_Repetition():
            return "draw", white_m, black_m

        state = _game_outcome(board)
        if state != "ongoing":
            return state, white_m, black_m

        side_is_white = board.white_to_move
        cfg = white_cfg if side_is_white else black_cfg
        move = _make_engine_move(board, cfg)
        if move is None:
            return _game_outcome(board), white_m, black_m

        legal_moves = board.Generate_Legal_Moves()
        if not any(m == move or m.To_UCI() == move.To_UCI() for m in legal_moves):
            return "draw", white_m, black_m

        stats = Engine.Get_Search_Stats()
        target = white_m if side_is_white else black_m
        target.moves += 1
        target.nodes += stats["nodes"]
        target.qnodes += stats["qnodes"]
        target.time_s += stats["time_s"]

        if not board.Make_Move(move):
            return "draw", white_m, black_m

    return "draw", white_m, black_m


def _merge_metrics(dst: SideMetrics, src: SideMetrics):
    dst.moves += src.moves
    dst.nodes += src.nodes
    dst.qnodes += src.qnodes
    dst.time_s += src.time_s


def run_match(
    current_cfg: SearchConfig,
    baseline_cfg: SearchConfig,
    openings: list[str],
    games_per_opening: int = 4,
    max_plies: int = 160,
) -> MatchResult:
    result = MatchResult(white_metrics=SideMetrics(), black_metrics=SideMetrics())

    for fen in openings:
        for game_index in range(games_per_opening):
            current_is_white = (game_index % 2 == 0)
            white_cfg = current_cfg if current_is_white else baseline_cfg
            black_cfg = baseline_cfg if current_is_white else current_cfg

            outcome, w_m, b_m = _play_game(
                fen,
                white_cfg,
                black_cfg,
                max_plies=max_plies,
                clear_tt_before_game=True,
            )

            _merge_metrics(result.white_metrics, w_m)
            _merge_metrics(result.black_metrics, b_m)

            if current_is_white:
                if outcome == "white":
                    result.wins += 1
                elif outcome == "black":
                    result.losses += 1
                else:
                    result.draws += 1
            else:
                if outcome == "black":
                    result.wins += 1
                elif outcome == "white":
                    result.losses += 1
                else:
                    result.draws += 1

    return result


def _avg(value: float, count: int) -> float:
    return (value / count) if count > 0 else 0.0


def print_match_report(title: str, result: MatchResult):
    total_games = result.wins + result.losses + result.draws
    white_moves = result.white_metrics.moves
    black_moves = result.black_metrics.moves

    print(f"=== {title} ===")
    print(f"Games: {total_games}")
    print(f"W/D/L: {result.wins}/{result.draws}/{result.losses}")
    print(
        "As White: moves={} avg_nodes/move={:.0f} avg_qnodes/move={:.0f} avg_time_ms/move={:.1f}".format(
            white_moves,
            _avg(result.white_metrics.nodes, white_moves),
            _avg(result.white_metrics.qnodes, white_moves),
            _avg(result.white_metrics.time_s * 1000.0, white_moves),
        )
    )
    print(
        "As Black: moves={} avg_nodes/move={:.0f} avg_qnodes/move={:.0f} avg_time_ms/move={:.1f}".format(
            black_moves,
            _avg(result.black_metrics.nodes, black_moves),
            _avg(result.black_metrics.qnodes, black_moves),
            _avg(result.black_metrics.time_s * 1000.0, black_moves),
        )
    )


def run_default_suite():
    Engine.Toggle_Logging(False)

    depth_current = SearchConfig(name="current-depth4", depth=4)
    depth_baseline = SearchConfig(name="baseline-depth3", depth=3)
    depth_match = run_match(depth_current, depth_baseline, OPENINGS, games_per_opening=4, max_plies=140)
    print_match_report("Depth Match (4 vs 3)", depth_match)

    time_current = SearchConfig(name="current-0.30s", depth=64, time_limit=0.30)
    time_baseline = SearchConfig(name="baseline-0.20s", depth=64, time_limit=0.20)
    time_match = run_match(time_current, time_baseline, OPENINGS, games_per_opening=4, max_plies=140)
    print_match_report("Time Match (300ms vs 200ms)", time_match)


if __name__ == "__main__":
    run_default_suite()
