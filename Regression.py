import time
import random
import tkinter as tk
from tkinter import TclError, messagebox
from dataclasses import dataclass
from typing import List

import Engine
from Board import Board
from ChessUI import ChessUI


@dataclass
class PerftCase:
    name: str
    fen: str
    depths: dict


@dataclass
class TacticCase:
    name: str
    fen: str
    depth: int
    expected_moves_uci: List[str]
    expect_checkmate: bool = False


def coord_to_square(coord: tuple[int, int]) -> str:
    row, col = coord
    return f"{chr(ord('a') + col)}{8 - row}"


def move_to_uci(move) -> str:
    if move is None:
        return "none"
    promo = ""
    if move.is_pawn_promotion:
        choice = (move.promotion_choice or "q").lower()
        promo = choice
    return f"{coord_to_square(move.start)}{coord_to_square(move.end)}{promo}"


def perft(board: Board, depth: int) -> int:
    if depth == 0:
        return 1
    moves = board.Generate_Legal_Moves()
    if depth == 1:
        return len(moves)

    nodes = 0
    for move in moves:
        if not board.Make_Move(move):
            continue
        nodes += perft(board, depth - 1)
        board.Undo_Move()
    return nodes


def run_perft_suite() -> tuple[bool, str]:
    cases = [
        PerftCase(
            name="startpos",
            fen=Board.START_FEN,
            depths={1: 20, 2: 400, 3: 8902, 4: 197281},
        ),
        PerftCase(
            name="kiwipete",
            fen="r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
            depths={1: 48, 2: 2039, 3: 97862},
        ),
        PerftCase(
            name="ep-and-pins",
            fen="8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
            depths={1: 14, 2: 191, 3: 2812},
        ),
    ]

    all_ok = True
    lines = ["=== Perft Suite ==="]

    for case in cases:
        board = Board()
        board.Load_FEN(case.fen)
        lines.append(f"[{case.name}]")
        for depth, expected in sorted(case.depths.items()):
            t0 = time.perf_counter()
            got = perft(board, depth)
            elapsed = time.perf_counter() - t0
            ok = got == expected
            all_ok = all_ok and ok
            status = "PASS" if ok else "FAIL"
            lines.append(
                f"  d{depth}: {status} expected={expected} got={got} time={elapsed:.3f}s"
            )

    return all_ok, "\n".join(lines)


def run_tactic_suite() -> tuple[bool, str]:
    # Fixed tactical smoke tests: mate, hanging pieces, forks, and simple combos.
    cases = [
        TacticCase(
            name="mate-in-1-queen",
            fen="6k1/5Q2/6K1/8/8/8/8/8 w - - 0 1",
            depth=3,
            expected_moves_uci=["f7g7", "f7f8", "f7e8"],
            expect_checkmate=True,
        ),
        TacticCase(
            name="mate-in-2-pattern",
            fen="6k1/5ppp/6q1/8/8/6Q1/5PPP/6K1 w - - 0 1",
            depth=4,
            expected_moves_uci=["g3b8", "g3b3", "g3b8"],
            expect_checkmate=False,
        ),
        TacticCase(
            name="win-hanging-queen",
            fen="4k3/8/8/3q4/4Q3/8/8/4K3 w - - 0 1",
            depth=3,
            expected_moves_uci=["e4d5"],
            expect_checkmate=False,
        ),
        TacticCase(
            name="knight-fork",
            fen="6k1/5ppp/8/8/3n4/5N2/5PPP/3Q2K1 w - - 0 1",
            depth=3,
            expected_moves_uci=["f3d4", "d1d4"],
            expect_checkmate=False,
        ),
        TacticCase(
            name="simple-combination",
            fen="r3k2r/ppp2ppp/2n5/3q4/3P4/2N1Q3/PPP2PPP/R3K2R w KQkq - 0 1",
            depth=3,
            expected_moves_uci=["e3e8", "c3d5"],
            expect_checkmate=False,
        ),
    ]

    all_ok = True
    lines = ["=== Tactics Suite ==="]
    Engine.Toggle_Logging(False)

    def move_is_checkmate(board: Board, move) -> bool:
        if move is None:
            return False
        if not board.Make_Move(move):
            return False
        legal = board.Generate_Legal_Moves()
        in_check = board.Is_King_In_Check(board.white_to_move)
        board.Undo_Move()
        return len(legal) == 0 and in_check

    for case in cases:
        board = Board()
        board.Load_FEN(case.fen)
        best = Engine.Find_Best_Move(board, case.depth)
        uci = move_to_uci(best)
        in_expected = uci in case.expected_moves_uci
        is_mate = move_is_checkmate(board, best)
        ok = is_mate if case.expect_checkmate else in_expected
        all_ok = all_ok and ok
        status = "PASS" if ok else "FAIL"
        lines.append(
            f"[{case.name}] {status} depth={case.depth} best={uci} expected={case.expected_moves_uci} checkmate={is_mate}"
        )

    return all_ok, "\n".join(lines)


