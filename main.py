import argparse
import tkinter as tk

import Engine
from Board import Board
from ChessUI import ChessUI
from Regression import run_full_regression
from StructuredGames import run_structured_games


def run_bench(depth: int, repeats: int, detailed_log: bool):
    Engine.Toggle_Logging(True)
    Engine.Toggle_Detailed_Log(detailed_log)

    for index in range(repeats):
        board = Board()
        print(f"\n=== Bench {index + 1}/{repeats} | depth {depth} ===")
        best_move = Engine.Find_Best_Move(board, depth)
        print(f"Best move: {best_move}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench", action="store_true", help="Run a headless engine benchmark instead of the UI.")
    parser.add_argument("--regression", action="store_true", help="Run full regression suite: perft, tactics, benchmark.")
    parser.add_argument("--structured-games", action="store_true", help="Run structured games against random, material-only, and baseline engines.")
    parser.add_argument("--all-tests", action="store_true", help="Run regression and structured games together.")
    parser.add_argument("--depth", type=int, default=4, help="Search depth for bench mode.")
    parser.add_argument("--repeats", type=int, default=1, help="How many bench runs to execute.")
    parser.add_argument("--games-per-opening", type=int, default=2, help="Games per opening in structured games mode.")
    parser.add_argument("--detailed-log", action="store_true", help="Write detailed log entries in bench mode.")
    args = parser.parse_args()

    if args.all_tests:
        reg_ok = run_full_regression(depth=args.depth)
        sg_ok = run_structured_games(current_depth=args.depth, games_per_opening=args.games_per_opening)
        raise SystemExit(0 if (reg_ok and sg_ok) else 1)

    if args.regression:
        ok = run_full_regression(depth=args.depth)
        raise SystemExit(0 if ok else 1)

    if args.structured_games:
        ok = run_structured_games(current_depth=args.depth, games_per_opening=args.games_per_opening)
        raise SystemExit(0 if ok else 1)

    if args.bench:
        run_bench(args.depth, args.repeats, args.detailed_log)
        return

    root = tk.Tk()
    ChessUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
