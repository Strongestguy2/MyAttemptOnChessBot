import tkinter as tk

def Initialization ():
    global pieces, turn, selected_piece, valid_moves, captured_white, captured_black, material_difference, MATERIAL_VALUES, last_move

    pieces = {
        "wK" : (4, 7),
        "bK" : (4, 0),
        "wQ" : (3, 7),
        "bQ" : (3, 0),
        "wN1" : (1, 7), "wN2" : (6, 7),
        "bN1" : (1, 0), "bN2" : (6, 0),
        "wB1" : (2, 7), "wB2" : (5, 7),
        "bB1" : (2, 0), "bB2" : (5, 0),
        "wR1" : (0, 7), "wR2" : (7, 7),
        "bR1" : (0, 0), "bR2" : (7, 0),
        "wP1" : (0, 6), "wP2" : (1, 6), "wP3" : (2, 6), "wP4" : (3, 6), 
        "wP5" : (4, 6), "wP6" : (5, 6), "wP7" : (6, 6), "wP8" : (7, 6),
        "bP1" : (0, 1), "bP2" : (1, 1), "bP3" : (2, 1), "bP4" : (3, 1),
        "bP5" : (4, 1), "bP6" : (5, 1), "bP7" : (6, 1), "bP8" : (7, 1),
    }

    MATERIAL_VALUES = {
        "K" : 0,
        "Q" : 10,
        "N" : 3,
        "B" : 3,
        "R" : 5,
        "P" : 1,
    }

    turn = ["white"]
    selected_piece = None
    valid_moves = []

    captured_white = []
    captured_black = []
    material_difference = 0

    last_move = []

#region UI stuff (Draw_Chessboard() + On_Canvas_Click() + Update_Material_Panel() + Convert_To_Icon())

def Draw_Chessboard(canvas, pieces, valid_moves):
    square_size = 50

    for row in range (8):
        for col in range (8):
            x1 = col * square_size
            y1 = row * square_size
            x2 = x1 + square_size
            y2 = y1 + square_size

            if (row + col) % 2 == 0:
                color = "white"
            else:
                color = "#739552"

            canvas.create_rectangle(x1, y1, x2, y2, fill=color)
            
            if row == 7:
                canvas.create_text (x1 + square_size - 5, y2 - 5, text=chr(97 + col), fill = "#739552" if color == "white" else "white", anchor="se", font=("Arial", 10))
            if col == 0:
                canvas.create_text (x1 + 5, y1 + 5, text=str(8 - row), fill = "#739552" if color == "white" else "white", anchor="nw", font=("Arial", 10))

    for move in valid_moves:
        col, row = move
        x = col * square_size + square_size // 2
        y = row * square_size + square_size // 2
        canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="#739552")

    for piece, position in pieces.items():
        col, row = position
        x = col * square_size + square_size // 2
        y = row * square_size + square_size // 2
        canvas.create_text(x, y, text=Convert_To_Icon(piece), font=("Arial", 24))

def On_Canvas_Click (event, canvas, pieces, turn):
    square_size = 50
    col = event.x // square_size
    row = event.y // square_size
    clicked_square = (col, row)

    global selected_piece, valid_moves

    if selected_piece:
        if clicked_square in valid_moves:
            Move_Piece (canvas, pieces, selected_piece, clicked_square, turn)
            selected_piece = None
            valid_moves = []
        else:
            selected_piece = None
            valid_moves = []
            Draw_Chessboard (canvas, pieces, valid_moves)
    else:
        for piece, position in pieces.items():
            if position == clicked_square and piece.startswith(turn[0][0]):
                selected_piece = piece
                valid_moves = Calculate_Valid_Moves (piece, position, pieces, last_move)
                Draw_Chessboard (canvas, pieces, valid_moves)
                break

def Update_Material_Panel ():
    white_captured = " ".join (Convert_To_Icon (p) for p in captured_white)
    black_captured = " ".join (Convert_To_Icon (p) for p in captured_black)

    white_material_label.config (text = f"White material: {white_captured} (+{material_difference})")
    black_material_label.config (text = f"Black material: {black_captured} ({-material_difference})")

def Convert_To_Icon(piece):
    color, piece_type = piece[0], piece[1]
    icons = {
        ('w', 'K'): "♔",
        ('b', 'K'): "♚",
        ('w', 'Q'): "♕",
        ('b', 'Q'): "♛",
        ('w', 'N'): "♘",
        ('b', 'N'): "♞",
        ('w', 'B'): "♗",
        ('b', 'B'): "♝",
        ('w', 'R'): "♖",
        ('b', 'R'): "♜",
        ('w', 'P'): "♙",
        ('b', 'P'): "♟",
    }
    return icons.get((color, piece_type), piece)

#endregion

