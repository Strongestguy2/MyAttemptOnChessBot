import tkinter as tk

#region Initialization(Initialization(), Fen_To_Board(fen))
def Initialization():
    global pieces, turn, selected_piece, valid_moves, captured_white, captured_black, material_difference, MATERIAL_VALUES, last_move, moved, move_history

    starting_position = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    pieces, turn, moved = Fen_To_Board(starting_position)

    MATERIAL_VALUES = {
        "K": 0, "Q": 10, "N": 3, "B": 3, "R": 5, "P": 1,
    }

    selected_piece = None
    valid_moves = []
    captured_white = []
    captured_black = []
    material_difference = 0
    last_move = []
    move_history = []
    
    
def Fen_To_Board(fen):
    pieces = {}
    rows = fen.split(' ')[0].split('/')
    turn = ["white" if fen.split(' ')[1] == 'w' else "black"]
    moved = {}

    piece_type_from_symbol = {
        'k': 'K', 'p': 'P', 'n': 'N', 'b': 'B', 'r': 'R', 'q': 'Q'
    }

    for row in range(8):
        col = 0
        for char in rows[row]:
            if char.isdigit():
                col += int(char)
            else:
                color = 'w' if char.isupper() else 'b'
                piece_type = piece_type_from_symbol[char.lower()]
                piece_id = f"{color}{piece_type}{len([p for p in pieces if p.startswith(color + piece_type)]) + 1}"
                pieces[piece_id] = (col, row)  # Adjusted row indexing
                moved[piece_id] = False
                col += 1

    return pieces, turn, moved
#endregion

#region UI Functions(Draw_Chessbaord(), On_Canvas_Click(), Update_Material_Panel(), Convert_To_Icon())
def Draw_Chessboard(canvas, pieces, valid_moves, king_in_check_pos=None):
    square_size = 50

    for row in range(8):
        for col in range(8):
            x1, y1 = col * square_size, row * square_size
            x2, y2 = x1 + square_size, y1 + square_size
            color = "white" if (row + col) % 2 == 0 else "#739552"
            canvas.create_rectangle(x1, y1, x2, y2, fill=color)
            if row == 7:
                canvas.create_text(x1 + square_size - 5, y2 - 5, text=chr(97 + col), fill="#739552" if color == "white" else "white", anchor="se", font=("Arial", 10))
            if col == 0:
                canvas.create_text(x1 + 5, y1 + 5, text=str(8 - row), fill="#739552" if color == "white" else "white", anchor="nw", font=("Arial", 10))

    for move in valid_moves:
        col, row = move
        x, y = col * square_size + square_size // 2, row * square_size + square_size // 2
        canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="#739552")

    for piece, position in pieces.items():
        col, row = position
        x, y = col * square_size + square_size // 2, row * square_size + square_size // 2
        canvas.create_text(x, y, text=Convert_To_Icon(piece), font=("Arial", 24))

    # Highlight the king's square if in check
    if king_in_check_pos:
        x1 = king_in_check_pos[0] * square_size
        y1 = king_in_check_pos[1] * square_size
        x2 = x1 + square_size
        y2 = y1 + square_size
        canvas.create_rectangle(x1, y1, x2, y2, fill="red")

def On_Canvas_Click(event, canvas, pieces, turn):
    square_size = 50
    col, row = event.x // square_size, event.y // square_size
    clicked_square = (col, row)

    global selected_piece, valid_moves

    if selected_piece:
        if clicked_square in valid_moves:
            Move_Piece(canvas, pieces, selected_piece, clicked_square, turn)
            selected_piece = None
            valid_moves = []
        else:
            selected_piece = None
            valid_moves = []
            Draw_Chessboard(canvas, pieces, valid_moves)
    else:
        for piece, position in pieces.items():
            if position == clicked_square and piece.startswith(turn[0][0]):
                selected_piece = piece
                valid_moves = Calculate_Valid_Moves(piece, position, pieces, last_move)
                Draw_Chessboard(canvas, pieces, valid_moves)
                break

def Update_Material_Panel():
    white_captured = " ".join(Convert_To_Icon(p) for p in captured_white)
    black_captured = " ".join(Convert_To_Icon(p) for p in captured_black)
    white_material_label.config(text=f"White material: {white_captured} (+{material_difference})")
    black_material_label.config(text=f"Black material: {black_captured} ({-material_difference})")

