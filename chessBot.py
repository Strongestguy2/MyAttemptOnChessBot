import tkinter as tk
import numpy as np
from Bitboard import Board_To_Bitboard, Print_Bitboard, generate_pawn_moves, generate_pawn_attacks, generate_knight_moves, generate_bishop_moves, generate_rook_moves, generate_queen_moves, generate_king_moves, Print_All_Bitboards

#region Initialization(Initialization(), Fen_To_Board(fen))
def Initialization():
    global pieces, turn, selected_piece, valid_moves, captured_white, captured_black, material_difference, MATERIAL_VALUES, last_move, moved, move_history, current_move_index, bitboards

    starting_position = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    pieces, turn, moved = Fen_To_Board(starting_position)
    bitboards = Board_To_Bitboard(pieces)

    MATERIAL_VALUES = {
        "K": 0, "Q": 10, "N": 3, "B": 3, "R": 5, "P": 1,
    }

    selected_piece = None
    valid_moves = []
    captured_white = []
    captured_black = []
    material_difference = 0
    last_move = []
    move_history = [starting_position]  # Initialize with the starting position
    current_move_index = 0
    
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
                piece_key = (color, piece_type, len([p for p in pieces if p[0] == color and p[1] == piece_type]) + 1)
                pieces[piece_key] = (col, row)
                col += 1

    return pieces, turn, moved

