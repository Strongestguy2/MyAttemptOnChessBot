from typing import Tuple, Optional

class Move:
    __slots__ = (
        "start",
        "end",
        "piece_moved",
        "piece_captured",
        "is_pawn_promotion",
        "promotion_choice",
        "is_en_passant",
        "is_castling",
        "gives_check",
    )

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
            gives_check: bool = False,
    ):
        self.start = start
        self.end = end
        self.piece_moved = piece_moved
        self.piece_captured = piece_captured
        self.is_pawn_promotion = is_pawn_promotion
        self.promotion_choice = promotion_choice
        self.is_en_passant = is_en_passant
        self.is_castling = is_castling
        self.gives_check = gives_check

    def __str__ (self):
        return f"{self.piece_moved} {self.start} -> {self.end}" + \
                (f" capture {self.piece_captured}" if self.piece_captured else "") + \
                (f" promotion " if self.is_pawn_promotion else "") + \
                (f" en passant" if self.is_en_passant else "") + \
                (f" castling" if self.is_castling else "")

    def __eq__(self, other):
        if not isinstance(other, Move):
            return False
        return (
            self.start == other.start and
            self.end == other.end and
            self.piece_moved == other.piece_moved and
            self.piece_captured == other.piece_captured and
            self.is_pawn_promotion == other.is_pawn_promotion and
            self.promotion_choice == other.promotion_choice and
            self.is_en_passant == other.is_en_passant and
            self.is_castling == other.is_castling
        )

    def __hash__(self):
        return hash(
            (
                self.start,
                self.end,
                self.piece_moved,
                self.piece_captured,
                self.is_pawn_promotion,
                self.promotion_choice,
                self.is_en_passant,
                self.is_castling,
            )
        )
    
    def To_UCI(self):
        start_sq = chr(self.start[1] + ord('a')) + str(8 - self.start[0])
        end_sq = chr(self.end[1] + ord('a')) + str(8 - self.end[0])
        promo = ('' if not self.is_pawn_promotion else self.promotion_choice.lower())
        return start_sq + end_sq + promo