#region Moving Pieces (Move_Piece())
def Move_Piece (canvas, pieces, piece, new_position, turn):
    global material_difference, last_move

    captured_piece = None
    old_position = pieces[piece]

    # Check for en passant
    if piece[1] == "P" and abs(old_position[1] - new_position[1]) == 1:
        captured_position = (new_position[0], old_position[1])
        for other_piece, pos in pieces.items():
            if pos == captured_position and other_piece[1] == "P" and len(last_move) >= 3:
                last_piece, last_start, last_end = last_move[0]
                if abs(last_start[1] - last_end[1]) == 2:
                    captured_piece = other_piece
                    break

    # Check for normal capture
    if new_position in pieces.values() and not captured_piece:
        for other_piece, pos in pieces.items():
            if pos == new_position:
                captured_piece = other_piece
                break

    if captured_piece:
        del pieces[captured_piece]

        if piece.startswith("w"):
            captured_black.append(captured_piece)
            material_difference += MATERIAL_VALUES[captured_piece[1]]
        else:
            captured_white.append(captured_piece)
            material_difference -= MATERIAL_VALUES[captured_piece[1]]

        Update_Material_Panel()

    pieces[piece] = new_position

    # Pawn promotion and check for end of game as before
    if piece[1] == "P" and (new_position[1] == 0 or new_position[1] == 7):
        Promote_Pawn(canvas, piece, new_position, turn)
        return

    last_move[:] = [(piece, old_position, new_position)]

    if "wK" not in pieces:
        Display_Game_Over(canvas, "Black wins!")
    elif "bK" not in pieces:
        Display_Game_Over(canvas, "White wins!")
    else:
        turn[0] = "black" if turn[0] == "white" else "white"

    canvas.delete("all")
    Draw_Chessboard(canvas, pieces, [])

# endregion

#region chess Check Move (Is_Valid_Move() + Check all pieces valid moves + Calculate_Valid_Moves())


def Check_King_Valid_Moves (position, pieces, turn):
    moves = []
    for dx in range (-1, 2):
        for dy in range (-1, 2):
            if dx == 0 and dy == 0:
                continue
            new_position = (position[0] + dx, position[1] + dy)
            if 0 <= new_position[0] < 8 and 0 <= new_position[1] < 8:
                if not any (pieces.get (p) == new_position for p in pieces if p.startswith (turn[0])):
                    moves.append (new_position)
    return moves

def Check_Queen_Valid_Moves (position, pieces, turn):
    moves = []
    directions = [(1, 1), (1, -1), (-1, 1), (-1, -1), (1, 0), (-1, 0), (0, 1), (0, -1)]

    for dx, dy in directions:
        for step in range (1, 8):
            new_position = (position[0] + step * dx, position[1] + step * dy)
            if 0 <= new_position[0] < 8 and 0 <= new_position[1] < 8:
                if any(pieces.get(p) == new_position for p in pieces if p.startswith(turn[0])):
                    break
                moves.append(new_position)
                if any(pieces.get(p) == new_position for p in pieces if not p.startswith(turn[0])):
                    break
    return moves

def Check_Knight_Valid_Moves (position, pieces, turn):
    moves = []
    directions = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]

    for dx, dy in directions:
        new_position = (position[0] + dx, position[1] + dy)
        if 0 <= new_position[0] < 8 and 0 <= new_position[1] < 8:
            if not any(pieces.get(p) == new_position for p in pieces if p.startswith(turn[0])):
                moves.append(new_position)
    return moves

def Check_Bishop_Valid_Moves (position, pieces, turn):
    moves = []
    directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]

    for dx, dy in directions:
        for step in range (1, 8):
            new_position = (position[0] + step * dx, position[1] + step * dy)
            if 0 <= new_position[0] < 8 and 0 <= new_position[1] < 8:
                if any(pieces.get(p) == new_position for p in pieces if p.startswith(turn[0])):
                    break
                moves.append(new_position)
                if any(pieces.get(p) == new_position for p in pieces if not p.startswith(turn[0])):
                    break
                
    return moves

def Check_Rook_Valid_Moves (position, pieces, turn):
    moves = []
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]

    for dx, dy in directions:
        for step in range (1, 8):
            new_position = (position[0] + step * dx, position[1] + step * dy)
            if 0 <= new_position[0] < 8 and 0 <= new_position[1] < 8:
                if any(pieces.get(p) == new_position for p in pieces if p.startswith(turn[0])):
                    break
                moves.append(new_position)
                if any(pieces.get(p) == new_position for p in pieces if not p.startswith(turn[0])):
                    break
    return moves

