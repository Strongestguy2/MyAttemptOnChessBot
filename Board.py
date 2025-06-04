from typing import Optional, Tuple, List, Set
from Move import Move
from Zobrist import hash_board



class Board:
    FIND_LEGAL_MOVES_TIME = 0

    def __init__(self):
        self.board = [
            ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
            ['p'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['.'] * 8,
            ['P'] * 8,
            ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
        ]

        self.white_to_move = True
        self.castling_rights = {'K', 'Q', 'k', 'q'}
        self.en_passant_square :  Optional [Tuple[int, int]] = None
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.move_history = []
        self.position_history = {}
        self.track_repetition = True

    def Print_Board (self):
        for row in self.board:
            print (' '.join(row))

        print (f"turn: {'white' if self.white_to_move else 'black'}")
        print (f"castling rights: {self.castling_rights}")
        print (f"en passant square: {self.en_passant_square}")
        print (f"halfmove clock: {self.halfmove_clock}")
        print (f"fullmove number: {self.fullmove_number}")
    
    def Hash_Board(self) -> str:
        return hash_board(self)
    
    def Copy_For_Color(self, white: bool):
        clone = Board.__new__(Board)
        clone.board = [row[:] for row in self.board]
        clone.white_to_move = white
        clone.castling_rights = self.castling_rights.copy()
        clone.en_passant_square = self.en_passant_square
        clone.halfmove_clock = self.halfmove_clock
        clone.fullmove_number = self.fullmove_number
        clone.move_history = []
        clone.position_history = self.position_history.copy()
        clone.track_repetition = self.track_repetition
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
    
    def _Generate_Piece_Moves (self, piece: str, row: int, col: int, moves: list, include_castling = True):
        piece_type = piece.upper()

        if piece_type == 'P':
            self._Generate_Pawn_Moves (row, col, moves)
        elif piece_type == 'N':
            self._Generate_Knight_Moves (row, col, moves)
        elif piece_type == 'B':
            self._Generate_Bishop_Moves (row, col, moves)
        elif piece_type == 'R':
            self._Generate_Rook_Moves (row, col, moves)
        elif piece_type == 'Q':
            self._Generate_Queen_Moves (row, col, moves)
        elif piece_type == 'K':
            self._Generate_King_Moves (row, col, moves)
        
        if piece_type == 'K' and include_castling:
            if self.white_to_move:
                self._Get_White_Castling_Moves(moves)
            else:
                self._Get_Black_Castling_Moves(moves)

    def _Generate_Pawn_Moves (self, row: int, col: int, moves: list):
        direction = -1 if self.white_to_move else 1
        start_row = 6 if self.white_to_move else 1
        enemy_pieces = [p.lower() for p in "pnbrqk"] if self.white_to_move else [p.upper() for p in "PNBRQK"]

        #forward 1
        if self.board[row + direction][col] == '.':
            end_row = row + direction
            if end_row == 0 or end_row == 7:
                moves.append (Move((row, col), (end_row, col), self.board[row][col], is_pawn_promotion=True, promotion_choice = 'Q'))
            else:
                moves.append (Move((row, col), (end_row, col), self.board[row][col]))
        
        #forward 2
        if row == start_row and self.board[row + 2 * direction][col] == '.':
            moves.append (Move((row, col), (row + 2 * direction, col), self.board[row][col]))

        #capture
        for dx in [-1, 1]:
            new_col = col + dx
            new_row = row + direction
            if 0 <= new_col < 8 and 0 <= new_row < 8:
                target = self.board[new_row][new_col]
                if target in enemy_pieces:
                    if new_row == 0 or new_row == 7:
                        moves.append (Move((row, col), (new_row, new_col), self.board[row][col], target, is_pawn_promotion=True, promotion_choice = 'Q'))
                    else:
                        moves.append (Move((row, col), (new_row, new_col), self.board[row][col], target))

        #en passant
        if self.en_passant_square:
            ep_row, ep_col = self.en_passant_square
            if (row + direction, ep_col) == self.en_passant_square and abs (ep_col - col) == 1:
                moves.append (Move((row, col), self.en_passant_square, self.board[row][col], piece_captured='p' if self.white_to_move else 'P', is_en_passant=True))

    def _Generate_Knight_Moves (self, row: int, col: int, moves: list):
        directions = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
        ally_pieces = [p.upper() for p in "PNBRQK"] if self.white_to_move else [p.lower() for p in "pnbrqk"]

        for dr, dc in directions:
            r, c = row + dr, col + dc

            if 0 <= r < 8 and 0 <= c < 8:
                target = self.board[r][c]
                if target == '.' or target not in ally_pieces:
                    moves.append (Move((row, col), (r, c), self.board[row][col], target if target != '.' else None))
    
    def _Generate_Bishop_Moves (self, row: int, col: int, moves: list):
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        self._Slide_Moves (row, col, directions, moves)

    def _Generate_Rook_Moves (self, row: int, col: int, moves: list):
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        self._Slide_Moves (row, col, directions, moves)

    def _Generate_Queen_Moves (self, row: int, col: int, moves: list):
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1), (1, 0), (-1, 0), (0, 1), (0, -1)]
        self._Slide_Moves (row, col, directions, moves)

    def _Generate_King_Moves (self, row: int, col: int, moves: list):
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1), (1, 0), (-1, 0), (0, 1), (0, -1)]
        ally_pieces = [p.upper() for p in "PNBRQK"] if self.white_to_move else [p.lower() for p in "pnbrqk"]

        for dr, dc in directions:
            r, c = row + dr, col + dc
            if 0 <= r < 8 and 0 <= c < 8:
                target = self.board[r][c]
                if target == '.' or target not in ally_pieces:
                    test_move = Move((row, col), (r, c), self.board[row][col], target if target != '.' else None)
                    self.Make_Move(test_move)
                    in_check = self.Is_King_In_Check()
                    self.Undo_Move()
                    if not in_check:
                        moves.append(test_move)

    def _Slide_Moves (self, row: int, col: int, directions: List[Tuple[int, int]], moves: list):
        ally_pieces = [p.upper() for p in "PNBRQK"] if self.white_to_move else [p.lower() for p in "pnbrqk"]

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
                if not self._Is_Square_Attacked((7, 4)) and not self._Is_Square_Attacked((7, 5)) and not self._Is_Square_Attacked((7, 6)):
                    moves.append(Move((7, 4), (7, 6), "K", is_castling=True))

        if "Q" in self.castling_rights:
            if self.board[7][1] == '.' and self.board[7][2] == '.' and self.board[7][3] == '.' and self.board[7][0] == 'R':
                if not self._Is_Square_Attacked((7, 4)) and not self._Is_Square_Attacked((7, 3)) and not self._Is_Square_Attacked((7, 2)):
                    moves.append(Move((7, 4), (7, 2), "K", is_castling=True))

    def _Get_Black_Castling_Moves (self, moves: list):
        if self.board[0][4] != 'k':
            return
        
        if "k" in self.castling_rights:
            if self.board[0][5] == '.' and self.board[0][6] == '.' and self.board[0][7] == 'r':
                if not self._Is_Square_Attacked ((0, 4)) and not self._Is_Square_Attacked ((0, 5)) and not self._Is_Square_Attacked ((0, 6)):
                    moves.append (Move((0, 4), (0, 6), "k", is_castling=True))

        if "q" in self.castling_rights:
            if self.board[0][3] == '.' and self.board[0][2] == '.' and self.board[0][1] == '.' and self.board[0][0] == 'r':
                if not self._Is_Square_Attacked ((0, 4)) and not self._Is_Square_Attacked ((0, 3)) and not self._Is_Square_Attacked ((0, 2)):
                    moves.append (Move((0, 4), (0, 2), "k", is_castling=True))

    def _Is_Square_Attacked(self, position: tuple) -> bool:
        row, col = position
        enemy_pieces = [p.lower() for p in "pnbrqk"] if self.white_to_move else [p.upper() for p in "PNBRQK"]

        directions = [
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (1, -1), (-1, 1), (-1, -1)
        ]

        knight_jumps = [
            (2, 1), (1, 2), (-1, 2), (-2, 1),
            (-2, -1), (-1, -2), (1, -2), (2, -1)
        ]

        for dr, dc in directions:
            r, c = row + dr, col + dc
            while 0 <= r < 8 and 0 <= c < 8:
                piece = self.board[r][c]
                if piece == '.':
                    r += dr
                    c += dc
                    continue
                if piece.isupper() == self.white_to_move:
                    break
                if piece.upper() == 'Q':
                    return True
                if (dr == 0 or dc == 0) and piece.upper() == 'R':
                    return True
                if (dr != 0 and dc != 0) and piece.upper() == 'B':
                    return True
                break

        for dr, dc in knight_jumps:
            r, c = row + dr, col + dc
            if 0 <= r < 8 and 0 <= c < 8:
                piece = self.board[r][c]
                if piece.upper() == 'N' and piece.isupper() != self.white_to_move:
                    return True

        pawn_dir = -1 if self.white_to_move else 1
        for dc in [-1, 1]:
            r, c = row + pawn_dir, col + dc
            if 0 <= r < 8 and 0 <= c < 8:
                piece = self.board[r][c]
                if piece.upper() == 'P' and piece.isupper() != self.white_to_move:
                    return True

        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                r, c = row + dr, col + dc
                if 0 <= r < 8 and 0 <= c < 8:
                    piece = self.board[r][c]
                    if piece.upper() == 'K' and piece.isupper() != self.white_to_move:
                        return True

        return False
    
    def Generate_Legal_Moves(self, include_castling=True) -> list:
        import time
        t0 = time.perf_counter()
        all_moves = []
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece == "." or piece.isupper() != self.white_to_move:
                    continue
                self._Generate_Piece_Moves(piece, row, col, all_moves, include_castling=include_castling)

        legal_moves = []
        for move in all_moves:
            if not self.Make_Move(move):
                continue
            if not self.Is_King_In_Check():
                legal_moves.append(move)
            self.Undo_Move()

        t1 = time.perf_counter()
        Board.FIND_LEGAL_MOVES_TIME += t1 - t0
        return legal_moves
    
    def Is_King_In_Check(self) -> bool:
        self.white_to_move = not self.white_to_move  # temporarily flip
        king_pos = self.Find_King(self.white_to_move)
        in_check = self._Is_Square_Attacked(king_pos)
        self.white_to_move = not self.white_to_move  # flip back
        return in_check

    def Find_King (self, white: bool) -> Tuple[int, int]:
        king_symbol = 'K' if white else 'k'
        for row in range(8):
            for col in range(8):
                if self.board[row][col] == king_symbol:
                    return (row, col)
        return (-1, -1)
        
    def Make_Move(self, move: Move):
        from_row, from_col = move.start
        to_row, to_col = move.end

        state = {
            'move': move,
            'captured_piece': self.board[to_row][to_col],
            'castling_rights': self.castling_rights.copy(),
            'en_passant_square': self.en_passant_square,
            'halfmove_clock': self.halfmove_clock,
            'fullmove_number': self.fullmove_number,
            'white_to_move': self.white_to_move,
            'moved_piece': self.board[from_row][from_col],
        }

        if move.is_en_passant:
            capture_row = to_row + (1 if self.white_to_move else -1)
            state['ep_capture'] = (capture_row, to_col, self.board[capture_row][to_col])
            self.board[capture_row][to_col] = '.'

        if move.is_castling:
            if to_col - from_col == 2:
                rook_from = (from_row, 7)
                rook_to = (from_row, 5)
            else:
                rook_from = (from_row, 0)
                rook_to = (from_row, 3)
            state['rook_move'] = (rook_from, rook_to)
            self.board[rook_to[0]][rook_to[1]] = self.board[rook_from[0]][rook_from[1]]
            self.board[rook_from[0]][rook_from[1]] = '.'

        self.move_history.append(state)
        self.en_passant_square = None

        if move.piece_moved.upper() == "P" and abs(from_row - to_row) == 2:
            mid_row = (from_row + to_row) // 2
            self.en_passant_square = (mid_row, from_col)

        moved_piece = self.board[from_row][from_col]
        if move.is_pawn_promotion:
            self.board[to_row][to_col] = move.promotion_choice
        else:
            self.board[to_row][to_col] = moved_piece

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

        self.white_to_move = not self.white_to_move

        if move.piece_captured or moved_piece.upper() == "P":
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        if not self.white_to_move:
            self.fullmove_number += 1

        if self.track_repetition:
            state['hash'] = self.Hash_Board()
            self.position_history[state['hash']] = self.position_history.get(state['hash'], 0) + 1

        return True

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

