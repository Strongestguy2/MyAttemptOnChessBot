import tkinter as tk
from tkinter import messagebox
from Board import Board
import Engine
import math

SQUARE_SIZE = 60
BOARD_SIZE = 8
DEFAULT_TEST_DEPTH = 3
QUICK_DEBUG_DEPTH = 2
PIECE_UNICODE = {
    'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
    'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚',
}
class ChessUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Chess Game")
        self.root.resizable(False, False)
        self.board = Board()

        self.white_ai = tk.BooleanVar(value=False)
        self.black_ai = tk.BooleanVar(value=True)
        self.logging_enabled = tk.BooleanVar(value=True)
        self.search_depth = tk.IntVar(value=DEFAULT_TEST_DEPTH)
        self.search_mode = tk.StringVar(value="depth")
        self.move_time_value = tk.DoubleVar(value=1.0)
        self.move_time_unit = tk.StringVar(value="sec")
        self.quick_debug_mode = tk.BooleanVar(value=False)
        self.last_auto_depth = None
        self.ai_is_searching = False
        self.ai_search_token = 0
        self.pending_ai_root_hash = None

        self.selected_square = None
        self.valid_moves = []
        self.last_ai_move = None
        self.game_over = False
        self.game_result_latch = None
        self.current_eval_cp = 0.0

        self.canvas = tk.Canvas(root, width=BOARD_SIZE*SQUARE_SIZE, height=BOARD_SIZE*SQUARE_SIZE)
        self.canvas.grid(row=0, column=1)
        self.canvas.bind("<Button-1>", self.On_Click)

        self.eval_canvas = tk.Canvas(root, width=40, height=BOARD_SIZE*SQUARE_SIZE, bg='white')
        self.eval_canvas.grid(row=0, column=0, sticky="ns")

        self.move_panel = tk.Label(root, text="", font=("Arial", 12), justify=tk.LEFT)
        self.move_panel.grid(row=0, column=2, sticky="nw", padx=10)

        control_frame = tk.Frame(root)
        control_frame.grid(row=1, column=0, columnspan=3)

        tk.Button(control_frame, text="Undo", command=self.Undo).pack(side=tk.LEFT, padx=10)
        tk.Button(control_frame, text="Restart", command=self.Restart).pack(side=tk.LEFT, padx=10)
        tk.Button(control_frame, text="Clear TT", command=self.Clear_TT).pack(side=tk.LEFT, padx=10)

        tk.Checkbutton(control_frame, text="AI controls White", variable=self.white_ai).pack(side=tk.LEFT, padx=10)
        tk.Checkbutton(control_frame, text="AI controls Black", variable=self.black_ai).pack(side=tk.LEFT, padx=10)
        tk.Checkbutton(
            control_frame,
            text="Quick debug (depth 2)",
            variable=self.quick_debug_mode,
        ).pack(side=tk.LEFT, padx=10)

        tk.Label(control_frame, text="Search depth").pack(side=tk.LEFT, padx=(10, 2))
        tk.Spinbox(
            control_frame,
            from_=2,
            to=64,
            width=3,
            textvariable=self.search_depth,
        ).pack(side=tk.LEFT)

        tk.Label(control_frame, text="Mode").pack(side=tk.LEFT, padx=(10, 2))
        tk.OptionMenu(control_frame, self.search_mode, "depth", "time", "auto").pack(side=tk.LEFT)

        tk.Label(control_frame, text="Move time").pack(side=tk.LEFT, padx=(10, 2))
        tk.Entry(control_frame, width=6, textvariable=self.move_time_value).pack(side=tk.LEFT)
        tk.OptionMenu(control_frame, self.move_time_unit, "ms", "sec").pack(side=tk.LEFT)

        tk.Checkbutton(control_frame, text="Enable Logging", variable=self.logging_enabled, 
                       command=self.Toggle_Logging).pack(side=tk.LEFT, padx=10)

        # Keep engine logging state aligned with the UI toggle from startup.
        self.Toggle_Logging()
        self.Refresh_Eval_Cache()

        self.Draw_Board()
        self.Update_Status()
        self.root.after(100, self.Update_Loop)

    def Update_Loop(self):
        if not self.game_over and self.Is_AI_Turn():
            self.Play_AI_Move()

        self.Draw_Board()
        self.Update_Status()
        self.root.after(100, self.Update_Loop)

    def Is_AI_Turn(self):
        return (self.board.white_to_move and self.white_ai.get()) or (not self.board.white_to_move and self.black_ai.get())

    def Play_AI_Move(self):
        if getattr(self, "ai_is_searching", False):
            return
        
        self.ai_is_searching = True
        self.ai_search_token += 1
        search_token = self.ai_search_token
        
        import threading
        
        # Take a snapshot of the board for the background thread to search on
        # to prevent the main UI thread from reading search-corrupted states!
        search_board = self.board.Copy_For_Color(self.board.white_to_move)
        self.pending_ai_root_hash = self.board.Hash_Board()
        
        def ai_worker():
            root_hash = self.pending_ai_root_hash
            depth = QUICK_DEBUG_DEPTH if self.quick_debug_mode.get() else max(DEFAULT_TEST_DEPTH, self.search_depth.get())
            move_time = self.Get_Move_Time_Seconds()
            mode = self.search_mode.get()
            self.last_auto_depth = None

            if mode == "time" and not self.quick_debug_mode.get():
                move = Engine.Find_Best_Move(search_board, max_depth=64, time_limit=move_time)
            elif mode == "auto" and not self.quick_debug_mode.get():
                auto_depth = Engine.Estimate_Auto_Depth(search_board, min_depth=3, max_depth=8, last_time=getattr(self, "last_ai_time", 0.0))
                self.last_auto_depth = auto_depth
                move = Engine.Find_Best_Move(search_board, max_depth=auto_depth)
            else:
                move = Engine.Find_Best_Move(search_board, max_depth=depth)
            
            self.root.after(0, lambda m=move, h=root_hash, token=search_token: self._apply_ai_move(m, h, token))
            
        threading.Thread(target=ai_worker, daemon=True).start()

    def _apply_ai_move(self, move, root_hash, search_token):
        self.ai_is_searching = False

        # Drop stale search results if the board changed while the engine was thinking.
        if search_token != self.ai_search_token or root_hash != self.board.Hash_Board():
            self.pending_ai_root_hash = None
            return

        if move is None:
            self.pending_ai_root_hash = None
            self.Check_Endgame()
            return

        legal_moves = self.board.Generate_Legal_Moves()
        is_legal = any(m == move or m.To_UCI() == move.To_UCI() for m in legal_moves)
        if not is_legal:
            self.pending_ai_root_hash = None
            return

        self.last_ai_time = getattr(Engine.ctx, "total_time_taken", 0.0)
        self.board.Make_Move(move)
        self.last_ai_move = move
        self.pending_ai_root_hash = None
        self.Refresh_Eval_Cache()
        self.Check_Endgame()

    def Update_Status(self):
        side_to_move = "White" if self.board.white_to_move else "Black"
        last_move = self.Format_Move(self.last_ai_move) if self.last_ai_move else "N/A"
        depth = QUICK_DEBUG_DEPTH if self.quick_debug_mode.get() else max(DEFAULT_TEST_DEPTH, self.search_depth.get())
        search_mode = self.search_mode.get()
        time_s = self.Get_Move_Time_Seconds()
        if search_mode == "time":
            mode_line = f"Search mode: time ({time_s:.2f}s/move)"
        elif search_mode == "auto":
            if self.last_auto_depth is None:
                mode_line = "Search mode: auto (dynamic depth)"
            else:
                mode_line = f"Search mode: auto (last depth {self.last_auto_depth})"
        else:
            mode_line = f"Search mode: depth ({depth})"

        self.move_panel.config(
            text=(
                f"Turn: {side_to_move}\n"
                f"Last AI Move: {last_move}\n"
                f"{mode_line}\n"
                f"Nodes searched: {Engine.NODES_SEARCHED:,}"
            )
        )

    def Draw_Board(self):
        self.canvas.delete("all")
        color1, color2 = "#EEEED2", "#769656"
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                x0, y0 = c * SQUARE_SIZE, r * SQUARE_SIZE
                x1, y1 = x0 + SQUARE_SIZE, y0 + SQUARE_SIZE

                color = color1 if (r + c) % 2 == 0 else color2
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")

                piece = self.board.board[r][c]
                if piece != ".":
                    self.canvas.create_text(x0 + SQUARE_SIZE/2, y0 + SQUARE_SIZE/2,
                                            text=PIECE_UNICODE[piece], font=("Arial", 32))

                # File label
                if r == 7:
                    self.canvas.create_text(x0 + 5, y1 - 5, text=chr(c + ord('a')), anchor="sw", font=("Arial", 8))
                # Rank label
                if c == 0:
                    self.canvas.create_text(x0 + 5, y0 + 5, text=str(8 - r), anchor="nw", font=("Arial", 8))

        self.Draw_Eval_Bar()
        self.Draw_Valid_Moves()

    def Draw_Eval_Bar (self):
        self.eval_canvas.delete("all")
        score_cp = self.current_eval_cp
        height = BOARD_SIZE * SQUARE_SIZE

        # Map centipawn score to bar position with smooth saturation.
        # Around +/-300cp still moves noticeably, extreme scores do not clip abruptly.
        normalized = math.tanh(score_cp / 300.0)
        y = height * (1 - (normalized + 1) / 2)
        y = max(0, min(height, y))

        self.eval_canvas.create_rectangle(0, 0, 40, y, fill="black")
        self.eval_canvas.create_rectangle(0, y, 40, height, fill="white")
        self.eval_canvas.create_line(0, y, 40, y, fill="red", width=2)
        self.eval_canvas.create_text(20, height - 10, text=f"{score_cp:+.0f}", font=("Arial", 9))
        self.eval_canvas.create_text(20, 10, text=f"{(score_cp / 100.0):+.2f}", font=("Arial", 9))
    
    def Draw_Valid_Moves (self):
        for move in self.valid_moves:
            r, c = move.end
            x = c * SQUARE_SIZE + SQUARE_SIZE / 2
            y = r * SQUARE_SIZE + SQUARE_SIZE / 2
            radius = 8
            self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill="black", outline="")
    
    def Format_Move(self, move):
        if not move:
            return "N/A"

        piece = PIECE_UNICODE[move.piece_moved]
        start = self.Coord_To_Square(move.start)
        end = self.Coord_To_Square(move.end)
        return f"{piece} {start} to {end}"
    
    def Coord_To_Square (self, coord):
        row, col = coord
        return chr (col + ord('a')) + str (8 - row)
    
    def On_Click(self, event):
        if self.game_over or self.Is_AI_Turn():
            return

        col = event.x // SQUARE_SIZE
        row = event.y // SQUARE_SIZE
        if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
            return

        if self.selected_square is None:
            piece = self.board.board[row][col]
            if piece != "." and piece.isupper() == self.board.white_to_move:
                self.selected_square = (row, col)
                self.valid_moves = [m for m in self.board.Generate_Legal_Moves() if m.start == self.selected_square]
        else:
            for move in self.valid_moves:
                if move.end == (row, col):
                    self.board.Make_Move(move)
                    self.Reset_Selection()
                    self.Refresh_Eval_Cache()
                    self.Check_Endgame()
                    return
            self.Reset_Selection()

    def Reset_Selection (self):
        self.selected_square = None
        self.valid_moves = []

    def Check_Endgame (self):
        result, reason = self.board.Get_Game_Result()
        if result == "ongoing":
            return

        latch = (self.board.Hash_Board(), result, reason)
        if self.game_result_latch == latch:
            self.game_over = True
            return

        self.game_over = True
        self.game_result_latch = latch
        self.pending_ai_root_hash = None

        if reason == "checkmate":
            message = f"{result.capitalize()} wins by checkmate!"
        elif reason == "stalemate":
            message = "Draw by stalemate."
        elif reason == "threefold_repetition":
            message = "Draw by threefold repetition."
        elif reason == "fifty_move_rule":
            message = "Draw by fifty-move rule."
        else:
            message = "It's a draw!"

        self.Refresh_Eval_Cache()
        messagebox.showinfo("Game Over", message)

    def Refresh_Eval_Cache(self):
        result, reason = self.board.Get_Game_Result()
        if reason == "checkmate":
            self.current_eval_cp = -Engine.MATE_SCORE if self.board.white_to_move else Engine.MATE_SCORE
        elif result == "draw":
            self.current_eval_cp = 0.0
        else:
            self.current_eval_cp = Engine.Evaluate_Position(self.board)

    def Undo (self):
        self.ai_search_token += 1
        self.ai_is_searching = False
        self.pending_ai_root_hash = None
        if self.board.move_history:
            self.board.Undo_Move()
            if self.board.move_history and self.Is_AI_Turn() and (self.white_ai.get() != self.black_ai.get()):
                self.board.Undo_Move()
            self.game_over = False
            self.game_result_latch = None
            self.last_ai_move = None
            self.Reset_Selection()
            self.Refresh_Eval_Cache()
            self.Draw_Board()
            self.Update_Status()

    def Restart (self):
        self.ai_search_token += 1
        self.ai_is_searching = False
        self.pending_ai_root_hash = None
        self.board = Board()
        self.game_over = False
        self.game_result_latch = None
        self.last_ai_move = None
        self.Reset_Selection()
        self.Refresh_Eval_Cache()
        self.Draw_Board()
        self.Update_Status()

    def Toggle_Logging(self):
        Engine.Toggle_Logging(self.logging_enabled.get())

    def Get_Move_Time_Seconds(self) -> float:
        try:
            raw_value = max(0.05, float(self.move_time_value.get()))
        except (tk.TclError, ValueError):
            raw_value = 1.0
            self.move_time_value.set(raw_value)
        if self.move_time_unit.get() == "ms":
            return max(0.05, raw_value / 1000.0)
        return raw_value

    def Clear_TT(self):
        Engine.Clear_Transposition_Table()

if __name__ == "__main__":
    root = tk.Tk()
    chess_ui = ChessUI(root)
    root.mainloop()
