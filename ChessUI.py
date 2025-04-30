import tkinter as tk
from tkinter import messagebox
from Board import Board
from Engine import Find_Best_Move, Evaluate_Position, NODES_SEARCHED

SQUARE_SIZE = 60
BOARD_SIZE = 8
DEPTH = 3
PIECE_UNICODE = {
    'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
    'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚',
}
CHECKMATE = 0

class ChessUI(tk.Tk):
    def __init__(self, root):
        self.root = root
        self.root.title("Chess Game")
        self.board = Board()

        self.white_ai = tk.BooleanVar(value=False)
        self.black_ai = tk.BooleanVar(value=True)

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

        self.Draw_Board()
        self.root.after(100, self.Update_Loop)

    def Update_Loop(self):
        global CHECKMATE
        if CHECKMATE or self.game_over:
            return

        # Step 1: AI move (only when it's AI's turn)
        if (self.board.white_to_move and self.white_ai.get()) or (not self.board.white_to_move and self.black_ai.get()):
            self.Play_AI_Move()

        self.Draw_Board()
        
        self.root.after(100, self.Update_Loop)

    def Play_AI_Move(self):
        move = Find_Best_Move(self.board, DEPTH)
        if move:
            self.board.Make_Move(move)
            self.last_ai_move = move
            self.Check_Endgame()

    def Update_Best_Moves(self):
        white_best, black_best = None, None
        if self.board.white_to_move:
            white_board = self.board.Copy_For_Color(True)
            white_best = Find_Best_Move(white_board, DEPTH)
        else:
            black_board = self.board.Copy_For_Color(False)
            black_best = Find_Best_Move(black_board, DEPTH)
        
        self.move_panel.config(text=self.Format_Best_Moves(white_best, black_best))

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
        score = Evaluate_Position(self.board)
        height = BOARD_SIZE * SQUARE_SIZE
        y = height * (1 - (score + 10) / 20)
        y = max(0, min(height, y))
        self.eval_canvas.create_rectangle(0, 0, 40, y, fill="black")
        self.eval_canvas.create_rectangle(0, y, 40, height, fill="white")
        self.eval_canvas.create_line(0, y, 40, y, fill="red", width=2)
        self.eval_canvas.create_text(20, height - 10, text=f"{score:+.2f}", font=("Arial", 10))
    
    def Draw_Valid_Moves (self):
        for move in self.valid_moves:
            r, c = move.end
            x = c * SQUARE_SIZE + SQUARE_SIZE / 2
            y = r * SQUARE_SIZE + SQUARE_SIZE / 2
            radius = 8
            self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill="black", outline="")
    
    def Format_Best_Moves (self,white_move, black_move):
        def move_to_str(move):
            if not move:
                return "N/A"
            piece = PIECE_UNICODE[move.piece_moved]
            start = self.Coord_To_Square (move.start)
            end = self.Coord_To_Square (move.end)
            return f"{piece} {start} to {end}"
        
        return f"White Best Move:\n{move_to_str(white_move)}\n\nBlack Best Move:\n{move_to_str(black_move)}"
    
    def Coord_To_Square (self, coord):
        row, col = coord
        return chr (col + ord('a')) + str (8 - row)
    
    def On_Click(self, event):
        global CHECKMATE
        if self.game_over: return

        col = event.x // SQUARE_SIZE
        row = event.y // SQUARE_SIZE

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
            
            global CHECKMATE
            CHECKMATE = 1
            self.game_over = True

    def Undo (self):
        if self.board.move_history:
            self.board.Undo_Move()
            self.game_over = False
            self.Reset_Selection()

    def Restart (self):
        self.board = Board()
        self.game_over = False
        self.Reset_Selection()

if __name__ == "__main__":
    root = tk.Tk()
    chess_ui = ChessUI(root)
    root.mainloop()
