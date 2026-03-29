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
        self.quick_debug_mode = tk.BooleanVar(value=False)

        self.selected_square = None
        self.valid_moves = []
        self.last_ai_move = None
        self.game_over = False

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
            to=6,
            width=3,
            textvariable=self.search_depth,
        ).pack(side=tk.LEFT)

        tk.Checkbutton(control_frame, text="Enable Logging", variable=self.logging_enabled, 
                       command=self.Toggle_Logging).pack(side=tk.LEFT, padx=10)

        # Keep engine logging state aligned with the UI toggle from startup.
        self.Toggle_Logging()

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
        depth = QUICK_DEBUG_DEPTH if self.quick_debug_mode.get() else max(DEFAULT_TEST_DEPTH, self.search_depth.get())
        move = Engine.Find_Best_Move(self.board, depth)
        if move is None:
            self.Check_Endgame()
            return

        self.board.Make_Move(move)
        self.last_ai_move = move
        self.Check_Endgame()

    def Update_Status(self):
        side_to_move = "White" if self.board.white_to_move else "Black"
        last_move = self.Format_Move(self.last_ai_move) if self.last_ai_move else "N/A"
        depth = QUICK_DEBUG_DEPTH if self.quick_debug_mode.get() else max(DEFAULT_TEST_DEPTH, self.search_depth.get())
        self.move_panel.config(
            text=(
                f"Turn: {side_to_move}\n"
                f"Last AI Move: {last_move}\n"
                f"Search depth: {depth}\n"
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
        score_cp = Engine.Evaluate_Position(self.board)
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
                    self.Check_Endgame()
                    return
            self.Reset_Selection()

    def Reset_Selection (self):
        self.selected_square = None
        self.valid_moves = []

    def Check_Endgame (self):
        if not self.board.Generate_Legal_Moves():
            winner = "Black" if self.board.white_to_move else "White"
            if self.board.Is_King_In_Check ():
                messagebox.showinfo("Game Over", f"{winner} wins by checkmate!")
            else:
                messagebox.showinfo("Game Over", "It's a draw!")
            self.game_over = True

    def Undo (self):
        if self.board.move_history:
            self.board.Undo_Move()
            if self.board.move_history and self.Is_AI_Turn() and (self.white_ai.get() != self.black_ai.get()):
                self.board.Undo_Move()
            self.game_over = False
            self.last_ai_move = None
            self.Reset_Selection()
            self.Draw_Board()
            self.Update_Status()

    def Restart (self):
        self.board = Board()
        self.game_over = False
        self.last_ai_move = None
        self.Reset_Selection()
        self.Draw_Board()
        self.Update_Status()

    def Toggle_Logging(self):
        Engine.Toggle_Logging(self.logging_enabled.get())

if __name__ == "__main__":
    root = tk.Tk()
    chess_ui = ChessUI(root)
    root.mainloop()