def Convert_To_Icon(piece):
    color, piece_type = piece[0], piece[1]
    icons = {
        ('w', 'K'): "♔", ('b', 'K'): "♚", ('w', 'Q'): "♕", ('b', 'Q'): "♛",
        ('w', 'N'): "♘", ('b', 'N'): "♞", ('w', 'B'): "♗", ('b', 'B'): "♝",
        ('w', 'R'): "♖", ('b', 'R'): "♜", ('w', 'P'): "♙", ('b', 'P'): "♟",
    }
    return icons.get((color, piece_type), piece)
#endregion

#region Moving Pieces(Move_Piece(), Update_Move_History())
def Move_Piece(canvas, pieces, piece, new_position, turn):
    global material_difference, last_move, move_history

    captured_piece = None
    old_position = pieces[piece]

    # Check for en passant
    if piece[1] == "P" and abs(old_position[0] - new_position[0]) == 1 and old_position[1] != new_position[1]:
        captured_position = (new_position[0], old_position[1])
        for other_piece, pos in pieces.items():
            if pos == captured_position and other_piece[1] == "P" and len(last_move) >= 3:
                last_piece, last_start, last_end = last_move
                if abs(last_start[1] - last_end[1]) == 2 and last_end == captured_position:
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
            captured_white.append(captured_piece)
            material_difference += MATERIAL_VALUES[captured_piece[1]]
        else:
            captured_black.append(captured_piece)
            material_difference -= MATERIAL_VALUES[captured_piece[1]]
        Update_Material_Panel()

    # Update piece position
    pieces[piece] = new_position

    # Pawn promotion
    if piece[1] == "P" and (new_position[1] == 0 or new_position[1] == 7):
        Promote_Pawn(canvas, pieces, piece, new_position, turn)
        return

    # Record the last move
    last_move[:] = [piece, old_position, new_position]
    move_history.append(f"{piece}: {old_position} -> {new_position}")
    Update_Move_History()

    # Check for game over
    if "wK1" not in pieces:
        Display_Game_Over(canvas, "Black wins!")
        for x in pieces:
            print (x)
        return
    elif "bK1" not in pieces:
        Display_Game_Over(canvas, "White wins!")
        return

    # Switch turn
    turn[0] = "black" if turn[0] == "white" else "white"

    # Check if the new side is in check
    if Is_In_Check(pieces, turn[0]):
        # Find king position for highlighting
        king_pos = None
        for p, pos in pieces.items():
            if p.startswith(turn[0][0]) and p[1] == "K":
                king_pos = pos
                break
        if Is_Checkmate(pieces, turn[0]):
            Display_Game_Over(canvas, f"{'White' if turn[0] == 'black' else 'Black'} wins by checkmate!")
            return
        else:
            # Redraw board with king highlighted
            Draw_Chessboard(canvas, pieces, [], king_in_check_pos=king_pos)
            return

    # Redraw board
    canvas.delete("all")
    Draw_Chessboard(canvas, pieces, [])

def Update_Move_History():
    move_history_text.config(state=tk.NORMAL)
    move_history_text.delete(1.0, tk.END)
    move_history_text.insert(tk.END, "\n".join(move_history))
    move_history_text.config(state=tk.DISABLED)
#endregion

#region Checks(Is_Square_Attacked(), Get_Basic_Moves(), Is_In_Check(), Calculate_Valid_Moves(), Is_Checkmate())
def Is_Square_Attacked(pieces, pos, color, visited=None):
    if visited is None:
        visited = set()
    key = (tuple(pieces.items()), pos, color)
    if key in visited:
        return False
    visited.add(key)

    # Uses Get_Basic_Moves to see if an opponent can capture 'pos'
    opponent_color = "white" if color == "black" else "black"
    for p, piece_pos in pieces.items():
        if p.startswith(opponent_color[0]):
            # Basic moves without check consideration
            enemy_moves = Get_Basic_Moves(p, piece_pos, pieces, last_move, skip_king=True)
            if pos in enemy_moves:
                return True
    return False

def Get_Basic_Moves(piece, pos, pieces, last_move, skip_king=False):
    # Piece letter
    piece_type = piece[1]
    # Return raw moves, ignoring checks
    if piece_type == "K":
        if skip_king:
            return []
        return Check_King_Valid_Moves(pos, pieces, piece[0])
    if piece_type == "Q":
        return Check_Queen_Valid_Moves(pos, pieces, piece[0])
    if piece_type == "N":
        return Check_Knight_Valid_Moves(pos, pieces, piece[0])
    if piece_type == "B":
        return Check_Bishop_Valid_Moves(pos, pieces, piece[0])
    if piece_type == "R":
        return Check_Rook_Valid_Moves(pos, pieces, piece[0])
    if piece_type == "P":
        return Check_Pawn_Valid_Moves(pos, pieces, piece[0], last_move)
    return []

