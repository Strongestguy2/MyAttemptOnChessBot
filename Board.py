from typing import Optional, Tuple, List, Set
from Move import Move

class Board:
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


    def Print_Board (self):
        for row in self.board:
            print (' '.join(row))

        print (f"turn: {'white' if self.white_to_move else 'black'}")
        print (f"castling rights: {self.castling_rights}")
        print (f"en passant square: {self.en_passant_square}")
        print (f"halfmove clock: {self.halfmove_clock}")
        print (f"fullmove number: {self.fullmove_number}")
    
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
        if piece == 'P':
            self._Generate_Pawn_Moves (row, col, moves)
        elif piece == 'N':
            self._Generate_Knight_Moves (row, col, moves)
        elif piece == 'B':
            self._Generate_Bishop_Moves (row, col, moves)
        elif piece == 'R':
            self._Generate_Rook_Moves (row, col, moves)
        elif piece == 'Q':
            self._Generate_Queen_Moves (row, col, moves)
        elif piece == 'K':
            self._Generate_King_Moves (row, col, moves)
        
        if str (piece).upper() == 'K' and include_castling:
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
                if target == '.':
                    moves.append (Move((row, col), (r, c), self.board[row][col]))
                elif target not in ally_pieces:
                    moves.append (Move((row, col), (r, c), self.board[row][col], target))

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
                else:
                    moves.append (Move((row, col), (r, c), self.board[row][col], target))
                    break
                r += dr
                c += dc

    def _Get_White_Castling_Moves (self, moves: list):
        if "K" in self.castling_rights:
            if self.board[7][5] == '.' and self.board[7][6] == '.':
                if not self._Is_Square_Attacked ((7, 4)) and not self._Is_Square_Attacked ((7, 5)) and not self._Is_Square_Attacked ((7, 6)):
                    moves.append (Move((7, 4), (7, 6), "K", is_castling=True))

        if "Q" in self.castling_rights:
            if self.board[7][3] == '.' and self.board[7][2] == '.' and self.board[7][1] == '.':
                if not self._Is_Square_Attacked ((7, 4)) and not self._Is_Square_Attacked ((7, 3)) and not self._Is_Square_Attacked ((7, 2)):
                    moves.append (Move((7, 4), (7, 2), "K", is_castling=True))

    def _Get_Black_Castling_Moves (self, moves: list):
        if "k" in self.castling_rights:
            if self.board[0][5] == '.' and self.board[0][6] == '.':
                if not self._Is_Square_Attacked ((0, 4)) and not self._Is_Square_Attacked ((0, 5)) and not self._Is_Square_Attacked ((0, 6)):
                    moves.append (Move((0, 4), (0, 6), "k", is_castling=True))

        if "q" in self.castling_rights:
            if self.board[0][3] == '.' and self.board[0][2] == '.' and self.board[0][1] == '.':
                if not self._Is_Square_Attacked ((0, 4)) and not self._Is_Square_Attacked ((0, 3)) and not self._Is_Square_Attacked ((0, 2)):
                    moves.append (Move((0, 4), (0, 2), "k", is_castling=True))

    def _Is_Square_Attacked (self, position: tuple) -> bool:
        enemy_moves = []
        self.white_to_move = not self.white_to_move
        enemy_moves = self.Get_Pseudo_Legal_Moves(include_castling=False)
        self.white_to_move = not self.white_to_move

        for move in enemy_moves:
            if move.end == position:
                return True
        
        return False
    
    def Generate_Legal_Moves (self) -> list:
        legal_moves = []

        for move in self.Get_Pseudo_Legal_Moves():
            self.Make_Move(move)
            if not self.Is_King_In_Check():
                legal_moves.append(move)
            self.Undo_Move()

        return legal_moves
    
    def Is_King_In_Check (self) -> bool:
        king_symbol = 'K' if self.white_to_move else 'k'

        for row in range(8):
            for col in range(8):
                if self.board[row][col] == king_symbol:
                    return self._Is_Square_Attacked ((row, col))
        
        return False

    def Find_King (self, white: bool) -> Tuple[int, int]:
        king_symbol = 'K' if white else 'k'
        for row in range(8):
            for col in range(8):
                if self.board[row][col] == king_symbol:
                    return (row, col)
        return (-1, -1)
        
    def Make_Move (self, move: Move):
        from_row, from_col = move.start
        to_row, to_col = move.end

        state = {
            'board_snapshot': [row.copy() for row in self.board],
            'white_to_move': self.white_to_move,
            'castling_rights': self.castling_rights.copy(),
            'en_passant_square': self.en_passant_square,
            'halfmove_clock': self.halfmove_clock,
            'fullmove_number': self.fullmove_number
        }
        self.move_history.append (state)

        self.en_passant_square = None

        if move.piece_moved.upper() == "P" and abs (move.start[0] - move.end[0]) == 2:
            mid_row = (move.start[0] + move.end[0]) // 2
            self.en_passant_square = (mid_row, move.start[1])
        
        if move.is_en_passant:
            capture_row = move.start[0]
            self.board[capture_row][to_col] = '.'

        self.board[to_row][to_col] = move.promotion_choice if move.is_pawn_promotion else move.piece_moved
        self.board[from_row][from_col] = '.'

        self.white_to_move = not self.white_to_move

        if move.piece_captured or move.piece_moved.upper() == "P":
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        if not self.white_to_move:
            self.fullmove_number += 1

        if move.is_castling:
            if move.end == (7, 6):
                self.board[7][5] = 'R'
                self.board[7][7] = '.'
            elif move.end == (7, 2):
                self.board[7][3] = 'R'
                self.board[7][0] = '.'
            elif move.end == (0, 6):
                self.board[0][5] = 'r'
                self.board[0][7] = '.'
            elif move.end == (0, 2):
                self.board[0][3] = 'r'
                self.board[0][0] = '.'
        
        if move.piece_moved.upper() == "K":
            self.castling_rights.discard('K')
            self.castling_rights.discard('Q')
        elif move.piece_moved.upper() == "R":
            if move.start == (7, 7):
                self.castling_rights.discard('K')
            elif move.start == (7, 0):
                self.castling_rights.discard('Q')
        elif move.piece_moved.upper() == "r":
            if move.start == (0, 7):
                self.castling_rights.discard('k')
            elif move.start == (0, 0):
                self.castling_rights.discard('q')

    def Undo_Move (self):
        if not self.move_history:
            return
        
        last_state = self.move_history.pop()
        self.board = last_state['board_snapshot']
        self.white_to_move = last_state['white_to_move']
        self.castling_rights = last_state['castling_rights']
        self.en_passant_square = last_state['en_passant_square']
        self.halfmove_clock = last_state['halfmove_clock']
        self.fullmove_number = last_state['fullmove_number']

board = Board()
board.Print_Board()
