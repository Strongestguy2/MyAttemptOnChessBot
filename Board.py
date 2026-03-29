from typing import Optional, Tuple, List, Set
from Move import Move
from Zobrist import hash_board, ZOBRIST_PIECES, ZOBRIST_CASTLING, ZOBRIST_EN_PASSANT, ZOBRIST_TURN


class Board:
    FIND_LEGAL_MOVES_TIME = 0
    START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    def __init__(self):
        self.board = [['.'] * 8 for _ in range(8)]

        self.white_to_move = True
        self.castling_rights = set()
        self.en_passant_square :  Optional [Tuple[int, int]] = None
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.move_history = []
        self.position_history = {}
        self.track_repetition = True
        self.Load_FEN(Board.START_FEN)

    def _Rebuild_Position_History(self):
        self.position_history = {}
        if self.track_repetition:
            start_hash = self.Hash_Board()
            self.position_history[start_hash] = 1

    def _Square_To_Coords(self, square: str) -> Optional[Tuple[int, int]]:
        if len(square) != 2:
            return None
        file_char = square[0].lower()
        rank_char = square[1]
        if file_char < 'a' or file_char > 'h' or rank_char < '1' or rank_char > '8':
            return None
        col = ord(file_char) - ord('a')
        row = 8 - int(rank_char)
        return (row, col)

    def Load_FEN(self, fen: str):
        parts = fen.strip().split()
        if len(parts) != 6:
            raise ValueError(f"Invalid FEN (expected 6 fields): {fen}")

        placement, active_color, castling, en_passant, halfmove, fullmove = parts
        ranks = placement.split('/')
        if len(ranks) != 8:
            raise ValueError(f"Invalid FEN board layout: {fen}")

        new_board = []
        valid_pieces = set("PNBRQKpnbrqk")
        
        self.white_king_pos = (-1, -1)
        self.black_king_pos = (-1, -1)

        row_idx = 0
        for rank in ranks:
            row = []
            col_idx = 0
            for char in rank:
                if char.isdigit():
                    row.extend(['.'] * int(char))
                    col_idx += int(char)
                elif char in valid_pieces:
                    row.append(char)
                    if char == 'K':
                        self.white_king_pos = (row_idx, col_idx)
                    elif char == 'k':
                        self.black_king_pos = (row_idx, col_idx)
                    col_idx += 1
                else:
                    raise ValueError(f"Invalid FEN piece character '{char}' in: {fen}")
            if len(row) != 8:
                raise ValueError(f"Invalid FEN rank width in: {fen}")
            new_board.append(row)
            row_idx += 1

        self.board = new_board
        self.white_to_move = active_color == 'w'
        self.castling_rights = set() if castling == '-' else set(castling)
        self.en_passant_square = None if en_passant == '-' else self._Square_To_Coords(en_passant)
        self.halfmove_clock = int(halfmove)
        self.fullmove_number = int(fullmove)
        self.move_history = []
        self.zobrist_key = hash_board(self)
        self._Rebuild_Position_History()

    def Print_Board (self):
        for row in self.board:
            print (' '.join(row))

        print (f"turn: {'white' if self.white_to_move else 'black'}")
        print (f"castling rights: {self.castling_rights}")
        print (f"en passant square: {self.en_passant_square}")
        print (f"halfmove clock: {self.halfmove_clock}")
        print (f"fullmove number: {self.fullmove_number}")
    
    def Hash_Board(self) -> str:
        return self.zobrist_key
    
    def Copy_For_Color(self, white: bool, isolate_history: bool = True):
        clone = Board.__new__(Board)
        clone.board = [row[:] for row in self.board]
        clone.white_to_move = white
        clone.castling_rights = self.castling_rights.copy()
        clone.en_passant_square = self.en_passant_square
        clone.halfmove_clock = self.halfmove_clock
        clone.fullmove_number = self.fullmove_number
        clone.move_history = []
        if isolate_history:
            # Search copies should not mutate repetition data from the UI/game board.
            clone.position_history = {}
            clone.track_repetition = False
        else:
            clone.position_history = self.position_history.copy()
            clone.track_repetition = self.track_repetition
        clone.zobrist_key = self.zobrist_key
        clone.white_king_pos = self.white_king_pos
        clone.black_king_pos = self.black_king_pos
        return clone
    
    def Get_Pseudo_Legal_Moves (self, include_castling = True) -> list:
        moves = []
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece == '.':
                    continue

                if self.white_to_move and piece.isupper():
                    self._Generate_Piece_Moves (piece, row, col, moves, include_castling)
                elif not self.white_to_move and piece.islower():
                    self._Generate_Piece_Moves (piece, row, col, moves, include_castling)
        return moves
    
    def _Generate_Piece_Moves(
        self,
        piece: str,
        row: int,
        col: int,
        moves: list,
        include_castling = True,
        white: Optional[bool] = None,
    ):
        is_white = self.white_to_move if white is None else white
        piece_type = piece.upper()

        if piece_type == 'P':
            self._Generate_Pawn_Moves(row, col, moves, is_white)
        elif piece_type == 'N':
            self._Generate_Knight_Moves(row, col, moves, is_white)
        elif piece_type == 'B':
            self._Generate_Bishop_Moves(row, col, moves, is_white)
        elif piece_type == 'R':
            self._Generate_Rook_Moves(row, col, moves, is_white)
        elif piece_type == 'Q':
            self._Generate_Queen_Moves(row, col, moves, is_white)
        elif piece_type == 'K':
            self._Generate_King_Moves(row, col, moves, is_white)
        
        if piece_type == 'K' and include_castling:
            if is_white:
                self._Get_White_Castling_Moves(moves)
            else:
                self._Get_Black_Castling_Moves(moves)

    def _Generate_Pawn_Moves (self, row: int, col: int, moves: list, is_white: bool):
        direction = -1 if is_white else 1
        start_row = 6 if is_white else 1
        enemy_pieces = [p.lower() for p in "PNBRQK"] if is_white else [p.upper() for p in "PNBRQK"]
        promotion_choice = 'Q' if is_white else 'q'

        one_forward = row + direction
        if 0 <= one_forward < 8 and self.board[one_forward][col] == '.':
            end_row = one_forward
            if end_row == 0 or end_row == 7:
                moves.append(Move((row, col), (end_row, col), self.board[row][col], is_pawn_promotion=True, promotion_choice=promotion_choice))
            else:
                moves.append(Move((row, col), (end_row, col), self.board[row][col]))

            two_forward = row + 2 * direction
            if row == start_row and 0 <= two_forward < 8 and self.board[two_forward][col] == '.':
                moves.append(Move((row, col), (two_forward, col), self.board[row][col]))

        #capture
        for dx in [-1, 1]:
            new_col = col + dx
            new_row = row + direction
            if 0 <= new_col < 8 and 0 <= new_row < 8:
                target = self.board[new_row][new_col]
                if target in enemy_pieces:
                    if new_row == 0 or new_row == 7:
                        moves.append(Move((row, col), (new_row, new_col), self.board[row][col], target, is_pawn_promotion=True, promotion_choice=promotion_choice))
                    else:
                        moves.append(Move((row, col), (new_row, new_col), self.board[row][col], target))

        #en passant
        if self.en_passant_square:
            ep_row, ep_col = self.en_passant_square
            if (row + direction, ep_col) == self.en_passant_square and abs (ep_col - col) == 1:
                moves.append(Move((row, col), self.en_passant_square, self.board[row][col], piece_captured='p' if is_white else 'P', is_en_passant=True))

    def _Generate_Knight_Moves (self, row: int, col: int, moves: list, is_white: bool):
        directions = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
        ally_pieces = [p.upper() for p in "PNBRQK"] if is_white else [p.lower() for p in "PNBRQK"]

        for dr, dc in directions:
            r, c = row + dr, col + dc

            if 0 <= r < 8 and 0 <= c < 8:
                target = self.board[r][c]
                if target == '.' or target not in ally_pieces:
                    moves.append (Move((row, col), (r, c), self.board[row][col], target if target != '.' else None))
    
    def _Generate_Bishop_Moves (self, row: int, col: int, moves: list, is_white: bool):
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        self._Slide_Moves(row, col, directions, moves, is_white)

    def _Generate_Rook_Moves (self, row: int, col: int, moves: list, is_white: bool):
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        self._Slide_Moves(row, col, directions, moves, is_white)

    def _Generate_Queen_Moves (self, row: int, col: int, moves: list, is_white: bool):
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1), (1, 0), (-1, 0), (0, 1), (0, -1)]
        self._Slide_Moves(row, col, directions, moves, is_white)

    def _Generate_King_Moves (self, row: int, col: int, moves: list, is_white: bool):
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1), (1, 0), (-1, 0), (0, 1), (0, -1)]
        ally_pieces = [p.upper() for p in "PNBRQK"] if is_white else [p.lower() for p in "PNBRQK"]

        for dr, dc in directions:
            r, c = row + dr, col + dc
            if 0 <= r < 8 and 0 <= c < 8:
                target = self.board[r][c]
                if target == '.' or target not in ally_pieces:
                    moves.append(Move((row, col), (r, c), self.board[row][col], target if target != '.' else None))

    def _Slide_Moves (self, row: int, col: int, directions: List[Tuple[int, int]], moves: list, is_white: bool):
        ally_pieces = [p.upper() for p in "PNBRQK"] if is_white else [p.lower() for p in "PNBRQK"]

        for dr, dc in directions:
            r, c = row + dr, col + dc
            while 0 <= r < 8 and 0 <= c < 8:
                target = self.board[r][c]
                if target == '.':
                    moves.append (Move((row, col), (r, c), self.board[row][col]))
                elif target in ally_pieces:
                    break
                elif target.lower() == 'k':
                    break
                else:
                    moves.append (Move((row, col), (r, c), self.board[row][col], target))
                    break
                r += dr
                c += dc

    def _Get_White_Castling_Moves (self, moves: list):
        if self.board[7][4] != 'K':
            return
        
        if "K" in self.castling_rights:
            if self.board[7][5] == '.' and self.board[7][6] == '.' and self.board[7][7] == 'R':
                if not self._Is_Square_Attacked((7, 4), False) and not self._Is_Square_Attacked((7, 5), False) and not self._Is_Square_Attacked((7, 6), False):
                    moves.append(Move((7, 4), (7, 6), "K", is_castling=True))

        if "Q" in self.castling_rights:
            if self.board[7][1] == '.' and self.board[7][2] == '.' and self.board[7][3] == '.' and self.board[7][0] == 'R':
                if not self._Is_Square_Attacked((7, 4), False) and not self._Is_Square_Attacked((7, 3), False) and not self._Is_Square_Attacked((7, 2), False):
                    moves.append(Move((7, 4), (7, 2), "K", is_castling=True))

    def _Get_Black_Castling_Moves (self, moves: list):
        if self.board[0][4] != 'k':
            return
        
        if "k" in self.castling_rights:
            if self.board[0][5] == '.' and self.board[0][6] == '.' and self.board[0][7] == 'r':
                if not self._Is_Square_Attacked((0, 4), True) and not self._Is_Square_Attacked((0, 5), True) and not self._Is_Square_Attacked((0, 6), True):
                    moves.append (Move((0, 4), (0, 6), "k", is_castling=True))

        if "q" in self.castling_rights:
            if self.board[0][3] == '.' and self.board[0][2] == '.' and self.board[0][1] == '.' and self.board[0][0] == 'r':
                if not self._Is_Square_Attacked((0, 4), True) and not self._Is_Square_Attacked((0, 3), True) and not self._Is_Square_Attacked((0, 2), True):
                    moves.append (Move((0, 4), (0, 2), "k", is_castling=True))

    _DIRECTIONS = [
        (1, 0), (-1, 0), (0, 1), (0, -1),
        (1, 1), (1, -1), (-1, 1), (-1, -1)
    ]
    _KNIGHT_JUMPS = [
        (2, 1), (1, 2), (-1, 2), (-2, 1),
        (-2, -1), (-1, -2), (1, -2), (2, -1)
    ]

    def _Is_Square_Attacked(self, position: tuple, by_white: bool) -> bool:
        row, col = position

        for dr, dc in self._DIRECTIONS:
            r, c = row + dr, col + dc
            while 0 <= r < 8 and 0 <= c < 8:
                piece = self.board[r][c]
                if piece == '.':
                    r += dr
                    c += dc
                    continue
                if piece.isupper() != by_white:
                    break
                if piece.upper() == 'Q':
                    return True
                if (dr == 0 or dc == 0) and piece.upper() == 'R':
                    return True
                if (dr != 0 and dc != 0) and piece.upper() == 'B':
                    return True
                break

        for dr, dc in self._KNIGHT_JUMPS:
            r, c = row + dr, col + dc
            if 0 <= r < 8 and 0 <= c < 8:
                piece = self.board[r][c]
                if piece.upper() == 'N' and piece.isupper() == by_white:
                    return True

        pawn_dir = 1 if by_white else -1
        for dc in [-1, 1]:
            r, c = row + pawn_dir, col + dc
            if 0 <= r < 8 and 0 <= c < 8:
                piece = self.board[r][c]
                if piece.upper() == 'P' and piece.isupper() == by_white:
                    return True

        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                r, c = row + dr, col + dc
                if 0 <= r < 8 and 0 <= c < 8:
                    piece = self.board[r][c]
                    if piece.upper() == 'K' and piece.isupper() == by_white:
                        return True

        return False


    def Generate_Legal_Moves(self, include_castling=True) -> list:
        import time
        t0 = time.perf_counter()
        
        pseudo_moves = self.Get_Pseudo_Legal_Moves(include_castling)
        legal_moves = []
        for move in pseudo_moves:
            self.Make_Move(move)
            if not self.Is_King_In_Check(move.piece_moved.isupper()):
                legal_moves.append(move)
            self.Undo_Move()
            
        t1 = time.perf_counter()
        Board.FIND_LEGAL_MOVES_TIME += t1 - t0
        return legal_moves

    def Generate_Legal_Capture_Moves(self) -> list:
        import time
        t0 = time.perf_counter()
        
        pseudo_noisy_moves = self._Generate_Pseudo_Legal_Capture_Moves()
        legal_capture_moves = []
        for move in pseudo_noisy_moves:
            self.Make_Move(move)
            if not self.Is_King_In_Check(move.piece_moved.isupper()):
                legal_capture_moves.append(move)
            self.Undo_Move()
            
        t1 = time.perf_counter()
        Board.FIND_LEGAL_MOVES_TIME += t1 - t0
        return legal_capture_moves

    def _Generate_Pseudo_Legal_Capture_Moves(self) -> list:
        pseudo_noisy_moves = []
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece == '.' or piece.isupper() != self.white_to_move:
                    continue
                piece_moves = []
                self._Generate_Piece_Moves(piece, row, col, piece_moves, include_castling=False)
                for move in piece_moves:
                    if move.piece_captured or move.is_pawn_promotion:
                        pseudo_noisy_moves.append(move)
        return pseudo_noisy_moves

    def Is_King_In_Check(self, white: Optional[bool] = None) -> bool:
        king_is_white = self.white_to_move if white is None else white
        king_pos = self.Find_King(king_is_white)
        if king_pos == (-1, -1):
            return False
        return self._Is_Square_Attacked(king_pos, not king_is_white)

    def Find_King (self, white: bool) -> Tuple[int, int]:
        return self.white_king_pos if white else self.black_king_pos
        
    def Make_Move(self, move: Move):
        from_row, from_col = move.start
        to_row, to_col = move.end
        captured_piece = self.board[to_row][to_col]

        state = {
            'move': move,
            'captured_piece': captured_piece,
            'castling_rights': self.castling_rights.copy(),
            'en_passant_square': self.en_passant_square,
            'halfmove_clock': self.halfmove_clock,
            'fullmove_number': self.fullmove_number,
            'white_to_move': self.white_to_move,
            'moved_piece': self.board[from_row][from_col],
            'zobrist_key': self.zobrist_key,
            'white_king_pos': self.white_king_pos,
            'black_king_pos': self.black_king_pos,
        }

        # Remove old turn
        if self.white_to_move:
            self.zobrist_key ^= ZOBRIST_TURN

        # Remove old en_passant
        if self.en_passant_square:
            self.zobrist_key ^= ZOBRIST_EN_PASSANT[self.en_passant_square[1]]

        # Remove old castling
        for cr in self.castling_rights:
            self.zobrist_key ^= ZOBRIST_CASTLING[cr]

        moved_piece = self.board[from_row][from_col]
        
        # Remove old location of moved_piece
        self.zobrist_key ^= ZOBRIST_PIECES[(moved_piece, from_row, from_col)]

        if captured_piece != '.':
            self.zobrist_key ^= ZOBRIST_PIECES[(captured_piece, to_row, to_col)]

        if move.is_en_passant:
            capture_row = to_row + (1 if self.white_to_move else -1)
            state['ep_capture'] = (capture_row, to_col, self.board[capture_row][to_col])
            ep_captured_piece = self.board[capture_row][to_col]
            self.zobrist_key ^= ZOBRIST_PIECES[(ep_captured_piece, capture_row, to_col)]
            self.board[capture_row][to_col] = '.'

        if move.is_castling:
            if to_col - from_col == 2:
                rook_from = (from_row, 7)
                rook_to = (from_row, 5)
            else:
                rook_from = (from_row, 0)
                rook_to = (from_row, 3)
            state['rook_move'] = (rook_from, rook_to)
            rook_piece = self.board[rook_from[0]][rook_from[1]]
            self.zobrist_key ^= ZOBRIST_PIECES[(rook_piece, rook_from[0], rook_from[1])]
            self.zobrist_key ^= ZOBRIST_PIECES[(rook_piece, rook_to[0], rook_to[1])]
            self.board[rook_to[0]][rook_to[1]] = rook_piece
            self.board[rook_from[0]][rook_from[1]] = '.'

        self.move_history.append(state)
        self.en_passant_square = None

        if move.piece_moved.upper() == "P" and abs(from_row - to_row) == 2:
            mid_row = (from_row + to_row) // 2
            self.en_passant_square = (mid_row, from_col)
            self.zobrist_key ^= ZOBRIST_EN_PASSANT[from_col]

        if move.is_pawn_promotion:
            promotion_choice = (move.promotion_choice or 'Q').upper()
            promoted_piece = promotion_choice if moved_piece.isupper() else promotion_choice.lower()
            self.board[to_row][to_col] = promoted_piece
            self.zobrist_key ^= ZOBRIST_PIECES[(promoted_piece, to_row, to_col)]
        else:
            self.board[to_row][to_col] = moved_piece
            self.zobrist_key ^= ZOBRIST_PIECES[(moved_piece, to_row, to_col)]
            if moved_piece == 'K':
                self.white_king_pos = (to_row, to_col)
            elif moved_piece == 'k':
                self.black_king_pos = (to_row, to_col)

        self.board[from_row][from_col] = '.'

        # Update castling rights when rooks or king move
        if moved_piece == 'K':
            self.castling_rights.discard('K')
            self.castling_rights.discard('Q')
        elif moved_piece == 'k':
            self.castling_rights.discard('k')
            self.castling_rights.discard('q')
        elif moved_piece == 'R' and move.start == (7, 0):
            self.castling_rights.discard('Q')
        elif moved_piece == 'R' and move.start == (7, 7):
            self.castling_rights.discard('K')
        elif moved_piece == 'r' and move.start == (0, 0):
            self.castling_rights.discard('q')
        elif moved_piece == 'r' and move.start == (0, 7):
            self.castling_rights.discard('k')

        if captured_piece == 'R' and move.end == (7, 0):
            self.castling_rights.discard('Q')
        elif captured_piece == 'R' and move.end == (7, 7):
            self.castling_rights.discard('K')
        elif captured_piece == 'r' and move.end == (0, 0):
            self.castling_rights.discard('q')
        elif captured_piece == 'r' and move.end == (0, 7):
            self.castling_rights.discard('k')

        # Add new castling
        for cr in self.castling_rights:
            self.zobrist_key ^= ZOBRIST_CASTLING[cr]

        self.white_to_move = not self.white_to_move
        if self.white_to_move:
            self.zobrist_key ^= ZOBRIST_TURN

        if move.piece_captured or moved_piece.upper() == "P":
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        if self.white_to_move:
            self.fullmove_number += 1

        if self.track_repetition:
            state['hash'] = self.Hash_Board()
            self.position_history[state['hash']] = self.position_history.get(state['hash'], 0) + 1

        move.gives_check = self.Is_King_In_Check(self.white_to_move)

        return True


    def Make_Null_Move(self):
        self.move_history.append({
            'move': None,
            'castling_rights': self.castling_rights.copy(),
            'en_passant_square': self.en_passant_square,
            'halfmove_clock': self.halfmove_clock,
            'fullmove_number': self.fullmove_number,
            'white_to_move': self.white_to_move,
            'zobrist_key': self.zobrist_key,
            'white_king_pos': self.white_king_pos,
            'black_king_pos': self.black_king_pos,
        })
        if self.white_to_move:
            self.zobrist_key ^= ZOBRIST_TURN
        
        if self.en_passant_square:
            self.zobrist_key ^= ZOBRIST_EN_PASSANT[self.en_passant_square[1]]
            self.en_passant_square = None
            
        self.white_to_move = not self.white_to_move
        if self.white_to_move:
            self.zobrist_key ^= ZOBRIST_TURN
            
        self.halfmove_clock += 1
        if self.white_to_move:
            self.fullmove_number += 1

    def Undo_Null_Move(self):
        last_state = self.move_history.pop()
        self.castling_rights = last_state['castling_rights']
        self.en_passant_square = last_state['en_passant_square']
        self.halfmove_clock = last_state['halfmove_clock']
        self.fullmove_number = last_state['fullmove_number']
        self.white_to_move = last_state['white_to_move']
        self.zobrist_key = last_state['zobrist_key']
        self.white_king_pos = last_state['white_king_pos']
        self.black_king_pos = last_state['black_king_pos']

    def Undo_Move (self):
        if not self.move_history:
            return

        last_state = self.move_history.pop()
        move = last_state['move']
        from_row, from_col = move.start
        to_row, to_col = move.end

        # Restore moved piece
        if move.is_pawn_promotion:
            self.board[from_row][from_col] = last_state['moved_piece']
            self.board[to_row][to_col] = last_state['captured_piece']
        else:
            self.board[from_row][from_col] = last_state['moved_piece']
            self.board[to_row][to_col] = last_state['captured_piece']

        # Undo en passant capture
        if move.is_en_passant and 'ep_capture' in last_state:
            r, c, piece = last_state['ep_capture']
            self.board[r][c] = piece

        # Undo castling rook move
        if move.is_castling and 'rook_move' in last_state:
            rook_from, rook_to = last_state['rook_move']
            self.board[rook_from[0]][rook_from[1]] = self.board[rook_to[0]][rook_to[1]]
            self.board[rook_to[0]][rook_to[1]] = '.'

        self.castling_rights = last_state['castling_rights']
        self.en_passant_square = last_state['en_passant_square']
        self.halfmove_clock = last_state['halfmove_clock']
        self.fullmove_number = last_state['fullmove_number']
        self.white_to_move = last_state['white_to_move']
        self.zobrist_key = last_state['zobrist_key']
        self.white_king_pos = last_state['white_king_pos']
        self.black_king_pos = last_state['black_king_pos']

        if self.track_repetition and 'hash' in last_state:
            key = last_state['hash']
            if key in self.position_history:
                self.position_history[key] -= 1
                if self.position_history[key] == 0:
                    del self.position_history[key]

    def Is_Threefold_Repetition (self) -> bool:
        key = self.Hash_Board()
        return self.position_history.get(key, 0) >= 3
    
    def Is_Fifty_Move_Rule (self) -> bool:
        return self.halfmove_clock >= 100
