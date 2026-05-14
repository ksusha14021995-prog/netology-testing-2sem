"""Task manager service — original homework source, instrumented with @logged."""
import datetime

from middleware import logged

# Упрощенная «база» задач
TASKS_DB: dict[int, dict] = {}


@logged("task_manager")
def create_task(title: str, user_id: int, due_date: datetime.date) -> dict:
    """
    Создает новую задачу и сохраняет ее в TASKS_DB.
    Возвращает словарь с данными о задаче.
    Генерирует ValueError, если title пустой или дата просрочена.
    """
    if not title:
        raise ValueError("Task title cannot be empty.")
    if due_date < datetime.date.today():
        raise ValueError("Due date cannot be in the past.")

    task_id = len(TASKS_DB) + 1
    task_data = {
        "task_id": task_id,
        "title": title,
        "user_id": user_id,
        "due_date": due_date,
        "created_at": datetime.datetime.now(),
        "completed": False,
    }
    TASKS_DB[task_id] = task_data
    return task_data


@logged("task_manager")
def complete_task(task_id: int) -> dict:
    """
    Отмечает задачу как завершенную.
    Поднимает KeyError, если такой задачи нет.
    """
    if task_id not in TASKS_DB:
        raise KeyError(f"Task with id={task_id} not found.")

    task_data = TASKS_DB[task_id]
    task_data["completed"] = True
    return task_data


if __name__ == "__main__":
    new_task = create_task("Finish project", user_id=101, due_date=datetime.date(2026, 8, 1))
    print("Created task:", new_task)

    updated_task = complete_task(new_task["task_id"])
    print("Updated (completed) task:", updated_task)
