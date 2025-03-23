from Board import Board
from Move import Move
import Engine

if __name__ == "__main__":
    board = Board()

    # Custom test board — white has passed pawn on e6
    board.board = [
        ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
        ['p', 'p', 'p', '.', 'p', 'p', 'p', 'p'],
        ['.', '.', '.', 'p', '.', '.', '.', '.'],
        ['.', '.', '.', '.', '.', '.', '.', '.'],
        ['.', '.', '.', '.', '.', '.', '.', '.'],
        ['.', '.', '.', 'P', '.', '.', '.', '.'],
        ['P', 'P', 'P', '.', 'P', 'P', 'P', 'P'],
        ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
    ]
    board.white_to_move = True
    board.castling_rights = {'K', 'Q', 'k', 'q'}
    board.en_passant_square = None
    board.halfmove_clock = 0
    board.fullmove_number = 1

    board.Print_Board()

    print("\nBot is thinking...")
    best_move = Engine.Find_Best_Move(board, depth=4)
    print(f"\nBot chose: {best_move}")
    board.Make_Move(best_move)
    board.Print_Board()
    print(f"Transposition hit: {Engine.TRANSPOSITION_HITS}")

    print ("SEE TEST")
    board.board = [
        ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
        ['p', '.', 'p', '.', 'p', 'p', 'p', 'p'],
        ['.', '.', '.', '.', '.', '.', '.', '.'],
        ['.', '.', 'n', '.', '.', '.', '.', '.'],
        ['.', 'P', '.', '.', '.', '.', '.', '.'],
        ['.', '.', '.', '.', '.', '.', '.', '.'],
        ['P', 'P', '.', '.', 'P', 'P', 'P', 'P'],
        ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
    ]

    board.white_to_move = True
    board.Print_Board()

    from_pos = (5 - 1, 1)
    to_pos = (4 - 1, 2)
    move = Move(start=from_pos, end=to_pos, piece_moved='P', piece_captured='n')

    score = Engine.Static_Exchange_Evaluation(board, move)
    print(f"SEE for {move}: {score}")
