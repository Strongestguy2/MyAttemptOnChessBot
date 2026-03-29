from Board import Board
from Engine import Find_Best_Move as Best_Move

def self_play_step_by_step(depth=3, max_moves=100):
    board = Board()
    print("Initial Position:")
    board.Print_Board()

    move_num = 0
    while move_num < max_moves:
        command = input("Type 'go' to make the next move (or 'exit' to quit): ").strip().lower()
        if command == "exit":
            print("Exiting self-play.")
            break
        if command != "go":
            continue

        if board.Is_Fifty_Move_Rule():
            print("Fifty-move rule reached. Game drawn.")
            break

        if board.Is_Threefold_Repetition():
            print("Threefold repetition reached. Game drawn.")
            break

        legal_moves = board.Generate_Legal_Moves()
        if not legal_moves:
            if board.Is_King_In_Check():
                print("Checkmate!")
            else:
                print("Stalemate!")
            break

        best_move = Best_Move(board, max_depth=depth)
        if best_move is None:
            print("No move returned. Possibly stalemate or bug.")
            break

        print(f"\nMove {move_num + 1}: {'White' if board.white_to_move else 'Black'} plays {best_move}")
        board.Make_Move(best_move)
        board.Print_Board()

        move_num += 1

    print("\nGame complete.")

if __name__ == "__main__":
    self_play_step_by_step(depth=3)
