from keyboards import ACHIEVEMENTS
from db import get_total_completed_quizzes, get_perfect_quizzes_count


def get_user_achievements(user_id: int) -> list[dict]:
    total_quizzes = get_total_completed_quizzes(user_id)
    perfect_quizzes = get_perfect_quizzes_count(user_id)

    result = []

    result.append({
        "key": "first_quiz",
        "completed": total_quizzes >= 1,
        **ACHIEVEMENTS["first_quiz"]
    })

    result.append({
        "key": "quiz_master",
        "completed": total_quizzes >= 10,
        **ACHIEVEMENTS["quiz_master"]
    })

    result.append({
        "key": "perfect_quiz",
        "completed": perfect_quizzes >= 1,
        **ACHIEVEMENTS["perfect_quiz"]
    })

    return result