def Is_In_Check(pieces, color):
    # Find king
    king_piece = None
    for p, king_pos in pieces.items():
        if p.startswith(color[0]) and p[1] == "K":
            king_piece = (p, king_pos)
            break
    if not king_piece:
        return False

    king_pos = king_piece[1]
    # Check if any enemy piece can capture king_pos
    opponent_color = "white" if color == "black" else "black"
    for p, pos in pieces.items():
        if p.startswith(opponent_color[0]):
            # Use basic moves ignoring check
            enemy_moves = Get_Basic_Moves(p, pos, pieces, last_move)
            if king_pos in enemy_moves:
                return True
    return False

def Calculate_Valid_Moves(piece, position, pieces, last_move):
    candidate_moves = Get_Basic_Moves(piece, position, pieces, last_move)
    safe_moves = []
    color = "white" if piece.startswith("w") else "black"

    old_pos = pieces[piece]
    for move_pos in candidate_moves:
        captured_piece = None
        if move_pos in pieces.values():
            for op, opos in pieces.items():
                if opos == move_pos:
                    captured_piece = op
                    break

        pieces[piece] = move_pos
        if captured_piece:
            del pieces[captured_piece]

        # Always verify king safety, even if not currently in check
        if not Is_In_Check(pieces, color):
            safe_moves.append(move_pos)

        pieces[piece] = old_pos
        if captured_piece:
            pieces[captured_piece] = move_pos

    return safe_moves

def Is_Checkmate(pieces, color):
    # If not in check, no need to check for checkmate
    if not Is_In_Check(pieces, color):
        return False

    # Try every piece of 'color'; if any valid move leads out of check, not checkmate
    for p, pos in pieces.items():
        if p.startswith(color[0]):
            moves = Calculate_Valid_Moves(p, pos, pieces, last_move)
            if moves:
                return False
    return True
#endregion

#region Check Pieces Valid Moves
def Check_King_Valid_Moves(position, pieces, turn):
    safe_moves = []
    color = "white" if turn == "w" else "black"
    # Normal king moves
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            if dx == 0 and dy == 0:
                continue
            new_position = (position[0] + dx, position[1] + dy)
            if 0 <= new_position[0] < 8 and 0 <= new_position[1] < 8:
                if not any(pieces.get(p) == new_position for p in pieces if p.startswith(turn[0])):
                    if not Is_Square_Attacked(pieces, new_position, color):
                        safe_moves.append(new_position)

    # Castling
    king_id = f"{turn}K"
    if not moved.get(king_id, True):
        row = 7 if color == "white" else 0

        # Short castling (king-side)
        # Rook at (7, row)
        for r, rpos in pieces.items():
            if r.startswith(turn[0] + "R") and rpos == (7, row) and not moved.get(r, True):
                if (5, row) not in pieces.values() and (6, row) not in pieces.values():
                    if not Is_Square_Attacked(pieces, (4, row), color) \
                       and not Is_Square_Attacked(pieces, (5, row), color) \
                       and not Is_Square_Attacked(pieces, (6, row), color):
                        safe_moves.append((6, row))

        # Long castling (queen-side)
        # Rook at (0, row)
        for r, rpos in pieces.items():
            if r.startswith(turn[0] + "R") and rpos == (0, row) and not moved.get(r, True):
                if (1, row) not in pieces.values() and (2, row) not in pieces.values() and (3, row) not in pieces.values():
                    if not Is_Square_Attacked(pieces, (4, row), color) \
                       and not Is_Square_Attacked(pieces, (3, row), color) \
                       and not Is_Square_Attacked(pieces, (2, row), color):
                        safe_moves.append((2, row))

    return safe_moves

def Check_Queen_Valid_Moves(position, pieces, turn):
    moves = []
    directions = [(1, 1), (1, -1), (-1, 1), (-1, -1), (1, 0), (-1, 0), (0, 1), (0, -1)]
    for dx, dy in directions:
        for step in range(1, 8):
            new_position = (position[0] + step * dx, position[1] + step * dy)
            if 0 <= new_position[0] < 8 and 0 <= new_position[1] < 8:
                if any(pieces.get(p) == new_position for p in pieces if p.startswith(turn[0])):
                    break
                moves.append(new_position)
                if any(pieces.get(p) == new_position for p in pieces if not p.startswith(turn[0])):
                    break
    return moves

