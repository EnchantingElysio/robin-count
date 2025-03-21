import math

def get_progress_bar(goal: int, total: int, num_squares: int = 10) -> str:
    progress = int(total/goal) * 100
    # Assume total = 135 and goal = 300
    # progress = 45
    # ⬛⬛⬛⬛◼️▫️▫️▫️▫️
    
    whole_squares: int = progress // num_squares      # 4
    partial_squares: int = progress % num_squares     # 5
    empty_squares: int = num_squares - math.ceil(progress / num_squares)
    

    progress_bar_string = ""

    if whole_squares > num_squares:
        for x in range(num_squares):
            progress_bar_string += ":yellow_square:" # green?
        return progress_bar_string

    for x in range(whole_squares):
        progress_bar_string += ":black_large_square:"

    if partial_squares > 5:
        progress_bar_string += ":black_medium_square:"
    elif partial_squares == 5:
        progress_bar_string += ":black_medium_small_sqare:"
    elif partial_squares < 5 and partial_squares > 0:
        progress_bar_string += ":black_small_square:"

    for x in range(empty_squares):
        progress_bar_string += ":white_small_square:"

    return progress_bar_string