def run_benchmark(depth: int = 4) -> tuple[bool, str]:
    positions = [
        ("startpos", Board.START_FEN),
        ("open-center", "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 2 3"),
        ("quiet-endgame", "8/2k5/3p4/3P4/8/2K5/8/8 w - - 0 1"),
    ]

    Engine.Toggle_Logging(False)

    lines = ["=== Benchmark ===", f"depth={depth}"]
    all_ok = True

    for name, fen in positions:
        board = Board()
        board.Load_FEN(fen)

        t0 = time.perf_counter()
        best = Engine.Find_Best_Move(board, depth)
        elapsed = time.perf_counter() - t0

        ok = best is not None
        all_ok = all_ok and ok
        lines.append(
            f"[{name}] best={move_to_uci(best)} score_cp={Engine.LAST_ROOT_SCORE:+.0f} "
            f"nodes={Engine.NODES_SEARCHED} time={elapsed:.3f}s "
            f"nps={(int(Engine.NODES_SEARCHED / elapsed) if elapsed > 0 else 0)}"
        )

    return all_ok, "\n".join(lines)


def _board_signature(board: Board):
    return (
        tuple(tuple(row) for row in board.board),
        board.white_to_move,
        tuple(sorted(board.castling_rights)),
        board.en_passant_square,
        board.halfmove_clock,
        board.fullmove_number,
        board.white_king_pos,
        board.black_king_pos,
    )


def run_consistency_suite(seed: int = 42, steps: int = 300) -> tuple[bool, str]:
    rng = random.Random(seed)
    lines = ["=== Consistency Suite ==="]
    all_ok = True

    board = Board()
    saved_states = []
    for _ in range(steps):
        legal_moves = board.Generate_Legal_Moves()
        if not legal_moves:
            break
        move = rng.choice(legal_moves)
        saved_states.append((_board_signature(board), board.Hash_Board()))
        if not board.Make_Move(move):
            all_ok = False
            lines.append("[make-undo] FAIL make returned False")
            break

    while saved_states and all_ok:
        expected_sig, expected_hash = saved_states.pop()
        board.Undo_Move()
        if _board_signature(board) != expected_sig or board.Hash_Board() != expected_hash:
            all_ok = False
            lines.append("[make-undo] FAIL board/hash mismatch after undo")
            break

    if all_ok:
        lines.append("[make-undo] PASS")

    isolation_board = Board()
    original_sig = _board_signature(isolation_board)
    original_hash = isolation_board.Hash_Board()
    clone = isolation_board.Copy_For_Color(isolation_board.white_to_move)
    clone_moves = clone.Generate_Legal_Moves()
    if clone_moves:
        clone.Make_Move(clone_moves[0])
    unchanged = _board_signature(isolation_board) == original_sig and isolation_board.Hash_Board() == original_hash
    if unchanged:
        lines.append("[copy-isolation] PASS")
    else:
        all_ok = False
        lines.append("[copy-isolation] FAIL source board changed after clone move")

    return all_ok, "\n".join(lines)