def Check_Knight_Valid_Moves(position, pieces, turn):
    moves = []
    directions = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
    for dx, dy in directions:
        new_position = (position[0] + dx, position[1] + dy)
        if 0 <= new_position[0] < 8 and 0 <= new_position[1] < 8:
            if not any(pieces.get(p) == new_position for p in pieces if p.startswith(turn[0])):
                moves.append(new_position)
    return moves

def Check_Bishop_Valid_Moves(position, pieces, turn):
    moves = []
    directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    for dx, dy in directions:
        for step in range(1, 8):
            new_position = (position[0] + step * dx, position[1] + step * dy)
            if 0 <= new_position[0] < 8 and 0 <= new_position[1] < 8:
                if any(pieces.get(p) == new_position for p in pieces if p.startswith(turn[0])):
                    break
                moves.append(new_position)
                if any(pieces.get(p) == new_position for p in pieces if not p.startswith(turn[0])):
                    break
    return moves

def Check_Rook_Valid_Moves(position, pieces, turn):
    moves = []
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    for dx, dy in directions:
        for step in range(1, 8):
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
    x, y = position

    # Forward move by 1
    forward_step = -1 if turn == 'w' else 1
    if 0 <= y + forward_step < 8 and not any(pieces.get(p) == (x, y + forward_step) for p in pieces):
        moves.append((x, y + forward_step))

        # First move can advance 2
        if (turn == 'w' and y == 6) or (turn == 'b' and y == 1):
            if not any(pieces.get(p) == (x, y + 2 * forward_step) for p in pieces):
                moves.append((x, y + 2 * forward_step))

    # Diagonal captures
    for dx in [-1, 1]:
        nx, ny = x + dx, y + forward_step
        if 0 <= nx < 8 and 0 <= ny < 8:
            # Normal capture
            if any(pieces.get(p) == (nx, ny) and not p.startswith(turn) for p in pieces):
                moves.append((nx, ny))
            # En passant
            if last_move and len(last_move) >= 3:
                last_piece, last_start, last_end = last_move
                if last_piece[1] == 'P' and abs(last_start[1] - last_end[1]) == 2:
                    if (nx, ny) == (last_end[0], last_end[1] + forward_step):
                        if any(pieces.get(p) == last_end for p in pieces):
                            moves.append((nx, ny))

    return moves

#endregion

#region Pawn Promotion
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
#endregion

#region Game Over
def Display_Game_Over(canvas, message):
    canvas.delete("all")
    canvas.create_text(200, 150, text=message, font=("Arial", 24), fill="red")
    canvas.create_text(200, 200, text="Click 'Try Again' to restart", font=("Arial", 16), fill="black")
    try_again_button = tk.Button(canvas.master, text="Try Again", font=("Arial", 14), command=lambda: Restart_Game(canvas))
    try_again_button.place(x=150, y=250)

def Restart_Game(canvas):
    Initialization()
    canvas.delete("all")
    Draw_Chessboard(canvas, pieces, valid_moves)
    for widget in canvas.master.winfo_children():
        if isinstance(widget, tk.Button):
            widget.destroy()
    Update_Material_Panel()
#endregion

#region Main
if __name__ == "__main__":
    window = tk.Tk()
    window.title("Chessboard")

    canvas = tk.Canvas(window, width=400, height=400)
    canvas.pack(side="right")

    top_panel = tk.Frame(window)
    top_panel.pack(side="top")

    bottom_panel = tk.Frame(window)
    bottom_panel.pack(side="bottom")

    left_panel = tk.Frame(window)
    left_panel.pack(side="left", fill="y")

    white_material_label = tk.Label(top_panel, text="White material: ", font=("Arial", 14))
    white_material_label.pack(side="left")

    black_material_label = tk.Label(bottom_panel, text="Black material: ", font=("Arial", 14))
    black_material_label.pack(side="left")

    move_history_text = tk.Text(left_panel, width=30, height=25, state=tk.DISABLED)
    move_history_text.pack(side="left", fill="y")

    Initialization()
    Draw_Chessboard(canvas, pieces, valid_moves)
    canvas.bind("<Button-1>", lambda event: On_Canvas_Click(event, canvas, pieces, turn))

    window.mainloop()
#endregion
