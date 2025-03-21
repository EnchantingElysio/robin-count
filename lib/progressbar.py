import math

def get_progress_bar(goal: int, total: int, num_squares: int = 10) -> str:
    progress = int(total/goal * 100)
    
    whole_squares: int = progress // num_squares
    partial_squares: int = progress % num_squares
    empty_squares: int = num_squares - math.ceil(progress / num_squares)

    progress_bar_string = ""

    if whole_squares >= num_squares:
        for x in range(num_squares):
            progress_bar_string += "🟨"
        return progress_bar_string

    for x in range(whole_squares):
        progress_bar_string += "⬛"

    if partial_squares > 5:
        progress_bar_string += "◼️"
    elif partial_squares == 5:
        progress_bar_string += "◾"

    elif partial_squares < 5 and partial_squares > 0:
        progress_bar_string += "▪️"

    for x in range(empty_squares):
        progress_bar_string += "▫️"

    return progress_bar_string