def run_terminal_state_suite() -> tuple[bool, str]:
    lines = ["=== Terminal State Suite ==="]
    all_ok = True

    cases = [
        ("checkmate", "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1", "white", "checkmate"),
        ("stalemate", "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", "draw", "stalemate"),
        ("fifty-move", "8/8/8/8/8/8/2k5/2K5 w - - 100 1", "draw", "fifty_move_rule"),
    ]

    for name, fen, expected_result, expected_reason in cases:
        board = Board()
        board.Load_FEN(fen)
        result, reason = board.Get_Game_Result()
        ok = result == expected_result and reason == expected_reason
        all_ok = all_ok and ok
        lines.append(
            f"[{name}] {'PASS' if ok else 'FAIL'} result={result} reason={reason} expected=({expected_result}, {expected_reason})"
        )

    repetition_board = Board()
    repetition_board.position_history[repetition_board.Hash_Board()] = 3
    result, reason = repetition_board.Get_Game_Result()
    repetition_ok = result == "draw" and reason == "threefold_repetition"
    all_ok = all_ok and repetition_ok
    lines.append(
        f"[threefold] {'PASS' if repetition_ok else 'FAIL'} result={result} reason={reason} expected=(draw, threefold_repetition)"
    )

    return all_ok, "\n".join(lines)


def run_tt_mate_suite() -> tuple[bool, str]:
    lines = ["=== TT Mate Suite ==="]
    all_ok = True

    cases = [
        (Engine.MATE_SCORE - 3, 1),
        (Engine.MATE_SCORE - 7, 4),
        (-(Engine.MATE_SCORE - 5), 2),
        (-(Engine.MATE_SCORE - 11), 6),
        (42, 3),
    ]

    for score, ply in cases:
        stored = Engine._Score_To_TT(score, ply)
        restored = Engine._Score_From_TT(stored, ply)
        ok = restored == score
        all_ok = all_ok and ok
        lines.append(
            f"[score={score} ply={ply}] {'PASS' if ok else 'FAIL'} stored={stored} restored={restored}"
        )

    return all_ok, "\n".join(lines)


def run_ui_state_suite() -> tuple[bool, str]:
    lines = ["=== UI State Suite ==="]

    try:
        root = tk.Tk()
        root.withdraw()
    except TclError as exc:
        lines.append(f"[ui-init] SKIP {exc}")
        return True, "\n".join(lines)

    original_showinfo = messagebox.showinfo
    shown_messages = []

    def fake_showinfo(title, text):
        shown_messages.append((title, text))

    messagebox.showinfo = fake_showinfo

    try:
        ui = ChessUI(root)
        ui.root.after_cancel(ui.root.after(1, lambda: None))

        mate_fen = "7k/6Q1/6K1/8/8/8/8/8 b - - 0 1"
        ui.board.Load_FEN(mate_fen)
        ui.Refresh_Eval_Cache()
        ui.Check_Endgame()
        ui.Check_Endgame()
        popup_ok = len(shown_messages) == 1 and ui.game_over
        lines.append(f"[single-popup] {'PASS' if popup_ok else 'FAIL'} popups={len(shown_messages)} game_over={ui.game_over}")

        ui.Restart()
        restart_ok = (not ui.game_over) and ui.game_result_latch is None
        ui.board.Load_FEN(mate_fen)
        ui.Refresh_Eval_Cache()
        ui.Check_Endgame()
        restart_latch_ok = len(shown_messages) == 2
        restart_ok = restart_ok and restart_latch_ok
        lines.append(f"[restart-reset] {'PASS' if restart_ok else 'FAIL'} popups={len(shown_messages)} latch={ui.game_result_latch is not None}")

        ui.Restart()
        legal = ui.board.Generate_Legal_Moves()
        if legal:
            ui.board.Make_Move(legal[0])
        ui.game_over = True
        ui.game_result_latch = ("latched", "draw", "stalemate")
        ui.Undo()
        undo_ok = (not ui.game_over) and ui.game_result_latch is None
        lines.append(f"[undo-reset] {'PASS' if undo_ok else 'FAIL'}")

        all_ok = popup_ok and restart_ok and undo_ok
        return all_ok, "\n".join(lines)
    finally:
        messagebox.showinfo = original_showinfo
        root.destroy()


