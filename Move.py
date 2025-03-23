from typing import Tuple, Optional

class Move:
    def __init__(
            self,
            start: Tuple[int, int],
            end: Tuple[int, int],
            piece_moved: str,
            piece_captured: Optional[str] = None,
            is_pawn_promotion: bool = False,
            promotion_choice: Optional[str] = None,
            is_en_passant: bool = False,
            is_castling: bool = False,
    ):
        self.start = start
        self.end = end
        self.piece_moved = piece_moved
        self.piece_captured = piece_captured
        self.is_pawn_promotion = is_pawn_promotion
        self.promotion_choice = promotion_choice
        self.is_en_passant = is_en_passant
        self.is_castling = is_castling

    def __str__ (self):
        return f"{self.piece_moved} {self.start} -> {self.end}" + \
                (f" capture {self.piece_captured}" if self.piece_captured else "") + \
                (f" promotion " if self.is_pawn_promotion else "") + \
                (f" en passant" if self.is_en_passant else "") + \
                (f" castling" if self.is_castling else "")
    
example_move = Move(start=(6, 4), end=(4, 4), piece_moved='P')
print(example_move)
