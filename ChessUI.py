import tkinter as tk
from Board import Board
from Engine import Find_Best_Move, Evaluate_Position

SQUARE_SIZE = 60
BOARD_SIZE = 8
PIECE_UNICODE = {
    'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
    'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚',
}

class ChessUI(tk.Tk):
    def __init__(self, root):
        self.root = root
        self.root.title("Chess Game")

        self.board = Board()
        self.white_ai = tk.BooleanVar(value=False)
        self.black_ai = tk.BooleanVar(value=True)
        self.selected_square = None
        self.valid_moves = []

        self.canvas = tk.Canvas (root, width=BOARD_SIZE * SQUARE_SIZE, height=BOARD_SIZE * SQUARE_SIZE, bg = "white")
        self.canvas.grid (row=0, column=1)

        self.eval_canvas = tk.Canvas(root, width=40, height=BOARD_SIZE*SQUARE_SIZE, bg='white')
        self.eval_canvas.grid(row=0, column=0, sticky="ns")

        self.canvas.bind("<Button-1>", self.On_Click)
        control_frame = tk.Frame(root)
        control_frame.grid(row=1, column=2, columnspan=2)

        tk.Checkbutton(control_frame, text="AI controls White", variable=self.white_ai).pack(side=tk.LEFT, padx=10)
        tk.Checkbutton(control_frame, text="AI controls Black", variable=self.black_ai).pack(side=tk.LEFT, padx=10)

        self.root.after (100, self.Update_Loop)
        self.Draw_Board()

    def Update_Loop(self):
        if (self.board.white_to_move and self.white_ai.get()) or \
           (not self.board.white_to_move and self.black_ai.get()):
            move = Find_Best_Move(self.board, depth=3)
            if move:
                self.board.Make_Move(move)
        self.Draw_Board()
        self.root.after(100, self.Update_Loop)

    def Draw_Board(self):
        self.canvas.delete("all")
        colour1, colour2 = "#EEEED2", "#769656"
        for r in range (BOARD_SIZE):
            for c in range (BOARD_SIZE):
               x0 = c * SQUARE_SIZE
               y0 = r * SQUARE_SIZE
               x1 = x0 + SQUARE_SIZE
               y1 = y0 + SQUARE_SIZE
               colour = colour1 if (r + c) % 2 == 0 else colour2
               self.canvas.create_rectangle(x0, y0, x1, y1, fill=colour, outline="")
               piece = self.board.board[r][c]
               if piece != ".":
                   self.canvas.create_text(x0 + SQUARE_SIZE / 2, y0 + SQUARE_SIZE / 2, text=PIECE_UNICODE[piece], font=("Arial", 32))
        self.Draw_Eval_Bar()
        self.Draw_Valid_Moves()

    def Draw_Eval_Bar (self):
        self.eval_canvas.delete("all")
        score = Evaluate_Position(self.board)
        height = BOARD_SIZE * SQUARE_SIZE
        y = height * (1 - (score + 10) / 20)
        y = max (0, min (y, height))
        self.eval_canvas.create_rectangle(0, 0, 40, y, fill="black")
        self.eval_canvas.create_rectangle(0, y, 40, height, fill="white")
        self.eval_canvas.create_line(0, y, 40, y, fill="red", width=2)
    
    def Draw_Valid_Moves (self):
        for move in self.valid_moves:
            r, c = move.end
            x = c * SQUARE_SIZE + SQUARE_SIZE / 2
            y = r * SQUARE_SIZE + SQUARE_SIZE / 2
            radius = 8
            self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill="black", outline="")

    def On_Click(self, event):
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
                    break
            self.selected_square = None
            self.valid_moves = []

if __name__ == "__main__":
    root = tk.Tk()
    chess_ui = ChessUI(root)
    root.mainloop()
