def next_question_index(current_index, question_count, waiting_for_host):
    """Advance only after the current question's result has been published."""
    if not waiting_for_host or current_index >= question_count:
        return None
    return current_index + 1