def Board_To_Fen(pieces, turn):
    board = [["" for _ in range(8)] for _ in range(8)]
    for piece, (col, row) in pieces.items():
        board[row][col] = piece[1].lower() if piece[0] == 'b' else piece[1].upper()

    fen_rows = []
    for row in board:
        empty_count = 0
        fen_row = ""
        for cell in row:
            if cell == "":
                empty_count += 1
            else:
                if empty_count > 0:
                    fen_row += str(empty_count)
                    empty_count = 0
                fen_row += cell
        if empty_count > 0:
            fen_row += str(empty_count)
        fen_rows.append(fen_row)

    fen_board = "/".join(fen_rows)
    fen_turn = "b" if turn[0] == "white" else "w"
    return f"{fen_board} {fen_turn} - - 0 1"
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

    if current_move_index != len(move_history) - 1:
        return

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
            if position == clicked_square and piece[0] == turn[0][0]:
                selected_piece = piece
                valid_moves = Calculate_Valid_Moves(piece, position)
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
    global material_difference, last_move, move_history, current_move_index, en_passant_target

    captured_piece = None
    old_position = pieces[piece]

    # Check for en passant
    en_passant_target = np.uint64(0)
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
        if piece[0] == "w":
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

    # Set en passant target
    if piece[1] == "P" and abs(old_position[1] - new_position[1]) == 2:
        en_passant_target = np.uint64(1) << ((old_position[1] + new_position[1]) // 2 * 8 + old_position[0])

    # Record the last move
    last_move[:] = [piece, old_position, new_position]
    move_history.append(Board_To_Fen(pieces, turn))  # Store the FEN string
    current_move_index = len(move_history) - 1  # Update the current move index
    Update_Move_History()

    # Print the bitboard
    bitboards = Board_To_Bitboard(pieces)
    Print_Bitboard(bitboards['all'])  # Print only the 'all' bitboard

    # Check for game over
    if not any(p[0] == 'w' and p[1] == 'K' for p in pieces):
        Display_Game_Over(canvas, "Black wins!")
        return
    elif not any(p[0] == 'b' and p[1] == 'K' for p in pieces):
        Display_Game_Over(canvas, "White wins!")
        return

    # Switch turn
    turn[0] = "black" if turn[0] == "white" else "white"

    # Check if the new side is in check
    if Is_In_Check(pieces, turn[0]):
        # Find king position for highlighting
        king_pos = None
        for p, pos in pieces.items():
            if p[0] == turn[0][0] and p[1] == "K":
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
def Is_Square_Attacked(square, color):
    enemy_color = 'b' if color == 'w' else 'w'
    enemy_pawns = bitboards['p'] if enemy_color == 'b' else bitboards['P']
    enemy_knights = bitboards['n'] if enemy_color == 'b' else bitboards['N']
    enemy_bishops = bitboards['b'] if enemy_color == 'b' else bitboards['B']
    enemy_rooks = bitboards['r'] if enemy_color == 'b' else bitboards['R']
    enemy_queens = bitboards['q'] if enemy_color == 'b' else bitboards['Q']
    enemy_kings = bitboards['k'] if enemy_color == 'b' else bitboards['K']

    square_bit = 1 << square

    if generate_pawn_attacks(enemy_pawns, enemy_color) & square_bit:
        return True
    if generate_knight_moves(enemy_knights, bitboards['all']) & square_bit:
        return True
    if generate_bishop_moves(enemy_bishops, bitboards['all']) & square_bit:
        return True
    if generate_rook_moves(enemy_rooks, bitboards['all']) & square_bit:
        return True
    if generate_queen_moves(enemy_queens, bitboards['all']) & square_bit:
        return True
    if generate_king_moves(enemy_kings, bitboards['all']) & square_bit:
        return True
    return False

def Calculate_Valid_Moves(piece, position):
    piece_type = piece[1]
    color = piece[0]
    bitboard = np.uint64(1) << (position[1] * 8 + position[0])  # Ensure bitboard is correctly generated
    occupancy = bitboards['all']

    print(f"Calculating valid moves for {piece} at {position} (bitboard: {bitboard})")

    if piece_type == 'P':
        # Debug: Check if the pawn is in its starting position
        starting_position = 1 if color == 'w' else 6
        if position[1] == starting_position:
            print(f"Pawn {piece} at {position} is in its starting position (rank {starting_position + 1}).")
        else:
            print(f"Pawn {piece} at {position} is NOT in its starting position (should be on rank {starting_position + 1}).")

        moves_bitboard = generate_pawn_moves(bitboard, color, occupancy)
    elif piece_type == 'N':
        moves_bitboard = generate_knight_moves(bitboard, occupancy)
    elif piece_type == 'B':
        moves_bitboard = generate_bishop_moves(bitboard, occupancy)
    elif piece_type == 'R':
        moves_bitboard = generate_rook_moves(bitboard, occupancy)
    elif piece_type == 'Q':
        moves_bitboard = generate_queen_moves(bitboard, occupancy)
    elif piece_type == 'K':
        moves_bitboard = generate_king_moves(bitboard, occupancy)
    else:
        return []

    # Convert bitboard to list of positions
    valid_moves = []
    for i in range(64):
        if (moves_bitboard >> i) & 1:
            valid_moves.append((i % 8, i // 8))
    return valid_moves

def Is_In_Check(pieces, color):
    # Find king
    king_piece = None
    for p, king_pos in pieces.items():
        if p[0] == color[0] and p[1] == "K":
            king_piece = (p, king_pos)
            break
    if not king_piece:
        return False

    king_pos = king_piece[1]
    # Check if any enemy piece can capture king_pos
    opponent_color = "white" if color == "black" else "black"
    for p, pos in pieces.items():
        if p[0] == opponent_color[0]:
            # Use basic moves ignoring check
            enemy_moves = Calculate_Valid_Moves(p, pos)
            if king_pos in enemy_moves:
                return True
    return False

def Is_Checkmate(pieces, color):
    # If not in check, no need to check for checkmate
    if not Is_In_Check(pieces, color):
        return False

    # Try every piece of 'color'; if any valid move leads out of check, not checkmate
    for p, pos in pieces.items():
        if p.startswith(color[0]):
            moves = Calculate_Valid_Moves(p, pos)
            if moves:
                return False
    return True
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

#region UI
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

def Navigate_Move(direction):
    global current_move_index, pieces, turn, move_history

    if direction == -1 and current_move_index > 0:
        current_move_index -= 1
    elif direction == 1 and current_move_index < len(move_history) - 1:
        current_move_index += 1
    else:
        return

    # Load the board state from the FEN string
    fen = move_history[current_move_index]
    pieces, turn, moved = Fen_To_Board(fen)

    # Redraw the board
    canvas.delete("all")
    Draw_Chessboard(canvas, pieces, valid_moves)
#endregion

#region Main
if __name__ == "__main__":
    window = tk.Tk()
    window.title("Chessboard")

    right_panel = tk.Frame(window)
    right_panel.pack(side="right")

    canvas = tk.Canvas(right_panel, width=400, height=400)
    canvas.pack(side="top")

    top_panel = tk.Frame(window)
    top_panel.pack(side="top")

    left_panel = tk.Frame(window)
    left_panel.pack(side="left")

    bottom_frame = tk.Frame(window)
    bottom_frame.pack(side="bottom")

    right_bottom_frame = tk.Frame(right_panel)
    right_bottom_frame.pack(side="bottom")

    white_material_label = tk.Label(left_panel, text="White material: ", font=("Arial", 14))
    white_material_label.pack(side = "top")

    black_material_label = tk.Label(left_panel, text="Black material: ", font=("Arial", 14))
    black_material_label.pack(side="bottom")

    move_history_text = tk.Text(left_panel, width=30, height=25, state=tk.DISABLED)
    move_history_text.pack(side="left", fill = "y")

    back_button = tk.Button(right_bottom_frame, text="←", font=("Arial", 14), command=lambda: Navigate_Move(-1))
    back_button.pack(side="left", padx=10)

    import_pgn_button = tk.Button(right_bottom_frame, text="Import PGN", font=("Arial", 14))
    import_pgn_button.pack(side="left", padx=10)

    forward_button = tk.Button(right_bottom_frame, text="→", font=("Arial", 14), command=lambda: Navigate_Move(1))
    forward_button.pack(side="left", padx=10)

    Initialization()
    Draw_Chessboard(canvas, pieces, valid_moves)
    canvas.bind("<Button-1>", lambda event: On_Canvas_Click(event, canvas, pieces, turn))

    window.mainloop()
#endregion
