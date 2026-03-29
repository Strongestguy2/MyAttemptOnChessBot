import sys
import threading
from Board import Board
from Engine import Find_Best_Move, ctx


def _apply_moves(board: Board, move_tokens: list[str]):
    for mv_str in move_tokens:
        legal_moves = board.Generate_Legal_Moves()
        selected = None
        for mv in legal_moves:
            if mv.To_UCI() == mv_str:
                selected = mv
                break
        if selected is None:
            break
        board.Make_Move(selected)


def _parse_position(parts: list[str], current_board: Board) -> Board:
    if len(parts) < 2:
        return current_board

    if parts[1] == 'startpos':
        board = Board()
        if 'moves' in parts:
            moves_idx = parts.index('moves')
            _apply_moves(board, parts[moves_idx + 1:])
        return board

    if parts[1] == 'fen':
        moves_idx = parts.index('moves') if 'moves' in parts else len(parts)
        fen_tokens = parts[2:moves_idx]
        if len(fen_tokens) >= 6:
            fen = ' '.join(fen_tokens[:6])
            board = Board()
            board.Load_FEN(fen)
            if moves_idx < len(parts):
                _apply_moves(board, parts[moves_idx + 1:])
            return board

    return current_board


def _parse_go(parts: list[str], board: Board) -> tuple[int, float | None, bool]:
    depth = 64
    wtime = btime = winc = binc = movetime = 0
    infinite = False

    i = 1
    while i < len(parts):
        token = parts[i]
        if token == 'wtime' and i + 1 < len(parts):
            wtime = int(parts[i + 1])
            i += 2
            continue
        if token == 'btime' and i + 1 < len(parts):
            btime = int(parts[i + 1])
            i += 2
            continue
        if token == 'winc' and i + 1 < len(parts):
            winc = int(parts[i + 1])
            i += 2
            continue
        if token == 'binc' and i + 1 < len(parts):
            binc = int(parts[i + 1])
            i += 2
            continue
        if token == 'movetime' and i + 1 < len(parts):
            movetime = int(parts[i + 1])
            i += 2
            continue
        if token == 'depth' and i + 1 < len(parts):
            depth = max(1, int(parts[i + 1]))
            i += 2
            continue
        if token == 'infinite':
            infinite = True
            i += 1
            continue
        i += 1

    if infinite:
        return max(depth, 64), None, True

    time_limit = None
    if movetime > 0:
        time_limit = max(0.05, (movetime / 1000.0) * 0.95)
    else:
        if board.white_to_move and wtime > 0:
            time_limit = (wtime / 1000.0) / 40.0 + (winc / 1000.0 * 0.8)
        elif (not board.white_to_move) and btime > 0:
            time_limit = (btime / 1000.0) / 40.0 + (binc / 1000.0 * 0.8)
        if time_limit is not None:
            time_limit = max(0.05, time_limit)

    return depth, time_limit, False

def uci_loop():
    board = Board()
    search_thread = None
    stop_event = threading.Event()

    def stop_search(wait: bool):
        nonlocal search_thread
        if search_thread is not None and search_thread.is_alive():
            stop_event.set()
            if wait:
                search_thread.join()
        search_thread = None
        stop_event.clear()

    def emit_info(depth: int, score: float, pv: list[str], elapsed: float):
        elapsed_ms = max(1, int(elapsed * 1000))
        nodes = ctx.nodes_searched
        nps = int(nodes / elapsed) if elapsed > 0 else 0
        pv_text = f" pv {' '.join(pv)}" if pv else ""
        print(
            f"info depth {depth} score cp {int(round(score))} nodes {nodes} "
            f"time {elapsed_ms} nps {nps}{pv_text}"
        )
        sys.stdout.flush()

    def run_search(local_board: Board, depth: int, time_limit: float | None):
        best_move = Find_Best_Move(
            local_board,
            max_depth=depth,
            time_limit=time_limit,
            stop_checker=stop_event.is_set,
            info_callback=emit_info,
        )
        if best_move:
            print(f'bestmove {best_move.To_UCI()}')
        else:
            print('bestmove 0000')
        sys.stdout.flush()

    while True:
        line = sys.stdin.readline().strip()
        if not line:
            continue

        parts = line.split()
        cmd = parts[0]

        if cmd == 'uci':
            print('id name Chess Bot')
            print('id author Python')
            print('option name Clear Hash type button')
            print('uciok')
            sys.stdout.flush()

        elif cmd == 'isready':
            print('readyok')
            sys.stdout.flush()

        elif cmd == 'ucinewgame':
            stop_search(wait=True)
            ctx.transposition_table.clear()
            board = Board()

        elif cmd == 'setoption':
            joined = ' '.join(parts)
            if 'name Clear Hash' in joined:
                ctx.transposition_table.clear()

        elif cmd == 'position':
            stop_search(wait=True)
            try:
                board = _parse_position(parts, board)
            except Exception:
                board = Board()

        elif cmd == 'go':
            stop_search(wait=True)
            depth, time_limit, _ = _parse_go(parts, board)
            local_board = board.Copy_For_Color(board.white_to_move)
            stop_event.clear()
            search_thread = threading.Thread(target=run_search, args=(local_board, depth, time_limit), daemon=True)
            search_thread.start()

        elif cmd == 'stop':
            stop_search(wait=True)

        elif cmd == 'quit':
            stop_search(wait=True)
            break

if __name__ == '__main__':
    uci_loop()
