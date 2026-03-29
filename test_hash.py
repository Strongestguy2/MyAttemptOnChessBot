
from Board import Board
from Zobrist import hash_board
import random

def test_hash_consistency():
    board = Board()
    for _ in range(100):
        moves = board.Generate_Legal_Moves()
        if not moves:
            break
        move = random.choice(moves)
        
        pre_hash = board.zobrist_key
        board_hash_pre = hash_board(board)
        assert pre_hash == board_hash_pre, "Hash mismatch before move!"
        
        board.Make_Move(move)
        
        post_hash = board.zobrist_key
        board_hash_post = hash_board(board)
        assert post_hash == board_hash_post, f"Hash mismatch after move! {move}"
        
        board.Undo_Move()
        
        undo_hash = board.zobrist_key
        assert undo_hash == pre_hash, "Hash mismatch after undo!"
        assert undo_hash == hash_board(board), "Hash mismatch after undo and hash_board!"
    
    print("Hash consistency test passed 100 random moves.")
    
if __name__ == "__main__":
    test_hash_consistency()