def run_search_stability_suite(depth: int = 4, repeats: int = 2) -> tuple[bool, str]:
    positions = [
        ("startpos", Board.START_FEN),
        ("open-center", "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 2 3"),
        ("sharp-center", "r1bqkb1r/pppp1ppp/2n2n2/1B2p3/4P3/2N2N2/PPPP1PPP/R1BQK2R b KQkq - 1 4"),
        ("quiet-endgame", "8/2k5/3p4/3P4/8/2K5/8/8 w - - 0 1"),
    ]

    all_ok = True
    lines = ["=== Search Stability Suite ===", f"depth={depth} repeats={repeats}"]

    for name, fen in positions:
        times_ms = []
        qratios = []
        nps_values = []
        got_move = True

        for _ in range(repeats):
            board = Board()
            board.Load_FEN(fen)
            best = Engine.Find_Best_Move(board, depth)
            stats = Engine.Get_Search_Stats()
            if best is None:
                got_move = False
                break
            times_ms.append(stats["time_ms"])
            qratios.append(stats.get("qratio", 0.0))
            nps_values.append(stats["nps"])

        if not got_move:
            all_ok = False
            lines.append(f"[{name}] FAIL bestmove=none")
            continue

        avg_time = sum(times_ms) / len(times_ms)
        min_time = min(times_ms)
        max_time = max(times_ms)
        avg_qratio = sum(qratios) / len(qratios)
        max_qratio = max(qratios)
        avg_nps = sum(nps_values) / len(nps_values)

        if max_qratio > 6.0:
            all_ok = False

        lines.append(
            "[{name}] avg_time_ms={avg_time:.1f} min_time_ms={min_time} max_time_ms={max_time} "
            "avg_qratio={avg_qratio:.2f} max_qratio={max_qratio:.2f} avg_nps={avg_nps:.0f}".format(
                name=name,
                avg_time=avg_time,
                min_time=min_time,
                max_time=max_time,
                avg_qratio=avg_qratio,
                max_qratio=max_qratio,
                avg_nps=avg_nps,
            )
        )

    return all_ok, "\n".join(lines)


def run_full_regression(depth: int = 4) -> bool:
    previous_verbose = Engine.VERBOSE_SEARCH
    Engine.VERBOSE_SEARCH = False
    try:
        results = []

        perft_ok, perft_report = run_perft_suite()
        results.append((perft_ok, perft_report))

        tactics_ok, tactics_report = run_tactic_suite()
        results.append((tactics_ok, tactics_report))

        bench_depths = [3] if depth <= 3 else [3, depth]
        for bench_depth in bench_depths:
            bench_ok, bench_report = run_benchmark(bench_depth)
            results.append((bench_ok, bench_report))

        consistency_ok, consistency_report = run_consistency_suite()
        results.append((consistency_ok, consistency_report))

        terminal_ok, terminal_report = run_terminal_state_suite()
        results.append((terminal_ok, terminal_report))

        tt_ok, tt_report = run_tt_mate_suite()
        results.append((tt_ok, tt_report))

        ui_ok, ui_report = run_ui_state_suite()
        results.append((ui_ok, ui_report))

        stability_ok, stability_report = run_search_stability_suite(depth=max(3, depth), repeats=2)
        results.append((stability_ok, stability_report))

        print("\n\n".join(r[1] for r in results))

        all_ok = all(r[0] for r in results)
        print("\n=== Regression Summary ===")
        print(f"overall={'PASS' if all_ok else 'FAIL'}")
        return all_ok
    finally:
        Engine.VERBOSE_SEARCH = previous_verbose


if __name__ == "__main__":
    success = run_full_regression(depth=4)
    raise SystemExit(0 if success else 1)
