from aiogram.fsm.state import State, StatesGroup

class Test(StatesGroup):
    """Состояния для прохождения теста"""
    in_progress = State()

class AdminContent(StatesGroup):
    """Состояния для управления контентом админом"""
    viewing_block = State()
    waiting_for_title = State()
    waiting_for_text = State()
    waiting_for_video = State()
    waiting_for_pdf = State()
    waiting_for_question_text = State()
    editing_question = State()