def Check_Pawn_Valid_Moves(position, pieces, turn, last_move):
    moves = []
    direction = -1 if turn == "w" else 1
    start_row = 6 if turn == "w" else 1

    new_position = (position[0], position[1] + direction)
    if 0 <= new_position[1] < 8 and new_position not in pieces.values():
        moves.append(new_position)

    if position[1] == start_row:
        double_step = (position[0], position[1] + 2 * direction)
        if new_position not in pieces.values() and double_step not in pieces.values():
            moves.append(double_step)

    for dx in [-1, 1]:
        captured_position = (position[0] + dx, position[1] + direction)
        if 0 <= captured_position[0] < 8 and 0 <= captured_position[1] < 8:
            if any(pieces.get(p) == captured_position for p in pieces if not p.startswith(turn)):
                moves.append(captured_position)

            if last_move and len(last_move) > 0 and last_move[0][0][1] == "P":
                last_start = last_move[0][1]
                last_end = last_move[0][2]
                if abs(last_start[1] - last_end[1]) == 2 and last_end == (position[0] + dx, position[1]):
                    en_passant_position = (position[0] + dx, position[1] + direction)
                    moves.append(en_passant_position)  # Add en passant capture move
    
    return moves

def Calculate_Valid_Moves (piece, position, pieces, last_move):
    if piece[1] == "K":
        return Check_King_Valid_Moves (position, pieces, piece[0])
    elif piece[1] == "Q":
        return Check_Queen_Valid_Moves (position, pieces, piece[0])
    elif piece[1] == "N":
        return Check_Knight_Valid_Moves (position, pieces, piece[0])
    elif piece[1] == "B":
        return Check_Bishop_Valid_Moves (position, pieces, piece[0])
    elif piece[1] == "R":
        return Check_Rook_Valid_Moves (position, pieces, piece[0])
    elif piece[1] == "P":
        return Check_Pawn_Valid_Moves (position, pieces, piece[0], last_move)
    return []

# endregion

#region Fundamental logics(Promote_Pawn())

def Promote_Pawn(canvas, piece, position, turn):
    promotion_panel = tk.Frame(canvas.master)
    promotion_panel.place(x=200, y=200)

    def promote_to(new_piece_type):
        global material_difference
        del pieces[piece]
        new_piece = f"{turn[0][0]}{new_piece_type}{len([p for p in pieces if p.startswith(turn[0][0] + new_piece_type)]) + 1}"
        pieces[new_piece] = position
        material_difference += MATERIAL_VALUES[new_piece_type] - MATERIAL_VALUES["P"]
        promotion_panel.destroy()
        Update_Material_Panel()
        Draw_Chessboard(canvas, pieces, [])
        turn[0] = "black" if turn[0] == "white" else "white"

    for piece_type in ["Q", "R", "B", "N"]:
        icon = Convert_To_Icon(f"{turn[0][0]}{piece_type}")
        button = tk.Button(
            promotion_panel, text=icon, font=("Arial", 18),
            command=lambda pt=piece_type: promote_to(pt)
        )
        button.pack(pady=5)

# endregion
#region Game Over (Display_Game_Over() + Restart_Game())
def Display_Game_Over(canvas, message):
    # Clear the canvas
    canvas.delete("all")
    
    # Display the game-over message
    canvas.create_text(200, 150, text=message, font=("Arial", 24), fill="red")
    canvas.create_text(200, 200, text="Click 'Try Again' to restart", font=("Arial", 16), fill="black")
    
    # Add "Try Again" button outside the canvas clearing process
    try_again_button = tk.Button(
        canvas.master, 
        text="Try Again", 
        font=("Arial", 14), 
        command=lambda: Restart_Game(canvas)
    )
    # Place the button relative to the window, not the canvas
    try_again_button.place(x=150, y=250)

def Restart_Game (canvas):
    Initialization ()
    canvas.delete ("all")
    Draw_Chessboard (canvas, pieces, valid_moves)

    for widget in canvas.master.winfo_children ():
        if isinstance (widget, tk.Button):
            widget.destroy ()

    Update_Material_Panel ()

# endregion

#region Main   
if __name__ == "__main__":
    window = tk.Tk()
    window.title("Chessboard")

    canvas = tk.Canvas(window, width=400, height=400)
    canvas.pack()

    top_panel = tk.Frame(window)
    top_panel.pack(side = "top")

    bottom_panel = tk.Frame(window)
    bottom_panel.pack(side = "bottom")

    white_material_label = tk.Label(top_panel, text="White material: ", font = ("Arial", 14))
    white_material_label.pack(side = "left")

    black_material_label = tk.Label(bottom_panel, text="Black material: ", font = ("Arial", 14))
    black_material_label.pack(side = "left")

    Initialization()

    Draw_Chessboard(canvas, pieces, valid_moves)

    canvas.bind("<Button-1>", lambda event: On_Canvas_Click(event, canvas, pieces, turn))

    window.mainloop()
#endregion
