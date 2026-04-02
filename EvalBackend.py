import json
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


PIECE_ORDER = ("P", "N", "B", "R", "Q", "K", "p", "n", "b", "r", "q", "k")
PIECE_INDEX = {piece: index for index, piece in enumerate(PIECE_ORDER)}
PHASE_WEIGHTS = {"N": 1, "B": 1, "R": 2, "Q": 4}
MATERIAL_VALUES = {
    "P": 100,
    "N": 320,
    "B": 330,
    "R": 500,
    "Q": 900,
    "K": 0,
    "p": 100,
    "n": 320,
    "b": 330,
    "r": 500,
    "q": 900,
    "k": 0,
}


@dataclass(slots=True)
class FeatureVector:
    side_to_move: int
    white_king_square: int
    black_king_square: int
    phase: int
    white_material: int
    black_material: int
    piece_counts: tuple[int, ...]
    occupancy: tuple[int, ...]

    def as_dense(self) -> tuple[float, ...]:
        return (
            self.occupancy
            + (
                float(self.side_to_move),
                float(self.white_king_square),
                float(self.black_king_square),
                float(self.phase),
                float(self.white_material),
                float(self.black_material),
            )
            + tuple(float(value) for value in self.piece_counts)
        )


@dataclass(slots=True)
class StubNNUEWeights:
    bias: float
    side_to_move_weight: float
    phase_weight: float
    material_balance_weight: float
    king_activity_weight: float
    piece_count_weights: tuple[float, ...]

    @classmethod
    def default(cls) -> "StubNNUEWeights":
        return cls(
            bias=0.0,
            side_to_move_weight=8.0,
            phase_weight=0.5,
            material_balance_weight=0.0125,
            king_activity_weight=1.5,
            piece_count_weights=(
                100.0, 320.0, 330.0, 500.0, 900.0, 0.0,
                -100.0, -320.0, -330.0, -500.0, -900.0, 0.0,
            ),
        )

    @classmethod
    def from_payload(cls, payload: dict) -> "StubNNUEWeights":
        default = cls.default()
        piece_count_weights = payload.get("piece_count_weights", list(default.piece_count_weights))
        if len(piece_count_weights) != len(PIECE_ORDER):
            raise ValueError("piece_count_weights must have length 12")
        return cls(
            bias=float(payload.get("bias", default.bias)),
            side_to_move_weight=float(payload.get("side_to_move_weight", default.side_to_move_weight)),
            phase_weight=float(payload.get("phase_weight", default.phase_weight)),
            material_balance_weight=float(payload.get("material_balance_weight", default.material_balance_weight)),
            king_activity_weight=float(payload.get("king_activity_weight", default.king_activity_weight)),
            piece_count_weights=tuple(float(value) for value in piece_count_weights),
        )


@runtime_checkable
class EvalBackend(Protocol):
    def load(self, weights_path: str | None = None) -> None:
        ...

    def is_ready(self) -> bool:
        ...

    def evaluate(self, features: FeatureVector) -> float:
        ...


def _square_index(row: int, col: int) -> int:
    return row * 8 + col


def _king_activity(square_index: int, white: bool) -> float:
    if square_index < 0:
        return 0.0
    row = square_index // 8
    col = square_index % 8
    mirrored_row = row if white else 7 - row
    return 7.0 - (abs(mirrored_row - 3.5) + abs(col - 3.5))


def extract_features_from_board(board) -> FeatureVector:
    occupancy = [0] * (len(PIECE_ORDER) * 64)
    piece_counts = [0] * len(PIECE_ORDER)
    white_material = 0
    black_material = 0
    phase = 0
    white_king_square = -1
    black_king_square = -1

    for row, board_row in enumerate(board.board):
        for col, piece in enumerate(board_row):
            if piece == ".":
                continue
            piece_index = PIECE_INDEX[piece]
            square_index = _square_index(row, col)
            occupancy[piece_index * 64 + square_index] = 1
            piece_counts[piece_index] += 1
            if piece.isupper():
                white_material += MATERIAL_VALUES[piece]
            else:
                black_material += MATERIAL_VALUES[piece]
            phase += PHASE_WEIGHTS.get(piece.upper(), 0)
            if piece == "K":
                white_king_square = square_index
            elif piece == "k":
                black_king_square = square_index

    return FeatureVector(
        side_to_move=1 if board.white_to_move else -1,
        white_king_square=white_king_square,
        black_king_square=black_king_square,
        phase=max(0, min(24, phase)),
        white_material=white_material,
        black_material=black_material,
        piece_counts=tuple(piece_counts),
        occupancy=tuple(occupancy),
    )


class StubNNUEBackend:
    def __init__(self):
        self.weights = StubNNUEWeights.default()
        self._ready = True

    def load(self, weights_path: str | None = None) -> None:
        if not weights_path:
            self.weights = StubNNUEWeights.default()
            self._ready = True
            return

        with open(weights_path, "r", encoding="utf-8") as weights_file:
            payload = json.load(weights_file)
        self.weights = StubNNUEWeights.from_payload(payload)
        self._ready = True

    def is_ready(self) -> bool:
        return self._ready

    def evaluate(self, features: FeatureVector) -> float:
        weights = self.weights
        score = weights.bias
        score += features.side_to_move * weights.side_to_move_weight
        score += (features.phase - 12) * weights.phase_weight
        score += (features.white_material - features.black_material) * weights.material_balance_weight
        score += _king_activity(features.white_king_square, True) * weights.king_activity_weight
        score -= _king_activity(features.black_king_square, False) * weights.king_activity_weight
        score += sum(count * weight for count, weight in zip(features.piece_counts, weights.piece_count_weights))
        return score
